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
from datetime import datetime
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nemo_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NEMOToolServer:
    """Main server class for NEMO Tool Display system"""
    
    def __init__(self):
        self.mqtt_broker = os.getenv('MQTT_BROKER', '192.168.1.100')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '8883'))
        self.mqtt_username = os.getenv('MQTT_USERNAME', '')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', '')
        self.mqtt_use_ssl = os.getenv('MQTT_USE_SSL', 'true').lower() == 'true'
        
        # ESP32 Display Configuration
        esp32_tools_str = os.getenv('ESP32_DISPLAY_TOOLS', '')
        self.esp32_display_tools = [name.strip().lower() for name in esp32_tools_str.split(',') if name.strip()]
        
        self.mqtt_client = None
        self.running = False
        
    async def init_mqtt(self):
        """Initialize MQTT client for receiving tool status and distributing to ESP32 displays"""
        self.mqtt_client = mqtt.Client()
        
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Configure SSL if enabled
        if self.mqtt_use_ssl:
            import ssl
            # For self-signed certificates, we need to disable certificate verification
            self.mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                                   cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS, 
                                   ciphers=None)
            self.mqtt_client.tls_insecure_set(True)  # Allow self-signed certificates
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_publish = self.on_mqtt_publish
        
        # Set keepalive and other options for LAN reliability
        self.mqtt_client.keepalive = 60
        self.mqtt_client.will_set("nemo/server/status", "offline", qos=1, retain=True)
        
        try:
            protocol = "mqtts" if self.mqtt_use_ssl else "mqtt"
            logger.info(f"Connecting to MQTT broker at {protocol}://{self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait a moment for connection to establish
            await asyncio.sleep(1)
            
            if self.mqtt_client.is_connected():
                # Subscribe to tool status updates from NEMO backend
                self.mqtt_client.subscribe("nemo/backend/tools/+/status", qos=1)
                self.mqtt_client.subscribe("nemo/backend/tools/overall", qos=1)
                
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
        """MQTT disconnection callback"""
        logger.warning(f"MQTT disconnected with code {rc}")
    
    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"Message published with mid: {mid}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages from NEMO backend"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"Received message on topic {topic}")
            
            # Handle individual tool status updates
            if topic.startswith("nemo/backend/tools/") and topic.endswith("/status"):
                tool_id = topic.split("/")[-2]  # Extract tool ID from topic
                self.process_tool_status(tool_id, payload)
            
            # Handle overall status updates
            elif topic == "nemo/backend/tools/overall":
                self.process_overall_status(payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def process_tool_status(self, tool_id: str, tool_data: dict):
        """Process individual tool status update and forward to ESP32 displays"""
        try:
            # Check if this tool has an ESP32 display
            tool_name = tool_data.get('name', '').lower()
            if self.esp32_display_tools and tool_name not in self.esp32_display_tools:
                logger.debug(f"Tool {tool_name} not configured for ESP32 display, skipping")
                return
            
            # Forward to ESP32 display topic
            esp32_topic = f"nemo/esp32/{tool_id}/status"
            payload_json = json.dumps(tool_data)
            
            result = self.mqtt_client.publish(esp32_topic, payload_json, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Forwarded status for tool {tool_id} to ESP32 display")
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
        
        try:
            await self.init_mqtt()
            
            self.running = True
            logger.info("Server started, listening for tool status updates via MQTT")
            
            # Log which tools we're monitoring
            if self.esp32_display_tools:
                logger.info(f"Monitoring ESP32 displays for: {', '.join(self.esp32_display_tools)}")
            else:
                logger.warning("No ESP32 display tools configured - will forward all tool updates")
            
            # Keep the server running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
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


async def main():
    """Main entry point"""
    server = NEMOToolServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
