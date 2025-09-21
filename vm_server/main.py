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
        
        # Load tool ID to name mappings from YAML file
        self.tool_id_to_name = self.load_tool_mappings()
        logger.info(f"Tool mappings loaded: {self.tool_id_to_name}")
        
        # Track last users for each tool
        self.last_users = {}  # tool_id -> user_name
        
        self.mqtt_client = None
        self.running = False
    
    def load_tool_mappings(self) -> Dict[str, str]:
        """Load tool ID to name mappings from YAML file"""
        mappings_file = 'tool_mappings.yaml'
        
        # Check if YAML is available
        if not YAML_AVAILABLE:
            logger.error("PyYAML not available. Please install it: pip install PyYAML")
            raise ImportError("PyYAML is required for tool mappings")
        
        # Check if mappings file exists
        if not os.path.exists(mappings_file):
            logger.error(f"Tool mappings file {mappings_file} not found!")
            logger.error("Please create the tool_mappings.yaml file with your tool mappings.")
            raise FileNotFoundError(f"Tool mappings file {mappings_file} not found")
        
        try:
            with open(mappings_file, 'r') as file:
                mappings = yaml.safe_load(file)
                
                if not mappings:
                    logger.error(f"Tool mappings file {mappings_file} is empty or invalid")
                    raise ValueError("Empty or invalid tool mappings file")
                
                logger.info(f"Loaded {len(mappings)} tool mappings from {mappings_file}")
                
                # Convert all keys to strings to ensure consistent lookup
                string_mappings = {str(k): v for k, v in mappings.items()}
                
                # Log the mappings for debugging
                for tool_id, tool_name in string_mappings.items():
                    logger.info(f"Mapped tool ID {tool_id} to tool name '{tool_name}'")
                
                return string_mappings
                
        except Exception as e:
            logger.error(f"Error loading tool mappings from {mappings_file}: {e}")
            raise
        
    async def init_mqtt(self):
        """Initialize MQTT client for receiving tool status and distributing to ESP32 displays"""
        self.mqtt_client = mqtt.Client()
        
        if self.config['mqtt_username'] and self.config['mqtt_password']:
            self.mqtt_client.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
        
        # Configure SSL if enabled
        if self.config['mqtt_use_ssl']:
            import ssl
            # Use the actual CA certificate for proper SSL connection
            ca_cert_path = "mqtt/certs/ca.crt"
            if os.path.exists(ca_cert_path):
                self.mqtt_client.tls_set(ca_certs=ca_cert_path, certfile=None, keyfile=None, 
                                       cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, 
                                       ciphers=None)
                logger.info(f"Using SSL with CA certificate: {ca_cert_path}")
            else:
                # Fallback to insecure mode if CA cert not found
                self.mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                                       cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS, 
                                       ciphers=None)
                self.mqtt_client.tls_insecure_set(True)
                logger.warning("CA certificate not found, using insecure SSL mode")
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_publish = self.on_mqtt_publish
        
        # Set keepalive and other options for LAN reliability
        self.mqtt_client.keepalive = 60
        self.mqtt_client.will_set("nemo/server/status", "offline", qos=1, retain=True)
        
        try:
            protocol = "mqtts" if self.config['mqtt_use_ssl'] else "mqtt"
            logger.info(f"Connecting to MQTT broker at {protocol}://{self.config['mqtt_broker']}:{self.config['mqtt_port']}")
            self.mqtt_client.connect(self.config['mqtt_broker'], self.config['mqtt_port'], 60)
            self.mqtt_client.loop_start()
            
            # Wait a moment for connection to establish
            await asyncio.sleep(1)
            
            if self.mqtt_client.is_connected():
                # Subscribe to tool status updates from NEMO backend
                self.mqtt_client.subscribe("nemo/tools/+/+", qos=1)  # Subscribe to all tool events
                self.mqtt_client.subscribe("nemo/tools/overall", qos=1)
                
                # Publish server online status
                self.mqtt_client.publish("nemo/server/status", "online", qos=1, retain=True)
                logger.info(f"Successfully connected to MQTT broker with SSL and subscribed to tool status updates")
            else:
                raise Exception("MQTT connection not established")
                
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("MQTT connection established")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback with auto-reconnect"""
        logger.warning(f"MQTT disconnected with code {rc}")
        
        # Publish offline status
        if self.mqtt_client:
            try:
                self.mqtt_client.publish("nemo/server/status", "offline", qos=1, retain=True)
            except:
                pass
        
        # Auto-reconnect if not intentionally disconnected
        if rc != 0 and self.running:
            logger.info("Attempting to reconnect to MQTT broker...")
            try:
                self.mqtt_client.reconnect()
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
    
    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"Message published with mid: {mid}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages from NEMO backend"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.info(f"Received message on topic: {topic}")
            
            # Handle individual tool status updates
            if topic.startswith("nemo/tools/") and len(topic.split("/")) >= 4:
                parts = topic.split("/")
                tool_id = parts[2]  # Extract tool ID from topic (e.g., "nemo/tools/1/disabled")
                event_type = parts[3]  # Extract event type (e.g., "disabled", "enabled", etc.)
                
                logger.info(f"Processing tool message: ID={tool_id}, event_type={event_type}")
                
                # Convert tool ID to tool name for ESP32 topic
                logger.info(f"Looking up tool ID '{tool_id}' in mappings: {self.tool_id_to_name}")
                tool_name = self.tool_id_to_name.get(tool_id)
                if tool_name:
                    logger.info(f"Found mapping: tool ID {tool_id} -> {tool_name}")
                    logger.info(f"Calling process_tool_status with: tool_id={tool_id}, event_type={event_type}, tool_name={tool_name}")
                    self.process_tool_status(tool_id, payload, event_type, tool_name)
                else:
                    logger.warning(f"No tool name mapping found for tool ID {tool_id}")
                    logger.warning(f"Available mappings: {list(self.tool_id_to_name.keys())}")
            
            # Handle overall status updates
            elif topic == "nemo/tools/overall":
                self.process_overall_status(payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def process_tool_status(self, tool_id: str, tool_data: dict, event_type: str = None, tool_name: str = None):
        """Process individual tool status update and forward to ESP32 displays"""
        logger.info(f"process_tool_status called: tool_id={tool_id}, event_type={event_type}, tool_name={tool_name}")
        try:
            # Use provided tool_name or extract from data
            if not tool_name:
                tool_name = tool_data.get('tool', {}).get('name', '').lower()
                if not tool_name and 'name' in tool_data:
                    tool_name = tool_data.get('name', '').lower()
            
            # Check if this tool has an ESP32 display (tool_name must be in our mappings)
            if tool_name not in self.tool_id_to_name.values():
                logger.debug(f"Tool {tool_name} not configured for ESP32 display, skipping")
                return
            
            # Create a lightweight message for ESP32 displays - only essential data
            tool_info = tool_data.get('tool', {})
            user_info = tool_data.get('user', {})
            interlock_info = tool_data.get('interlock', {})
            
            # Format timestamp to readable format (Month Day, Hour:Minute AM/PM)
            formatted_time = "Unknown"
            if tool_data.get('timestamp'):
                try:
                    from datetime import datetime, timedelta
                    # Parse the ISO timestamp
                    dt = datetime.fromisoformat(tool_data['timestamp'].replace('Z', '+00:00'))
                    # Apply timezone offset
                    dt = dt + timedelta(hours=self.config['timezone_offset_hours'])
                    # Format as "Jan 15, 2:30 PM"
                    formatted_time = dt.strftime("%b %d, %I:%M %p")
                    logger.debug(f"Original timestamp: {tool_data['timestamp']}, Adjusted time: {formatted_time}")
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {e}")
                    formatted_time = "Invalid Time"
            
            # Handle user tracking and label switching
            current_user = user_info.get('first_name', '')
            current_last_name = user_info.get('last_name', '')
            
            # Join first and last name into a single string, but limit to configured length
            full_name = current_user
            if current_last_name:
                potential_full_name = f"{current_user} {current_last_name}"
                # If combined name is longer than configured max, use only first name
                if len(potential_full_name) > self.config['max_name_length']:
                    full_name = current_user
                    logger.info(f"Name too long ({len(potential_full_name)} chars): '{potential_full_name}' -> using first name only: '{current_user}'")
                else:
                    full_name = potential_full_name
            
            user_label = "User"
            user_display_name = full_name
            
            if event_type == "enabled" and current_user:
                # Tool enabled - show current user and update last user
                self.last_users[tool_id] = full_name
                user_label = "User"
                user_display_name = full_name
            elif event_type == "disabled" and tool_id in self.last_users:
                # Tool disabled - show last user
                user_label = "Last User"
                user_display_name = self.last_users[tool_id]
            elif event_type == "disabled" and not tool_id in self.last_users:
                # Tool disabled but no last user recorded - show current user as last
                user_label = "Last User"
                user_display_name = full_name
                if current_user:
                    self.last_users[tool_id] = full_name
            
            # Determine time label based on event type
            time_label = "Time"
            if event_type == "enabled":
                time_label = "Enabled Since"
            elif event_type == "disabled":
                time_label = "Disabled Since"
            
            # Create minimal message for ESP32 - only essential fields
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
            logger.info(f"ESP32 message size: {len(payload_json)} bytes")
            logger.info(f"ESP32 message content: {payload_json}")
            
            result = self.mqtt_client.publish(esp32_topic, payload_json, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Successfully forwarded {event_type} status for tool {tool_name} (ID: {tool_id}) to ESP32 display")
            else:
                logger.warning(f"Failed to forward tool {tool_id} status: {result.rc}")
                
        except Exception as e:
            logger.error(f"Error processing tool status for {tool_id}: {e}")
    
    def process_overall_status(self, overall_data: dict):
        """Process overall status update and forward to ESP32 displays"""
        try:
            # Forward to ESP32 displays
            esp32_topic = "nemo/esp32/overall"
            payload_json = json.dumps(overall_data)
            
            result = self.mqtt_client.publish(esp32_topic, payload_json, qos=1, retain=True)
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
            # Validate tool mappings before starting
            if not self.tool_id_to_name:
                logger.error("No tool mappings found! Please check tool_mappings.yaml")
                return
            
            await self.init_mqtt()
            
            self.running = True
            logger.info("Server started successfully, listening for tool status updates via MQTT")
            
            # Log which tools we're monitoring
            tool_names = list(self.tool_id_to_name.values())
            logger.info(f"Monitoring ESP32 displays for: {', '.join(tool_names)}")
            logger.info(f"Total tools configured: {len(tool_names)}")
            
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
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
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
