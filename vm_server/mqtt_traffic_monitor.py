#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import threading
import time
import sys
from datetime import datetime

class MQTTTrafficMonitor:
    def __init__(self):
        self.running = True
        self.message_count = 0
        
    def on_connect_1883(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to port 1883 (ESP32s)")
            client.subscribe("#")  # Subscribe to all topics
        else:
            print(f"❌ Failed to connect to port 1883: {rc}")
    
    def on_connect_8883(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to port 8883 (NEMO SSL)")
            client.subscribe("#")  # Subscribe to all topics
        else:
            print(f"❌ Failed to connect to port 8883: {rc}")
    
    def on_message_1883(self, client, userdata, msg):
        self.log_message("ESP32s", msg)
    
    def on_message_8883(self, client, userdata, msg):
        self.log_message("NEMO", msg)
    
    def log_message(self, source, msg):
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Format message based on content
        if len(msg.payload) > 100:
            payload_preview = msg.payload[:100].decode('utf-8', errors='ignore') + "..."
        else:
            payload_preview = msg.payload.decode('utf-8', errors='ignore')
        
        print(f"[{timestamp}] [{source:>6}] 📨 {msg.topic}")
        print(f"                    💬 {payload_preview}")
        print(f"                    📊 QoS:{msg.qos} | Retain:{msg.retain} | Size:{len(msg.payload)} bytes")
        print("─" * 80)
    
    def start_monitoring(self):
        print("=" * 80)
        print("MQTT TRAFFIC MONITOR - Real-time Message Flow")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Monitoring all topics on both ports...")
        print("Press Ctrl+C to stop")
        print("=" * 80)
        
        # Create clients for both ports
        client_1883 = mqtt.Client()
        client_8883 = mqtt.Client()
        
        # Set up callbacks for port 1883
        client_1883.on_connect = self.on_connect_1883
        client_1883.on_message = self.on_message_1883
        
        # Set up callbacks for port 8883
        client_8883.on_connect = self.on_connect_8883
        client_8883.on_message = self.on_message_8883
        
        try:
            # Connect to both ports
            print("Connecting to brokers...")
            client_1883.connect("localhost", 1883, 60)
            client_8883.tls_set("mqtt/certs/ca.crt")
            client_8883.connect("localhost", 8883, 60)
            
            # Start loops in separate threads
            thread_1883 = threading.Thread(target=client_1883.loop_forever)
            thread_8883 = threading.Thread(target=client_8883.loop_forever)
            
            thread_1883.daemon = True
            thread_8883.daemon = True
            
            thread_1883.start()
            thread_8883.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")
            print(f"📊 Total messages monitored: {self.message_count}")
            self.running = False
            client_1883.disconnect()
            client_8883.disconnect()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    monitor = MQTTTrafficMonitor()
    monitor.start_monitoring()
