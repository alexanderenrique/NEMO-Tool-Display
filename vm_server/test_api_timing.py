#!/usr/bin/env python3
"""
API Timing Test
Measures how long it takes to retrieve the entire tool status from Stanford NEMO API
"""

import asyncio
import aiohttp
import time
import os
from dotenv import load_dotenv

load_dotenv()

async def test_api_timing():
    """Test API response time"""
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
    
    print("Stanford NEMO API Timing Test")
    print("=" * 40)
    print(f"API URL: {api_url}")
    print(f"Token: {nemo_token[:10]}...")
    print()
    
    # Test multiple requests to get average timing
    times = []
    tool_counts = []
    
    for i in range(5):
        print(f"Test {i+1}/5: ", end="", flush=True)
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        end_time = time.time()
                        
                        duration = end_time - start_time
                        times.append(duration)
                        tool_counts.append(len(data))
                        
                        print(f"✅ {duration:.2f}s - {len(data)} tools")
                    else:
                        print(f"❌ HTTP {response.status}")
                        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    if times:
        print()
        print("Results Summary:")
        print("-" * 20)
        print(f"Average time: {sum(times)/len(times):.2f} seconds")
        print(f"Fastest time: {min(times):.2f} seconds")
        print(f"Slowest time: {max(times):.2f} seconds")
        print(f"Average tools: {sum(tool_counts)/len(tool_counts):.0f} tools")
        print()
        
        # Performance analysis
        avg_time = sum(times)/len(times)
        if avg_time < 1.0:
            print("🚀 Excellent performance! (< 1 second)")
        elif avg_time < 2.0:
            print("✅ Good performance (1-2 seconds)")
        elif avg_time < 5.0:
            print("⚠️  Moderate performance (2-5 seconds)")
        else:
            print("🐌 Slow performance (> 5 seconds)")
        
        print()
        print("Polling interval recommendations:")
        if avg_time < 1.0:
            print("  - 30 seconds: Very comfortable")
            print("  - 15 seconds: Good")
            print("  - 10 seconds: Aggressive but manageable")
        elif avg_time < 2.0:
            print("  - 30 seconds: Comfortable")
            print("  - 15 seconds: Good")
            print("  - 10 seconds: May cause delays")
        else:
            print("  - 60 seconds: Recommended minimum")
            print("  - 30 seconds: May cause delays")
            print("  - Consider caching or filtering")

if __name__ == "__main__":
    asyncio.run(test_api_timing())
