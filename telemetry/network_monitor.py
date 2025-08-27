#!/usr/bin/env python3
"""
NCS Network Monitor - Collects network KPIs for agent decision making
"""

import os
import time
import json
import psutil
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point

class NetworkMonitor:
    def __init__(self):
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt-broker')
        self.influx_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        
        self.setup_mqtt()
        self.setup_influx()
        
        print("📡 Network Monitor started")

    def setup_mqtt(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        self.mqtt_client.loop_start()

    def setup_influx(self):
        self.influx_client = InfluxDBClient(
            url=self.influx_url,
            token="ncs-research-token-2024",
            org="ncs-lab"
        )
        self.write_api = self.influx_client.write_api()

    def collect_metrics(self):
        network_stats = psutil.net_io_counters()
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        metrics = {
            'bytes_sent': network_stats.bytes_sent,
            'bytes_recv': network_stats.bytes_recv,
            'packets_sent': network_stats.packets_sent, 
            'packets_recv': network_stats.packets_recv,
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'timestamp': time.time()
        }
        
        # Publish to MQTT
        self.mqtt_client.publish("ncs/network/kpis", json.dumps(metrics))
        
        # Log to InfluxDB
        point = Point("network_kpis").field("cpu_percent", cpu_percent).field("memory_percent", memory.percent)
        self.write_api.write(bucket="control-kpis", record=point)
        
        return metrics

    def run(self):
        while True:
            self.collect_metrics()
            time.sleep(1)

if __name__ == '__main__':
    monitor = NetworkMonitor()
    monitor.run()
