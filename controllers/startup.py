#!/usr/bin/env python3
import time
import socket
import sys

def wait_for_mqtt(host='mqtt-broker', port=1883, timeout=60):
    print(f"⏳ Waiting for MQTT broker at {host}:{port}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"✅ MQTT broker is ready!")
                return True
        except Exception as e:
            pass
        time.sleep(3)
    print(f"❌ MQTT broker not ready after {timeout}s")
    return False

if __name__ == "__main__":
    if wait_for_mqtt():
        print("🚀 Starting controller service...")
        import controller_service
    else:
        sys.exit(1)
