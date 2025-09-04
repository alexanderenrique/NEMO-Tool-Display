#!/usr/bin/env python3

"""
NEMO Tool Display - VM Server
Main application that pings API for tool status and distributes via MQTT
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
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
        self.api_url = os.getenv('API_URL', 'https://nemo.stanford.edu/api/tool_status/')
        self.nemo_token = os.getenv('NEMO_TOKEN', '')
        self.mqtt_broker = os.getenv('MQTT_BROKER', '192.168.1.100')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_username = os.getenv('MQTT_USERNAME', '')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', '')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '30'))  # seconds
        self.bind_address = os.getenv('BIND_ADDRESS', '0.0.0.0')
        
        # ESP32 Display Configuration
        esp32_tools_str = os.getenv('ESP32_DISPLAY_TOOLS', '')
        self.esp32_display_tools = [name.strip().lower() for name in esp32_tools_str.split(',') if name.strip()]
        
        # Legacy filtering options (kept for compatibility)
        self.filter_visible_only = os.getenv('FILTER_VISIBLE_ONLY', 'false').lower() == 'true'
        self.specific_tools = os.getenv('SPECIFIC_TOOLS', '').split(',') if os.getenv('SPECIFIC_TOOLS') else []
        self.filter_active_only = os.getenv('FILTER_ACTIVE_ONLY', 'false').lower() == 'true'
        
        self.mqtt_client = None
        self.session = None
        self.running = False
        
    async def init_mqtt(self):
        """Initialize MQTT client for LAN distribution"""
        self.mqtt_client = mqtt.Client()
        
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_publish = self.on_mqtt_publish
        
        # Set keepalive and other options for LAN reliability
        self.mqtt_client.keepalive = 60
        self.mqtt_client.will_set("nemo/server/status", "offline", qos=1, retain=True)
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait a moment for connection to establish
            await asyncio.sleep(1)
            
            if self.mqtt_client.is_connected():
                # Publish server online status
                self.mqtt_client.publish("nemo/server/status", "online", qos=1, retain=True)
                logger.info(f"Successfully connected to MQTT broker for LAN distribution")
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
    
    async def init_http_session(self):
        """Initialize HTTP session for API calls"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'NEMO-Tool-Display/1.0',
            'Accept': 'application/json'
        }
        
        if self.nemo_token:
            headers['Token'] = self.nemo_token
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info("HTTP session initialized with NEMO token")
    
    def _apply_filters(self, tools: List[Dict]) -> List[Dict]:
        """Apply client-side filtering to tools - prioritize ESP32 display tools"""
        filtered_tools = tools.copy()
        
        # Primary filter: Only tools that have ESP32 displays attached
        if self.esp32_display_tools:
            filtered_tools = [tool for tool in filtered_tools 
                            if tool.get('name', '').lower() in self.esp32_display_tools]
            logger.debug(f"After ESP32 display filter: {len(filtered_tools)} tools")
            
            # Log which tools we're monitoring
            tool_names = [tool.get('name', 'Unknown') for tool in filtered_tools]
            logger.info(f"Monitoring ESP32 displays for: {', '.join(tool_names)}")
        else:
            logger.warning("No ESP32 display tools configured - will publish all tools")
        
        # Legacy filters (only apply if ESP32 filter is not used)
        if not self.esp32_display_tools:
            # Filter 1: Visible tools only
            if self.filter_visible_only:
                filtered_tools = [tool for tool in filtered_tools if tool.get('visible', False)]
                logger.debug(f"After visible filter: {len(filtered_tools)} tools")
            
            # Filter 2: Specific tools by name
            if self.specific_tools:
                specific_tools_clean = [name.strip().lower() for name in self.specific_tools if name.strip()]
                if specific_tools_clean:
                    filtered_tools = [tool for tool in filtered_tools 
                                    if tool.get('name', '').lower() in specific_tools_clean]
                    logger.debug(f"After specific tools filter: {len(filtered_tools)} tools")
            
            # Filter 3: Active tools only (in_use or problematic)
            if self.filter_active_only:
                filtered_tools = [tool for tool in filtered_tools 
                                if tool.get('in_use', False) or tool.get('problematic', False)]
                logger.debug(f"After active filter: {len(filtered_tools)} tools")
        
        return filtered_tools
    
    def _format_start_time(self, start_time_str: str) -> str:
        """Format start time to readable 12-hour format"""
        if not start_time_str:
            return ""
        
        try:
            from datetime import datetime
            # Parse the ISO format timestamp
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            
            # Format as "MMM DD, YYYY at HH:MM AM/PM"
            formatted_time = start_time.strftime("%b %d, %Y at %I:%M %p")
            return formatted_time
        except Exception as e:
            logger.debug(f"Error formatting start time {start_time_str}: {e}")
            return start_time_str  # Return original if formatting fails
    
    async def fetch_tool_status(self) -> Optional[List[Dict]]:
        """Fetch tool status from Stanford NEMO API"""
        try:
            async with self.session.get(self.api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched {len(data)} tools from Stanford NEMO API")
                    
                    # Apply client-side filtering
                    filtered_data = self._apply_filters(data)
                    logger.info(f"Filtered {len(data)} tools down to {len(filtered_data)} tools")
                    
                    # Convert Stanford API format to our display format
                    converted_tools = []
                    for tool in filtered_data:
                        # Map Stanford status to our display status
                        if tool.get('in_use', False):
                            status = 'active'
                        elif tool.get('problematic', False):
                            status = 'maintenance'
                        elif not tool.get('operational', True):
                            status = 'offline'
                        else:
                            status = 'idle'
                        
                        # Build detailed tool information
                        converted_tool = {
                            'id': str(tool.get('id', '')),
                            'name': tool.get('name', 'Unknown Tool'),
                            'status': status,
                            'category': tool.get('category', ''),
                            'visible': tool.get('visible', False),
                            'operational': tool.get('operational', False),
                            'problematic': tool.get('problematic', False),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Add detailed user information if tool is in use
                        if tool.get('in_use', False):
                            converted_tool.update({
                                'user': {
                                    'name': tool.get('operator_name', '') or tool.get('customer_name', ''),
                                    'username': tool.get('operator_username', '') or tool.get('customer_username', ''),
                                    'id': tool.get('operator_id', '') or tool.get('customer_id', '')
                                },
                                'usage': {
                                    'start_time': tool.get('current_usage_start', ''),
                                    'start_time_formatted': self._format_start_time(tool.get('current_usage_start', '')),
                                    'usage_id': tool.get('current_usage_id', '')
                                }
                            })
                        else:
                            # For idle/problematic/offline tools, minimal user info
                            converted_tool.update({
                                'user': None,
                                'usage': None
                            })
                        converted_tools.append(converted_tool)
                    
                    logger.info(f"Converted {len(converted_tools)} tools for display")
                    return converted_tools
                else:
                    logger.error(f"Stanford NEMO API request failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching tool status from Stanford NEMO API: {e}")
            return None
    
    def publish_tool_status(self, tools: List[Dict]):
        """Publish tool status to MQTT for LAN distribution"""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            logger.error("MQTT client not connected - cannot publish to LAN")
            return
        
        try:
            # Publish individual tool status with retry logic
            for tool in tools:
                topic = f"nemo/tools/{tool.get('id', 'unknown')}/status"
                
                # Create enhanced payload based on tool status
                payload = {
                    'id': tool.get('id'),
                    'name': tool.get('name'),
                    'status': tool.get('status', 'unknown'),
                    'category': tool.get('category', ''),
                    'operational': tool.get('operational', False),
                    'problematic': tool.get('problematic', False),
                    'timestamp': tool.get('timestamp', datetime.now().isoformat())
                }
                
                # Add detailed user info if tool is in use
                if tool.get('status') == 'active' and tool.get('user'):
                    payload.update({
                        'user': tool.get('user'),
                        'usage': tool.get('usage')
                    })
                else:
                    payload.update({
                        'user': None,
                        'usage': None
                    })
                
                payload_json = json.dumps(payload)
                
                # Publish with QoS 1 for reliability over LAN
                result = self.mqtt_client.publish(topic, payload_json, qos=1, retain=True)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published status for tool {tool.get('id')} to LAN")
                else:
                    logger.warning(f"Failed to publish tool {tool.get('id')}: {result.rc}")
            
            # Publish overall status
            overall_topic = "nemo/tools/overall"
            overall_payload = json.dumps({
                'total_tools': len(tools),
                'active_tools': len([t for t in tools if t.get('status') == 'active']),
                'idle_tools': len([t for t in tools if t.get('status') == 'idle']),
                'maintenance_tools': len([t for t in tools if t.get('status') == 'maintenance']),
                'timestamp': datetime.now().isoformat()
            })
            
            result = self.mqtt_client.publish(overall_topic, overall_payload, qos=1, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published overall status for {len(tools)} tools to LAN")
            else:
                logger.warning(f"Failed to publish overall status: {result.rc}")
            
        except Exception as e:
            logger.error(f"Error publishing tool status to LAN: {e}")
    
    async def run_cycle(self):
        """Run one polling cycle"""
        logger.info("Starting polling cycle")
        
        tools = await self.fetch_tool_status()
        if tools is not None:
            self.publish_tool_status(tools)
        else:
            logger.warning("No tool data received, skipping MQTT publish")
    
    async def start(self):
        """Start the server"""
        logger.info("Starting NEMO Tool Display Server")
        
        try:
            await self.init_http_session()
            await self.init_mqtt()
            
            self.running = True
            logger.info(f"Server started, polling every {self.poll_interval} seconds")
            
            while self.running:
                await self.run_cycle()
                await asyncio.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources")
        
        if self.session:
            await self.session.close()
        
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
