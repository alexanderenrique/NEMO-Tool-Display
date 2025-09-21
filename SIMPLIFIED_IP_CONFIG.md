# Simplified IP Configuration for NEMO Tool Display

## Overview

The system now uses a **hybrid approach** for IP configuration:

- **VM Server**: Dynamic IP detection (auto-detects current network IP)
- **ESP32**: Fixed broker IP (manually configured in `platformio.ini`)

## Why This Approach?

- **MQTT Broker IP must be known at compile time** for ESP32
- **Broker IP should be stable** and not change frequently
- **VM Server can adapt** to different networks automatically

## Configuration

### ESP32 Configuration (Fixed)
The ESP32 broker IP is set in `platformio.ini`:

```ini
build_flags = 
    -DMQTT_BROKER="10.0.0.31"  # Change this to your computer's IP
    -DMQTT_PORT=1883
    -DMQTT_CLIENT_ID="nemo_display_001"
    -DTARGET_TOOL_NAME="woollam"
```

**To change the broker IP:**
1. Edit `platformio.ini`
2. Update the `MQTT_BROKER` value
3. Recompile: `pio run -t upload`

### VM Server Configuration (Dynamic)
The VM server automatically detects its IP address on startup.

**Manual override** (if needed):
```bash
# Set in vm_server/config.env
MQTT_BROKER=192.168.1.100
```

## Usage

### Quick Start
```bash
# 1. Update ESP32 broker IP in platformio.ini if needed
# 2. Compile and upload ESP32
pio run -t upload

# 3. Start the system
./vm_server/quick_restart.sh
```

### Full Setup
```bash
# Complete setup with IP detection
./vm_server/setup_and_start.sh
```

## Network Requirements

- **ESP32 and VM Server** must be on the same network
- **MQTT Broker** runs on the VM Server's IP address
- **Port 1883** must be open for MQTT communication

## Troubleshooting

### ESP32 Can't Connect
1. **Check broker IP**: Ensure `platformio.ini` has the correct IP
2. **Verify network**: ESP32 and server must be on same network
3. **Check WiFi**: Update SSID/password in `src/main.cpp`

### VM Server Issues
1. **IP detection**: Check if server detects correct IP in logs
2. **Manual override**: Set `MQTT_BROKER` in `vm_server/config.env`
3. **Network connectivity**: Ensure server is connected to network

## Files

- **ESP32 Config**: `platformio.ini` (manual)
- **VM Server Config**: `vm_server/config.env` (auto-detected)
- **Dynamic Setup**: `vm_server/dynamic_ip_setup.py` (VM server only)

## Benefits

✅ **Simple**: ESP32 uses fixed, stable broker IP  
✅ **Flexible**: VM server adapts to different networks  
✅ **Reliable**: No complex dynamic compilation needed  
✅ **Maintainable**: Clear separation of concerns
