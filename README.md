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

- Computer with wired internet connection
- Python 3.11+
- PlatformIO
- ESP32 development board
- OLED display (SSD1306 128x64)
- Jumper wires

## Step 1: VM Server Setup

### 1.1 One-Command Setup (Recommended)

The easiest way to set up and start the VM server is using our master script:

```bash
cd vm_server
./setup_and_start.sh
```

This script will:
- ✅ Install Mosquitto MQTT broker
- ✅ Configure MQTT broker with SSL/TLS support
- ✅ Set up Python virtual environment
- ✅ Install Python dependencies
- ✅ Generate SSL certificates (optional)
- ✅ Configure environment settings
- ✅ Start the MQTT broker
- ✅ Start the NEMO server
- ✅ **VM is ready to go!**

The script provides comprehensive setup including:
- **SSL/TLS encryption** - Optional secure MQTT communication
- **Environment configuration** - Automatic `.env` file creation
- **Certificate generation** - Self-signed certificates for SSL
- **Process monitoring** - Automatic cleanup on exit
- **ESP32 configuration** - Ready-to-use values for your ESP32

### 1.2 Alternative: Configuration Only

If you prefer to configure without starting:

```bash
# Just configure (without starting)
./configure_nemo.sh
```

### 1.3 Manual Setup (Advanced)

If you prefer manual setup:

```bash
cd vm_server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config.env.example .env
# Edit .env with your API and MQTT settings

# Install and start MQTT broker
# On Ubuntu/Debian: sudo apt install mosquitto mosquitto-clients
# On macOS: brew install mosquitto
# On Windows: Download from https://mosquitto.org/download/

# Start the server
python main.py
```

### 1.4 Configuration

Edit the `.env` file with your settings:

```env
API_URL=http://your-api-server/api/tools
API_KEY=your_api_key
MQTT_BROKER=localhost
MQTT_PORT=1883
POLL_INTERVAL=30
```

### 1.5 Test the Server

```bash
# Test MQTT broker
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT"
mosquitto_sub -h localhost -t "test/topic"

# Test the complete system
python test_mqtt_system.py
```

## Step 2: ESP32 Display Node Setup

### 2.1 Hardware Connections

Connect your OLED display to ESP32:

```
ESP32 Pin  →  OLED Display
GPIO 21    →  SDA
GPIO 22    →  SCL
3.3V       →  VCC
GND        →  GND
```

### 2.2 Configure WiFi and MQTT

Edit `platformio.ini` with your network settings:

```ini
build_flags = 
    -DWIFI_SSID="your_wifi_ssid"
    -DWIFI_PASSWORD="your_wifi_password"
    -DMQTT_BROKER="192.168.1.100"  # Your computer's IP address
```

### 2.3 Upload Firmware

```bash
# Install PlatformIO if not already installed
pip install platformio

# Upload to ESP32
pio run --target upload

# Monitor serial output (115200 baud)
pio device monitor
```

### 2.4 Find Your Computer's IP Address

```bash
# On Linux/macOS
hostname -I | awk '{print $1}'

# On Windows
ipconfig | findstr "IPv4"
```

## Step 3: Test the Complete System

### 3.1 Start the VM Server

```bash
cd vm_server
./setup_and_start.sh
```

You should see:
```
================================
🎉 NEMO Tool Display System Ready!
================================
✓ System Status:
  - MQTT Broker: Running on port 1883 (non-SSL)
  - NEMO Server: Running (PID: 12345)
  - Configuration: .env

✓ MQTT Topics:
  - Backend Input: nemo/backend/tools/+/status
  - Backend Overall: nemo/backend/tools/overall
  - ESP32 Output: nemo/esp32/{tool_id}/status
  - ESP32 Overall: nemo/esp32/overall
  - Server Status: nemo/server/status
```

### 3.2 Monitor MQTT Messages

```bash
# Subscribe to all NEMO topics
mosquitto_sub -h localhost -t "nemo/#" -v
```

### 3.3 Check ESP32 Display

The display should show:
- WiFi connection status
- MQTT connection status
- Tool information (when data is available)

## Configuration Reference

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

- `nemo/backend/tools/+/status` - Individual tool status (backend input)
- `nemo/backend/tools/overall` - Overall system status (backend input)
- `nemo/esp32/{tool_id}/status` - Individual tool status (ESP32 output)
- `nemo/esp32/overall` - Overall system status (ESP32 output)
- `nemo/server/status` - Server status

### Message Format

```json
{
  "id": "drill_001",
  "name": "Cordless Drill",
  "status": "active",
  "category": "power_tools",
  "operational": true,
  "problematic": false,
  "timestamp": "2024-01-15T10:30:00",
  "user": {
    "name": "John Doe",
    "username": "johndoe",
    "id": "12345"
  },
  "usage": {
    "start_time": "2024-01-15T10:30:00",
    "start_time_formatted": "Jan 15, 2024 at 10:30 AM",
    "usage_id": "usage_001"
  }
}
```

## Troubleshooting

### VM Server Issues

**Problem**: "MQTT connection failed"
**Solution**: 
- Check if MQTT broker is running: `ps aux | grep mosquitto`
- Verify MQTT_BROKER in `.env` file
- Check firewall settings

**Problem**: "API request failed"
**Solution**:
- Verify API_URL in `.env` file
- Check if API server is running
- Test API with: `curl http://your-api-url/api/tools`

**Problem**: Setup script fails
**Solution**:
- Check if Mosquitto is installed: `mosquitto --version`
- Verify Python dependencies: `pip install -r requirements.txt`
- Check logs: `tail -f mqtt/log/mosquitto.log`
- Run setup again: `./setup_and_start.sh`

### ESP32 Issues

**Problem**: "WiFi connection failed"
**Solution**:
- Check SSID and password in `platformio.ini`
- Ensure WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Check signal strength

**Problem**: "MQTT connection failed"
**Solution**:
- Verify MQTT_BROKER IP in `platformio.ini`
- Check if VM server is running
- Ensure ESP32 and computer are on same network
- Test MQTT broker: `mosquitto_pub -h 192.168.1.100 -t "test" -m "hello"`

**Problem**: Display not working
**Solution**:
- Check I2C wiring (SDA/SCL pins)
- Verify display address (usually 0x3C)
- Check power supply (3.3V)
- Monitor serial output for error messages

### Network Issues

**Problem**: ESP32 can't reach MQTT broker
**Solution**:
- Ensure both devices are on same subnet
- Check router settings
- Try pinging from ESP32 to computer IP
- Verify MQTT broker is listening on all interfaces

## Project Structure

```
├── vm_server/                    # Python VM server
│   ├── main.py                  # Main server application
│   ├── setup_and_start.sh       # Master setup and startup script
│   ├── configure_nemo.sh        # Configuration-only script
│   ├── test_mqtt_system.py      # MQTT testing utilities
│   ├── network_discovery.py     # Network discovery utility
│   ├── requirements.txt         # Python dependencies
│   ├── config.env.example       # Environment configuration template
│   └── mqtt/                    # MQTT broker configuration
│       ├── config/
│       │   └── mosquitto.conf   # MQTT broker configuration
│       ├── data/                # MQTT persistence data
│       ├── log/                 # MQTT logs
│       └── certs/               # SSL certificates (if enabled)
├── src/                         # ESP32 source code
│   └── main.cpp                 # Display node firmware
├── include/                     # ESP32 headers
│   ├── config.h                 # Configuration constants
│   └── lv_conf.h                # LVGL configuration
├── platformio.ini               # PlatformIO configuration
├── docker-compose.yml           # Docker setup (alternative)
└── README.md                    # This file
```

## Development

### Adding New Tools

1. Update your API to include new tool data
2. The VM server will automatically detect and publish new tools
3. Display nodes will show new tools as they receive MQTT messages

### Customizing the Display

Edit `src/main.cpp` to modify:
- Display layout and graphics
- Tool status indicators
- User interface elements
- Update intervals

### Scaling the System

- Add more ESP32 display nodes
- Each node can display different tools
- Use MQTT topic filtering for specific tools
- Consider load balancing for high-traffic scenarios

## Docker Setup (Alternative)

If you prefer using Docker:

```bash
# Start MQTT broker and server
docker-compose up -d

# Check logs
docker-compose logs -f nemo-server

# Stop services
docker-compose down
```

## Key Features

### Simplified Configuration
- ✅ **One-command setup** - `./setup_and_start.sh` handles everything
- ✅ **SSL/TLS support** - Optional encrypted MQTT communication
- ✅ **Automatic configuration** - Creates all necessary config files
- ✅ **Certificate generation** - Self-signed SSL certificates
- ✅ **Process monitoring** - Automatic cleanup on exit
- ✅ **ESP32 ready** - Provides configuration values for ESP32

### Robust MQTT Communication
- ✅ **Reliable message delivery** - QoS 1 for important messages
- ✅ **Automatic reconnection** - handles network interruptions
- ✅ **Message persistence** - retains messages during broker restarts
- ✅ **Topic filtering** - efficient message routing

### ESP32 Display Features
- ✅ **Real-time updates** - immediate status changes
- ✅ **User-friendly interface** - clear tool status display
- ✅ **Low power consumption** - efficient ESP32 operation
- ✅ **Easy configuration** - simple WiFi and MQTT setup

## License

MIT License - see LICENSE file for details

## Support

If you encounter issues:
1. Check the logs in `vm_server/mqtt/log/mosquitto.log`
2. Monitor ESP32 serial output (115200 baud)
3. Test MQTT with `mosquitto_sub` and `mosquitto_pub`
4. Verify network connectivity with `ping`
5. Run the setup script again: `./setup_and_start.sh`