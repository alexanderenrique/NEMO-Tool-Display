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
        self.api_url = os.getenv('API_URL', 'http://localhost:8000/api/tools')
        self.api_key = os.getenv('API_KEY', '')
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_username = os.getenv('MQTT_USERNAME', '')
        self.mqtt_password = os.getenv('MQTT_PASSWORD', '')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '30'))  # seconds
        
        self.mqtt_client = None
        self.session = None
        self.running = False
        
    async def init_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client()
        
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
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
    
    async def init_http_session(self):
        """Initialize HTTP session for API calls"""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
                'Content-Type': 'application/json'
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info("HTTP session initialized")
    
    async def fetch_tool_status(self) -> Optional[List[Dict]]:
        """Fetch tool status from API"""
        try:
            async with self.session.get(self.api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched {len(data.get('tools', []))} tools")
                    return data.get('tools', [])
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching tool status: {e}")
            return None
    
    def publish_tool_status(self, tools: List[Dict]):
        """Publish tool status to MQTT"""
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            logger.error("MQTT client not connected")
            return
        
        try:
            # Publish individual tool status
            for tool in tools:
                topic = f"nemo/tools/{tool.get('id', 'unknown')}/status"
                payload = json.dumps({
                    'id': tool.get('id'),
                    'name': tool.get('name'),
                    'status': tool.get('status', 'unknown'),
                    'user': tool.get('user'),
                    'last_updated': tool.get('last_updated', datetime.now().isoformat()),
                    'timestamp': datetime.now().isoformat()
                })
                
                self.mqtt_client.publish(topic, payload, qos=1)
                logger.debug(f"Published status for tool {tool.get('id')}")
            
            # Publish overall status
            overall_topic = "nemo/tools/overall"
            overall_payload = json.dumps({
                'total_tools': len(tools),
                'active_tools': len([t for t in tools if t.get('status') == 'active']),
                'timestamp': datetime.now().isoformat()
            })
            
            self.mqtt_client.publish(overall_topic, overall_payload, qos=1)
            logger.info(f"Published status for {len(tools)} tools")
            
        except Exception as e:
            logger.error(f"Error publishing tool status: {e}")
    
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
