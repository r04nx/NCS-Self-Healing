#!/usr/bin/env python3
import socket
import time
import sys

def wait_for_service(host, port, timeout=60):
    """Wait for a service to become available"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"✅ {host}:{port} is ready!")
                return True
        except:
            pass
        print(f"⏳ Waiting for {host}:{port}...")
        time.sleep(2)
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: wait-for-mqtt.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    if wait_for_service(host, port):
        sys.exit(0)
    else:
        print(f"❌ Service {host}:{port} not ready after timeout")
        sys.exit(1)
