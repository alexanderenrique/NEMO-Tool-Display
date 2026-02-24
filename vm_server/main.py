#!/usr/bin/env python3

"""
NEMO Tool Display - VM Server
Main application that receives tool status via MQTT and distributes to ESP32 displays
"""

import asyncio
import json
import logging
import os
import sys
import socket
from datetime import datetime
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from config_parser import get_mqtt_ports, get_esp32_port, get_nemo_port, get_mqtt_broker

# Load environment variables
load_dotenv('config.env')

# Configuration validation and loading
def load_config():
    """Load and validate configuration from environment variables"""
    config = {}
    
    # MQTT Configuration
    # MQTT_BROKER defaults to localhost since Mosquitto runs on the same VM
    # Note: NEMO backend needs to know the VM's IP address (e.g., 10.0.0.31) to connect to Mosquitto
    config['mqtt_broker'] = os.getenv('MQTT_BROKER', 'localhost')
    config['mqtt_use_ssl'] = os.getenv('MQTT_USE_SSL', 'false').lower() == 'true'
    config['mqtt_username'] = os.getenv('MQTT_USERNAME', '')
    config['mqtt_password'] = os.getenv('MQTT_PASSWORD', '')
    
    # Display Configuration
    config['timezone_offset_hours'] = int(os.getenv('TIMEZONE_OFFSET_HOURS', '-7'))
    config['max_name_length'] = int(os.getenv('MAX_NAME_LENGTH', '13'))
    
    # Logging Configuration
    config['log_level'] = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Validate required configurations
    
    if config['timezone_offset_hours'] < -12 or config['timezone_offset_hours'] > 14:
        raise ValueError("TIMEZONE_OFFSET_HOURS must be between -12 and 14")
    
    if config['max_name_length'] < 1 or config['max_name_length'] > 50:
        raise ValueError("MAX_NAME_LENGTH must be between 1 and 50")
    
    return config

# Load configuration
try:
    CONFIG = load_config()
except Exception as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Configure logging
log_level = getattr(logging, CONFIG['log_level'], logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nemo_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def get_local_ip():
    """Get the local IP address dynamically"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        try:
            # Fallback: use hostname resolution
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                raise Exception("Got loopback address")
            return local_ip
        except Exception:
            return "127.0.0.1"


class NEMOToolServer:
    """Main server class for NEMO Tool Display system"""
    
    def __init__(self):
        # Load configuration
        self.config = CONFIG
        
        # MQTT broker defaults to localhost (Mosquitto runs on same VM)
        logger.info(f"MQTT broker: {self.config['mqtt_broker']}")

        # Track last users for each tool (keyed by tool_id)
        self.last_users = {}  # tool_id (str) -> user_name
        
        self.mqtt_client_nemo = None  # Client for receiving from NEMO on port 1886
        self.mqtt_client_esp32 = None  # Client for publishing to ESP32s on port 1883
        self.running = False

    async def init_mqtt(self):
        """Initialize MQTT clients: one for receiving from NEMO (1886), one for publishing to ESP32s (1883)"""
        
        # ===== NEMO Client (port 1886) - Receives messages from NEMO backend =====
        import time
        unique_id = f"nemo_receiver_{int(time.time())}"
        self.mqtt_client_nemo = mqtt.Client(client_id=unique_id)
        
        if self.config['mqtt_username'] and self.config['mqtt_password']:
            self.mqtt_client_nemo.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
        
        # Configure SSL if enabled
        if self.config['mqtt_use_ssl']:
            import ssl
            # Use the actual CA certificate for proper SSL connection
            ca_cert_path = "mqtt/certs/ca.crt"
            if os.path.exists(ca_cert_path):
                self.mqtt_client_nemo.tls_set(ca_certs=ca_cert_path, certfile=None, keyfile=None, 
                                       cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, 
                                       ciphers=None)
                logger.info(f"NEMO Client: Using SSL with CA certificate: {ca_cert_path}")
            else:
                # Fallback to insecure mode if CA cert not found
                self.mqtt_client_nemo.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                                       cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS, 
                                       ciphers=None)
                self.mqtt_client_nemo.tls_insecure_set(True)
                logger.warning("NEMO Client: CA certificate not found, using insecure SSL mode")
        
        self.mqtt_client_nemo.on_connect = self.on_mqtt_connect_nemo
        self.mqtt_client_nemo.on_disconnect = self.on_mqtt_disconnect_nemo
        self.mqtt_client_nemo.on_message = self.on_mqtt_message
        
        # Set keepalive and other options for LAN reliability
        self.mqtt_client_nemo.keepalive = 60
        self.mqtt_client_nemo.will_set("nemo/server/status", "offline", qos=1, retain=True)
        
        # ===== ESP32 Client (port 1883) - Publishes to ESP32 displays =====
        import time
        unique_id = f"esp32_publisher_{int(time.time())}"
        self.mqtt_client_esp32 = mqtt.Client(client_id=unique_id)
        
        if self.config['mqtt_username'] and self.config['mqtt_password']:
            self.mqtt_client_esp32.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
        
        self.mqtt_client_esp32.on_connect = self.on_mqtt_connect_esp32
        self.mqtt_client_esp32.on_disconnect = self.on_mqtt_disconnect_esp32
        self.mqtt_client_esp32.on_publish = self.on_mqtt_publish
        
        # Set keepalive
        self.mqtt_client_esp32.keepalive = 60
        
        try:
            # Connect NEMO client to port 1886 (non-TLS) or 8883 (TLS)
            protocol = "mqtts" if self.config['mqtt_use_ssl'] else "mqtt"
            nemo_port = 8883 if self.config['mqtt_use_ssl'] else get_nemo_port()
            logger.info(f"Connecting NEMO client to {protocol}://{self.config['mqtt_broker']}:{nemo_port}")
            self.mqtt_client_nemo.connect(self.config['mqtt_broker'], nemo_port, 60)
            self.mqtt_client_nemo.loop_start()
            
            # Wait for NEMO client to establish connection
            await asyncio.sleep(2)
            
            # Connect ESP32 client to configured port
            esp32_port = get_esp32_port()
            logger.info(f"Connecting ESP32 client to mqtt://{self.config['mqtt_broker']}:{esp32_port}")
            self.mqtt_client_esp32.connect(self.config['mqtt_broker'], esp32_port, 60)
            self.mqtt_client_esp32.loop_start()
            
            # Wait for ESP32 client to establish connection
            await asyncio.sleep(2)
            
            # Check NEMO client connection
            if not self.mqtt_client_nemo.is_connected():
                raise Exception("NEMO MQTT client connection not established")
            
            # Check ESP32 client connection
            if not self.mqtt_client_esp32.is_connected():
                raise Exception("ESP32 MQTT client connection not established")
            
            logger.info("✅ Both MQTT clients connected successfully!")
            logger.info(f"   📥 Receiving from NEMO on port {nemo_port}")
            logger.info(f"   📤 Publishing to ESP32s on port {esp32_port}")
                
        except Exception as e:
            logger.error(f"Failed to connect MQTT clients: {e}")
            raise
    
    def on_mqtt_connect_nemo(self, client, userdata, flags, rc):
        """MQTT connection callback for NEMO client (port 1886)"""
        if rc == 0:
            logger.info("✅ NEMO MQTT client connected successfully")
            # Subscribe to tool status updates from NEMO backend
            client.subscribe("nemo/tools/+/+", qos=1)  # Subscribe to all tool events
            client.subscribe("nemo/tools/overall", qos=1)
            logger.info("📥 Subscribed to NEMO tool status updates (nemo/tools only)")
        else:
            logger.error(f"❌ NEMO MQTT connection failed with code {rc}")
    
    def on_mqtt_connect_esp32(self, client, userdata, flags, rc):
        """MQTT connection callback for ESP32 client (port 1883)"""
        if rc == 0:
            logger.info("✅ ESP32 MQTT client connected successfully")
            # Publish server online status
            client.publish("nemo/server/status", "online", qos=1, retain=True)
            logger.info("📤 Ready to publish to ESP32 displays")
        else:
            logger.error(f"❌ ESP32 MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect_nemo(self, client, userdata, rc):
        """MQTT disconnection callback for NEMO client with auto-reconnect"""
        logger.warning(f"⚠️  NEMO MQTT client disconnected with code {rc}")
        
        # Auto-reconnect if not intentionally disconnected
        if rc != 0 and self.running:
            logger.info("🔄 Attempting to reconnect NEMO MQTT client...")
            try:
                client.reconnect()
            except Exception as e:
                logger.error(f"❌ NEMO client reconnection failed: {e}")
    
    def on_mqtt_disconnect_esp32(self, client, userdata, rc):
        """MQTT disconnection callback for ESP32 client with manual reconnection"""
        if rc == 0:
            logger.info("✅ ESP32 MQTT client disconnected cleanly")
        else:
            logger.warning(f"⚠️  ESP32 MQTT client disconnected with code {rc}")
            
            # Manual reconnection like NEMO client
            if rc != 0 and self.running:
                logger.info("🔄 Attempting to reconnect ESP32 MQTT client...")
                try:
                    client.reconnect()
                    logger.info("✅ ESP32 MQTT client reconnected successfully")
                except Exception as e:
                    logger.error(f"❌ ESP32 client reconnection failed: {e}")
                    # Try again after a delay
                    try:
                        import time
                        time.sleep(2)
                        client.reconnect()
                        logger.info("✅ ESP32 MQTT client reconnected on retry")
                    except Exception as e2:
                        logger.error(f"❌ ESP32 client second reconnection attempt failed: {e2}")
    
    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"Message published with mid: {mid}")
    
    def get_mqtt_error_description(self, rc):
        """Get human-readable description of MQTT error codes"""
        error_codes = {
            0: "MQTT_ERR_SUCCESS",
            1: "MQTT_ERR_AGAIN", 
            2: "MQTT_ERR_PROTOCOL",
            3: "MQTT_ERR_INVAL",
            4: "MQTT_ERR_NO_CONN",
            5: "MQTT_ERR_CONN_REFUSED",
            6: "MQTT_ERR_NOT_FOUND",
            7: "MQTT_ERR_CONN_LOST",
            8: "MQTT_ERR_TLS",
            9: "MQTT_ERR_PAYLOAD_SIZE",
            10: "MQTT_ERR_NOT_SUPPORTED",
            11: "MQTT_ERR_AUTH",
            12: "MQTT_ERR_ACL_DENIED",
            13: "MQTT_ERR_UNKNOWN",
            14: "MQTT_ERR_ERRNO",
            15: "MQTT_ERR_QUEUE_SIZE"
        }
        return error_codes.get(rc, f"Unknown error code: {rc}")
    
    async def connection_status_monitor(self):
        """Monitor MQTT connection status every 5 seconds"""
        while self.running:
            try:
                await asyncio.sleep(5)
                
                # Check NEMO client
                nemo_connected = self.mqtt_client_nemo.is_connected() if self.mqtt_client_nemo else False
                nemo_state = self.mqtt_client_nemo._state if self.mqtt_client_nemo else "None"
                
                # Check ESP32 client  
                esp32_connected = self.mqtt_client_esp32.is_connected() if self.mqtt_client_esp32 else False
                esp32_state = self.mqtt_client_esp32._state if self.mqtt_client_esp32 else "None"
                
                # Check if ports are actually listening
                esp32_port = get_esp32_port()
                nemo_port = get_nemo_port()
                port_1883_listening = self.check_port_listening(esp32_port)
                port_1886_listening = self.check_port_listening(nemo_port)
                
                # Only require SSL port when TLS is enabled in config (avoids false warnings when testing without TLS)
                ssl_required = self.config.get("mqtt_use_ssl", False)
                ssl_ok = (
                    self.check_port_listening(8883)
                    if (ssl_required and os.path.exists("mqtt/certs/ca.crt"))
                    else True
                )
                
                # Only log if there are issues
                if not nemo_connected or not esp32_connected or not port_1883_listening or not port_1886_listening or not ssl_ok:
                    nemo_ok = "connected" if nemo_connected else "disconnected"
                    esp32_ok = "connected" if esp32_connected else "disconnected"
                    logger.warning(f"⚠️ NEMO (1886): {nemo_ok} | ESP32 (1883): {esp32_ok} | Ports 1883/1886: {'open' if port_1883_listening and port_1886_listening else 'check'}")
                
                # If ESP32 port is closed, restart mosquitto
                if not port_1883_listening:
                    logger.warning(f"🚨 Port {esp32_port} is closed! Restarting mosquitto to reopen it...")
                    await self.restart_mosquitto()
                    continue
                
                # If ESP32 is disconnected but port is open, try to trigger reconnection
                if not esp32_connected and self.mqtt_client_esp32 and port_1883_listening:
                    logger.warning("🔄 ESP32 client is disconnected, triggering reconnection...")
                    try:
                        self.mqtt_client_esp32.reconnect()
                    except Exception as e:
                        logger.error(f"❌ Manual ESP32 reconnection failed: {e}")
                        
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
    
    def check_port_listening(self, port):
        """Check if a port is listening"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    async def restart_mosquitto(self):
        """Restart mosquitto to reopen port 1883"""
        try:
            logger.info("🔄 Restarting mosquitto...")
            
            # Kill existing mosquitto
            import subprocess
            subprocess.run(["pkill", "-f", "mosquitto.*mqtt/config/mosquitto.conf"], capture_output=True)
            await asyncio.sleep(2)
            
            # Start mosquitto again
            subprocess.run([
                "mosquitto", 
                "-c", "mqtt/config/mosquitto.conf", 
                "-d"
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            # Wait for it to start
            await asyncio.sleep(3)
            
            # Check if all ports are now listening
            esp32_port = get_esp32_port()
            nemo_port = get_nemo_port()
            port_1883_ok = self.check_port_listening(esp32_port)
            port_1886_ok = self.check_port_listening(nemo_port)
            
            # Check SSL port if certificates exist
            ssl_port_ok = False
            ssl_message = ""
            if os.path.exists("mqtt/certs/ca.crt"):
                ssl_port_ok = self.check_port_listening(8883)
                ssl_message = f", 8883 (SSL): {ssl_port_ok}"
            
            # Determine which ports to check
            all_ports_ok = port_1883_ok and port_1886_ok
            if os.path.exists("mqtt/certs/ca.crt"):
                all_ports_ok = all_ports_ok and ssl_port_ok
            
            if all_ports_ok:
                ports_list = f"{esp32_port}, {nemo_port}"
                if os.path.exists("mqtt/certs/ca.crt"):
                    ports_list += ", 8883 (SSL)"
                logger.info(f"✅ Mosquitto restarted successfully - all ports are open ({ports_list})")
            else:
                logger.error(f"❌ Mosquitto restart failed - Port {esp32_port}: {port_1883_ok}, Port {nemo_port}: {port_1886_ok}{ssl_message}")
                
        except Exception as e:
            logger.error(f"❌ Failed to restart mosquitto: {e}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages from NEMO backend"""
        topic = msg.topic
        raw_payload = msg.payload.decode(errors="replace")
        try:
            payload = json.loads(raw_payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None

        try:
            # Handle individual tool status updates
            if topic.startswith("nemo/tools/") and len(topic.split("/")) >= 4:
                parts = topic.split("/")
                tool_identifier = parts[2]  # Tool ID or name from topic (e.g., "1" or "woollam" from "nemo/tools/1/start")
                event_type = parts[3]  # Extract event type (e.g., "start", "end", "enabled", "disabled")

                # NEMO may publish non-JSON payloads for simple enabled/disabled topics.
                # Normalize into a dict so downstream processing is consistent.
                if isinstance(payload, dict):
                    tool_data = payload
                else:
                    tool_data = {}
                    if payload is not None:
                        tool_data["value"] = payload

                # Ensure tool_id/tool_name exist even when payload is empty/non-JSON.
                if "tool_id" not in tool_data:
                    try:
                        tool_data["tool_id"] = int(tool_identifier)
                    except (ValueError, TypeError):
                        pass
                tool_data.setdefault("tool_name", tool_identifier)
                tool_data.setdefault("timestamp", datetime.utcnow().isoformat() + "+00:00")

                if isinstance(payload, dict):
                    logger.info(f"📥 inbound  {topic} | {json.dumps(payload)}")
                else:
                    logger.info(
                        f"📥 inbound  {topic} | {raw_payload[:200]}{'...' if len(raw_payload) > 200 else ''}"
                    )
                self.process_tool_status(tool_identifier, tool_data, event_type)

            # Handle overall status updates
            elif topic == "nemo/tools/overall":
                logger.info(f"📥 inbound  {topic} | {json.dumps(payload)}")
                self.process_overall_status(payload)

            else:
                if payload is None:
                    logger.debug(
                        f"[1886] Other topic: {topic} -> {raw_payload[:200]}{'...' if len(raw_payload) > 200 else ''}"
                    )
                else:
                    logger.debug(f"[1886] Other topic: {topic} -> {payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def process_tool_status(self, tool_identifier: str, tool_data: dict, event_type: str = None):
        """Process individual tool status update and forward to ESP32 displays.
        
        NEMO sends separate events: enabled/disabled (tool on/off) and start/end (usage session).
        We forward start/end/enabled/disabled and map to a consistent vocabulary:
        active (in use), enabled (available), disabled (tool off).
        """
        try:
            # Parse NEMO message format:
            # {"event": "tool_usage_start", "usage_id": 232, "user_id": 1, 
            #  "user_name": "Alex Denton (admin)", "tool_id": 1, "tool_name": "woollam",
            #  "start_time": "2025-10-14T19:00:11.106294+00:00", "end_time": null}
            
            # Extract tool_id from payload (preferred) or use identifier from topic as fallback
            tool_id = tool_data.get('tool_id')
            if tool_id is None:
                # Fallback: try to parse identifier as integer
                try:
                    tool_id = int(tool_identifier)
                except (ValueError, TypeError):
                    logger.warning(f"Could not extract tool_id from payload or topic identifier '{tool_identifier}'")
                    return
            
            # Extract tool_name from payload for display purposes only
            tool_name = tool_data.get('tool_name', tool_identifier)
            
            # Extract user name from NEMO message
            full_user_name = tool_data.get('user_name', '')
            logger.debug(f"Raw user_name from NEMO: {full_user_name}")
            
            # Parse name - NEMO sends "FirstName LastName (role)" format
            # Example: "Alex Denton (admin)" -> extract "Alex Denton"
            user_display_name = full_user_name
            if full_user_name and '(' in full_user_name:
                # Remove role part: "Alex Denton (admin)" -> "Alex Denton"
                user_display_name = full_user_name.split('(')[0].strip()
            
            # Trim to max length if needed
            if len(user_display_name) > self.config['max_name_length']:
                # Try first name only
                first_name = user_display_name.split()[0] if ' ' in user_display_name else user_display_name
                user_display_name = first_name[:self.config['max_name_length']]
                logger.debug(f"Name too long, trimmed to: '{user_display_name}'")
            
            # If NEMO doesn't include a user_name on state-only events, prefer the last known user.
            if not user_display_name and tool_id is not None:
                user_display_name = self.last_users.get(str(tool_id), "")

            # Map NEMO event types to a consistent vocabulary.
            # start = someone using tool -> active; end/enabled/idle = tool available -> enabled; disabled = tool off
            ESP32_ACTIVE = "active"
            ESP32_ENABLED = "enabled"
            ESP32_DISABLED = "disabled"
            if event_type == "start":
                esp32_event = ESP32_ACTIVE
            elif event_type in ("end", "enabled", "idle"):
                esp32_event = ESP32_ENABLED
            elif event_type == "disabled":
                esp32_event = ESP32_DISABLED
            else:
                return  # only forward start/end/enabled/disabled
            
            # Format timestamp to readable format (Month Day, Hour:Minute AM/PM)
            formatted_time = "Unknown"
            timestamp_candidates = []
            if event_type == "start":
                timestamp_candidates = ["start_time", "timestamp"]
            elif event_type == "end":
                timestamp_candidates = ["end_time", "timestamp"]
            elif event_type in ("enabled", "disabled", "idle"):
                timestamp_candidates = ["timestamp", "enabled_at", "disabled_at", "updated_at"]
            timestamp_value = None
            for key in timestamp_candidates:
                if tool_data.get(key):
                    timestamp_value = tool_data.get(key)
                    break
            
            if timestamp_value:
                try:
                    from datetime import datetime, timedelta
                    dt = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
                    dt = dt + timedelta(hours=self.config["timezone_offset_hours"])
                    formatted_time = dt.strftime("%b %d, %I:%M %p")
                    logger.debug(f"Parsed timestamp: {timestamp_value} -> {formatted_time}")
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp '{timestamp_value}': {e}")
                    formatted_time = "Invalid Time"
            
            # User labels: active = "User", idle/disabled = "Last User"
            if user_display_name:
                self.last_users[str(tool_id)] = user_display_name
            user_label = "User" if esp32_event == ESP32_ACTIVE else "Last User"
            time_label = "Enabled Since" if esp32_event != ESP32_DISABLED else "Disabled Since"
            
            # Create minimal message for ESP32 - only fields the display uses (config.h: active/idle/disabled)
            esp32_message = {
                "event_type": esp32_event,
                "in_use": esp32_event == ESP32_ACTIVE,
                "timestamp": formatted_time,
                "time_label": time_label,
                "user_label": user_label,
                "user_name": user_display_name,
                "tool_name": tool_name,
            }
            
            esp32_topic = f"nemo/esp32/{tool_id}/status"
            payload_json = json.dumps(esp32_message)
            logger.info(f"📤 outbound {esp32_topic} | {payload_json}")
            result = self.mqtt_client_esp32.publish(esp32_topic, payload_json, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ {tool_name} (ID: {tool_id}): {esp32_event} → ESP32")
            else:
                logger.error(f"❌ Failed to forward tool {tool_id} status: {result.rc} ({self.get_mqtt_error_description(result.rc)})")
                
        except Exception as e:
            logger.error(f"Error processing tool status for {tool_identifier}: {e}")
    
    def process_overall_status(self, overall_data: dict):
        """Process overall status update and forward to ESP32 displays"""
        try:
            # Forward to ESP32 displays using ESP32 client (port 1883)
            esp32_topic = "nemo/esp32/overall"
            payload_json = json.dumps(overall_data)
            logger.info(f"📤 outbound {esp32_topic} | {payload_json}")
            result = self.mqtt_client_esp32.publish(esp32_topic, payload_json, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ overall → ESP32")
            else:
                logger.warning(f"Failed to forward overall status: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error processing overall status: {e}")
    
    
    async def start(self):
        """Start the server"""
        logger.info("Starting NEMO Tool Display Server")
        try:
            await self.init_mqtt()
            
            self.running = True
            logger.info("Server ready — NEMO (1886) → ESP32 (1883)")
            
            # Start connection status monitor
            asyncio.create_task(self.connection_status_monitor())
            
            # Keep the server running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
            logger.exception("Full error details:")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources")
        
        if self.mqtt_client_nemo:
            self.mqtt_client_nemo.loop_stop()
            self.mqtt_client_nemo.disconnect()
        
        if self.mqtt_client_esp32:
            self.mqtt_client_esp32.loop_stop()
            self.mqtt_client_esp32.disconnect()
        
        self.running = False
        logger.info("Cleanup completed")


def validate_environment():
    """Validate that all required files and dependencies are present"""
    required_files = ['config.env']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        logger.error("Please ensure all required files are present before starting the server")
        return False
    return True


async def main():
    """Main entry point"""
    logger.info("NEMO Tool Display Server - Starting up")

    # Validate environment before starting
    if not validate_environment():
        logger.error("Environment validation failed. Exiting.")
        sys.exit(1)
    
    try:
        server = NEMOToolServer()
        await server.start()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.exception("Full error details:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
