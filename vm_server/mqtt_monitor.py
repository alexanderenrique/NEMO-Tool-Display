#!/usr/bin/env python3
"""
Comprehensive MQTT Monitor
Combines broker status monitoring, message watching, and traffic analysis
"""

import paho.mqtt.client as mqtt
import threading
import time
import sys
import os
import signal
from datetime import datetime
from collections import defaultdict

class ComprehensiveMQTTMonitor:
    def __init__(self):
        self.running = True
        self.message_count = 0
        self.topic_stats = defaultdict(int)
        self.port_stats = {'1883': 0, '8883': 0}
        self.start_time = datetime.now()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        sys.exit(0)
    
    def on_connect_1883(self, client, userdata, flags, rc):
        """Connection callback for port 1883 (ESP32s)"""
        if rc == 0:
            print(f"✅ Connected to port 1883 (ESP32s)")
            client.subscribe("#")  # Subscribe to all topics
        else:
            print(f"❌ Failed to connect to port 1883: {rc}")
    
    def on_connect_8883(self, client, userdata, flags, rc):
        """Connection callback for port 8883 (NEMO SSL)"""
        if rc == 0:
            print(f"✅ Connected to port 8883 (NEMO SSL)")
            client.subscribe("#")  # Subscribe to all topics
        else:
            print(f"❌ Failed to connect to port 8883: {rc}")
    
    def on_message_1883(self, client, userdata, msg):
        """Message callback for port 1883"""
        self.log_message("ESP32s", msg, "1883")
    
    def on_message_8883(self, client, userdata, msg):
        """Message callback for port 8883"""
        self.log_message("NEMO", msg, "8883")
    
    def log_message(self, source, msg, port):
        """Log and analyze incoming messages"""
        self.message_count += 1
        self.topic_stats[msg.topic] += 1
        self.port_stats[port] += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Format message based on content
        try:
            if len(msg.payload) > 200:
                payload_preview = msg.payload[:200].decode('utf-8', errors='ignore') + "..."
            else:
                payload_preview = msg.payload.decode('utf-8', errors='ignore')
        except:
            payload_preview = f"<binary data: {len(msg.payload)} bytes>"
        
        # Color coding based on topic
        topic_color = self.get_topic_color(msg.topic)
        
        print(f"[{timestamp}] [{source:>6}] {topic_color}📨 {msg.topic}")
        print(f"                    💬 {payload_preview}")
        print(f"                    📊 QoS:{msg.qos} | Retain:{msg.retain} | Size:{len(msg.payload)} bytes")
        print("─" * 80)
    
    def get_topic_color(self, topic):
        """Get color emoji based on topic type"""
        if "esp32" in topic.lower():
            return "🔌"  # ESP32 messages
        elif "nemo" in topic.lower():
            return "🏭"  # NEMO messages
        elif "status" in topic.lower():
            return "📊"  # Status messages
        elif "error" in topic.lower():
            return "❌"  # Error messages
        else:
            return "📡"  # Other messages
    
    def print_status_header(self):
        """Print the status header"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("=" * 80)
        print("🔍 COMPREHENSIVE MQTT MONITOR")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Runtime: {datetime.now() - self.start_time}")
        print(f"Messages: {self.message_count} total")
        print("=" * 80)
    
    def print_broker_status(self):
        """Print broker status information"""
        print("\n🖥️  BROKER STATUS:")
        
        # Check if mosquitto is running
        try:
            result = os.popen("pgrep -f 'mosquitto.*mqtt/config/mosquitto.conf'").read().strip()
            if result:
                print(f"  🟢 Broker: RUNNING (PID: {result})")
            else:
                print("  🔴 Broker: NOT RUNNING")
        except:
            print("  ❓ Broker: Status unknown")
        
        # Check port status
        print("\n🔌 PORT STATUS:")
        for port, name in [("1883", "ESP32s"), ("8883", "NEMO SSL"), ("9001", "WebSocket")]:
            try:
                result = os.popen(f"lsof -i :{port}").read().strip()
                if result:
                    print(f"  🟢 {port} ({name}): LISTENING")
                else:
                    print(f"  🔴 {port} ({name}): NOT LISTENING")
            except:
                print(f"  ❓ {port} ({name}): Status unknown")
    
    def print_message_stats(self):
        """Print message statistics"""
        print(f"\n📊 MESSAGE STATISTICS:")
        print(f"  Total Messages: {self.message_count}")
        print(f"  Port 1883 (ESP32s): {self.port_stats['1883']}")
        print(f"  Port 8883 (NEMO): {self.port_stats['8883']}")
        
        if self.topic_stats:
            print(f"\n📈 TOP TOPICS:")
            sorted_topics = sorted(self.topic_stats.items(), key=lambda x: x[1], reverse=True)
            for topic, count in sorted_topics[:10]:  # Top 10 topics
                print(f"  {topic}: {count} messages")
    
    def print_recent_activity(self):
        """Print recent log activity"""
        print(f"\n📝 RECENT ACTIVITY:")
        log_file = "mqtt/log/mosquitto.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-3:]:  # Last 3 lines
                        print(f"  {line.strip()}")
            except:
                print("  ❌ Could not read log file")
        else:
            print("  📝 No log file found")
    
    def start_monitoring(self):
        """Start the comprehensive monitoring"""
        self.print_status_header()
        print("🔌 Connecting to MQTT brokers...")
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
            client_1883.connect("localhost", 1883, 60)
            
            # Try SSL connection for port 8883
            try:
                if os.path.exists("mqtt/certs/ca.crt"):
                    client_8883.tls_set("mqtt/certs/ca.crt")
                client_8883.connect("localhost", 8883, 60)
            except Exception as e:
                print(f"⚠️  Could not connect to port 8883 (SSL): {e}")
                client_8883 = None
            
            # Start loops in separate threads
            thread_1883 = threading.Thread(target=client_1883.loop_forever)
            thread_1883.daemon = True
            thread_1883.start()
            
            if client_8883:
                thread_8883 = threading.Thread(target=client_8883.loop_forever)
                thread_8883.daemon = True
                thread_8883.start()
            
            # Main monitoring loop
            last_status_update = time.time()
            while self.running:
                current_time = time.time()
                
                # Update status every 30 seconds
                if current_time - last_status_update > 30:
                    self.print_status_header()
                    self.print_broker_status()
                    self.print_message_stats()
                    self.print_recent_activity()
                    print(f"\n🔄 Refreshing in 30 seconds... (Ctrl+C to stop)")
                    last_status_update = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.print_final_stats()
            if client_1883:
                client_1883.disconnect()
            if client_8883:
                client_8883.disconnect()
    
    def print_final_stats(self):
        """Print final statistics"""
        print("\n" + "=" * 80)
        print("📊 FINAL STATISTICS")
        print("=" * 80)
        print(f"Total Messages Monitored: {self.message_count}")
        print(f"Port 1883 (ESP32s): {self.port_stats['1883']}")
        print(f"Port 8883 (NEMO): {self.port_stats['8883']}")
        print(f"Runtime: {datetime.now() - self.start_time}")
        
        if self.topic_stats:
            print(f"\nTop Topics:")
            sorted_topics = sorted(self.topic_stats.items(), key=lambda x: x[1], reverse=True)
            for topic, count in sorted_topics[:5]:
                print(f"  {topic}: {count} messages")
        
        print("=" * 80)

def main():
    """Main entry point"""
    print("Starting Comprehensive MQTT Monitor...")
    monitor = ComprehensiveMQTTMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
