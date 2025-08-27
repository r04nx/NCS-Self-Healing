#!/usr/bin/env python3
"""
NCS Controller Service - LQR/PID with Runtime Reconfiguration
Supports real-time tuning of gains, sampling period, and control mode
"""

import os
import json
import time
import threading
import numpy as np
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
from scipy import linalg
import control
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class NCSController:
    def __init__(self):
        # Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt-broker')
        self.influx_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.control_type = os.getenv('CONTROL_TYPE', 'lqr')
        
        # Control parameters (runtime tunable)
        self.Ts = float(os.getenv('SAMPLING_PERIOD', 0.01))  # 10ms default
        self.control_active = True
        
        # State space matrices (inverted pendulum example)
        self.A = np.array([[0, 1, 0, 0],
                          [0, 0, -7.35, 0],
                          [0, 0, 0, 1], 
                          [0, 0, 29.43, 0]])
        self.B = np.array([[0], [1.47], [0], [-2.94]])
        self.C = np.array([[1, 0, 0, 0], [0, 0, 1, 0]])
        self.D = np.array([[0], [0]])
        
        # LQR matrices
        self.Q = np.diag([10, 1, 10, 1])  # State penalty
        self.R = np.array([[0.1]])        # Control penalty
        self.K = None
        self.compute_lqr_gains()
        
        # PID parameters
        self.Kp = 50.0
        self.Ki = 0.1
        self.Kd = 5.0
        self.integral_error = 0.0
        self.prev_error = 0.0
        
        # State tracking
        self.plant_state = np.zeros(4)
        self.control_input = 0.0
        self.reference = np.array([0, 0, 0, 0])  # Origin
        self.control_cost = 0.0
        
        # KPIs
        self.settling_time = 0.0
        self.overshoot = 0.0
        self.steady_state_error = 0.0
        
        # Communication
        self.setup_mqtt()
        self.setup_influx()
        
        # Control loop
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()
        
        print(f"Controller initialized: {self.control_type.upper()}, Ts={self.Ts}s")

    def compute_lqr_gains(self):
        """Compute optimal LQR gains"""
        try:
            self.K, S, E = control.lqr(self.A, self.B, self.Q, self.R)
            print(f"LQR gains updated: K={self.K.flatten()}")
        except Exception as e:
            print(f"LQR computation failed: {e}")
            self.K = np.array([[1, 0.5, 10, 2]])  # Fallback gains

    def setup_mqtt(self):
        """Setup MQTT communication"""
        self.mqtt_client = mqtt.Client(client_id="", protocol=mqtt.MQTTv311)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        self.mqtt_client.loop_start()

    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"MQTT connected with result code {rc}")
        client.subscribe("ncs/plant/+/state")
        client.subscribe("ncs/agent/commands")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            if 'plant' in msg.topic and 'state' in msg.topic:
                # Update plant state
                self.plant_state = np.array(payload['state'])
                
            elif 'agent/commands' in msg.topic:
                # Agent control commands
                self.handle_agent_command(payload)
                
        except Exception as e:
            print(f"MQTT message error: {e}")

    def handle_agent_command(self, command):
        """Handle commands from agents"""
        if 'sampling_period' in command:
            self.set_sampling_period(command['sampling_period'])
        if 'lqr_gains' in command:
            self.set_lqr_gains(command['lqr_gains'])
        if 'control_active' in command:
            self.control_active = command['control_active']

    def setup_influx(self):
        """Setup InfluxDB client"""
        self.influx_client = InfluxDBClient(
            url=self.influx_url,
            token="ncs-research-token-2024",
            org="ncs-lab"
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def control_loop(self):
        """Main control loop"""
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = current_time - last_time
            
            if dt >= self.Ts and self.control_active:
                # Compute control input
                if self.control_type == 'lqr':
                    error = self.plant_state - self.reference
                    self.control_input = -np.dot(self.K, error)[0]
                elif self.control_type == 'pid':
                    self.control_input = self.compute_pid()
                
                # Apply control limits
                self.control_input = np.clip(self.control_input, -10, 10)
                
                # Publish control
                self.publish_control()
                
                # Compute KPIs
                self.compute_kpis()
                
                # Log to InfluxDB
                self.log_telemetry()
                
                last_time = current_time
            
            time.sleep(0.001)  # 1ms resolution

    def compute_pid(self):
        """PID controller implementation"""
        error = self.plant_state[0]  # Position error
        
        # Proportional
        p_term = self.Kp * error
        
        # Integral
        self.integral_error += error * self.Ts
        i_term = self.Ki * self.integral_error
        
        # Derivative
        d_term = self.Kd * (error - self.prev_error) / self.Ts
        self.prev_error = error
        
        return p_term + i_term + d_term

    def compute_kpis(self):
        """Compute control performance KPIs"""
        # Control cost (LQR)
        x = self.plant_state - self.reference
        u = self.control_input
        self.control_cost = np.dot(x.T, np.dot(self.Q, x)) + self.R[0,0] * u**2
        
        # Settling time (simplified)
        if np.linalg.norm(x) < 0.05:  # Within 5% of reference
            self.settling_time = 0.0
        else:
            self.settling_time += self.Ts
            
        # Overshoot
        self.overshoot = max(0, abs(self.plant_state[0]) - 1.0)
        
        # Steady state error
        self.steady_state_error = abs(self.plant_state[0] - self.reference[0])

    def publish_control(self):
        """Publish control input to plant"""
        payload = {
            'control_input': float(self.control_input),
            'timestamp': time.time(),
            'controller_type': self.control_type,
            'gains': self.K.tolist() if self.K is not None else [self.Kp, self.Ki, self.Kd]
        }
        self.mqtt_client.publish("ncs/control/input", json.dumps(payload))

    def log_telemetry(self):
        """Log telemetry to InfluxDB"""
        points = [
            Point("control_kpis")
            .field("control_cost", self.control_cost)
            .field("settling_time", self.settling_time) 
            .field("overshoot", self.overshoot)
            .field("steady_state_error", self.steady_state_error)
            .field("control_input", self.control_input)
            .field("sampling_period", self.Ts)
            .time(int(time.time() * 1000000000)),
            
            Point("plant_state")
            .field("position", self.plant_state[0])
            .field("velocity", self.plant_state[1])
            .field("angle", self.plant_state[2])
            .field("angular_velocity", self.plant_state[3])
            .time(int(time.time() * 1000000000))
        ]
        
        try:
            self.write_api.write(bucket="control-kpis", record=points)
        except Exception as e:
            print(f"InfluxDB write error: {e}")

    # REST API Methods
    def set_sampling_period(self, ts):
        """Set sampling period"""
        self.Ts = max(0.001, min(0.1, float(ts)))  # Clamp between 1ms-100ms
        print(f"Sampling period updated: {self.Ts}s")
        return {"status": "success", "Ts": self.Ts}

    def set_lqr_gains(self, gains):
        """Set LQR gains manually"""
        if len(gains) == 4:
            self.K = np.array([gains])
            print(f"LQR gains manually set: {self.K}")
            return {"status": "success", "K": self.K.tolist()}
        return {"status": "error", "message": "Invalid gains dimension"}

    def set_lqr_weights(self, q_diag, r_val):
        """Set LQR weight matrices and recompute gains"""
        self.Q = np.diag(q_diag)
        self.R = np.array([[r_val]])
        self.compute_lqr_gains()
        return {"status": "success", "Q": q_diag, "R": r_val, "K": self.K.tolist()}

    def set_pid_params(self, kp, ki, kd):
        """Set PID parameters"""
        self.Kp = float(kp)
        self.Ki = float(ki)
        self.Kd = float(kd)
        self.integral_error = 0.0  # Reset integral
        return {"status": "success", "Kp": self.Kp, "Ki": self.Ki, "Kd": self.Kd}

    def get_status(self):
        """Get controller status"""
        return {
            "control_type": self.control_type,
            "sampling_period": self.Ts,
            "active": self.control_active,
            "lqr_gains": self.K.tolist() if self.K is not None else None,
            "pid_params": {"Kp": self.Kp, "Ki": self.Ki, "Kd": self.Kd},
            "plant_state": self.plant_state.tolist(),
            "control_input": float(self.control_input),
            "kpis": {
                "control_cost": float(self.control_cost),
                "settling_time": float(self.settling_time),
                "overshoot": float(self.overshoot),
                "steady_state_error": float(self.steady_state_error)
            }
        }

# Flask REST API
app = Flask(__name__)
controller = NCSController()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(controller.get_status())

@app.route('/set_sampling_period', methods=['POST'])
def set_sampling_period():
    ts = request.json.get('Ts', controller.Ts)
    result = controller.set_sampling_period(ts)
    return jsonify(result)

@app.route('/set_lqr_gains', methods=['POST'])
def set_lqr_gains():
    gains = request.json.get('K', [])
    result = controller.set_lqr_gains(gains)
    return jsonify(result)

@app.route('/set_lqr_weights', methods=['POST'])
def set_lqr_weights():
    q = request.json.get('Q', [10, 1, 10, 1])
    r = request.json.get('R', 0.1)
    result = controller.set_lqr_weights(q, r)
    return jsonify(result)

@app.route('/set_pid_params', methods=['POST'])
def set_pid_params():
    kp = request.json.get('Kp', controller.Kp)
    ki = request.json.get('Ki', controller.Ki) 
    kd = request.json.get('Kd', controller.Kd)
    result = controller.set_pid_params(kp, ki, kd)
    return jsonify(result)

@app.route('/switch_mode', methods=['POST'])
def switch_mode():
    mode = request.json.get('mode', 'lqr')
    if mode in ['lqr', 'pid']:
        controller.control_type = mode
        return jsonify({"status": "success", "mode": mode})
    return jsonify({"status": "error", "message": "Invalid mode"})

@app.route('/activate', methods=['POST'])
def activate():
    active = request.json.get('active', True)
    controller.control_active = bool(active)
    return jsonify({"status": "success", "active": controller.control_active})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
