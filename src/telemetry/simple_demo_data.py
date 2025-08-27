#!/usr/bin/env python3
"""
Simple Demo Data Generator for NCS Dashboard
Generates realistic data patterns directly to show in Grafana
"""

import time
import random
import requests
from datetime import datetime

class SimpleDataDemo:
    def __init__(self):
        # Use localhost ports for simplicity
        self.influx_url = "http://localhost:8086"
        print("🎭 Demo Data Generator - Creating realistic NCS patterns")

    def generate_realistic_pattern(self):
        """Generate realistic system behavior patterns"""
        current_time = time.time()
        cycle = (current_time % 180) / 180  # 3-minute cycles
        
        if cycle < 0.33:  # Normal operation phase
            stability = 0.85 + random.uniform(-0.03, 0.03)
            control_cost = random.uniform(0.2, 0.6)
            mttr = random.uniform(2.0, 6.0)
            recoveries = random.randint(0, 2)
            latency = random.uniform(18.0, 28.0)
            phase = "NORMAL"
            
        elif cycle < 0.66:  # Attack/degradation phase
            stability = 0.45 + random.uniform(-0.1, 0.15)
            control_cost = random.uniform(1.5, 4.0)
            mttr = random.uniform(12.0, 25.0)
            recoveries = random.randint(4, 10)
            latency = random.uniform(45.0, 80.0)
            phase = "ATTACK"
            
        else:  # Recovery phase  
            stability = 0.75 + random.uniform(-0.05, 0.08)
            control_cost = random.uniform(0.5, 1.5)
            mttr = random.uniform(3.0, 12.0)
            recoveries = random.randint(2, 5)
            latency = random.uniform(25.0, 40.0)
            phase = "RECOVERY"
            
        return {
            'phase': phase,
            'stability_margin': max(0.1, min(0.95, stability)),
            'control_cost': control_cost,
            'mttr': mttr,
            'num_recoveries': recoveries,
            'latency_p95': latency,
            'overshoot': random.uniform(0.08, 0.22),
            'settling_time': random.uniform(2.8, 4.2),
            'jitter_std': random.uniform(3.0, 10.0),
        }

    def write_to_influx_direct(self, data):
        """Write directly to InfluxDB using line protocol"""
        try:
            timestamp_ns = int(time.time() * 1_000_000_000)
            
            lines = [
                f"control_kpis,host=demo stability_margin={data['stability_margin']},control_cost={data['control_cost']},overshoot={data['overshoot']},settling_time={data['settling_time']} {timestamp_ns}",
                f"agent_kpis,host=demo mttr={data['mttr']},num_recoveries={data['num_recoveries']} {timestamp_ns}",
                f"network_kpis,host=demo latency_p95={data['latency_p95']},jitter_std={data['jitter_std']} {timestamp_ns}"
            ]
            
            line_data = '\n'.join(lines)
            
            # Write using InfluxDB line protocol
            response = requests.post(
                f"{self.influx_url}/api/v2/write?org=ncs-lab&bucket=control-kpis&precision=ns",
                headers={
                    'Authorization': 'Token admin-token',
                    'Content-Type': 'text/plain; charset=utf-8'
                },
                data=line_data,
                timeout=5
            )
            
            if response.status_code == 204:
                print(f"📊 [{data['phase']}] Stability: {data['stability_margin']:.2f}, MTTR: {data['mttr']:.1f}s, Cost: {data['control_cost']:.2f}")
            else:
                print(f"⚠️  InfluxDB response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Write error: {e}")

    def run_demo(self):
        """Run the demo data generation"""
        print("🚀 Starting realistic NCS demo data generation...")
        print("📊 Watch your Grafana dashboard for real-time updates!")
        print("🔄 Data patterns: NORMAL → ATTACK → RECOVERY (3-min cycles)")
        
        while True:
            try:
                data = self.generate_realistic_pattern()
                self.write_to_influx_direct(data)
                time.sleep(3)  # Update every 3 seconds for smooth animation
                
            except KeyboardInterrupt:
                print("\n⏹️  Demo stopped")
                break
            except Exception as e:
                print(f"❌ Demo error: {e}")
                time.sleep(5)

if __name__ == '__main__':
    demo = SimpleDataDemo()
    demo.run_demo()
