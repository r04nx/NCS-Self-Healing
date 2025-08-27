#!/usr/bin/env python3
"""
Simple NCS Controller for Testing
"""
import os
import json
import time
import threading
import numpy as np
from flask import Flask, request, jsonify

class SimpleController:
    def __init__(self):
        self.Ts = 0.01
        self.control_active = True
        self.control_cost = 0.0
        self.plant_state = np.zeros(4)
        self.control_input = 0.0
        
        print("Simple Controller initialized")

    def get_status(self):
        return {
            "control_type": "lqr",
            "sampling_period": self.Ts,
            "active": self.control_active,
            "plant_state": self.plant_state.tolist(),
            "control_input": float(self.control_input),
            "kpis": {
                "control_cost": float(self.control_cost),
                "settling_time": 3.2,
                "overshoot": 0.1,
                "steady_state_error": 0.05
            }
        }

    def set_sampling_period(self, ts):
        self.Ts = max(0.001, min(0.1, float(ts)))
        return {"status": "success", "Ts": self.Ts}

    def set_lqr_weights(self, q, r):
        return {"status": "success", "Q": q, "R": r}

# Flask REST API
app = Flask(__name__)
controller = SimpleController()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(controller.get_status())

@app.route('/set_sampling_period', methods=['POST'])
def set_sampling_period():
    ts = request.json.get('Ts', controller.Ts)
    result = controller.set_sampling_period(ts)
    return jsonify(result)

@app.route('/set_lqr_weights', methods=['POST'])
def set_lqr_weights():
    q = request.json.get('Q', [10, 1, 10, 1])
    r = request.json.get('R', 0.1)
    result = controller.set_lqr_weights(q, r)
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 Starting Simple Controller...")
    app.run(host='0.0.0.0', port=5001, debug=False)
