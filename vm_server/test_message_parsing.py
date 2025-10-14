#!/usr/bin/env python3
"""
Test message parsing and trimming logic
"""

import json
from datetime import datetime, timedelta

# Sample NEMO message
nemo_message = {
    "event": "tool_usage_start",
    "usage_id": 235,
    "user_id": 1,
    "user_name": "Alex Denton (admin)",
    "tool_id": 1,
    "tool_name": "woollam",
    "start_time": "2025-10-14T19:15:14.691967+00:00",
    "end_time": None
}

# Configuration
config = {
    'timezone_offset_hours': -7,
    'max_name_length': 14
}

# Extract tool name and event type
tool_name = "woollam"
event_type = "start"

print("=" * 80)
print("TESTING MESSAGE PARSING AND TRIMMING")
print("=" * 80)
print(f"\n📥 ORIGINAL NEMO MESSAGE ({len(json.dumps(nemo_message))} bytes):")
print(json.dumps(nemo_message, indent=2))

# Parse the message (same logic as main.py)
tool_data = nemo_message

# Extract user name from NEMO message
full_user_name = tool_data.get('user_name', '')
print(f"\n👤 Raw user_name from NEMO: '{full_user_name}'")

# Parse name - NEMO sends "FirstName LastName (role)" format
user_display_name = full_user_name
if full_user_name and '(' in full_user_name:
    # Remove role part: "Alex Denton (admin)" -> "Alex Denton"
    user_display_name = full_user_name.split('(')[0].strip()
    print(f"👤 After removing role: '{user_display_name}'")

# Trim to max length if needed
if len(user_display_name) > config['max_name_length']:
    # Try first name only
    first_name = user_display_name.split()[0] if ' ' in user_display_name else user_display_name
    user_display_name = first_name[:config['max_name_length']]
    print(f"👤 Trimmed to max length ({config['max_name_length']}): '{user_display_name}'")
else:
    print(f"👤 Name length OK ({len(user_display_name)} <= {config['max_name_length']})")

# Format timestamp
formatted_time = "Unknown"
timestamp_field = 'start_time' if event_type == 'start' else 'end_time'
timestamp_value = tool_data.get(timestamp_field)

print(f"\n⏰ Timestamp field: '{timestamp_field}' = '{timestamp_value}'")

if timestamp_value:
    try:
        # Parse the ISO timestamp
        dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
        print(f"⏰ Parsed UTC time: {dt}")
        
        # Apply timezone offset
        dt = dt + timedelta(hours=config['timezone_offset_hours'])
        print(f"⏰ Adjusted to timezone (UTC{config['timezone_offset_hours']}): {dt}")
        
        # Format as "Oct 14, 12:10 PM"
        formatted_time = dt.strftime("%b %d, %I:%M %p")
        print(f"⏰ Formatted for display: '{formatted_time}'")
    except Exception as e:
        print(f"❌ Failed to parse timestamp: {e}")
        formatted_time = "Invalid Time"

# Handle user tracking for start/end events
user_label = "User"
if event_type in ["start", "end"]:
    if event_type == "start":
        user_label = "User"
    else:  # end
        user_label = "Last User"

# Determine time label
time_label = "Time"
if event_type == "enabled":
    time_label = "Enabled Since"
elif event_type == "disabled":
    time_label = "Disabled Since"
elif event_type == "start":
    time_label = "Started"
elif event_type == "end":
    time_label = "Ended"

print(f"\n🏷️  Labels: user_label='{user_label}', time_label='{time_label}'")

# Create trimmed ESP32 message
esp32_message = {
    "event_type": event_type,
    "timestamp": formatted_time,
    "time_label": time_label,
    "user_label": user_label,
    "user_name": user_display_name
}

print(f"\n📤 TRIMMED ESP32 MESSAGE ({len(json.dumps(esp32_message))} bytes):")
print(json.dumps(esp32_message, indent=2))

# Calculate size reduction
original_size = len(json.dumps(nemo_message))
trimmed_size = len(json.dumps(esp32_message))
reduction = original_size - trimmed_size
reduction_pct = (reduction / original_size) * 100

print(f"\n📊 SIZE COMPARISON:")
print(f"   Original: {original_size} bytes")
print(f"   Trimmed:  {trimmed_size} bytes")
print(f"   Saved:    {reduction} bytes ({reduction_pct:.1f}% reduction)")
print("=" * 80)

