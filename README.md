# NEMO Tool Display

IoT system with ESP32 displays that show real-time tool status from the NEMO backend system. Displays show who is using tools, usage duration, and tool operational status.

## Quick Start

### 1. VM Server Setup
```bash
cd vm_server
./setup.sh
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
    -DWIFI_SSID="your_wifi_ssid"      # Replace with your WiFi SSID
    -DWIFI_PASSWORD="your_wifi_password"  # Replace with your WiFi password
    -DMQTT_BROKER="your_mqtt_broker_ip"  # Replace with your VM server's IP
    -DMQTT_PORT_ESP32=1883            # ESP32 MQTT port
    -DMQTT_USE_SSL=false              # Set to true if using SSL
    -DTARGET_TOOL_NAME="woollam"      # Tool name for this display
```

**⚠️ SECURITY WARNING:** Never commit real WiFi credentials or IP addresses to version control!

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
T_IRQ
T_DO (Touch MISO) = 32
T_DIN = 26
T_CS = 33
T_CLK = 25
MISO
LED
SCK = 25
MOSI = 26
DC/RS = 27
RESET = 14
CS  = 13
GND
VCC

## Configuration

The system uses **centralized configuration** to ensure consistency between ESP32 and VM server:

### Centralized Configuration System
- **`include/config.h`** - Master configuration with fallback defaults
- **`platformio.ini`** - ESP32 build-time configuration (overrides config.h)
- **`vm_server/config_parser.py`** - Python parser that reads from config.h

### VM Server (config.env)
```env
# MQTT Configuration
MQTT_BROKER=your_mqtt_broker_ip   # Replace with your VM server's IP
MQTT_PORT=1886                    # NEMO backend port (VM server only)
MQTT_USE_SSL=false
MQTT_USERNAME=
MQTT_PASSWORD=

# Display Configuration
TIMEZONE_OFFSET_HOURS=-7
MAX_NAME_LENGTH=13
LOG_LEVEL=INFO

# NEMO API Configuration
NEMO_API_URL=https://nemo.stanford.edu/api/tools/
NEMO_TOKEN=                        # Add your NEMO API token here
```

**Important:** Add your actual NEMO API token to enable automatic tool mapping generation.

### ESP32 (platformio.ini)
```ini
build_flags = 
    -DWIFI_SSID="your_wifi_ssid"      # Replace with your WiFi SSID
    -DWIFI_PASSWORD="your_wifi_password"  # Replace with your WiFi password
    -DMQTT_BROKER="your_mqtt_broker_ip"  # Replace with your VM server's IP
    -DMQTT_PORT_ESP32=1883            # ESP32 MQTT port
    -DMQTT_USE_SSL=false              # SSL enabled/disabled
    -DTARGET_TOOL_NAME="woollam"      # Tool name for this display
```

### Port Configuration
- **ESP32 Port (1883)**: Used by ESP32 displays to receive status updates
- **NEMO Port (1886)**: Used by VM server to receive messages from NEMO backend
- **Configuration**: ESP32 port defined in `platformio.ini`, NEMO port defined in `config.env`

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
- Check MQTT port (1883 for ESP32, 1886 for NEMO backend)
- Ensure ESP32 and server are on same network
- Check SSL settings match between ESP32 and server

**Display not working:**
- Check wiring connections (see Hardware Connections)
- Verify TFT_eSPI library is installed
- Monitor serial output: `pio device monitor`

### VM Server Issues
**MQTT broker won't start:**
- Check logs: `tail -f vm_server/mqtt/log/mosquitto.log`
- Verify ports 1883 and 1886 are not in use
- Check Mosquitto configuration: `mosquitto -c mqtt/config/mosquitto.conf -v`

**Tool mappings not updating:**
- Verify `NEMO_TOKEN` is set in `config.env`
- Check API connectivity: `curl -H "Authorization: Token YOUR_TOKEN" https://nemo.stanford.edu/api/tools/`
- Run manual generation: `python generate_tool_mappings.py --api`

**NEMO server issues:**
- Check Python dependencies: `pip install -r requirements.txt`
- Verify configuration in `config.env`
- Run comprehensive tests: `python3 test_system.py`
- Test MQTT: `mosquitto_sub -h localhost -t "nemo/#" -v`

### Network Issues
**ESP32 can't reach server:**
- Ensure both devices are on same network
- Check firewall settings on VM server
- Verify MQTT broker is listening on correct interface
- Test with: `mosquitto_pub -h SERVER_IP -t "test" -m "hello"`

## Monitoring and Debugging

### Available Scripts

#### Setup Script (`setup.sh`)
Complete system setup and configuration:
```bash
cd vm_server
./setup.sh
```

**What it does:**
- Installs Mosquitto MQTT broker
- Sets up Python virtual environment
- Creates MQTT configuration
- Starts all services

#### Quick Restart Script (`quick_restart.sh`)
Fast restart for development:
```bash
cd vm_server
./quick_restart.sh
```

**What it does:**
1. Stops all existing MQTT broker and server processes
2. Clears MQTT ports (1883, 1886, 8883, 9001)
3. Starts Mosquitto MQTT broker on both ports
4. Starts the NEMO server (vm_server/main.py)

#### Test Script (`test_system.py`)
Comprehensive system testing:
```bash
cd vm_server
python3 test_system.py
```

**What it tests:**
- System processes (MQTT broker, NEMO server)
- Port connectivity (1883, 1886, 9001)
- Message parsing and trimming logic
- MQTT connections (NEMO and ESP32)
- End-to-end functionality

#### MQTT Monitor (`mqtt_monitor.py`)
Real-time MQTT traffic monitoring:
```bash
cd vm_server
python3 mqtt_monitor.py
```

**Features:**
- Monitors all MQTT ports (1883, 1886, 8883)
- Shows message direction and content
- Displays connection status
- Real-time traffic analysis

**⚠️ Important - Internal Development Setup:**
When running the actual NEMO application and this display system on the same machine, restarting Mosquitto will temporarily break NEMO's MQTT connection:

1. **During restart:** NEMO's connection to Mosquitto is severed
2. **Message impact:** Messages published during the restart may be lost or queued
3. **Reconnection:** NEMO's MQTT plugin typically auto-reconnects once Mosquitto is back up

**Best Practice:** Avoid restarting Mosquitto during active tool usage. For production deployments, run the MQTT broker on a separate machine to prevent this issue.

### MQTT Monitoring
```bash
# Monitor all NEMO topics
mosquitto_sub -h localhost -t "nemo/#" -v

# Monitor specific tool
mosquitto_sub -h localhost -t "nemo/esp32/woollam/status" -v

# Monitor server status
mosquitto_sub -h localhost -t "nemo/server/status" -v

# Use the comprehensive monitor script
cd vm_server
python3 mqtt_monitor.py
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
│   ├── setup.sh                 # Complete system setup script
│   ├── quick_restart.sh         # Fast restart for development
│   ├── test_system.py           # Comprehensive system tests
│   ├── mqtt_monitor.py          # MQTT traffic monitor
│   ├── config_parser.py         # Centralized config parser
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

### 🔒 **CRITICAL SECURITY REQUIREMENTS**

1. **Never commit real credentials to version control:**
   - WiFi SSID and password in `platformio.ini`
   - MQTT broker IP addresses
   - NEMO API tokens in `config.env`
   - Any other sensitive configuration

2. **Use environment variables or local config files:**
   - Keep `config.env` in `.gitignore` (already configured)
   - Use placeholder values in committed files
   - Set real values locally for development

3. **API Token Security:**
   - Keep your NEMO token secure and don't commit it to version control
   - Use strong, unique tokens
   - Rotate tokens regularly

4. **MQTT Security:**
   - Consider enabling SSL/TLS for production deployments
   - Use authentication if possible
   - Restrict broker access with firewall rules

5. **Network Security:**
   - Use VPN or firewall rules to restrict access to MQTT broker
   - Consider using private networks for IoT devices
   - Monitor network traffic for anomalies

### 🛡️ **Security Checklist**
- [ ] All real credentials removed from committed files
- [ ] `config.env` is in `.gitignore` and not tracked
- [ ] Placeholder values used in example configurations
- [ ] MQTT broker secured with authentication (if needed)
- [ ] Network access restricted appropriately
- [ ] Regular security updates applied

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]