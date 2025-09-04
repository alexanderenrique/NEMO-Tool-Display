#!/usr/bin/env python3
"""
MQTT Test Client for NEMO Tool Display
Tests MQTT publishing and subscribing
"""

import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime
from test_api import generate_test_tools

class MQTTTester:
    def __init__(self, broker="localhost", port=1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker")
            # Subscribe to all tool topics
            client.subscribe("nemo/tools/+/status")
            client.subscribe("nemo/tools/overall")
        else:
            print(f"Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        print(f"Received on {topic}:")
        print(json.dumps(payload, indent=2))
        print("-" * 40)
    
    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def publish_test_data(self):
        """Publish test tool data"""
        tools = generate_test_tools()
        
        # Publish individual tool status
        for tool in tools:
            topic = f"nemo/tools/{tool['id']}/status"
            payload = json.dumps(tool)
            self.client.publish(topic, payload, qos=1)
            print(f"Published to {topic}")
        
        # Publish overall status
        overall_topic = "nemo/tools/overall"
        overall_payload = json.dumps({
            "total_tools": len(tools),
            "active_tools": len([t for t in tools if t["status"] == "active"]),
            "timestamp": datetime.now().isoformat()
        })
        self.client.publish(overall_topic, overall_payload, qos=1)
        print(f"Published to {overall_topic}")
    
    def run_test(self, duration=30):
        """Run test for specified duration"""
        if not self.connect():
            return
        
        print(f"Running MQTT test for {duration} seconds...")
        print("Publishing test data every 5 seconds...")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            self.publish_test_data()
            time.sleep(5)
        
        self.client.loop_stop()
        self.client.disconnect()
        print("Test completed")

if __name__ == "__main__":
    import sys
    
    broker = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"MQTT Test Client - Broker: {broker}")
    print("=" * 40)
    
    tester = MQTTTester(broker)
    tester.run_test(duration)
