#!/usr/bin/env python3
"""
NCS Plant Simulator - Inverted Pendulum and Unstable Systems
Supports network delays, packet loss, and sensor/actuator attacks
"""

import os
import json
import time
import threading
import numpy as np
from scipy.integrate import odeint
import paho.mqtt.client as mqtt
import random

class PlantSimulator:
    def __init__(self):
        # Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt-broker')
        self.plant_type = os.getenv('PLANT_TYPE', 'pendulum')
        self.plant_id = os.getenv('PLANT_ID', 'plant1')
        
        # Simulation parameters
        self.dt = 0.001  # 1ms integration step
        self.publish_dt = 0.01  # 10ms publish rate
        
        # Plant state
        if self.plant_type == 'pendulum':
            # [cart_position, cart_velocity, pendulum_angle, pendulum_angular_velocity]
            self.state = np.array([0.1, 0.0, 0.2, 0.0])  # Initial disturbance
            self.control_input = 0.0
        elif self.plant_type == 'unstable':
            # Second-order unstable system: x'' - 2*x' + x = u
            self.state = np.array([0.1, 0.05])  # [position, velocity]
            self.control_input = 0.0
            
        # Network effects simulation
        self.network_delay = 0.0  # seconds
        self.packet_loss_rate = 0.0  # 0-1
        self.jitter_std = 0.0  # seconds
        
        # Attack simulation
        self.sensor_attack = False
        self.actuator_attack = False
        self.attack_bias = 0.0
        self.attack_noise = 0.0
        
        # Delayed control buffer (for network delay simulation)
        self.control_buffer = []
        
        # Communication
        self.setup_mqtt()
        
        # Simulation threads
        self.sim_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.pub_thread = threading.Thread(target=self.publish_loop, daemon=True)
        
        self.sim_thread.start()
        self.pub_thread.start()
        
        print(f"Plant {self.plant_id} ({self.plant_type}) initialized")

    def setup_mqtt(self):
        """Setup MQTT communication"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        self.mqtt_client.loop_start()

    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"MQTT connected with result code {rc}")
        client.subscribe("ncs/control/input")
        client.subscribe(f"ncs/plant/{self.plant_id}/network")
        client.subscribe(f"ncs/plant/{self.plant_id}/attack")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if 'control/input' in msg.topic:
                # Apply network delay and jitter
                delay = self.network_delay + np.random.normal(0, self.jitter_std)
                delay = max(0, delay)  # No negative delay
                
                # Simulate packet loss
                if random.random() > self.packet_loss_rate:
                    # Schedule delayed control input
                    arrival_time = time.time() + delay
                    control_value = payload['control_input']
                    
                    # Apply actuator attack
                    if self.actuator_attack:
                        control_value += self.attack_bias + np.random.normal(0, self.attack_noise)
                    
                    self.control_buffer.append((arrival_time, control_value))
                    
            elif 'network' in msg.topic:
                # Network configuration
                self.network_delay = payload.get('delay', 0.0)
                self.packet_loss_rate = payload.get('loss_rate', 0.0)
                self.jitter_std = payload.get('jitter_std', 0.0)
                print(f"Network config updated: delay={self.network_delay}s, loss={self.packet_loss_rate}, jitter={self.jitter_std}s")
                
            elif 'attack' in msg.topic:
                # Attack configuration
                self.sensor_attack = payload.get('sensor_attack', False)
                self.actuator_attack = payload.get('actuator_attack', False)
                self.attack_bias = payload.get('bias', 0.0)
                self.attack_noise = payload.get('noise', 0.0)
                print(f"Attack config updated: sensor={self.sensor_attack}, actuator={self.actuator_attack}")
                
        except Exception as e:
            print(f"MQTT message error: {e}")

    def process_control_buffer(self):
        """Process delayed control inputs"""
        current_time = time.time()
        
        # Apply control inputs that have arrived
        while self.control_buffer and self.control_buffer[0][0] <= current_time:
            arrival_time, control_value = self.control_buffer.pop(0)
            self.control_input = control_value

    def pendulum_dynamics(self, state, t):
        """Inverted pendulum dynamics"""
        # Parameters
        M = 0.5  # cart mass
        m = 0.2  # pendulum mass  
        l = 0.3  # pendulum length
        g = 9.81  # gravity
        
        x, x_dot, theta, theta_dot = state
        u = self.control_input
        
        # Nonlinear dynamics
        sin_theta = np.sin(theta)
        cos_theta = np.cos(theta)
        
        denominator = M + m - m * cos_theta**2
        
        x_ddot = (u + m * l * theta_dot**2 * sin_theta - m * g * sin_theta * cos_theta) / denominator
        theta_ddot = (g * sin_theta - x_ddot * cos_theta) / l
        
        return [x_dot, x_ddot, theta_dot, theta_ddot]

    def unstable_dynamics(self, state, t):
        """Second-order unstable system dynamics"""
        x, x_dot = state
        u = self.control_input
        
        # x'' - 2*x' + x = u (unstable poles at 1 ± 0j)
        x_ddot = 2 * x_dot - x + u
        
        return [x_dot, x_ddot]

    def simulation_loop(self):
        """Main simulation loop"""
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = current_time - last_time
            
            if dt >= self.dt:
                # Process delayed control inputs
                self.process_control_buffer()
                
                # Integrate dynamics
                if self.plant_type == 'pendulum':
                    self.state = odeint(self.pendulum_dynamics, self.state, [0, self.dt])[-1]
                elif self.plant_type == 'unstable':
                    self.state = odeint(self.unstable_dynamics, self.state, [0, self.dt])[-1]
                
                last_time = current_time
            
            time.sleep(0.0001)  # 0.1ms resolution

    def publish_loop(self):
        """Publish plant state"""
        last_time = time.time()
        
        while True:
            current_time = time.time()
            dt = current_time - last_time
            
            if dt >= self.publish_dt:
                # Get current state
                state_to_publish = self.state.copy()
                
                # Apply sensor attack
                if self.sensor_attack:
                    if self.plant_type == 'pendulum':
                        # Attack cart position and pendulum angle
                        state_to_publish[0] += self.attack_bias + np.random.normal(0, self.attack_noise)
                        state_to_publish[2] += self.attack_bias + np.random.normal(0, self.attack_noise)
                    elif self.plant_type == 'unstable':
                        # Attack position measurement
                        state_to_publish[0] += self.attack_bias + np.random.normal(0, self.attack_noise)
                
                # Prepare payload
                payload = {
                    'plant_id': self.plant_id,
                    'plant_type': self.plant_type,
                    'state': state_to_publish.tolist(),
                    'control_input': float(self.control_input),
                    'timestamp': current_time,
                    'network_effects': {
                        'delay': self.network_delay,
                        'loss_rate': self.packet_loss_rate,
                        'jitter_std': self.jitter_std
                    },
                    'attacks': {
                        'sensor_attack': self.sensor_attack,
                        'actuator_attack': self.actuator_attack,
                        'bias': self.attack_bias,
                        'noise': self.attack_noise
                    }
                }
                
                # Publish state
                self.mqtt_client.publish(f"ncs/plant/{self.plant_id}/state", json.dumps(payload))
                
                # Compute and publish KPIs
                self.publish_kpis(current_time)
                
                last_time = current_time
            
            time.sleep(0.001)  # 1ms resolution

    def publish_kpis(self, timestamp):
        """Compute and publish plant KPIs"""
        if self.plant_type == 'pendulum':
            # Pendulum KPIs
            cart_pos, cart_vel, pend_angle, pend_vel = self.state
            
            kpis = {
                'plant_id': self.plant_id,
                'stability_margin': 1.0 - min(1.0, abs(pend_angle) / np.pi),  # 0=unstable, 1=stable
                'energy': 0.5 * (cart_vel**2 + pend_vel**2) + 9.81 * 0.3 * (1 - np.cos(pend_angle)),
                'cart_deviation': abs(cart_pos),
                'pendulum_deviation': abs(pend_angle),
                'control_effort': abs(self.control_input),
                'timestamp': timestamp
            }
            
        elif self.plant_type == 'unstable':
            # Unstable system KPIs
            position, velocity = self.state
            
            kpis = {
                'plant_id': self.plant_id,
                'stability_margin': max(0.0, 1.0 - abs(position) / 5.0),  # Unstable if |x| > 5
                'energy': 0.5 * velocity**2 + 0.5 * position**2,
                'position_deviation': abs(position),
                'velocity': abs(velocity),
                'control_effort': abs(self.control_input),
                'timestamp': timestamp
            }
        
        self.mqtt_client.publish(f"ncs/plant/{self.plant_id}/kpis", json.dumps(kpis))

    def get_linearized_model(self):
        """Get linearized model around operating point (for LQR design)"""
        if self.plant_type == 'pendulum':
            # Linearized inverted pendulum (upright position)
            M, m, l, g = 0.5, 0.2, 0.3, 9.81
            
            A = np.array([[0, 1, 0, 0],
                          [0, 0, -m*g/(M+m), 0],
                          [0, 0, 0, 1], 
                          [0, 0, g*(M+m)/(l*(M+m)), 0]])
            
            B = np.array([[0], [1/(M+m)], [0], [-1/(l*(M+m))]])
            
        elif self.plant_type == 'unstable':
            # Second-order unstable system
            A = np.array([[0, 1], [1, 2]])  # Unstable eigenvalues: 1 ± sqrt(2)
            B = np.array([[0], [1]])
            
        C = np.eye(A.shape[0])  # Full state feedback
        D = np.zeros((C.shape[0], B.shape[1]))
        
        return A, B, C, D

if __name__ == '__main__':
    simulator = PlantSimulator()
    
    # Keep the simulator running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Plant {simulator.plant_id} shutting down")
