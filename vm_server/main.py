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

# Optional YAML import - only needed if tool_mappings.yaml exists
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Load environment variables
load_dotenv('config.env')

# Configuration validation and loading
def load_config():
    """Load and validate configuration from environment variables"""
    config = {}
    
    # MQTT Configuration
    config['mqtt_broker'] = os.getenv('MQTT_BROKER')
    config['mqtt_port'] = int(os.getenv('MQTT_PORT', '1883'))
    config['mqtt_use_ssl'] = os.getenv('MQTT_USE_SSL', 'false').lower() == 'true'
    config['mqtt_username'] = os.getenv('MQTT_USERNAME', '')
    config['mqtt_password'] = os.getenv('MQTT_PASSWORD', '')
    
    # Display Configuration
    config['timezone_offset_hours'] = int(os.getenv('TIMEZONE_OFFSET_HOURS', '-7'))
    config['max_name_length'] = int(os.getenv('MAX_NAME_LENGTH', '13'))
    
    # Logging Configuration
    config['log_level'] = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Validate required configurations
    if not config['mqtt_broker']:
        raise ValueError("MQTT_BROKER must be set in config.env")
    
    if config['mqtt_port'] < 1 or config['mqtt_port'] > 65535:
        raise ValueError("MQTT_PORT must be between 1 and 65535")
    
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
        
        # Auto-detect IP address if MQTT_BROKER is not set
        if not self.config['mqtt_broker']:
            detected_ip = get_local_ip()
            self.config['mqtt_broker'] = detected_ip
            logger.info(f"Auto-detected IP address: {detected_ip}")
        
        # Log configuration
        logger.info(f"Using MQTT broker: {self.config['mqtt_broker']}:{self.config['mqtt_port']}")
        logger.info(f"Timezone offset: {self.config['timezone_offset_hours']} hours")
        logger.info(f"Max name length: {self.config['max_name_length']} characters")
        logger.info(f"Log level: {self.config['log_level']}")
        
        # TOOL MAPPING SYSTEM - COMMENTED OUT (NEMO sends tool names directly in topics)
        # We now use the tool name directly from the MQTT topic instead of looking up mappings
        # # Load tool ID to name mappings from YAML file
        # self.tool_id_to_name = self.load_tool_mappings()
        # logger.info(f"Tool mappings loaded: {len(self.tool_id_to_name)} tools configured")
        # 
        # # Create reverse mapping: tool_name -> tool_id
        # self.tool_name_to_id = {name: id for id, name in self.tool_id_to_name.items()}
        
        # Track last users for each tool (keyed by tool_name now)
        self.last_users = {}  # tool_name -> user_name
        
        self.mqtt_client_nemo = None  # Client for receiving from NEMO on port 1886
        self.mqtt_client_esp32 = None  # Client for publishing to ESP32s on port 1883
        self.running = False
    
    # TOOL MAPPING SYSTEM - COMMENTED OUT (NEMO sends tool names directly in topics)
    # def load_tool_mappings(self) -> Dict[str, str]:
    #     """Load tool ID to name mappings from YAML file"""
    #     mappings_file = 'tool_mappings.yaml'
    #     
    #     # Check if YAML is available
    #     if not YAML_AVAILABLE:
    #         logger.error("PyYAML not available. Please install it: pip install PyYAML")
    #         raise ImportError("PyYAML is required for tool mappings")
    #     
    #     # Check if mappings file exists
    #     if not os.path.exists(mappings_file):
    #         logger.error(f"Tool mappings file {mappings_file} not found!")
    #         logger.error("Please create the tool_mappings.yaml file with your tool mappings.")
    #         raise FileNotFoundError(f"Tool mappings file {mappings_file} not found")
    #     
    #     try:
    #         with open(mappings_file, 'r') as file:
    #             mappings = yaml.safe_load(file)
    #             
    #             if not mappings:
    #                 logger.error(f"Tool mappings file {mappings_file} is empty or invalid")
    #                 raise ValueError("Empty or invalid tool mappings file")
    #             
    #             logger.info(f"Loaded {len(mappings)} tool mappings from {mappings_file}")
    #             
    #             # Convert all keys to strings to ensure consistent lookup
    #             string_mappings = {str(k): v for k, v in mappings.items()}
    #             
    #             # Log the mappings for debugging (only in DEBUG mode)
    #             if logger.level <= logging.DEBUG:
    #                 for tool_id, tool_name in string_mappings.items():
    #                     logger.debug(f"Mapped tool ID {tool_id} to tool name '{tool_name}'")
    #             
    #             return string_mappings
    #             
    #     except Exception as e:
    #         logger.error(f"Error loading tool mappings from {mappings_file}: {e}")
    #         raise

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
            # Connect NEMO client to port 1886
            protocol = "mqtts" if self.config['mqtt_use_ssl'] else "mqtt"
            nemo_port = self.config['mqtt_port']
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
            logger.info("📥 Subscribed to NEMO tool status updates")
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
                
                # Check SSL port if certificates exist
                ssl_port_listening = False
                if os.path.exists("mqtt/certs/ca.crt"):
                    ssl_port_listening = self.check_port_listening(8883)
                
                # Only log if there are issues
                if not nemo_connected or not esp32_connected or not port_1883_listening or not port_1886_listening or (os.path.exists("mqtt/certs/ca.crt") and not ssl_port_listening):
                    logger.info(f"🔍 CONNECTION STATUS CHECK:")
                    logger.info(f"   📥 NEMO (1886):  {'✅ Connected' if nemo_connected else '❌ Disconnected'} {'✅ Port Open' if port_1886_listening else '❌ Port Closed'}")
                    logger.info(f"   📤 ESP32 (1883): {'✅ Connected' if esp32_connected else '❌ Disconnected'} {'✅ Port Open' if port_1883_listening else '❌ Port Closed'}")
                    if os.path.exists("mqtt/certs/ca.crt"):
                        logger.info(f"   🔒 SSL (8883):   {'✅ Port Open' if ssl_port_listening else '❌ Port Closed'}")
                
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
            ], cwd="/Users/adenton/Desktop/NEMO-Tool-Display/vm_server")
            
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
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"Received message on topic: {topic}")
            
            # Handle individual tool status updates
            if topic.startswith("nemo/tools/") and len(topic.split("/")) >= 4:
                parts = topic.split("/")
                tool_name = parts[2]  # Tool name from topic (e.g., "woollam" from "nemo/tools/woollam/start")
                event_type = parts[3]  # Extract event type (e.g., "start", "end", "enabled", "disabled")
                
                logger.info(f"Processing tool message: tool_name={tool_name}, event_type={event_type}")
                
                # Call process_tool_status with the tool_name directly
                self.process_tool_status(tool_name, payload, event_type, tool_name)
            
            # Handle overall status updates
            elif topic == "nemo/tools/overall":
                self.process_overall_status(payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def process_tool_status(self, tool_name: str, tool_data: dict, event_type: str = None, _unused: str = None):
        """Process individual tool status update and forward to ESP32 displays
        
        Args:
            tool_name: Name of the tool (used for both tracking and ESP32 topic)
            tool_data: The full message payload from NEMO
            event_type: The event type (start, end, enabled, disabled)
            _unused: Unused parameter (kept for backwards compatibility)
        """
        logger.info(f"process_tool_status called: tool_name={tool_name}, event_type={event_type}")
        try:
            # Parse NEMO message format:
            # {"event": "tool_usage_start", "usage_id": 232, "user_id": 1, 
            #  "user_name": "Alex Denton (admin)", "tool_id": 1, "tool_name": "woollam",
            #  "start_time": "2025-10-14T19:00:11.106294+00:00", "end_time": null}
            
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
                logger.info(f"Name too long, trimmed to: '{user_display_name}'")
            
            # Format timestamp to readable format (Month Day, Hour:Minute AM/PM)
            formatted_time = "Unknown"
            # NEMO uses 'start_time' for start events and 'end_time' for end events
            timestamp_field = 'start_time' if event_type == 'start' else 'end_time'
            timestamp_value = tool_data.get(timestamp_field)
            
            if timestamp_value:
                try:
                    from datetime import datetime, timedelta
                    # Parse the ISO timestamp
                    dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                    # Apply timezone offset
                    dt = dt + timedelta(hours=self.config['timezone_offset_hours'])
                    # Format as "Oct 14, 12:10 PM"
                    formatted_time = dt.strftime("%b %d, %I:%M %p")
                    logger.debug(f"Parsed timestamp: {timestamp_value} -> {formatted_time}")
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp '{timestamp_value}': {e}")
                    formatted_time = "Invalid Time"
            
            # Handle user tracking for start/end events
            user_label = "User"
            if event_type in ["start", "end"]:
                # Track the user for this tool
                if user_display_name:
                    self.last_users[tool_name] = user_display_name
                
                if event_type == "start":
                    user_label = "User"
                else:  # end
                    user_label = "Last User"
            
            # Determine time label based on event type
            time_label = "Time"
            if event_type == "enabled":
                time_label = "Enabled Since"
            elif event_type == "disabled":
                time_label = "Disabled Since"
            elif event_type == "start":
                time_label = "Started"
            elif event_type == "end":
                time_label = "Ended"
            
            # Create minimal message for ESP32 - only essential fields
            # This trimming is critical to avoid overloading ESP32 memory!
            # Original NEMO messages can be 1KB+, we trim to ~150 bytes
            esp32_message = {
                "event_type": event_type,
                "timestamp": formatted_time,
                "time_label": time_label,
                "user_label": user_label,
                "user_name": user_display_name
            }
            
            # Forward to ESP32 display topic using tool name
            esp32_topic = f"nemo/esp32/{tool_name}/status"
            payload_json = json.dumps(esp32_message)
            
            logger.info(f"Publishing to ESP32 topic: {esp32_topic}")
            logger.info(f"ESP32 message size: {len(payload_json)} bytes (trimmed from original)")
            logger.info(f"ESP32 message content: {payload_json}")
            
            # Publish using the ESP32 client (port 1883)
            result = self.mqtt_client_esp32.publish(esp32_topic, payload_json, qos=1, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Successfully forwarded {event_type} status for tool {tool_name} to ESP32 display")
            else:
                logger.error(f"❌ Failed to forward tool {tool_name} status: {result.rc} ({self.get_mqtt_error_description(result.rc)})")
                
        except Exception as e:
            logger.error(f"Error processing tool status for {tool_name}: {e}")
    
    def process_overall_status(self, overall_data: dict):
        """Process overall status update and forward to ESP32 displays"""
        try:
            # Forward to ESP32 displays using ESP32 client (port 1883)
            esp32_topic = "nemo/esp32/overall"
            payload_json = json.dumps(overall_data)
            
            result = self.mqtt_client_esp32.publish(esp32_topic, payload_json, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Forwarded overall status to ESP32 displays")
            else:
                logger.warning(f"Failed to forward overall status: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error processing overall status: {e}")
    
    
    async def start(self):
        """Start the server"""
        logger.info("Starting NEMO Tool Display Server")
        logger.info(f"Configuration: {self.config}")
        
        try:
            # (REMOVED) Validate tool mappings before starting - not needed anymore
            # if not self.tool_id_to_name:
            #     logger.error("No tool mappings found! Please check tool_mappings.yaml")
            #     return
            
            await self.init_mqtt()
            
            self.running = True
            logger.info("Server started successfully, listening for tool status updates via MQTT")
            
            # (REMOVED) Log which tools we're monitoring - now we forward ALL tool events
            # Tool names come directly from NEMO topics - no mapping file needed!
            logger.info("Forwarding all tool events from NEMO to ESP32 displays")
            
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
    required_files = ['config.env', 'tool_mappings.yaml']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        logger.error("Please ensure all required files are present before starting the server")
        return False
    
    # Check if YAML is available
    if not YAML_AVAILABLE:
        logger.error("PyYAML not available. Please install it: pip install PyYAML")
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
