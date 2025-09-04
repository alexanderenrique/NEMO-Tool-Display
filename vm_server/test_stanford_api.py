#!/usr/bin/env python3
"""
Test script for Stanford NEMO API
Examines the API structure and response format
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_stanford_api():
    """Test the Stanford NEMO API"""
    api_url = "https://nemo.stanford.edu/api/tool_status/"
    nemo_token = os.getenv('NEMO_TOKEN')
    
    if not nemo_token:
        print("Error: NEMO_TOKEN not found in .env file")
        print("Please add NEMO_TOKEN=your_token_here to your .env file")
        return
    
    print("Testing Stanford NEMO API")
    print("=" * 40)
    print(f"API URL: {api_url}")
    print(f"Token: {nemo_token[:10]}..." if len(nemo_token) > 10 else f"Token: {nemo_token}")
    print()
    
    # Try different authentication methods
    auth_methods = [
        {'Token': nemo_token},
        {'Authorization': f'Token {nemo_token}'},
        {'Authorization': f'Bearer {nemo_token}'},
        {'X-API-Key': nemo_token},
        {'API-Key': nemo_token}
    ]
    
    headers_base = {
        'User-Agent': 'NEMO-Tool-Display/1.0',
        'Accept': 'application/json'
    }
    
    # Test each authentication method
    for i, auth_headers in enumerate(auth_methods):
        print(f"\n{i+1}. Testing authentication method: {list(auth_headers.keys())[0]}")
        headers = {**headers_base, **auth_headers}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(api_url) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ SUCCESS! Response type: {type(data)}")
                        print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        # Pretty print the response
                        print("\n   Full API Response:")
                        print(json.dumps(data, indent=2, default=str))
                        
                        # Analyze the structure
                        print("\n   Data Analysis:")
                        if isinstance(data, list):
                            print(f"   - Array with {len(data)} items")
                            if data:
                                print(f"   - First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
                        elif isinstance(data, dict):
                            print(f"   - Object with {len(data)} keys")
                            for key, value in data.items():
                                if isinstance(value, list):
                                    print(f"   - {key}: Array with {len(value)} items")
                                else:
                                    print(f"   - {key}: {type(value).__name__}")
                        
                        return  # Found working auth method, exit
                        
                    else:
                        print(f"   ❌ Failed: {response.status}")
                        error_text = await response.text()
                        print(f"   Error details: {error_text}")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print("\n❌ No working authentication method found!")

if __name__ == "__main__":
    asyncio.run(test_stanford_api())
