#!/usr/bin/env python3
"""
NCS Adversary Service - Chaos Engineering for Security and Resilience Testing
Implements DoS attacks, network manipulation, false data injection, and timing attacks
"""

import os
import json
import time
import threading
import subprocess
import random
import numpy as np
import paho.mqtt.client as mqtt
from datetime import datetime

class NCSAdversary:
    def __init__(self):
        # Configuration
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt-broker')
        
        # Attack state
        self.active_attacks = {}
        self.attack_threads = {}
        
        # Attack parameters
        self.dos_targets = ['controller', 'plant-pendulum', 'plant-unstable']
        self.network_interfaces = ['eth0']
        
        # Communication
        self.setup_mqtt()
        
        print("🦹‍♀️ NCS Adversary Service initialized - Ready for chaos!")

    def setup_mqtt(self):
        """Setup MQTT communication"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
        self.mqtt_client.loop_start()

    def on_mqtt_connect(self, client, userdata, flags, rc):
        print(f"Adversary MQTT connected with result code {rc}")
        client.subscribe("ncs/adversary/commands")
        client.subscribe("ncs/attacks/+")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if 'adversary/commands' in msg.topic:
                self.handle_command(payload)
            elif 'attacks' in msg.topic:
                attack_type = msg.topic.split('/')[-1]
                self.execute_attack(attack_type, payload)
                
        except Exception as e:
            print(f"Adversary MQTT message error: {e}")

    def handle_command(self, command):
        """Handle attack commands"""
        action = command.get('action', 'unknown')
        
        if action == 'start_attack':
            attack_type = command.get('attack_type', 'dos')
            params = command.get('parameters', {})
            self.start_attack(attack_type, params)
            
        elif action == 'stop_attack':
            attack_type = command.get('attack_type', 'all')
            self.stop_attack(attack_type)
            
        elif action == 'status':
            self.report_status()

    def start_attack(self, attack_type, params):
        """Start specified attack"""
        if attack_type in self.active_attacks:
            print(f"⚠️ Attack {attack_type} already active")
            return
            
        print(f"🔥 Starting attack: {attack_type}")
        
        # Mark attack as active
        self.active_attacks[attack_type] = {
            'start_time': time.time(),
            'parameters': params,
            'status': 'active'
        }
        
        # Publish attack start event
        self.mqtt_client.publish(
            "ncs/disturbance/attack",
            json.dumps({'type': 'attack_start', 'attack': attack_type, 'timestamp': time.time()})
        )
        
        # Start attack thread
        if attack_type == 'dos':
            thread = threading.Thread(target=self.dos_attack, args=(params,), daemon=True)
        elif attack_type == 'network_delay':
            thread = threading.Thread(target=self.network_delay_attack, args=(params,), daemon=True)
        elif attack_type == 'packet_loss':
            thread = threading.Thread(target=self.packet_loss_attack, args=(params,), daemon=True)
        elif attack_type == 'jitter':
            thread = threading.Thread(target=self.jitter_attack, args=(params,), daemon=True)
        elif attack_type == 'false_data':
            thread = threading.Thread(target=self.false_data_attack, args=(params,), daemon=True)
        elif attack_type == 'timing':
            thread = threading.Thread(target=self.timing_attack, args=(params,), daemon=True)
        elif attack_type == 'replay':
            thread = threading.Thread(target=self.replay_attack, args=(params,), daemon=True)
        else:
            print(f"❌ Unknown attack type: {attack_type}")
            return
            
        self.attack_threads[attack_type] = thread
        thread.start()

    def stop_attack(self, attack_type):
        """Stop specified attack (or all attacks)"""
        if attack_type == 'all':
            attacks_to_stop = list(self.active_attacks.keys())
        else:
            attacks_to_stop = [attack_type] if attack_type in self.active_attacks else []
            
        for attack in attacks_to_stop:
            if attack in self.active_attacks:
                self.active_attacks[attack]['status'] = 'stopping'
                duration = time.time() - self.active_attacks[attack]['start_time']
                print(f"🛑 Stopping attack: {attack} (ran for {duration:.1f}s)")
                
                # Cleanup network rules
                self.cleanup_network_attack(attack)
                
                # Remove from active attacks
                del self.active_attacks[attack]
                
                # Publish attack stop event
                self.mqtt_client.publish(
                    "ncs/disturbance/attack",
                    json.dumps({'type': 'attack_stop', 'attack': attack, 'timestamp': time.time()})
                )

    def dos_attack(self, params):
        """Denial of Service attack using iperf3"""
        target = params.get('target', 'controller')
        bandwidth = params.get('bandwidth', '50M')  # 50 Mbps
        duration = params.get('duration', 60)  # seconds
        
        print(f"💥 DoS: Flooding {target} with {bandwidth} for {duration}s")
        
        try:
            # Resolve target container IP (simplified - would need proper service discovery)
            target_map = {
                'controller': '172.20.0.10',  # Example IPs
                'plant-pendulum': '172.20.0.11',
                'plant-unstable': '172.20.0.12'
            }
            
            target_ip = target_map.get(target, '172.20.0.10')
            
            # Launch iperf3 client to flood target
            cmd = [
                'iperf3', '-c', target_ip, '-u',
                '-b', bandwidth, '-t', str(duration),
                '--length', '1024'  # Packet size
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if 'dos' in self.active_attacks:
                print(f"✅ DoS attack completed: {process.stdout}")
            
        except Exception as e:
            print(f"❌ DoS attack failed: {e}")
        
        # Mark as completed
        if 'dos' in self.active_attacks:
            self.active_attacks['dos']['status'] = 'completed'

    def network_delay_attack(self, params):
        """Network delay injection using tc netem"""
        delay = params.get('delay', '50ms')
        jitter = params.get('jitter', '10ms')
        duration = params.get('duration', 60)
        interface = params.get('interface', 'eth0')
        
        print(f"⏰ Network delay: {delay} ±{jitter} on {interface} for {duration}s")
        
        try:
            # Apply delay with netem
            subprocess.run([
                'tc', 'qdisc', 'replace', 'dev', interface, 'root',
                'netem', 'delay', delay, jitter, 'distribution', 'normal'
            ], check=True)
            
            # Wait for duration
            start_time = time.time()
            while time.time() - start_time < duration:
                if 'network_delay' not in self.active_attacks:
                    break
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Network delay attack failed: {e}")
        
        # Mark as completed
        if 'network_delay' in self.active_attacks:
            self.active_attacks['network_delay']['status'] = 'completed'

    def packet_loss_attack(self, params):
        """Packet loss injection using tc netem"""
        loss_rate = params.get('loss_rate', '3%')
        duration = params.get('duration', 60)
        interface = params.get('interface', 'eth0')
        
        print(f"📦 Packet loss: {loss_rate} on {interface} for {duration}s")
        
        try:
            # Apply packet loss with netem
            subprocess.run([
                'tc', 'qdisc', 'replace', 'dev', interface, 'root',
                'netem', 'loss', loss_rate
            ], check=True)
            
            # Wait for duration
            start_time = time.time()
            while time.time() - start_time < duration:
                if 'packet_loss' not in self.active_attacks:
                    break
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Packet loss attack failed: {e}")
        
        # Mark as completed
        if 'packet_loss' in self.active_attacks:
            self.active_attacks['packet_loss']['status'] = 'completed'

    def jitter_attack(self, params):
        """Network jitter attack using tc netem"""
        jitter = params.get('jitter', '20ms')
        duration = params.get('duration', 60)
        interface = params.get('interface', 'eth0')
        
        print(f"📡 Jitter attack: {jitter} on {interface} for {duration}s")
        
        try:
            # Apply jitter with netem
            subprocess.run([
                'tc', 'qdisc', 'replace', 'dev', interface, 'root',
                'netem', 'delay', '10ms', jitter, 'distribution', 'normal'
            ], check=True)
            
            # Wait for duration
            start_time = time.time()
            while time.time() - start_time < duration:
                if 'jitter' not in self.active_attacks:
                    break
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Jitter attack failed: {e}")
        
        # Mark as completed
        if 'jitter' in self.active_attacks:
            self.active_attacks['jitter']['status'] = 'completed'

    def false_data_attack(self, params):
        """False data injection attack"""
        target_plant = params.get('target', 'plant1')
        bias = params.get('bias', 0.5)  # Sensor bias
        noise = params.get('noise', 0.1)  # Noise level
        duration = params.get('duration', 60)
        
        print(f"🎭 False data injection: bias={bias}, noise={noise} on {target_plant} for {duration}s")
        
        try:
            # Send attack configuration to target plant
            attack_config = {
                'sensor_attack': True,
                'bias': bias,
                'noise': noise
            }
            
            self.mqtt_client.publish(
                f"ncs/plant/{target_plant}/attack",
                json.dumps(attack_config)
            )
            
            # Wait for duration
            start_time = time.time()
            while time.time() - start_time < duration:
                if 'false_data' not in self.active_attacks:
                    break
                time.sleep(1)
            
            # Stop attack
            attack_config['sensor_attack'] = False
            self.mqtt_client.publish(
                f"ncs/plant/{target_plant}/attack",
                json.dumps(attack_config)
            )
            
        except Exception as e:
            print(f"❌ False data attack failed: {e}")
        
        # Mark as completed
        if 'false_data' in self.active_attacks:
            self.active_attacks['false_data']['status'] = 'completed'

    def timing_attack(self, params):
        """Timing attack - manipulate message timestamps"""
        duration = params.get('duration', 60)
        time_offset = params.get('time_offset', 0.1)  # 100ms offset
        
        print(f"⏱️ Timing attack: {time_offset}s offset for {duration}s")
        
        try:
            # This would require intercepting and modifying packets
            # For simulation, we'll just inject delayed/advanced messages
            start_time = time.time()
            
            while time.time() - start_time < duration:
                if 'timing' not in self.active_attacks:
                    break
                
                # Inject false timestamps
                fake_timestamp = time.time() + time_offset
                
                # Send fake control messages with wrong timestamps
                fake_control = {
                    'control_input': random.uniform(-1, 1),
                    'timestamp': fake_timestamp,
                    'attack_marker': True
                }
                
                self.mqtt_client.publish("ncs/control/input", json.dumps(fake_control))
                time.sleep(0.1)  # 10Hz injection
            
        except Exception as e:
            print(f"❌ Timing attack failed: {e}")
        
        # Mark as completed
        if 'timing' in self.active_attacks:
            self.active_attacks['timing']['status'] = 'completed'

    def replay_attack(self, params):
        """Replay attack - record and replay old messages"""
        duration = params.get('duration', 60)
        
        print(f"🔄 Replay attack for {duration}s")
        
        # This is a simplified replay attack
        # In practice, would need to capture and store legitimate messages
        
        try:
            start_time = time.time()
            
            # Simulate replaying old control messages
            old_control_messages = [
                {'control_input': 0.5, 'timestamp': time.time() - 10},
                {'control_input': -0.3, 'timestamp': time.time() - 8},
                {'control_input': 0.8, 'timestamp': time.time() - 5}
            ]
            
            while time.time() - start_time < duration:
                if 'replay' not in self.active_attacks:
                    break
                
                # Replay old message
                old_msg = random.choice(old_control_messages)
                old_msg['timestamp'] = time.time() - random.uniform(5, 30)  # Old timestamp
                old_msg['replay_marker'] = True
                
                self.mqtt_client.publish("ncs/control/input", json.dumps(old_msg))
                time.sleep(0.5)  # 2Hz replay
            
        except Exception as e:
            print(f"❌ Replay attack failed: {e}")
        
        # Mark as completed
        if 'replay' in self.active_attacks:
            self.active_attacks['replay']['status'] = 'completed'

    def cleanup_network_attack(self, attack_type):
        """Cleanup network-based attacks"""
        if attack_type in ['network_delay', 'packet_loss', 'jitter']:
            try:
                # Remove tc rules
                for interface in self.network_interfaces:
                    subprocess.run(['tc', 'qdisc', 'del', 'dev', interface, 'root'], 
                                 capture_output=True)
                print(f"🧹 Cleaned up network rules for {attack_type}")
            except:
                pass  # Ignore cleanup errors

    def report_status(self):
        """Report current attack status"""
        status = {
            'active_attacks': len(self.active_attacks),
            'attacks': {}
        }
        
        for attack, info in self.active_attacks.items():
            duration = time.time() - info['start_time']
            status['attacks'][attack] = {
                'status': info['status'],
                'duration': duration,
                'parameters': info['parameters']
            }
        
        self.mqtt_client.publish(
            "ncs/adversary/status",
            json.dumps(status)
        )
        
        print(f"📊 Attack Status: {status}")

    def random_attack_sequence(self, params):
        """Execute a sequence of random attacks"""
        attacks = ['dos', 'network_delay', 'packet_loss', 'jitter', 'false_data']
        duration = params.get('total_duration', 300)  # 5 minutes
        attack_interval = params.get('interval', 60)   # 1 minute per attack
        
        print(f"🎲 Random attack sequence for {duration}s")
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Select random attack
            attack_type = random.choice(attacks)
            attack_params = {
                'duration': random.uniform(30, 90),
                'intensity': random.choice(['low', 'medium', 'high'])
            }
            
            # Adjust parameters based on intensity
            if attack_params['intensity'] == 'high':
                if attack_type == 'dos':
                    attack_params['bandwidth'] = '100M'
                elif attack_type == 'network_delay':
                    attack_params['delay'] = '100ms'
                elif attack_type == 'packet_loss':
                    attack_params['loss_rate'] = '10%'
            
            # Start attack
            self.start_attack(attack_type, attack_params)
            
            # Wait for interval
            time.sleep(attack_interval)
            
            # Stop attack
            self.stop_attack(attack_type)

if __name__ == '__main__':
    adversary = NCSAdversary()
    
    # Keep the adversary running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 NCS Adversary shutting down")
        adversary.stop_attack('all')
