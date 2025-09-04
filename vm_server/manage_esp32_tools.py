#!/usr/bin/env python3
"""
ESP32 Display Tools Manager
Helps manage the list of tools that have ESP32 displays attached
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def list_all_tools():
    """List all available tools from the API"""
    api_url = "https://nemo.stanford.edu/api/tool_status/"
    nemo_token = os.getenv('NEMO_TOKEN')
    
    if not nemo_token:
        print("Error: NEMO_TOKEN not found in .env file")
        return []
    
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
                    return data
                else:
                    print(f"Error: API returned status {response.status}")
                    return []
        except Exception as e:
            print(f"Error: {e}")
            return []

def display_tools(tools, filter_type=None):
    """Display tools in a nice format"""
    if not tools:
        print("No tools found")
        return
    
    print(f"\nFound {len(tools)} tools:")
    print("=" * 60)
    
    for tool in tools:
        name = tool.get('name', 'Unknown')
        tool_id = tool.get('id', 'N/A')
        visible = tool.get('visible', False)
        in_use = tool.get('in_use', False)
        operational = tool.get('operational', False)
        problematic = tool.get('problematic', False)
        category = tool.get('category', 'Unknown')
        
        # Status indicator
        if in_use:
            status = "🔧 IN USE"
        elif problematic:
            status = "⚠️  PROBLEMATIC"
        elif not operational:
            status = "❌ OFFLINE"
        else:
            status = "✅ IDLE"
        
        # Visibility indicator
        visibility = "👁️ " if visible else "🙈"
        
        print(f"{visibility} {name:<25} (ID: {tool_id:<3}) {status:<15} [{category}]")

def main():
    print("ESP32 Display Tools Manager")
    print("=" * 40)
    
    # Get current ESP32 tools from .env
    esp32_tools_str = os.getenv('ESP32_DISPLAY_TOOLS', '')
    current_esp32_tools = [name.strip().lower() for name in esp32_tools_str.split(',') if name.strip()]
    
    print(f"Current ESP32 display tools: {current_esp32_tools}")
    
    # Get all tools from API
    print("\nFetching all tools from Stanford NEMO API...")
    all_tools = asyncio.run(list_all_tools())
    
    if not all_tools:
        print("Failed to fetch tools from API")
        return
    
    # Show different filtered views
    print("\n1. ALL TOOLS:")
    display_tools(all_tools)
    
    print("\n2. VISIBLE TOOLS ONLY:")
    visible_tools = [tool for tool in all_tools if tool.get('visible', False)]
    display_tools(visible_tools)
    
    print("\n3. ACTIVE TOOLS (in use or problematic):")
    active_tools = [tool for tool in all_tools if tool.get('in_use', False) or tool.get('problematic', False)]
    display_tools(active_tools)
    
    print("\n4. CURRENT ESP32 DISPLAY TOOLS:")
    esp32_tools = [tool for tool in all_tools if tool.get('name', '').lower() in current_esp32_tools]
    display_tools(esp32_tools)
    
    # Show tools that are currently active and have ESP32 displays
    print("\n5. ACTIVE ESP32 DISPLAY TOOLS (currently in use/problematic):")
    active_esp32_tools = [tool for tool in esp32_tools if tool.get('in_use', False) or tool.get('problematic', False)]
    display_tools(active_esp32_tools)
    
    # Suggestions
    print("\n" + "=" * 60)
    print("SUGGESTIONS:")
    print(f"- You have {len(current_esp32_tools)} ESP32 displays configured")
    print(f"- {len(active_esp32_tools)} of them are currently active")
    print(f"- {len(visible_tools)} tools are visible in the system")
    
    if len(current_esp32_tools) > 10:
        print("⚠️  You have many ESP32 displays - consider if you need all of them")
    
    if len(active_esp32_tools) == 0:
        print("ℹ️  No ESP32 displays are currently active - all tools are idle")

if __name__ == "__main__":
    main()
