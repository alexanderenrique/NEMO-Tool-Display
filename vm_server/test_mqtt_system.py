#!/usr/bin/env python3
"""
Test script for NEMO MQTT System
Tests the MQTT broker and message forwarding functionality
"""

import json
import time
import paho.mqtt.client as mqtt
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

class MQTTTester:
    def __init__(self):
        self.broker = os.getenv('MQTT_BROKER', 'localhost')
        self.port = int(os.getenv('MQTT_PORT', '8883'))
        self.use_ssl = os.getenv('MQTT_USE_SSL', 'true').lower() == 'true'
        self.username = os.getenv('MQTT_USERNAME', '')
        self.password = os.getenv('MQTT_PASSWORD', '')
        
        self.received_messages = []
        self.client = None
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            # Subscribe to ESP32 topics to test forwarding
            client.subscribe("nemo/esp32/+/status", qos=1)
            client.subscribe("nemo/esp32/overall", qos=1)
            print("📡 Subscribed to ESP32 topics")
        else:
            print(f"❌ Failed to connect to MQTT broker: {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            self.received_messages.append((topic, payload))
            print(f"📨 Received on {topic}: {json.dumps(payload, indent=2)}")
        except json.JSONDecodeError:
            print(f"📨 Received on {topic}: {msg.payload.decode()}")
    
    def on_disconnect(self, client, userdata, rc):
        print(f"🔌 Disconnected from MQTT broker: {rc}")
    
    def connect(self):
        self.client = mqtt.Client()
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        if self.use_ssl:
            self.client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                              cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)
            self.client.tls_insecure_set(True)  # For testing with self-signed certs
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def publish_test_message(self, tool_id="test_tool_001"):
        """Publish a test message to the backend topic"""
        test_topic = f"nemo/backend/tools/{tool_id}/status"
        test_payload = {
            "id": tool_id,
            "name": "Test Tool",
            "status": "active",
            "category": "test",
            "operational": True,
            "problematic": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user": {
                "name": "Test User",
                "username": "testuser",
                "id": "12345",
                "first_name": "John",
                "last_name": "Doe"
            },
            "usage": {
                "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "start_time_formatted": time.strftime("%b %d, %Y at %I:%M %p"),
                "usage_id": "usage_001"
            }
        }
        
        result = self.client.publish(test_topic, json.dumps(test_payload), qos=1, retain=True)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 Published test message to {test_topic}")
            return True
        else:
            print(f"❌ Failed to publish test message: {result.rc}")
            return False
    
    def publish_overall_test(self):
        """Publish a test overall status message"""
        test_topic = "nemo/backend/tools/overall"
        test_payload = {
            "total_tools": 1,
            "active_tools": 1,
            "idle_tools": 0,
            "maintenance_tools": 0,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        result = self.client.publish(test_topic, json.dumps(test_payload), qos=1, retain=True)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 Published overall test message to {test_topic}")
            return True
        else:
            print(f"❌ Failed to publish overall test message: {result.rc}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

def main():
    print("🧪 NEMO MQTT System Test")
    print("=" * 40)
    
    tester = MQTTTester()
    
    # Connect to broker
    if not tester.connect():
        print("❌ Could not connect to MQTT broker. Make sure it's running.")
        return
    
    print("\n⏳ Waiting for connection to establish...")
    time.sleep(2)
    
    # Test individual tool status
    print("\n🔧 Testing individual tool status forwarding...")
    tester.publish_test_message("test_tool_001")
    
    # Wait for message to be processed and forwarded
    print("⏳ Waiting for message forwarding...")
    time.sleep(2)
    
    # Test overall status
    print("\n📊 Testing overall status forwarding...")
    tester.publish_overall_test()
    
    # Wait for message to be processed and forwarded
    print("⏳ Waiting for message forwarding...")
    time.sleep(2)
    
    # Summary
    print(f"\n📋 Test Summary:")
    print(f"   Messages received: {len(tester.received_messages)}")
    
    if tester.received_messages:
        print("   ✅ Message forwarding is working!")
        for topic, payload in tester.received_messages:
            print(f"      - {topic}")
    else:
        print("   ❌ No messages received. Check if NEMO server is running.")
    
    # Cleanup
    tester.disconnect()
    print("\n🏁 Test completed.")

if __name__ == "__main__":
    main()
