#!/usr/bin/env python3
"""
Test script to check if Stanford NEMO API supports filtering
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_api_filtering():
    """Test different filtering approaches"""
    api_url = "https://nemo.stanford.edu/api/tool_status/"
    nemo_token = os.getenv('NEMO_TOKEN')
    
    print(f"Debug: NEMO_TOKEN = {nemo_token[:10] if nemo_token else 'None'}...")
    
    if not nemo_token:
        print("Error: NEMO_TOKEN not found")
        return
    
    # Try different authentication methods
    auth_methods = [
        {'Token': nemo_token},
        {'Authorization': f'Token {nemo_token}'},
        {'Authorization': f'Bearer {nemo_token}'},
    ]
    
    headers_base = {
        'User-Agent': 'NEMO-Tool-Display/1.0',
        'Accept': 'application/json'
    }
    
    # Test different filtering approaches
    test_cases = [
        ("No filter", api_url),
        ("Query parameter ?name=woollam", f"{api_url}?name=woollam"),
        ("Query parameter ?tool=woollam", f"{api_url}?tool=woollam"),
        ("Query parameter ?id=161", f"{api_url}?id=161"),
        ("Query parameter ?visible=true", f"{api_url}?visible=true"),
        ("Query parameter ?in_use=true", f"{api_url}?in_use=true"),
        ("Query parameter ?category=Characterization", f"{api_url}?category=Characterization"),
    ]
    
    # Test each authentication method
    for auth_method in auth_methods:
        print(f"\n=== Testing auth method: {list(auth_method.keys())[0]} ===")
        headers = {**headers_base, **auth_method}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for test_name, test_url in test_cases:
                print(f"\n{test_name}:")
                print(f"URL: {test_url}")
                
                try:
                    async with session.get(test_url) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f"Response type: {type(data)}")
                            
                            if isinstance(data, list):
                                print(f"Number of tools: {len(data)}")
                                if len(data) > 0:
                                    print(f"First tool: {data[0].get('name', 'Unknown')}")
                                    if len(data) <= 5:
                                        print("All tools:")
                                        for tool in data:
                                            print(f"  - {tool.get('name')} (id: {tool.get('id')})")
                            else:
                                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            
                            # If we found a working auth method, break out
                            if response.status == 200:
                                print("✅ Found working authentication method!")
                                return
                        else:
                            error_text = await response.text()
                            print(f"Error: {error_text}")
                            
                except Exception as e:
                    print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_filtering())
