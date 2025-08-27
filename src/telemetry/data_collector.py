#!/usr/bin/env python3
"""
NCS Data Collector - Collects real-time data and writes to InfluxDB for Grafana
"""

import os
import time
import json
import requests
import random
import traceback
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class NCSDataCollector:
    def __init__(self):
        self.influx_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.controller_url = os.getenv('CONTROLLER_URL', 'http://controller:5001')
        self.agent_url = os.getenv('AGENT_URL', 'http://agent-coordinator:5002')
        
        # InfluxDB v2 credentials
        self.influx_token = "admin-token"
        self.influx_org = "ncs-lab" 
        self.influx_bucket = "control-kpis"
        
        self.setup_influx()
        print("📊 NCS Data Collector started")

    def setup_influx(self):
        """Initialize InfluxDB client"""
        try:
            # Try to create a simple client first
            self.influx_client = InfluxDBClient(
                url=self.influx_url,
                token=self.influx_token,
                org=self.influx_org,
                timeout=10000
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            print("✅ Connected to InfluxDB")
            
            # Test connection
            health = self.influx_client.health()
            print(f"✅ InfluxDB Health: {health.status}")
            
        except Exception as e:
            print(f"⚠️  InfluxDB connection issue: {e}")
            # Continue with synthetic data generation
            self.influx_client = None
            self.write_api = None

    def get_controller_data(self):
        """Fetch controller KPIs"""
        try:
            response = requests.get(f"{self.controller_url}/status", timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Controller API: {e}")
        return None

    def get_agent_data(self):
        """Fetch agent system KPIs"""
        try:
            response = requests.get(f"{self.agent_url}/status", timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Agent API: {e}")
        return None

    def generate_synthetic_data(self):
        """Generate realistic synthetic data for demonstration"""
        # Simulate varying system performance with some patterns
        base_time = time.time()
        
        # Create realistic patterns - system degrading then recovering
        cycle_position = (base_time % 120) / 120  # 2-minute cycle
        
        if cycle_position < 0.3:  # Normal operation
            stability = 0.85 + random.uniform(-0.05, 0.05)
            control_cost = random.uniform(0.1, 0.5)
            mttr = random.uniform(1.0, 5.0)
            recoveries = random.randint(0, 2)
            latency = random.uniform(15.0, 25.0)
        elif cycle_position < 0.7:  # Under attack/degraded
            stability = 0.60 + random.uniform(-0.15, 0.1)
            control_cost = random.uniform(1.0, 3.0)
            mttr = random.uniform(8.0, 20.0)
            recoveries = random.randint(3, 8)
            latency = random.uniform(35.0, 60.0)
        else:  # Recovery phase
            stability = 0.75 + random.uniform(-0.1, 0.1)
            control_cost = random.uniform(0.3, 1.2)
            mttr = random.uniform(2.0, 10.0)
            recoveries = random.randint(1, 4)
            latency = random.uniform(20.0, 35.0)
            
        return {
            'control_kpis': {
                'stability_margin': max(0.1, min(1.0, stability)),
                'control_cost': control_cost,
                'overshoot': random.uniform(0.05, 0.25),
                'settling_time': random.uniform(2.5, 4.5)
            },
            'agent_kpis': {
                'mttr': mttr,
                'num_recoveries': recoveries,
                'recovery_active': random.choice([True, False])
            },
            'network_kpis': {
                'latency_p95': latency,
                'jitter_std': random.uniform(2.0, 8.0),
                'packet_loss': random.uniform(0.0, 3.0)
            }
        }

    def write_data_to_influx(self, data):
        """Write data to InfluxDB"""
        if not self.write_api:
            return
            
        try:
            points = []
            timestamp = datetime.utcnow()

            # Helper function to create point
            def add_point(measurement, field_name, value):
                if isinstance(value, (int, float)) and not (isinstance(value, bool)):
                    point = Point(measurement) \
                        .field(field_name, float(value)) \
                        .time(timestamp, WritePrecision.NS)
                    points.append(point)

            # Control system KPIs
            control_data = data.get('control_kpis', data.get('kpis', {}))
            for metric, value in control_data.items():
                add_point("control_kpis", metric, value)

            # Agent system KPIs  
            agent_data = data.get('agent_kpis', {})
            # Also check top-level for agent metrics
            for key in ['mttr', 'num_recoveries']:
                if key in data:
                    agent_data[key] = data[key]
                    
            for metric, value in agent_data.items():
                add_point("agent_kpis", metric, value)

            # Network KPIs
            network_data = data.get('network_kpis', {})
            for metric, value in network_data.items():
                add_point("network_kpis", metric, value)

            # Write all points
            if points:
                self.write_api.write(bucket=self.influx_bucket, record=points)
                print(f"📊 Wrote {len(points)} data points")
            else:
                print("⚠️  No valid data points to write")

        except Exception as e:
            print(f"❌ InfluxDB write error: {e}")
            traceback.print_exc()

    def collect_and_store(self):
        """Main collection cycle"""
        # Try to get real data first
        controller_data = self.get_controller_data()
        agent_data = self.get_agent_data()

        if controller_data or agent_data:
            # Merge real data
            combined_data = {}
            if controller_data:
                combined_data.update(controller_data)
            if agent_data:
                combined_data.update(agent_data)
            
            print("📡 Using real system data")
            self.write_data_to_influx(combined_data)
        else:
            # Use synthetic data for demo
            synthetic_data = self.generate_synthetic_data()
            print("🎭 Using synthetic demo data")
            self.write_data_to_influx(synthetic_data)

    def run(self):
        """Main execution loop"""
        print("🚀 Starting NCS data collection (5s intervals)...")
        
        while True:
            try:
                self.collect_and_store()
                time.sleep(5)
            except KeyboardInterrupt:
                print("⏹️  Data collection stopped")
                break
            except Exception as e:
                print(f"❌ Collection error: {e}")
                time.sleep(10)

if __name__ == '__main__':
    collector = NCSDataCollector()
    collector.run()
