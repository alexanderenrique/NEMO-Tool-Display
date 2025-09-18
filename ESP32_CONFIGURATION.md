# ESP32 Display Configuration Guide

This guide explains how to configure ESP32 displays for specific tools in the NEMO Tool Display system.

## Important: Single Source of Truth

The tool name (`TARGET_TOOL_NAME`) should be defined in **only one place**:
- **PlatformIO**: In `platformio.ini` build flags (recommended)
- **Arduino IDE**: In your sketch file

**Do NOT** define it in `include/config.h` as this creates conflicts.

## Quick Configuration

Each ESP32 display needs to be configured for a specific tool. The configuration is done at compile time using build flags.

### Method 1: Using PlatformIO (Recommended)

Edit `platformio.ini` and modify the build flags:

```ini
; MQTT Configuration
build_flags = 
    -DMQTT_BROKER="192.168.1.100"
    -DMQTT_PORT=8883
    -DMQTT_CLIENT_ID="nemo_display_%d"
    -DMQTT_TOPIC_PREFIX="nemo/esp32"
    -DMQTT_USE_SSL=true
    -DTARGET_TOOL_NAME="woollam"  ; Change this to your tool name
```

### Method 2: Using Arduino IDE

Add these defines to your sketch (NOT in `include/config.h`):

```cpp
#define TARGET_TOOL_NAME "woollam"  // Change to your tool name
#define MQTT_BROKER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_USE_SSL false
```

**Note**: The `TARGET_TOOL_NAME` should only be defined in one place - either in `platformio.ini` build flags or in your Arduino sketch, not in `include/config.h`.

## Tool-Specific Configurations

### For Woollam Tool
```ini
-DTARGET_TOOL_NAME="woollam"
```

### For Fiji2 Tool
```ini
-DTARGET_TOOL_NAME="fiji2"
```

### For Savannah Tool
```ini
-DTARGET_TOOL_NAME="savannah"
```

### For Custom Tool
```ini
-DTARGET_TOOL_NAME="your_tool_name"
```

## Complete Configuration Example

Here's a complete `platformio.ini` configuration for a Woollam display:

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
upload_speed = 921600

; MQTT Configuration
build_flags = 
    -DMQTT_BROKER="192.168.1.100"
    -DMQTT_PORT=1883
    -DMQTT_CLIENT_ID="nemo_display_woollam"
    -DMQTT_TOPIC_PREFIX="nemo/esp32"
    -DMQTT_USE_SSL=false
    -DTARGET_TOOL_NAME="woollam"

; WiFi Configuration
build_flags = 
    -DWIFI_SSID="your_wifi_ssid"
    -DWIFI_PASSWORD="your_wifi_password"

; Display Configuration (480x320 TFT)
build_flags = 
    -DDISPLAY_WIDTH=480
    -DDISPLAY_HEIGHT=320
    -DDISPLAY_SDA=21
    -DDISPLAY_SCL=22
    -DDISPLAY_CS=5
    -DDISPLAY_DC=17
    -DDISPLAY_RST=16

; Libraries
lib_deps = 
    WiFi
    PubSubClient
    ArduinoJson
    TFT_eSPI
    Wire
    SPI

; Upload settings
upload_port = /dev/ttyUSB0
```

## How It Works

1. **Tool Filtering**: Each ESP32 display subscribes to `nemo/esp32/+/status` but only processes messages for its configured tool.

2. **Message Flow**:
   ```
   NEMO Backend → VM Server → ESP32 Display (filtered by tool name)
   ```

3. **Local Network**: ESP32s connect directly to the MQTT broker on port 1883 (no SSL needed for LAN).

4. **Display Updates**: The display updates immediately when a message for the configured tool is received.

## Setting Up Multiple Displays

To set up multiple displays for different tools:

1. **Create separate build configurations** in `platformio.ini`:

```ini
[env:woollam_display]
platform = espressif32
board = esp32dev
framework = arduino
build_flags = 
    -DTARGET_TOOL_NAME="woollam"
    -DMQTT_CLIENT_ID="nemo_display_woollam"
    ; ... other flags

[env:fiji2_display]
platform = espressif32
board = esp32dev
framework = arduino
build_flags = 
    -DTARGET_TOOL_NAME="fiji2"
    -DMQTT_CLIENT_ID="nemo_display_fiji2"
    ; ... other flags

[env:savannah_display]
platform = espressif32
board = esp32dev
framework = arduino
build_flags = 
    -DTARGET_TOOL_NAME="savannah"
    -DMQTT_CLIENT_ID="nemo_display_savannah"
    ; ... other flags
```

2. **Build and upload each configuration**:
   ```bash
   pio run -e woollam_display -t upload
   pio run -e fiji2_display -t upload
   pio run -e savannah_display -t upload
   ```

## Testing

After configuring and uploading:

1. **Check Serial Monitor**: The ESP32 will show which tool it's configured for:
   ```
   NEMO Tool Display Starting...
   Configured for tool: woollam
   ```

2. **Verify MQTT Connection**: Look for successful MQTT connection messages.

3. **Test Message Reception**: Send a test message from the VM server and verify the display updates.

## Troubleshooting

### Display Shows "No Tool Data"
- Check if the VM server is running
- Verify the tool name matches exactly (case-insensitive)
- Check MQTT connection status

### MQTT Connection Failed
- Ensure the VM server is running
- Check that port 1883 is accessible
- Verify the MQTT broker is running

### Wrong Tool Displayed
- Double-check the `TARGET_TOOL_NAME` configuration
- Rebuild and re-upload the firmware
- Check the VM server's `ESP32_DISPLAY_TOOLS` configuration

## Network Requirements

- **WiFi**: ESP32 must connect to the same network as the VM server
- **MQTT Broker**: Must be accessible on port 1883
- **VM Server**: Must be running and configured for the specific tool
