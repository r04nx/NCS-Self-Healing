#!/usr/bin/env python3
"""
Simple NCS Agent for Testing
"""
import json
import time
import threading
import numpy as np
from flask import Flask, request, jsonify

class SimpleAgent:
    def __init__(self):
        self.active_agents = ["reflex"]
        self.system_state = np.random.randn(10) * 0.1  # Small random state
        self.recovery_active = False
        self.mttr = 0.0
        self.num_recoveries = 0
        self.action_history_size = 0
        
        # Start simulation thread
        threading.Thread(target=self.simulation_loop, daemon=True).start()
        
        print("Simple Agent initialized")

    def simulation_loop(self):
        """Simulate agent behavior"""
        while True:
            # Update system state
            self.system_state += np.random.randn(10) * 0.01
            
            # Simulate occasional recovery events
            if np.random.random() < 0.1:  # 10% chance
                if not self.recovery_active:
                    self.recovery_active = True
                    recovery_time = np.random.exponential(15.0)  # Mean 15s recovery
                    threading.Timer(recovery_time, self.complete_recovery).start()
                    
            time.sleep(1)

    def complete_recovery(self):
        """Complete a recovery event"""
        self.recovery_active = False
        self.num_recoveries += 1
        # Update MTTR
        if self.num_recoveries > 0:
            self.mttr = np.random.exponential(12.0)  # Simulated MTTR

    def get_status(self):
        return {
            "active_agents": self.active_agents,
            "system_state": self.system_state.tolist(),
            "recovery_active": self.recovery_active,
            "mttr": float(self.mttr),
            "num_recoveries": self.num_recoveries,
            "action_history_size": self.action_history_size,
            "control_kpis": {
                "control_cost": float(np.random.exponential(2.0)),
                "stability_margin": float(0.8 + 0.1 * np.random.randn())
            },
            "network_kpis": {
                "latency_p95": float(20 + 5 * np.random.randn()),
                "jitter_std": float(5 + 2 * np.random.randn())
            },
            "plant_count": 2
        }

# Flask REST API
app = Flask(__name__)
agent = SimpleAgent()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(agent.get_status())

@app.route('/switch_agent', methods=['POST'])
def switch_agent():
    agent_type = request.json.get('agent_type', 'reflex')
    agent.active_agents = [agent_type]
    return jsonify({"status": "success", "agent_type": agent_type})

@app.route('/inject_disturbance', methods=['POST'])
def inject_disturbance():
    """Manually inject disturbance for testing"""
    agent.recovery_active = True
    threading.Timer(5.0, agent.complete_recovery).start()
    return jsonify({"status": "success", "message": "Disturbance injected"})

@app.route('/reset_metrics', methods=['POST'])
def reset_metrics():
    """Reset metrics"""
    agent.mttr = 0.0
    agent.num_recoveries = 0
    agent.action_history_size = 0
    return jsonify({"status": "success", "message": "Metrics reset"})

if __name__ == '__main__':
    print("🚀 Starting Simple Agent...")
    app.run(host='0.0.0.0', port=5002, debug=False)
