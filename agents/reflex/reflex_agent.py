#!/usr/bin/env python3
"""
Reflex Agent - Rule-based control and network adaptation
Fast response based on heuristic rules and thresholds
"""

import numpy as np
import time

class ReflexAgent:
    def __init__(self):
        # Thresholds for triggering actions
        self.stability_threshold = 0.7
        self.error_threshold = 0.1
        self.latency_threshold = 50.0  # ms
        self.jitter_threshold = 20.0   # ms
        self.loss_threshold = 0.02     # 2%
        
        # Action cooldowns to prevent oscillation
        self.last_action_time = {}
        self.cooldown_period = 5.0  # 5 seconds
        
        # State history for trend detection
        self.state_history = []
        self.history_length = 10
        
        print("Reflex Agent initialized with rule-based heuristics")

    def select_action(self, state):
        """Select action based on rule-based heuristics"""
        current_time = time.time()
        
        # Update state history
        self.state_history.append(state.copy())
        if len(self.state_history) > self.history_length:
            self.state_history.pop(0)
        
        # Extract state variables
        control_cost = state[0]
        settling_time = state[1] 
        overshoot = state[2]
        steady_state_error = state[3]
        latency_p95 = state[4]  # ms
        jitter_std = state[5]   # ms
        loss_rate = state[6]
        cart_position = state[7]
        pendulum_angle = state[8]
        stability_margin = state[9]
        
        # Rule 1: Critical instability - immediate action
        if stability_margin < 0.3:
            if self._can_act('emergency_stabilize', current_time):
                return {
                    'type': 'combined',
                    'control': {
                        'sampling_period': 0.005,  # Faster sampling
                        'lqr_weights': {'Q': [50, 5, 50, 5], 'R': 0.01}  # Aggressive control
                    },
                    'network': {
                        'priority': 46,  # Highest priority
                        'admission_control': True,  # Block non-critical traffic
                        'redundancy': True  # Enable packet duplication
                    }
                }
        
        # Rule 2: High network latency/jitter - prioritize network actions
        if latency_p95 > self.latency_threshold or jitter_std > self.jitter_threshold:
            if self._can_act('network_optimize', current_time):
                actions = {'type': 'network_adjust', 'priority': 46}
                
                # If jitter is very high, also slow down sampling
                if jitter_std > 50.0:
                    actions = {
                        'type': 'combined',
                        'control': {'sampling_period': 0.02},  # Slower sampling to handle jitter
                        'network': {'priority': 46, 'redundancy': True}
                    }
                    
                return actions
        
        # Rule 3: Packet loss - enable redundancy
        if loss_rate > self.loss_threshold:
            if self._can_act('handle_loss', current_time):
                return {
                    'type': 'network_adjust',
                    'redundancy': True,
                    'priority': 46
                }
        
        # Rule 4: High control cost - adjust LQR weights
        if control_cost > 10.0:
            if self._can_act('reduce_control_effort', current_time):
                return {
                    'type': 'control_adjust',
                    'lqr_weights': {'Q': [5, 0.5, 5, 0.5], 'R': 0.5}  # Lower control effort
                }
        
        # Rule 5: High steady state error - increase control aggressiveness
        if steady_state_error > self.error_threshold:
            if self._can_act('increase_performance', current_time):
                return {
                    'type': 'control_adjust',
                    'lqr_weights': {'Q': [20, 2, 20, 2], 'R': 0.05}  # More aggressive
                }
        
        # Rule 6: Oscillatory behavior detection
        if self._detect_oscillation():
            if self._can_act('dampen_oscillation', current_time):
                return {
                    'type': 'control_adjust',
                    'lqr_weights': {'Q': [10, 5, 10, 5], 'R': 0.1},  # Higher damping
                    'sampling_period': 0.015  # Moderate sampling rate
                }
        
        # Rule 7: System recovering - gradually reduce protection
        if stability_margin > 0.9 and self._is_recovering():
            if self._can_act('reduce_protection', current_time):
                return {
                    'type': 'network_adjust',
                    'admission_control': False,  # Allow all traffic
                    'priority': 0,  # Normal priority
                    'redundancy': False  # Disable duplication
                }
        
        # Rule 8: Switch to PID if LQR is struggling
        if settling_time > 10.0 and stability_margin < 0.6:
            if self._can_act('switch_controller', current_time):
                return {
                    'type': 'control_adjust',
                    'mode_switch': 'pid'
                }
        
        # No action needed
        return None

    def _can_act(self, action_type, current_time):
        """Check if action is allowed (not in cooldown)"""
        if action_type not in self.last_action_time:
            self.last_action_time[action_type] = current_time
            return True
            
        time_since_last = current_time - self.last_action_time[action_type]
        if time_since_last >= self.cooldown_period:
            self.last_action_time[action_type] = current_time
            return True
            
        return False

    def _detect_oscillation(self):
        """Detect oscillatory behavior in state history"""
        if len(self.state_history) < 6:
            return False
            
        # Check pendulum angle oscillation
        angles = [state[8] for state in self.state_history[-6:]]
        
        # Simple oscillation detection: alternating signs
        sign_changes = 0
        for i in range(1, len(angles)):
            if np.sign(angles[i]) != np.sign(angles[i-1]) and abs(angles[i]) > 0.1:
                sign_changes += 1
                
        # If more than 3 sign changes in 6 samples, it's oscillating
        return sign_changes >= 3

    def _is_recovering(self):
        """Check if system is in recovery phase"""
        if len(self.state_history) < 5:
            return False
            
        # Check if stability margin is consistently improving
        recent_stability = [state[9] for state in self.state_history[-5:]]
        
        # Trend detection: is stability generally increasing?
        trend_positive = 0
        for i in range(1, len(recent_stability)):
            if recent_stability[i] > recent_stability[i-1]:
                trend_positive += 1
                
        return trend_positive >= 3

    def get_thresholds(self):
        """Get current thresholds (for tuning/analysis)"""
        return {
            'stability_threshold': self.stability_threshold,
            'error_threshold': self.error_threshold, 
            'latency_threshold': self.latency_threshold,
            'jitter_threshold': self.jitter_threshold,
            'loss_threshold': self.loss_threshold,
            'cooldown_period': self.cooldown_period
        }

    def update_thresholds(self, **kwargs):
        """Update thresholds dynamically"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"Reflex agent threshold updated: {key} = {value}")
