# NEMO Tool Display

IoT project with a small screen that can be connected to tools to display if they are on or off, and who they are in use by.

## Project Overview

The NEMO Tool Display system consists of:
- **VM Server**: Python application that polls an API for tool status and distributes data via MQTT
- **Display Nodes**: ESP32-based devices with OLED screens that receive and display tool status via MQTT

## Architecture

```
API Server → VM Server (Python) → MQTT Broker → ESP32 Display Nodes
```

## Quick Start

### Prerequisites

- Python 3.11+
- PlatformIO
- ESP32 development board
- OLED display (SSD1306 128x64)
- MQTT broker (Mosquitto)

### VM Server Setup

1. Navigate to the VM server directory:
   ```bash
   cd vm_server
   ```

2. Run the setup script:
   ```bash
   ./run.sh
   ```

3. Configure your environment by editing `.env`:
   ```bash
   cp config.env.example .env
   # Edit .env with your API and MQTT settings
   ```

4. Start the server:
   ```bash
   python main.py
   ```

### ESP32 Display Node Setup

1. Install PlatformIO:
   ```bash
   pip install platformio
   ```

2. Configure WiFi and MQTT settings in `platformio.ini`:
   ```ini
   build_flags = 
       -DWIFI_SSID="your_wifi_ssid"
       -DWIFI_PASSWORD="your_wifi_password"
       -DMQTT_BROKER="192.168.1.100"
   ```

3. Upload to ESP32:
   ```bash
   pio run --target upload
   ```

### Docker Setup (Alternative)

1. Start MQTT broker and server:
   ```bash
   docker-compose up -d
   ```

2. Check logs:
   ```bash
   docker-compose logs -f nemo-server
   ```

## Configuration

### VM Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `API_URL` | Tool status API endpoint | `http://localhost:8000/api/tools` |
| `API_KEY` | API authentication key | (empty) |
| `MQTT_BROKER` | MQTT broker address | `localhost` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `POLL_INTERVAL` | API polling interval (seconds) | `30` |

### ESP32 Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `WIFI_SSID` | WiFi network name | (required) |
| `WIFI_PASSWORD` | WiFi password | (required) |
| `MQTT_BROKER` | MQTT broker IP address | `192.168.1.100` |
| `DISPLAY_SDA` | I2C SDA pin | `21` |
| `DISPLAY_SCL` | I2C SCL pin | `22` |

## MQTT Topics

- `nemo/tools/{tool_id}/status` - Individual tool status
- `nemo/tools/overall` - Overall system status

### Message Format

```json
{
  "id": "drill_001",
  "name": "Cordless Drill",
  "status": "active",
  "user": "John Doe",
  "last_updated": "2024-01-15T10:30:00",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Testing

### Test API Data
```bash
cd vm_server
python test_api.py
```

### Test MQTT Communication
```bash
cd vm_server
python mqtt_test.py [broker_ip] [duration_seconds]
```

## Hardware Requirements

### ESP32 Display Node
- ESP32 development board
- SSD1306 OLED display (128x64)
- Jumper wires
- Breadboard (optional)

### Wiring
```
ESP32    →  OLED
GPIO 21  →  SDA
GPIO 22  →  SCL
3.3V     →  VCC
GND      →  GND
```

## Development

### Project Structure
```
├── vm_server/           # Python VM server
│   ├── main.py         # Main server application
│   ├── test_api.py     # API testing utilities
│   ├── mqtt_test.py    # MQTT testing utilities
│   └── requirements.txt
├── src/                # ESP32 source code
│   └── main.cpp        # Display node firmware
├── include/            # ESP32 headers
│   └── config.h        # Configuration constants
├── platformio.ini      # PlatformIO configuration
├── docker-compose.yml  # Docker setup
└── mqtt/              # MQTT broker configuration
```

### Adding New Tools

1. Update your API to include new tool data
2. The VM server will automatically detect and publish new tools
3. Display nodes will show new tools as they receive MQTT messages

## Troubleshooting

### Common Issues

1. **WiFi Connection Failed**
   - Check SSID and password in `platformio.ini`
   - Ensure WiFi network is 2.4GHz (ESP32 doesn't support 5GHz)

2. **MQTT Connection Failed**
   - Verify MQTT broker IP address
   - Check if MQTT broker is running
   - Ensure firewall allows MQTT port (1883)

3. **Display Not Working**
   - Check I2C wiring (SDA/SCL pins)
   - Verify display address (usually 0x3C)
   - Check power supply (3.3V)

4. **API Connection Issues**
   - Verify API URL and authentication
   - Check network connectivity from VM
   - Review API response format

### Logs

- VM Server: `vm_server/nemo_server.log`
- MQTT Broker: `mqtt/log/mosquitto.log`
- ESP32: Serial monitor (115200 baud)

## License

MIT License - see LICENSE file for details