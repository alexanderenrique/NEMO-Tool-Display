#!/usr/bin/env python3
import json
from datetime import datetime, timedelta

nemo_message = {
    "event": "tool_usage_end",
    "usage_id": 235,
    "user_id": 1,
    "user_name": "Alex Denton (admin)",
    "tool_id": 1,
    "tool_name": "woollam",
    "start_time": "2025-10-14T19:15:14.691967+00:00",
    "end_time": "2025-10-14T19:16:30.123456+00:00"
}

config = {'timezone_offset_hours': -7, 'max_name_length': 14}
event_type = "end"

# Parse user
full_user_name = nemo_message.get('user_name', '')
user_display_name = full_user_name.split('(')[0].strip() if '(' in full_user_name else full_user_name

# Parse timestamp (use end_time for end events)
timestamp_field = 'end_time'
timestamp_value = nemo_message.get(timestamp_field)
dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
dt = dt + timedelta(hours=config['timezone_offset_hours'])
formatted_time = dt.strftime("%b %d, %I:%M %p")

esp32_message = {
    "event_type": event_type,
    "timestamp": formatted_time,
    "time_label": "Ended",
    "user_label": "Last User",
    "user_name": user_display_name
}

print("END Event Test:")
print(json.dumps(esp32_message, indent=2))
