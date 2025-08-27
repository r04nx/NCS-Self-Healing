#!/usr/bin/env python3
import requests
import threading
import time
import random
import subprocess
import sys

def dos_attack_controller():
    """Simulate DoS attack on controller"""
    print("🔥 Starting DoS attack on controller...")
    
    for i in range(50):
        try:
            # Flood controller with requests
            requests.post('http://localhost:5001/control', 
                         json={'setpoint': random.uniform(0.5, 2.5), 'plant_id': f'plant_{i}'}, 
                         timeout=1)
            requests.get('http://localhost:5001/status', timeout=1)
        except:
            pass
        
        if i % 10 == 0:
            print(f"💥 Attack progress: {i}/50 requests sent")
        
        time.sleep(0.1)
    
    print("✅ DoS attack phase completed")

def dos_attack_agents():
    """Simulate DoS attack on agents"""
    print("🎯 Starting DoS attack on agents...")
    
    for i in range(30):
        try:
            requests.post('http://localhost:5002/status', 
                         json={'agent_id': f'agent_{i}', 'action': 'overload'}, 
                         timeout=1)
            requests.get('http://localhost:5002/status', timeout=1)
        except:
            pass
        
        time.sleep(0.2)
    
    print("✅ Agent attack phase completed")

def network_stress():
    """Simulate network stress"""
    print("🌐 Starting network stress simulation...")
    
    for i in range(20):
        try:
            # Create multiple concurrent connections
            requests.get('http://localhost:5001/status', timeout=0.5)
            requests.get('http://localhost:5002/status', timeout=0.5)
            requests.get('http://localhost:8086/ping', timeout=0.5)
        except:
            pass
        time.sleep(0.3)
    
    print("✅ Network stress completed")

if __name__ == "__main__":
    print("🚀 NCS DoS Attack Experiment Started")
    print("📊 This will demonstrate system degradation and self-healing recovery")
    
    # Run attacks in parallel to simulate real DoS
    threads = [
        threading.Thread(target=dos_attack_controller),
        threading.Thread(target=dos_attack_agents),
        threading.Thread(target=network_stress)
    ]
    
    # Start all attack threads
    for thread in threads:
        thread.start()
    
    # Wait for all attacks to complete
    for thread in threads:
        thread.join()
    
    print("🎯 DoS attack experiment completed!")
    print("📈 System should now show degraded performance and begin self-healing")
