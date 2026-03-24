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
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Set by load_environment(): absolute path to config.env if it was read successfully
LOADED_CONFIG_ENV_PATH: Optional[str] = None


def load_environment():
    """Load vm_server/config.env (next to this script). Falls back to cwd .env via load_dotenv()."""
    global LOADED_CONFIG_ENV_PATH
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir / "config.env"

    if env_path.is_file():
        if not os.access(env_path, os.R_OK):
            print(
                f"⚠️  Cannot read env file: {env_path}. "
                "Trying .env in current working directory; else using process environment only."
            )
            load_dotenv()
            return
        try:
            load_dotenv(env_path)
            LOADED_CONFIG_ENV_PATH = str(env_path)
        except PermissionError:
            print(
                f"⚠️  Permission denied reading env file: {env_path}. "
                "Trying .env in current working directory; else using process environment only."
            )
            load_dotenv()
        return

    print(f"⚠️  config.env not found at {env_path}. Trying .env in current working directory.")
    load_dotenv()


# Load configuration from config.env (or fallback .env / existing environment)
load_environment()

class ComprehensiveMQTTMonitor:
    def __init__(self):
        self.running = True
        self.message_count = 0
        self.topic_stats = defaultdict(int)
        
        # Read MQTT configuration from environment
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port_esp32 = int(os.getenv('MQTT_PORT_ESP32', '1883'))
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1886'))
        self.mqtt_username = os.getenv('MQTT_USERNAME', '')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', '')
        
        self.port_stats = {str(self.mqtt_port_esp32): 0, str(self.mqtt_port): 0}
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
        """Connection callback for ESP32 port"""
        if rc == 0:
            print(f"✅ Connected to port {self.mqtt_port_esp32} (ESP32s)")
            result = client.subscribe("#", qos=1)  # Subscribe to all topics with QoS 1
            print(f"   📡 Subscribed to all topics on port {self.mqtt_port_esp32} (result: {result})")
        else:
            print(
                f"❌ Failed to connect to port {self.mqtt_port_esp32}: {rc} "
                f"({mqtt.error_string(rc)})"
            )
    
    def on_subscribe_1883(self, client, userdata, mid, granted_qos):
        """Subscription confirmation callback for ESP32 port"""
        print(f"   ✅ Subscription confirmed for port {self.mqtt_port_esp32} (QoS: {granted_qos})")
    
    def on_connect_1884(self, client, userdata, flags, rc):
        """Connection callback for NEMO Dev port"""
        if rc == 0:
            print(f"✅ Connected to port {self.mqtt_port} (NEMO Dev)")
            client.subscribe("#")  # Subscribe to all topics
        else:
            print(f"❌ Failed to connect to port {self.mqtt_port}: {rc} ({mqtt.error_string(rc)})")

    def on_disconnect_1883(self, client, userdata, rc):
        """Disconnect callback for ESP32 port"""
        if rc != 0:
            print(
                f"⚠️  Disconnected from port {self.mqtt_port_esp32} unexpectedly: "
                f"{rc} ({mqtt.error_string(rc)})"
            )

    def on_disconnect_1884(self, client, userdata, rc):
        """Disconnect callback for NEMO port"""
        if rc != 0:
            print(
                f"⚠️  Disconnected from port {self.mqtt_port} unexpectedly: "
                f"{rc} ({mqtt.error_string(rc)})"
            )
    
    def on_message_1883(self, client, userdata, msg):
        """Message callback for ESP32 port"""
        self.log_message("ESP32s", msg, str(self.mqtt_port_esp32))
    
    def on_message_1884(self, client, userdata, msg):
        """Message callback for NEMO port"""
        self.log_message("NEMO", msg, str(self.mqtt_port))
    
    def log_message(self, source, msg, port):
        """Log and analyze incoming messages"""
        self.message_count += 1
        self.topic_stats[msg.topic] += 1
        self.port_stats[port] += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Determine direction based on topic and port
        if port == str(self.mqtt_port_esp32):
            if "esp32" in msg.topic.lower():
                direction = "📤 TO ESP32"
            else:
                direction = "📥 FROM ESP32"
        else:
            direction = "📥 RECEIVED"
        
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
        
        print(f"[{timestamp}] [{source:>6}] {direction} {topic_color} {msg.topic}")
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
        ports_to_check = [
            (str(self.mqtt_port_esp32), "ESP32s"),
            (str(self.mqtt_port), "NEMO")
        ]
        
        for port, name in ports_to_check:
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
        print(f"  Port {self.mqtt_port_esp32} (ESP32s): {self.port_stats[str(self.mqtt_port_esp32)]}")
        print(f"  Port {self.mqtt_port} (NEMO): {self.port_stats[str(self.mqtt_port)]}")
        
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
        
        # Display configuration
        if LOADED_CONFIG_ENV_PATH:
            print(f"📋 Configuration loaded from: {LOADED_CONFIG_ENV_PATH}")
        else:
            print(
                "📋 Configuration: config.env was not loaded from disk "
                "(using process environment and/or .env in CWD if present)"
            )
        print(f"   MQTT_BROKER: {self.mqtt_broker}")
        print(f"   MQTT_PORT_ESP32: {self.mqtt_port_esp32}, MQTT_PORT (NEMO): {self.mqtt_port}")
        print(f"   MQTT_USERNAME: {self.mqtt_username or '(not set)'}")
        print(f"   MQTT_PASSWORD set: {'yes' if self.mqtt_password else 'no'}")
        print("")
        
        print("🔌 Connecting to MQTT brokers...")
        print("Press Ctrl+C to stop")
        print("=" * 80)
        
        # Create clients for ports 1883 (ESP32s) and NEMO port from config
        client_1883 = mqtt.Client(client_id=f"mqtt-monitor-esp32-{os.getpid()}")
        client_1884 = mqtt.Client(client_id=f"mqtt-monitor-nemo-{os.getpid()}")
        
        # Set up callbacks for port 1883
        client_1883.on_connect = self.on_connect_1883
        client_1883.on_message = self.on_message_1883
        client_1883.on_subscribe = self.on_subscribe_1883
        client_1883.on_disconnect = self.on_disconnect_1883
        
        # Set up callbacks for NEMO port
        client_1884.on_connect = self.on_connect_1884
        client_1884.on_message = self.on_message_1884
        client_1884.on_disconnect = self.on_disconnect_1884
        
        try:
            if self.mqtt_username and self.mqtt_password:
                client_1883.username_pw_set(self.mqtt_username, self.mqtt_password)
                client_1884.username_pw_set(self.mqtt_username, self.mqtt_password)

            # Connect to ESP32 port
            print(f"Connecting to {self.mqtt_broker}:{self.mqtt_port_esp32} (ESP32s)...")
            client_1883.connect(self.mqtt_broker, self.mqtt_port_esp32, 60)

            print(f"Connecting to {self.mqtt_broker}:{self.mqtt_port} (NEMO)...")
            client_1884.connect(self.mqtt_broker, self.mqtt_port, 60)
            
            # Start loops for all ports
            thread_1883 = threading.Thread(target=client_1883.loop_forever)
            thread_1883.daemon = True
            thread_1883.start()
            
            thread_1884 = threading.Thread(target=client_1884.loop_forever)
            thread_1884.daemon = True
            thread_1884.start()
            
            print(f"\n✅ Monitoring ports:")
            print(f"   📥 Port {self.mqtt_port} - Receiving from NEMO")
            print(f"   📤 Port {self.mqtt_port_esp32} - Publishing to ESP32s")
            print("=" * 80)
            
            # Main monitoring loop
            # last_status_update = time.time()
            while self.running:
                # current_time = time.time()
                
                # Update status every 30 seconds - DISABLED
                # if current_time - last_status_update > 30:
                #     self.print_status_header()
                #     self.print_broker_status()
                #     self.print_message_stats()
                #     self.print_recent_activity()
                #     print(f"\n🔄 Refreshing in 30 seconds... (Ctrl+C to stop)")
                #     last_status_update = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.print_final_stats()
            if client_1883:
                client_1883.disconnect()
            if client_1884:
                client_1884.disconnect()
    
    def print_final_stats(self):
        """Print final statistics"""
        print("\n" + "=" * 80)
        print("📊 FINAL STATISTICS")
        print("=" * 80)
        print(f"Total Messages Monitored: {self.message_count}")
        print(f"Port {self.mqtt_port_esp32} (ESP32s): {self.port_stats[str(self.mqtt_port_esp32)]}")
        print(f"Port {self.mqtt_port} (NEMO): {self.port_stats[str(self.mqtt_port)]}")
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
