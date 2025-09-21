# NEMO Tool Display

IoT system with ESP32 displays that show tool status and who is using them.

## Quick Start

### 1. VM Server Setup
```bash
cd vm_server
./setup_and_start.sh
```

### 2. ESP32 Configuration
Edit `platformio.ini`:
```ini
build_flags = 
    -DWIFI_SSID="your_wifi"
    -DWIFI_PASSWORD="your_password"
    -DMQTT_BROKER="192.168.1.100"  # Your computer's IP
    -DTARGET_TOOL_NAME="woollam"    # Tool name for this display
```

### 3. Upload Firmware
```bash
pio run -t upload
```

## Hardware Connections

**TFT Display (480x320):**
```
ESP32 Pin  →  Display Pin
GPIO 23    →  MOSI
GPIO 18    →  SCLK
GPIO 5     →  CS
GPIO 17    →  DC
GPIO 16    →  RST
3.3V       →  VCC
GND        →  GND
```

## Configuration

### VM Server (.env)
```env
API_URL=http://your-api-server/api/tools
API_KEY=your_api_key
MQTT_BROKER=localhost
MQTT_PORT=1883
ESP32_DISPLAY_TOOLS=woollam,fiji2,savannah
```

### ESP32 (platformio.ini)
```ini
build_flags = 
    -DWIFI_SSID="your_wifi"
    -DWIFI_PASSWORD="your_password"
    -DMQTT_BROKER="192.168.1.100"
    -DTARGET_TOOL_NAME="woollam"
```

## MQTT Topics

- `nemo/esp32/{tool_name}/status` - Tool status for ESP32 displays
- `nemo/server/status` - Server status

## Message Format

```json
{
  "id": "113",
  "name": "woollam",
  "status": "active",
  "category": "Exfab",
  "operational": true,
  "problematic": false,
  "timestamp": "2025-01-15T10:30:00",
  "user": {
    "name": "John Doe",
    "username": "johndoe",
    "id": 80
  },
  "usage": {
    "start_time": "2025-01-15T10:30:00",
    "start_time_formatted": "Jan 15, 2025 at 10:30 AM",
    "usage_id": 12345
  }
}
```

## Troubleshooting

**ESP32 can't connect:**
- Check WiFi credentials in `platformio.ini`
- Verify MQTT broker IP address
- Ensure ESP32 and server are on same network

**VM Server issues:**
- Check logs: `tail -f vm_server/mqtt/log/mosquitto.log`
- Verify API URL and key in `.env`
- Test MQTT: `mosquitto_sub -h localhost -t "nemo/#" -v`

**Display not working:**
- Check wiring connections
- Verify TFT_eSPI library is installed
- Monitor serial output: `pio device monitor`

## Project Structure

```
├── vm_server/           # Python server
│   ├── main.py         # Main application
│   ├── setup_and_start.sh
│   └── requirements.txt
├── src/main.cpp        # ESP32 firmware
├── include/config.h    # ESP32 configuration
└── platformio.ini     # Build configuration
```