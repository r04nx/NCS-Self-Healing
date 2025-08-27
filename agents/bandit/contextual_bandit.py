#!/usr/bin/env python3
"""
Contextual Bandit Agent - Thompson Sampling for Control-Network Co-Design
Learns optimal actions based on system context and reward feedback
"""

import numpy as np
import pickle
import os
from scipy.special import inv
from sklearn.preprocessing import StandardScaler

class ContextualBanditAgent:
    def __init__(self, n_actions=12, context_dim=10, alpha=0.1, lambda_reg=1.0):
        self.n_actions = n_actions
        self.context_dim = context_dim
        self.alpha = alpha  # Learning rate
        self.lambda_reg = lambda_reg  # Regularization
        
        # Thompson Sampling parameters for each action
        # Using linear bandits: reward = theta^T * context + noise
        self.A = [np.eye(context_dim) * lambda_reg for _ in range(n_actions)]  # Covariance matrices
        self.b = [np.zeros(context_dim) for _ in range(n_actions)]  # Reward vectors
        self.theta = [np.zeros(context_dim) for _ in range(n_actions)]  # Parameter estimates
        
        # Action tracking
        self.action_counts = np.zeros(n_actions)
        self.total_reward = 0.0
        self.n_updates = 0
        
        # Context preprocessing
        self.scaler = StandardScaler()
        self.context_buffer = []
        self.buffer_size = 100
        
        # Exploration parameters
        self.epsilon = 0.1  # ε-greedy fallback
        self.min_epsilon = 0.01
        self.epsilon_decay = 0.995
        
        # Model persistence
        self.model_file = "/app/bandit_model.pkl"
        self.load_model()
        
        print(f"Contextual Bandit Agent initialized: {n_actions} actions, {context_dim}D context")

    def preprocess_context(self, context):
        """Preprocess and normalize context vector"""
        context = np.array(context).reshape(1, -1)
        
        # Add to buffer for scaler fitting
        self.context_buffer.append(context.flatten())
        if len(self.context_buffer) > self.buffer_size:
            self.context_buffer.pop(0)
            
        # Fit scaler if enough samples
        if len(self.context_buffer) >= 10:
            try:
                self.scaler.fit(np.array(self.context_buffer))
                context = self.scaler.transform(context)
            except:
                pass  # Use raw context if scaling fails
                
        # Add bias term
        context = np.append(context.flatten(), 1.0)
        
        # Pad/truncate to correct dimension
        if len(context) < self.context_dim:
            context = np.pad(context, (0, self.context_dim - len(context)))
        else:
            context = context[:self.context_dim]
            
        return context

    def select_action(self, state):
        """Select action using Thompson Sampling"""
        context = self.preprocess_context(state)
        
        # ε-greedy exploration fallback
        if np.random.random() < self.epsilon:
            action = np.random.randint(self.n_actions)
            print(f"🎲 Bandit: ε-greedy exploration, action {action}")
            return action
        
        # Thompson Sampling: sample from posterior distributions
        sampled_rewards = []
        
        for a in range(self.n_actions):
            # Compute posterior mean and covariance
            A_inv = np.linalg.inv(self.A[a])
            self.theta[a] = A_inv @ self.b[a]
            
            # Sample from posterior: theta ~ N(theta_hat, alpha^2 * A^-1)
            theta_sample = np.random.multivariate_normal(
                self.theta[a], 
                self.alpha**2 * A_inv
            )
            
            # Compute expected reward
            reward_estimate = context @ theta_sample
            sampled_rewards.append(reward_estimate)
        
        # Select action with highest sampled reward
        action = np.argmax(sampled_rewards)
        self.action_counts[action] += 1
        
        # Decay epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        
        print(f"🧠 Bandit: selected action {action} (est. reward: {sampled_rewards[action]:.3f})")
        return action

    def update(self, context, action, reward):
        """Update bandit parameters with observed reward"""
        context = self.preprocess_context(context)
        
        # Update statistics for selected action
        self.A[action] += np.outer(context, context)
        self.b[action] += reward * context
        
        # Update tracking
        self.total_reward += reward
        self.n_updates += 1
        
        # Periodic model saving
        if self.n_updates % 10 == 0:
            self.save_model()
            
        print(f"🔄 Bandit: updated action {action} with reward {reward:.3f} "
              f"(avg: {self.total_reward/self.n_updates:.3f})")

    def get_action_preferences(self, state):
        """Get action preference scores for analysis"""
        context = self.preprocess_context(state)
        preferences = []
        
        for a in range(self.n_actions):
            A_inv = np.linalg.inv(self.A[a])
            theta_hat = A_inv @ self.b[a]
            
            # Expected reward
            expected_reward = context @ theta_hat
            
            # Confidence (uncertainty)
            confidence = np.sqrt(context @ A_inv @ context)
            
            preferences.append({
                'action': a,
                'expected_reward': float(expected_reward),
                'confidence': float(confidence),
                'count': int(self.action_counts[a])
            })
        
        return sorted(preferences, key=lambda x: x['expected_reward'], reverse=True)

    def get_statistics(self):
        """Get bandit learning statistics"""
        return {
            'total_updates': self.n_updates,
            'total_reward': float(self.total_reward),
            'average_reward': float(self.total_reward / max(1, self.n_updates)),
            'epsilon': float(self.epsilon),
            'action_counts': self.action_counts.tolist(),
            'most_selected': int(np.argmax(self.action_counts)),
            'least_selected': int(np.argmin(self.action_counts))
        }

    def save_model(self):
        """Save bandit model to file"""
        try:
            model_data = {
                'A': self.A,
                'b': self.b,
                'theta': self.theta,
                'action_counts': self.action_counts,
                'total_reward': self.total_reward,
                'n_updates': self.n_updates,
                'epsilon': self.epsilon,
                'scaler': self.scaler if hasattr(self.scaler, 'mean_') else None
            }
            
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
                
        except Exception as e:
            print(f"Bandit model save error: {e}")

    def load_model(self):
        """Load bandit model from file"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.A = model_data.get('A', self.A)
                self.b = model_data.get('b', self.b)
                self.theta = model_data.get('theta', self.theta)
                self.action_counts = model_data.get('action_counts', self.action_counts)
                self.total_reward = model_data.get('total_reward', 0.0)
                self.n_updates = model_data.get('n_updates', 0)
                self.epsilon = model_data.get('epsilon', self.epsilon)
                
                if model_data.get('scaler') is not None:
                    self.scaler = model_data['scaler']
                
                print(f"✅ Bandit model loaded: {self.n_updates} updates, "
                      f"avg reward: {self.total_reward/max(1,self.n_updates):.3f}")
                
            except Exception as e:
                print(f"Bandit model load error: {e}")

    def reset(self):
        """Reset bandit to initial state"""
        self.A = [np.eye(self.context_dim) * self.lambda_reg for _ in range(self.n_actions)]
        self.b = [np.zeros(self.context_dim) for _ in range(self.n_actions)]
        self.theta = [np.zeros(self.context_dim) for _ in range(self.n_actions)]
        self.action_counts = np.zeros(self.n_actions)
        self.total_reward = 0.0
        self.n_updates = 0
        self.epsilon = 0.1
        self.context_buffer = []
        self.scaler = StandardScaler()
        
        # Remove saved model
        if os.path.exists(self.model_file):
            os.remove(self.model_file)
            
        print("🔄 Bandit agent reset to initial state")
