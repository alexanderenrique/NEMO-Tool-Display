#!/usr/bin/env python3
"""
Test ESP32 MQTT client connection and publishing
"""

import paho.mqtt.client as mqtt
import json
import time
import threading

def on_connect(client, userdata, flags, rc):
    """Connection callback"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker on port 1883")
        print(f"   Client ID: {client._client_id}")
        print(f"   Keep alive: {client._keepalive}")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    """Disconnection callback"""
    print(f"⚠️  Disconnected with code {rc}")

def on_publish(client, userdata, mid):
    """Publish callback"""
    print(f"📤 Message published successfully (mid: {mid})")

def on_log(client, userdata, level, buf):
    """Log callback for debugging"""
    print(f"🔍 MQTT Log: {buf}")

def test_esp32_connection():
    """Test ESP32 client connection and publishing"""
    print("=" * 80)
    print("TESTING ESP32 MQTT CLIENT CONNECTION")
    print("=" * 80)
    
    # Create ESP32 client (same as main.py)
    client = mqtt.Client(client_id="test_esp32_publisher")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_log = on_log
    
    # Set keepalive
    client.keepalive = 60
    
    try:
        print(f"\n🔌 Connecting to localhost:1883...")
        client.connect("localhost", 1883, 60)
        
        # Start the loop in a separate thread
        client.loop_start()
        
        # Wait for connection
        time.sleep(1)
        
        if client.is_connected():
            print(f"✅ Client is connected!")
            
            # Test publishing a message
            test_message = {
                "event_type": "start",
                "timestamp": "Oct 14, 12:15 PM",
                "time_label": "Started",
                "user_label": "User",
                "user_name": "Alex Denton"
            }
            
            topic = "nemo/esp32/woollam/status"
            payload = json.dumps(test_message)
            
            print(f"\n📤 Publishing test message:")
            print(f"   Topic: {topic}")
            print(f"   Payload: {payload}")
            print(f"   Size: {len(payload)} bytes")
            
            result = client.publish(topic, payload, qos=1, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ Publish initiated successfully")
            else:
                print(f"❌ Publish failed with code {result.rc}")
            
            # Wait a moment for publish to complete
            time.sleep(1)
            
            # Test publishing server status
            print(f"\n📤 Publishing server status...")
            result2 = client.publish("nemo/server/status", "online", qos=1, retain=True)
            print(f"   Server status publish result: {result2.rc}")
            
            # Keep connected for a few seconds
            print(f"\n⏳ Keeping connection alive for 5 seconds...")
            time.sleep(5)
            
        else:
            print(f"❌ Client failed to connect!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        print(f"\n🔌 Disconnecting...")
        client.loop_stop()
        client.disconnect()
        print(f"✅ Test completed")

if __name__ == "__main__":
    test_esp32_connection()
