#!/usr/bin/env python3
import time
import random
import requests
from datetime import datetime

def generate_demo_data():
    """Generate realistic NCS demo data"""
    
    while True:
        try:
            # Create realistic patterns
            current_time = time.time()
            cycle = (current_time % 120) / 120  # 2-minute cycles
            
            if cycle < 0.4:  # Normal operation
                stability = 0.85 + random.uniform(-0.05, 0.05)
                control_cost = random.uniform(0.2, 0.6)
                mttr = random.uniform(2.0, 6.0)
                recoveries = random.randint(0, 3)
                latency = random.uniform(18.0, 28.0)
                phase = "NORMAL"
                
            elif cycle < 0.7:  # Attack phase
                stability = 0.45 + random.uniform(-0.1, 0.2)
                control_cost = random.uniform(1.5, 4.0)
                mttr = random.uniform(10.0, 25.0)
                recoveries = random.randint(4, 12)
                latency = random.uniform(45.0, 85.0)
                phase = "ATTACK"
                
            else:  # Recovery phase
                stability = 0.75 + random.uniform(-0.08, 0.1)
                control_cost = random.uniform(0.4, 1.8)
                mttr = random.uniform(3.0, 12.0)
                recoveries = random.randint(1, 6)
                latency = random.uniform(25.0, 45.0)
                phase = "RECOVERY"
            
            # Create InfluxDB line protocol data
            timestamp_ns = int(time.time() * 1_000_000_000)
            data = f"""control_kpis,host=demo stability_margin={stability:.3f},control_cost={control_cost:.3f},overshoot={random.uniform(0.08, 0.22):.3f},settling_time={random.uniform(2.5, 4.5):.3f} {timestamp_ns}
agent_kpis,host=demo mttr={mttr:.2f},num_recoveries={recoveries} {timestamp_ns}
network_kpis,host=demo latency_p95={latency:.2f},jitter_std={random.uniform(3.0, 12.0):.2f} {timestamp_ns}"""
            
            # Write to InfluxDB
            response = requests.post(
                'http://localhost:8086/write?db=control-kpis',
                data=data,
                timeout=3
            )
            
            if response.status_code == 204:
                print(f"📊 [{phase}] Stability: {stability:.2f}, MTTR: {mttr:.1f}s, Cost: {control_cost:.2f}, Recoveries: {recoveries}")
            else:
                print(f"⚠️ Write failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        time.sleep(3)  # Update every 3 seconds

if __name__ == '__main__':
    print("🚀 Starting NCS Demo Data Generator")
    print("📊 Generating realistic patterns: NORMAL → ATTACK → RECOVERY")
    print("🎯 Watch your Grafana dashboard for live updates!")
    generate_demo_data()
