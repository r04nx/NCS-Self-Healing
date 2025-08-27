#!/usr/bin/env python3
"""
NCS Multi-Agent Coordinator - Reflex/Bandit/MARL for Control-Network Co-Design
Automatically adapts control parameters and network configuration for optimal stability
"""

import os
import json
import time
import threading
import numpy as np
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from collections import deque
import pickle

# Agent implementations
from reflex.reflex_agent import ReflexAgent
from bandit.contextual_bandit import ContextualBanditAgent
# from marl.marl_agent import MARLAgent  # TODO: Implement MARL

class AgentCoordinator:
    def __init__(self):
        # Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt-broker')
        self.influx_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.controller_url = os.getenv('CONTROLLER_URL', 'http://controller:5001')
        self.agent_type = os.getenv('AGENT_TYPE', 'reflex')
        
        # State tracking
        self.control_kpis = {}
        self.network_kpis = {}
        self.plant_states = {}
        self.system_state = np.zeros(10)  # Combined state vector
        
        # Action history
        self.action_history = deque(maxlen=1000)
        self.reward_history = deque(maxlen=1000)
        
        # Agent instances
        self.agents = {}
        self.initialize_agents()
        
        # Performance tracking
        self.mttr_tracker = MTTRTracker()
        self.recovery_active = False
        self.disturbance_start_time = None
        
        # Communication
        self.setup_mqtt()
        self.setup_influx()
        
        # Agent decision loop
        self.decision_thread = threading.Thread(target=self.decision_loop, daemon=True)
        self.decision_thread.start()
        
        print(f"Agent Coordinator initialized with {self.agent_type} agent")

    def initialize_agents(self):
        """Initialize different types of agents"""
        if self.agent_type in ['reflex', 'all']:
            self.agents['reflex'] = ReflexAgent()
            
        if self.agent_type in ['bandit', 'all']:
            self.agents['bandit'] = ContextualBanditAgent(
                n_actions=12,  # Action space size
                context_dim=10,  # State space size
                alpha=0.1
            )
            
        # if self.agent_type in ['marl', 'all']:
        #     self.agents['marl'] = MARLAgent()
        
        print(f"Initialized agents: {list(self.agents.keys())}")

    def setup_mqtt(self):
        """Setup MQTT communication"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        self.mqtt_client.loop_start()

    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"Agent MQTT connected with result code {rc}")
        client.subscribe("ncs/plant/+/state")
        client.subscribe("ncs/plant/+/kpis")
        client.subscribe("ncs/control/kpis")
        client.subscribe("ncs/network/kpis")
        client.subscribe("ncs/disturbance/+")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if 'plant' in msg.topic and 'state' in msg.topic:
                plant_id = msg.topic.split('/')[2]
                self.plant_states[plant_id] = payload
                
            elif 'plant' in msg.topic and 'kpis' in msg.topic:
                plant_id = msg.topic.split('/')[2]
                self.update_plant_kpis(plant_id, payload)
                
            elif 'control/kpis' in msg.topic:
                self.control_kpis = payload
                
            elif 'network/kpis' in msg.topic:
                self.network_kpis = payload
                
            elif 'disturbance' in msg.topic:
                self.handle_disturbance_event(payload)
                
        except Exception as e:
            print(f"Agent MQTT message error: {e}")

    def update_plant_kpis(self, plant_id, kpis):
        """Update plant KPIs and check for instability"""
        stability_margin = kpis.get('stability_margin', 1.0)
        
        # Detect instability (start recovery timer)
        if stability_margin < 0.5 and not self.recovery_active:
            self.recovery_active = True
            self.disturbance_start_time = time.time()
            print(f"🚨 Instability detected in {plant_id}! Starting recovery...")
            
        # Detect recovery (stop timer)
        elif stability_margin > 0.8 and self.recovery_active:
            recovery_time = time.time() - self.disturbance_start_time
            self.mttr_tracker.record_recovery(recovery_time)
            self.recovery_active = False
            print(f"✅ Recovery achieved in {recovery_time:.2f}s (MTTR: {self.mttr_tracker.get_mttr():.2f}s)")

    def handle_disturbance_event(self, event):
        """Handle disturbance/attack events"""
        event_type = event.get('type', 'unknown')
        if event_type in ['start', 'attack_start']:
            self.recovery_active = True
            self.disturbance_start_time = time.time()
            print(f"🎯 Disturbance event: {event_type}")

    def setup_influx(self):
        """Setup InfluxDB client"""
        self.influx_client = InfluxDBClient(
            url=self.influx_url,
            token="ncs-research-token-2024",
            org="ncs-lab"
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def get_system_state(self):
        """Construct system state vector for agents"""
        state = np.zeros(10)
        
        # Control KPIs [0:4]
        if self.control_kpis:
            state[0] = self.control_kpis.get('control_cost', 0.0)
            state[1] = self.control_kpis.get('settling_time', 0.0)
            state[2] = self.control_kpis.get('overshoot', 0.0)
            state[3] = self.control_kpis.get('steady_state_error', 0.0)
            
        # Network KPIs [4:7]
        if self.network_kpis:
            state[4] = self.network_kpis.get('latency_p95', 0.0) * 1000  # Convert to ms
            state[5] = self.network_kpis.get('jitter_std', 0.0) * 1000
            state[6] = self.network_kpis.get('loss_rate', 0.0)
            
        # Plant KPIs [7:10]
        if self.plant_states:
            for plant_id, plant_data in self.plant_states.items():
                if 'state' in plant_data:
                    # Use first plant's position and angle as system indicators
                    plant_state = np.array(plant_data['state'])
                    if len(plant_state) >= 4:  # Pendulum
                        state[7] = plant_state[0]  # Cart position
                        state[8] = plant_state[2]  # Pendulum angle
                    elif len(plant_state) >= 2:  # Unstable system
                        state[7] = plant_state[0]  # Position
                        state[8] = plant_state[1]  # Velocity
                    break
                    
        # System stability indicator [9]
        stability_sum = 0.0
        for plant_id, plant_data in self.plant_states.items():
            if 'stability_margin' in plant_data:
                stability_sum += plant_data['stability_margin']
        state[9] = stability_sum / max(1, len(self.plant_states))
        
        return state

    def decision_loop(self):
        """Main agent decision loop"""
        last_decision_time = time.time()
        decision_interval = 1.0  # 1 second decision interval
        
        while True:
            current_time = time.time()
            
            if current_time - last_decision_time >= decision_interval:
                # Get current system state
                state = self.get_system_state()
                self.system_state = state
                
                # Make decisions with active agents
                actions_taken = []
                
                for agent_name, agent in self.agents.items():
                    if self.should_agent_act(agent_name, state):
                        try:
                            action = agent.select_action(state)
                            if action is not None:
                                self.execute_action(action, agent_name)
                                actions_taken.append((agent_name, action))
                        except Exception as e:
                            print(f"Agent {agent_name} error: {e}")
                
                # Log agent decisions
                if actions_taken:
                    self.log_agent_decision(actions_taken, state)
                    
                # Compute reward and train agents
                self.update_agents(state)
                
                last_decision_time = current_time
                
            time.sleep(0.1)  # 100ms resolution

    def should_agent_act(self, agent_name, state):
        """Determine if agent should act based on state"""
        # Always allow reflex agent (rule-based)
        if agent_name == 'reflex':
            return True
            
        # Bandit and MARL agents act on disturbances or poor performance
        instability = state[9] < 0.7  # Low stability margin
        high_error = state[3] > 0.1   # High steady state error
        high_latency = state[4] > 50.0  # >50ms latency
        high_jitter = state[5] > 20.0   # >20ms jitter
        
        return instability or high_error or high_latency or high_jitter

    def execute_action(self, action, agent_name):
        """Execute agent action"""
        try:
            if isinstance(action, dict):
                action_type = action.get('type', 'unknown')
                
                if action_type == 'control_adjust':
                    self.execute_control_action(action)
                elif action_type == 'network_adjust':
                    self.execute_network_action(action)
                elif action_type == 'combined':
                    if 'control' in action:
                        self.execute_control_action(action['control'])
                    if 'network' in action:
                        self.execute_network_action(action['network'])
                        
            elif isinstance(action, int):
                # Discrete action from bandit
                self.execute_discrete_action(action)
                
        except Exception as e:
            print(f"Action execution error: {e}")

    def execute_control_action(self, action):
        """Execute control parameter adjustments"""
        try:
            if 'sampling_period' in action:
                response = requests.post(
                    f"{self.controller_url}/set_sampling_period",
                    json={"Ts": action['sampling_period']},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"🎛️ Adjusted sampling period: {action['sampling_period']}")
                    
            if 'lqr_weights' in action:
                weights = action['lqr_weights']
                response = requests.post(
                    f"{self.controller_url}/set_lqr_weights",
                    json={"Q": weights['Q'], "R": weights['R']},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"🎛️ Adjusted LQR weights: Q={weights['Q']}, R={weights['R']}")
                    
            if 'mode_switch' in action:
                mode = action['mode_switch']
                response = requests.post(
                    f"{self.controller_url}/switch_mode",
                    json={"mode": mode},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"🎛️ Switched controller mode: {mode}")
                    
        except Exception as e:
            print(f"Control action error: {e}")

    def execute_network_action(self, action):
        """Execute network configuration changes"""
        # Publish network configuration to plant containers
        try:
            if 'priority' in action:
                # DSCP marking for control traffic
                self.mqtt_client.publish(
                    "ncs/network/config",
                    json.dumps({"action": "set_dscp", "dscp": action['priority']})
                )
                print(f"🌐 Set DSCP priority: {action['priority']}")
                
            if 'admission_control' in action:
                # Block non-critical traffic
                self.mqtt_client.publish(
                    "ncs/network/config", 
                    json.dumps({"action": "admission_control", "enabled": action['admission_control']})
                )
                print(f"🌐 Admission control: {action['admission_control']}")
                
            if 'redundancy' in action:
                # Enable packet duplication
                self.mqtt_client.publish(
                    "ncs/network/config",
                    json.dumps({"action": "redundancy", "enabled": action['redundancy']})
                )
                print(f"🌐 Packet redundancy: {action['redundancy']}")
                
        except Exception as e:
            print(f"Network action error: {e}")

    def execute_discrete_action(self, action_id):
        """Execute discrete action from action space"""
        # Action space mapping (12 discrete actions)
        actions = {
            0: {"type": "control_adjust", "sampling_period": 0.005},  # Faster sampling
            1: {"type": "control_adjust", "sampling_period": 0.02},   # Slower sampling
            2: {"type": "control_adjust", "lqr_weights": {"Q": [20, 2, 20, 2], "R": 0.05}},  # Higher Q
            3: {"type": "control_adjust", "lqr_weights": {"Q": [5, 0.5, 5, 0.5], "R": 0.2}}, # Lower Q
            4: {"type": "network_adjust", "priority": 46},  # High priority DSCP
            5: {"type": "network_adjust", "priority": 0},   # Normal priority
            6: {"type": "network_adjust", "admission_control": True},  # Block non-critical
            7: {"type": "network_adjust", "admission_control": False}, # Allow all traffic
            8: {"type": "network_adjust", "redundancy": True},   # Enable duplication
            9: {"type": "network_adjust", "redundancy": False},  # Disable duplication
            10: {"type": "control_adjust", "mode_switch": "pid"},  # Switch to PID
            11: {"type": "control_adjust", "mode_switch": "lqr"},  # Switch to LQR
        }
        
        if action_id in actions:
            self.execute_action(actions[action_id], "bandit")

    def compute_reward(self, prev_state, current_state, actions_taken):
        """Compute reward for agents based on state improvement"""
        # Stability improvement
        stability_reward = (current_state[9] - prev_state[9]) * 10.0
        
        # Control performance improvement  
        control_reward = -(current_state[0] - prev_state[0])  # Lower cost is better
        error_reward = -(current_state[3] - prev_state[3])    # Lower error is better
        
        # Network performance improvement
        latency_reward = -(current_state[4] - prev_state[4]) * 0.01  # Lower latency
        jitter_reward = -(current_state[5] - prev_state[5]) * 0.01   # Lower jitter
        
        # Action cost penalty
        action_penalty = -len(actions_taken) * 0.1
        
        total_reward = stability_reward + control_reward + error_reward + latency_reward + jitter_reward + action_penalty
        
        return total_reward

    def update_agents(self, current_state):
        """Update agents with reward feedback"""
        if len(self.reward_history) > 0 and len(self.action_history) > 0:
            prev_state = self.reward_history[-1] if self.reward_history else current_state
            
            # Get last actions
            last_actions = self.action_history[-1] if self.action_history else []
            
            # Compute reward
            reward = self.compute_reward(prev_state, current_state, last_actions)
            self.reward_history.append(current_state)
            
            # Train bandit agent
            if 'bandit' in self.agents and len(last_actions) > 0:
                for agent_name, action in last_actions:
                    if agent_name == 'bandit' and isinstance(action, int):
                        self.agents['bandit'].update(prev_state, action, reward)

    def log_agent_decision(self, actions_taken, state):
        """Log agent decisions to InfluxDB"""
        self.action_history.append(actions_taken)
        
        try:
            points = [
                Point("agent_decisions")
                .field("num_actions", len(actions_taken))
                .field("stability_margin", state[9])
                .field("control_cost", state[0])
                .field("latency_p95", state[4])
                .field("recovery_active", self.recovery_active)
                .time(int(time.time() * 1000000000))
            ]
            
            # Log individual actions
            for i, (agent_name, action) in enumerate(actions_taken):
                points.append(
                    Point("agent_actions")
                    .tag("agent", agent_name)
                    .field("action", str(action)[:100])  # Truncate long actions
                    .time(int(time.time() * 1000000000))
                )
            
            self.write_api.write(bucket="control-kpis", record=points)
            
        except Exception as e:
            print(f"Agent logging error: {e}")

    def get_status(self):
        """Get agent coordinator status"""
        return {
            "active_agents": list(self.agents.keys()),
            "system_state": self.system_state.tolist(),
            "recovery_active": self.recovery_active,
            "mttr": self.mttr_tracker.get_mttr(),
            "num_recoveries": len(self.mttr_tracker.recovery_times),
            "action_history_size": len(self.action_history),
            "control_kpis": self.control_kpis,
            "network_kpis": self.network_kpis,
            "plant_count": len(self.plant_states)
        }

class MTTRTracker:
    """Mean Time To Recovery tracker"""
    def __init__(self):
        self.recovery_times = deque(maxlen=100)  # Keep last 100 recoveries
        
    def record_recovery(self, recovery_time):
        """Record a recovery time"""
        self.recovery_times.append(recovery_time)
        
    def get_mttr(self):
        """Get mean time to recovery"""
        if not self.recovery_times:
            return 0.0
        return np.mean(self.recovery_times)

# Flask REST API
app = Flask(__name__)
coordinator = AgentCoordinator()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(coordinator.get_status())

@app.route('/switch_agent', methods=['POST'])
def switch_agent():
    agent_type = request.json.get('agent_type', 'reflex')
    if agent_type in ['reflex', 'bandit', 'marl']:
        coordinator.agent_type = agent_type
        return jsonify({"status": "success", "agent_type": agent_type})
    return jsonify({"status": "error", "message": "Invalid agent type"})

@app.route('/inject_disturbance', methods=['POST'])
def inject_disturbance():
    """Manually inject disturbance for testing"""
    event = {
        'type': 'manual_disturbance',
        'timestamp': time.time(),
        'severity': request.json.get('severity', 'medium')
    }
    coordinator.handle_disturbance_event(event)
    return jsonify({"status": "success", "event": event})

@app.route('/reset_metrics', methods=['POST'])
def reset_metrics():
    """Reset MTTR and performance metrics"""
    coordinator.mttr_tracker = MTTRTracker()
    coordinator.action_history.clear()
    coordinator.reward_history.clear()
    return jsonify({"status": "success", "message": "Metrics reset"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
