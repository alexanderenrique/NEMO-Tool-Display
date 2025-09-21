# NEMO Tool Display

IoT system with ESP32 displays that show real-time tool status from the NEMO backend system. Displays show who is using tools, usage duration, and tool operational status.

## Quick Start

### 1. VM Server Setup
```bash
cd vm_server
./setup_and_start.sh
```

The setup script will:
- Install and configure Mosquitto MQTT broker
- Set up Python virtual environment with dependencies
- **Automatically generate tool mappings from NEMO API** (if token configured)
- Configure SSL/TLS (optional)
- Start MQTT broker and NEMO server

### 2. ESP32 Configuration
Edit `platformio.ini` with your network and MQTT settings:
```ini
build_flags = 
    -DWIFI_SSID="your_wifi"
    -DWIFI_PASSWORD="your_password"
    -DMQTT_BROKER="192.168.1.100"  # Your VM server's IP
    -DMQTT_PORT=1883               # MQTT port (1883 or 8883 for SSL)
    -DMQTT_USE_SSL=false           # Set to true if using SSL
    -DTARGET_TOOL_NAME="woollam"   # Tool name for this display
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

### VM Server (config.env)
```env
# MQTT Configuration
MQTT_BROKER=10.0.0.31
MQTT_PORT=1883
MQTT_USE_SSL=false
MQTT_USERNAME=
MQTT_PASSWORD=

# Display Configuration
TIMEZONE_OFFSET_HOURS=-7
MAX_NAME_LENGTH=13
LOG_LEVEL=INFO

# NEMO API Configuration
NEMO_API_URL=https://nemo.stanford.edu/api/tools/
NEMO_TOKEN=your_nemo_token_here
```

**Important:** Replace `your_nemo_token_here` with your actual NEMO API token to enable automatic tool mapping generation.

### ESP32 (platformio.ini)
```ini
build_flags = 
    -DWIFI_SSID="your_wifi"
    -DWIFI_PASSWORD="your_password"
    -DMQTT_BROKER="192.168.1.100"    # VM server IP
    -DMQTT_PORT=1883                 # MQTT port
    -DMQTT_USE_SSL=false             # SSL enabled/disabled
    -DTARGET_TOOL_NAME="woollam"     # Tool name for this display
```

## Tool Mapping System

The system automatically generates tool mappings from the NEMO API:

### Automatic Generation
- Tool mappings are generated automatically when the VM server starts
- Requires `NEMO_TOKEN` to be set in `config.env`
- Fetches all tools from `https://nemo.stanford.edu/api/tools/`
- Updates `tool_mappings.yaml` with current tool data

### Manual Generation
```bash
cd vm_server
source venv/bin/activate
python generate_tool_mappings.py --api
```

### Tool Mapping Format
The `tool_mappings.yaml` file maps NEMO tool IDs to display names:
```yaml
'1': aja-sputter
'10': nanoscribe
'11': form2-3d-printer
'113': aja2-evap
# ... (199+ tools)
```

## MQTT Topics

**Backend Input (from NEMO):**
- `nemo/backend/tools/{tool_id}/status` - Individual tool status
- `nemo/backend/tools/overall` - Overall system status

**ESP32 Output (to displays):**
- `nemo/esp32/{tool_name}/status` - Tool status for specific display
- `nemo/esp32/overall` - Overall status for all displays

**Server Status:**
- `nemo/server/status` - VM server health status

## Message Format

### Tool Status Message
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

### Overall Status Message
```json
{
  "total_tools": 199,
  "active_tools": 15,
  "available_tools": 180,
  "problematic_tools": 4,
  "timestamp": "2025-01-15T10:30:00"
}
```

## Setup Process Details

### VM Server Setup Steps
1. **Configuration Validation** - Checks for required files
2. **Install Mosquitto** - MQTT broker installation
3. **Stop Existing Processes** - Clean shutdown of running services
4. **Clean Configuration** - Remove old config and log files
5. **Create Mosquitto Config** - Generate broker configuration
6. **Test Configuration** - Verify MQTT functionality
7. **Set Up Python Environment** - Create venv and install dependencies
8. **Generate Tool Mappings** - Fetch tools from NEMO API
9. **Configure SSL Settings** - Optional SSL/TLS setup
10. **Set Up Environment File** - Create/update configuration
11. **Update Mosquitto for SSL** - Add SSL configuration if enabled
12. **Start MQTT Broker** - Launch Mosquitto
13. **Start NEMO Server** - Launch Python application

### ESP32 Setup Steps
1. **Configure WiFi** - Set SSID and password in `platformio.ini`
2. **Configure MQTT** - Set broker IP, port, and SSL settings
3. **Set Tool Name** - Specify which tool this display shows
4. **Upload Firmware** - Compile and flash to ESP32

## Troubleshooting

### ESP32 Issues
**Can't connect to WiFi:**
- Check WiFi credentials in `platformio.ini`
- Verify network is 2.4GHz (ESP32 doesn't support 5GHz)
- Check signal strength

**Can't connect to MQTT:**
- Verify MQTT broker IP address in `platformio.ini`
- Check MQTT port (1883 for non-SSL, 8883 for SSL)
- Ensure ESP32 and server are on same network
- Check SSL settings match between ESP32 and server

**Display not working:**
- Check wiring connections (see Hardware Connections)
- Verify TFT_eSPI library is installed
- Monitor serial output: `pio device monitor`

### VM Server Issues
**MQTT broker won't start:**
- Check logs: `tail -f vm_server/mqtt/log/mosquitto.log`
- Verify port 1883/8883 is not in use
- Check Mosquitto configuration: `mosquitto -c mqtt/config/mosquitto.conf -v`

**Tool mappings not updating:**
- Verify `NEMO_TOKEN` is set in `config.env`
- Check API connectivity: `curl -H "Authorization: Token YOUR_TOKEN" https://nemo.stanford.edu/api/tools/`
- Run manual generation: `python generate_tool_mappings.py --api`

**NEMO server issues:**
- Check Python dependencies: `pip install -r requirements.txt`
- Verify configuration in `config.env`
- Test MQTT: `mosquitto_sub -h localhost -t "nemo/#" -v`

### Network Issues
**ESP32 can't reach server:**
- Ensure both devices are on same network
- Check firewall settings on VM server
- Verify MQTT broker is listening on correct interface
- Test with: `mosquitto_pub -h SERVER_IP -t "test" -m "hello"`

## Monitoring and Debugging

### MQTT Monitoring
```bash
# Monitor all NEMO topics
mosquitto_sub -h localhost -t "nemo/#" -v

# Monitor specific tool
mosquitto_sub -h localhost -t "nemo/esp32/woollam/status" -v

# Monitor server status
mosquitto_sub -h localhost -t "nemo/server/status" -v
```

### Log Files
- **MQTT Broker:** `vm_server/mqtt/log/mosquitto.log`
- **NEMO Server:** Console output or `nemo_server.log`
- **ESP32:** Serial monitor output

### Testing MQTT
```bash
# Publish test message
mosquitto_pub -h localhost -t "nemo/test" -m "test message"

# Subscribe to test
mosquitto_sub -h localhost -t "nemo/test" -v
```

## Project Structure

```
├── vm_server/                    # Python server and configuration
│   ├── main.py                  # Main NEMO server application
│   ├── setup_and_start.sh      # Master setup and start script
│   ├── generate_tool_mappings.py # Tool mapping generator
│   ├── config.env              # Server configuration
│   ├── tool_mappings.yaml      # Tool ID to name mappings
│   ├── requirements.txt        # Python dependencies
│   ├── mqtt/                   # MQTT broker files
│   │   ├── config/mosquitto.conf
│   │   ├── data/               # Persistence data
│   │   └── log/                # Log files
│   └── venv/                   # Python virtual environment
├── src/main.cpp                # ESP32 firmware
├── include/                    # ESP32 configuration
│   ├── config.h               # ESP32 settings
│   └── lv_conf.h              # LVGL configuration
├── lib/                       # ESP32 libraries
├── platformio.ini             # Build configuration
└── README.md                  # This file
```

## Security Notes

- **SSL/TLS:** Recommended for production environments
- **API Token:** Keep your NEMO token secure and don't commit it to version control
- **Network:** Consider using VPN for remote access
- **Firewall:** Restrict MQTT port access to trusted networks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]