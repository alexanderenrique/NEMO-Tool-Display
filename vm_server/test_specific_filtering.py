#!/usr/bin/env python3
"""
Test specific filtering options for Stanford NEMO API
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_specific_filtering():
    """Test specific filtering options"""
    api_url = "https://nemo.stanford.edu/api/tool_status/"
    nemo_token = os.getenv('NEMO_TOKEN')
    
    headers = {
        'Authorization': f'Token {nemo_token}',
        'User-Agent': 'NEMO-Tool-Display/1.0',
        'Accept': 'application/json'
    }
    
    # Test specific filtering options
    test_cases = [
        ("All tools", api_url),
        ("Filter by name=woollam", f"{api_url}?name=woollam"),
        ("Filter by id=161", f"{api_url}?id=161"),
        ("Filter by visible=true", f"{api_url}?visible=true"),
        ("Filter by in_use=true", f"{api_url}?in_use=true"),
        ("Filter by category=Characterization", f"{api_url}?category=Characterization"),
        ("Filter by problematic=true", f"{api_url}?problematic=true"),
        ("Filter by operational=true", f"{api_url}?operational=true"),
    ]
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for test_name, test_url in test_cases:
            print(f"\n{test_name}:")
            print(f"URL: {test_url}")
            
            try:
                async with session.get(test_url) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"Number of tools: {len(data)}")
                        
                        if len(data) > 0:
                            print("Tools found:")
                            for tool in data[:5]:  # Show first 5 tools
                                print(f"  - {tool.get('name')} (id: {tool.get('id')}, visible: {tool.get('visible')}, in_use: {tool.get('in_use')})")
                            
                            if len(data) > 5:
                                print(f"  ... and {len(data) - 5} more tools")
                    else:
                        error_text = await response.text()
                        print(f"Error: {error_text}")
                        
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_filtering())
