# Enhanced MQTT Message Format

## Overview

The NEMO Tool Display system now supports enhanced MQTT messages that provide detailed information about tool usage, including user details, duration, and start times.

## Message Format

### For Tools in Use (Active Status)

```json
{
  "id": "113",
  "name": "aja2-evap",
  "status": "active",
  "category": "Exfab",
  "operational": true,
  "problematic": false,
  "timestamp": "2025-09-04T16:38:31.921508",
  "user": {
    "name": "Nate Safron",
    "username": "nsafron",
    "id": 80
  },
  "usage": {
    "start_time": "2025-09-04T16:32:25.612035-07:00",
    "start_time_formatted": "Sep 04, 2025 at 04:32 PM",
    "usage_id": 94451
  }
}
```

### For Idle Tools

```json
{
  "id": "148",
  "name": "3d-wax-printer",
  "status": "idle",
  "category": "Exfab",
  "operational": true,
  "problematic": false,
  "timestamp": "2025-09-04T16:38:31.921755",
  "user": null,
  "usage": null
}
```

## Field Descriptions

### Basic Tool Information
- **id**: Tool ID from Stanford NEMO system
- **name**: Human-readable tool name
- **status**: Tool status (`active`, `idle`, `maintenance`, `offline`)
- **category**: Tool category (e.g., "Exfab", "Photolithography")
- **operational**: Whether the tool is operational
- **problematic**: Whether the tool has reported problems
- **timestamp**: When this message was generated

### User Information (only when tool is in use)
- **user.name**: Full name of the person using the tool
- **user.username**: Stanford username
- **user.id**: Stanford user ID

### Usage Information (only when tool is in use)
- **usage.start_time**: ISO timestamp when usage started
- **usage.start_time_formatted**: Human-readable start time in 12-hour format (e.g., "Sep 04, 2025 at 04:32 PM")
- **usage.usage_id**: Unique usage session ID

## ESP32 Display Features

The ESP32 display now shows:

1. **Tool Name** - Large, prominent display
2. **Status** - Color-coded status indicator
3. **User Information** - When in use:
   - User's full name
   - Start time of current session (formatted as "Sep 04, 2025 at 04:32 PM")
4. **Tool Details** - ID and category
5. **Last Updated** - Timestamp of last data refresh

## MQTT Topics

- **Individual Tools**: `nemo/tools/{tool_id}/status`
- **Overall Status**: `nemo/tools/overall`
- **Server Status**: `nemo/server/status`

## Configuration

Set the tools with ESP32 displays in your `.env` file:

```bash
ESP32_DISPLAY_TOOLS=woollam,fiji2,savannah
```

This ensures MQTT messages are only published for tools that actually have displays listening.

## Benefits

1. **Efficient MQTT Usage** - Only publishes to tools with displays
2. **Rich Information** - Detailed user and usage data
3. **Real-time Updates** - Duration and status updates
4. **Easy Management** - Simple configuration for display tools
5. **Scalable** - Easy to add/remove tools as displays are deployed
