#!/usr/bin/env python3
"""
Test Enhanced MQTT Messages
Demonstrates the new detailed message format for tools in use
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_enhanced_messages():
    """Test the enhanced message format"""
    api_url = "https://nemo.stanford.edu/api/tool_status/"
    nemo_token = os.getenv('NEMO_TOKEN')
    
    if not nemo_token:
        print("Error: NEMO_TOKEN not found in .env file")
        return
    
    headers = {
        'Authorization': f'Token {nemo_token}',
        'User-Agent': 'NEMO-Tool-Display/1.0',
        'Accept': 'application/json'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Fetched {len(data)} tools from Stanford NEMO API")
                    
                    # Find tools that are in use
                    in_use_tools = [tool for tool in data if tool.get('in_use', False)]
                    print(f"Found {len(in_use_tools)} tools currently in use")
                    
                    # Show enhanced message format for tools in use
                    for tool in in_use_tools[:3]:  # Show first 3 tools in use
                        print(f"\n{'='*60}")
                        print(f"Tool: {tool.get('name', 'Unknown')} (ID: {tool.get('id')})")
                        print(f"{'='*60}")
                        
                        # Simulate the enhanced message format
                        enhanced_message = {
                            'id': str(tool.get('id', '')),
                            'name': tool.get('name', 'Unknown Tool'),
                            'status': 'active',
                            'category': tool.get('category', ''),
                            'operational': tool.get('operational', False),
                            'problematic': tool.get('problematic', False),
                            'timestamp': datetime.now().isoformat(),
                            'user': {
                                'name': tool.get('operator_name', '') or tool.get('customer_name', ''),
                                'username': tool.get('operator_username', '') or tool.get('customer_username', ''),
                                'id': tool.get('operator_id', '') or tool.get('customer_id', '')
                            },
                            'usage': {
                                'start_time': tool.get('current_usage_start', ''),
                                'start_time_formatted': format_start_time(tool.get('current_usage_start', '')),
                                'usage_id': tool.get('current_usage_id', '')
                            }
                        }
                        
                        print("Enhanced MQTT Message:")
                        print(json.dumps(enhanced_message, indent=2))
                    
                    # Show idle tool format
                    idle_tools = [tool for tool in data if not tool.get('in_use', False) and tool.get('operational', False)]
                    if idle_tools:
                        print(f"\n{'='*60}")
                        print(f"Idle Tool Example: {idle_tools[0].get('name')} (ID: {idle_tools[0].get('id')})")
                        print(f"{'='*60}")
                        
                        idle_message = {
                            'id': str(idle_tools[0].get('id', '')),
                            'name': idle_tools[0].get('name', 'Unknown Tool'),
                            'status': 'idle',
                            'category': idle_tools[0].get('category', ''),
                            'operational': idle_tools[0].get('operational', False),
                            'problematic': idle_tools[0].get('problematic', False),
                            'timestamp': datetime.now().isoformat(),
                            'user': None,
                            'usage': None
                        }
                        
                        print("Idle Tool MQTT Message:")
                        print(json.dumps(idle_message, indent=2))
                    
                else:
                    print(f"Error: API returned status {response.status}")
        except Exception as e:
            print(f"Error: {e}")

def format_start_time(start_time_str: str) -> str:
    """Format start time to readable 12-hour format"""
    if not start_time_str:
        return ""
    
    try:
        # Parse the ISO format timestamp
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Format as "MMM DD, YYYY at HH:MM AM/PM"
        formatted_time = start_time.strftime("%b %d, %Y at %I:%M %p")
        return formatted_time
    except Exception as e:
        print(f"Error formatting start time {start_time_str}: {e}")
        return start_time_str  # Return original if formatting fails

if __name__ == "__main__":
    print("Enhanced MQTT Message Format Test")
    print("=" * 40)
    asyncio.run(test_enhanced_messages())
