#!/usr/bin/env python3
"""
Test script for NEMO Tool Display API
Simulates tool status data for testing
"""

import json
import random
import time
from datetime import datetime
from typing import List, Dict

def generate_test_tools() -> List[Dict]:
    """Generate test tool data"""
    tools = [
        {
            "id": "drill_001",
            "name": "Cordless Drill",
            "status": random.choice(["active", "idle", "maintenance"]),
            "user": random.choice(["John Doe", "Jane Smith", "Bob Johnson", ""]),
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": "saw_002", 
            "name": "Circular Saw",
            "status": random.choice(["active", "idle", "maintenance"]),
            "user": random.choice(["Alice Brown", "Charlie Wilson", ""]),
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": "wrench_003",
            "name": "Impact Wrench",
            "status": random.choice(["active", "idle", "maintenance"]),
            "user": random.choice(["David Lee", "Sarah Davis", ""]),
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": "multimeter_004",
            "name": "Digital Multimeter",
            "status": random.choice(["active", "idle", "maintenance"]),
            "user": random.choice(["Mike Taylor", "Lisa Anderson", ""]),
            "last_updated": datetime.now().isoformat()
        }
    ]
    
    return tools

def simulate_api_response():
    """Simulate API response"""
    return {
        "tools": generate_test_tools(),
        "timestamp": datetime.now().isoformat(),
        "total_count": 4
    }

if __name__ == "__main__":
    print("NEMO Tool Display - Test Data Generator")
    print("=" * 40)
    
    # Generate and display test data
    data = simulate_api_response()
    print(json.dumps(data, indent=2))
    
    print("\nIndividual tool statuses:")
    for tool in data["tools"]:
        status_icon = "🔧" if tool["status"] == "active" else "⏸️" if tool["status"] == "idle" else "🔧"
        user_info = f" (User: {tool['user']})" if tool["user"] else " (Available)"
        print(f"{status_icon} {tool['name']}: {tool['status']}{user_info}")
