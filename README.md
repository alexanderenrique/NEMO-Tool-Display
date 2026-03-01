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
- Generate an HMAC key for NEMO↔broker authentication (broker only accepts signed messages when set)
- Start MQTT broker and NEMO server

### 2. ESP32 Configuration
Edit `src/config.h` with your WiFi SSID/password, MQTT broker and credentials, and tool name (e.g. `TARGET_TOOL_NAME`).

**⚠️ SECURITY WARNING:** Never commit real WiFi credentials, MQTT passwords, or IP addresses to version control!

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
- **`src/config.h`** - Single configuration file (WiFi, MQTT, tool, display; not overridden by build flags)
- **`vm_server/config_parser.py`** - Python parser that reads from `src/config.h`

### VM Server (config.env)
```env
# MQTT Configuration
MQTT_BROKER=your_mqtt_broker_ip   # Replace with your VM server's IP
MQTT_PORT=1886                    # NEMO backend port (VM server only)
MQTT_USERNAME=
MQTT_PASSWORD=

# Display Configuration
TIMEZONE_OFFSET_HOURS=-7
MAX_NAME_LENGTH=13
LOG_LEVEL=INFO
```

### ESP32 (src/config.h)
All ESP32 settings (WiFi, MQTT broker/port/credentials, tool ID/name, display) are in `src/config.h`. When broker authentication is enabled on the VM server, set `MQTT_USERNAME` and `MQTT_PASSWORD` in `src/config.h` to match `vm_server/config.env`.

### Port Configuration
- **ESP32 Port (1883)**: Used by ESP32 displays to receive status updates
- **NEMO Port (1886)**: Used by VM server to receive messages from NEMO backend
- **Configuration**: ESP32 port in `src/config.h`, NEMO port in `config.env`

Tool names are provided in MQTT messages from NEMO; no separate tool lookup or mapping file is required.

## MQTT Topics

**Backend Input (from NEMO):**
- `nemo/backend/tools/{tool_id}/status` - Individual tool status
- `nemo/backend/tools/overall` - Overall system status

**ESP32 Output (to displays):**
- `nemo/esp32/{tool_id}/status` - Tool status for specific display (uses tool ID for routing)
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

### HMAC (NEMO↔broker)
When `MQTT_HMAC_KEY` is set in `config.env`, the VM server only accepts messages that include a valid HMAC. The broker (VM server) rejects any message without a correct signature. ESP32 traffic (port 1883) is not HMAC-protected.

**Envelope format when HMAC is enabled:** NEMO must publish:
```json
{"payload": "<original payload string>", "hmac": "<hex signature>", "algo": "sha256"}
```
- **payload**: The exact original payload string (e.g. JSON as a string). This is the string that was signed—same formatting/whitespace, no re-serialization.
- **hmac**: HMAC of that payload string, hex-encoded. Computed as `HMAC(secret_key, payload)` with key = shared secret (UTF-8), message = payload string (UTF-8), algorithm from `algo`.
- **algo**: Digest algorithm, e.g. `sha256` (default if omitted).

Verification uses the same secret (UTF-8), hashes the `payload` string as-is (UTF-8), and compares the hex digest with `hmac` using constant-time comparison. If HMAC is not required, leave `MQTT_HMAC_KEY` empty; then the server accepts normal (unwrapped) payloads.

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
9. **Set Up Environment File** - Create config.env and generate HMAC key
10. **Start MQTT Broker** - Launch Mosquitto
11. **Start NEMO Server** - Launch Python application

### ESP32 Setup Steps
1. **Configure WiFi** - Set SSID and password in `src/config.h`
2. **Configure MQTT** - Set broker IP and port in `src/config.h`
3. **Set Tool Name** - Specify which tool this display shows
4. **Upload Firmware** - Compile and flash to ESP32

## Troubleshooting

### ESP32 Issues
**Can't connect to WiFi:**
- Check WiFi credentials in `src/config.h`
- Verify network is 2.4GHz (ESP32 doesn't support 5GHz)
- Check signal strength

**Can't connect to MQTT:**
- Verify MQTT broker IP address in `src/config.h`
- Check MQTT port (1883 for ESP32, 1886 for NEMO backend)
- Ensure ESP32 and server are on same network
- Check MQTT broker IP and port match the server

**Display not working:**
- Check wiring connections (see Hardware Connections)
- Verify TFT_eSPI library is installed
- Monitor serial output: `pio device monitor`

### VM Server Issues
**MQTT broker won't start:**
- Check logs: `tail -f vm_server/mqtt/log/mosquitto.log`
- Verify ports 1883 and 1886 are not in use
- Check Mosquitto configuration: `mosquitto -c mqtt/config/mosquitto.conf -v`

**NEMO server issues:**
- Check Python dependencies: `pip install -r requirements.txt`
- Verify configuration in `config.env`
- Run comprehensive tests: `python3 test_system.py`
- Test MQTT: `mosquitto_sub -h localhost -t "nemo/#" -v`

**NEMO backend MQTT "unauthorized" (rc=5) or connection timeout:**
- The NEMO Django app (nemo-ce-alex) must use the **same** broker, port, username, and password as `vm_server/config.env`. Set NEMO's MQTT settings to match: `MQTT_BROKER` (use the machine IP where Mosquitto runs, or `localhost` if NEMO and Mosquitto run on the same host), `MQTT_PORT=1886`, `MQTT_USERNAME` and `MQTT_PASSWORD` identical to config.env.
- **Unauthorized (rc=5)**: Username/password in NEMO do not match the broker's password file. Re-run `vm_server/setup.sh` to set broker auth, then copy the printed MQTT config into NEMO's MQTT settings.
- **Connection timeout to localhost:1886**: Mosquitto may not be running, or NEMO is pointing at the wrong host. Start the broker (e.g. `vm_server/quick_restart.sh` or start Mosquitto manually) and ensure NEMO's broker host is correct. When VM server or mqtt_monitor starts, they print the current MQTT config for verification.

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
2. Clears MQTT ports (1883, 1886)
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
- Port connectivity (1883, 1886)
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
- Monitors MQTT ports (1883 and NEMO port from config)
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
│   ├── config.env              # Server configuration
│   ├── requirements.txt        # Python dependencies
│   ├── mqtt/                   # MQTT broker files
│   │   ├── config/mosquitto.conf
│   │   ├── data/               # Persistence data
│   │   └── log/                # Log files
│   └── venv/                   # Python virtual environment
├── src/main.cpp                # ESP32 firmware
├── src/config.h                # ESP32 configuration (single source)
├── include/                    # ESP32 headers
│   └── lv_conf.h              # LVGL configuration
├── lib/                       # ESP32 libraries
├── platformio.ini             # Build configuration
└── README.md                  # This file
```

## Security Notes

### 🔒 **CRITICAL SECURITY REQUIREMENTS**

1. **Never commit real credentials to version control:**
   - WiFi SSID and password in `src/config.h`
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
   - HMAC is between the NEMO backend and the VM server (broker): when `MQTT_HMAC_KEY` is set, the server only accepts messages with a valid HMAC and rejects others.
   - NEMO sends: `{"payload": "<exact payload string>", "hmac": "<hex>", "algo": "sha256"}`. The signed value is the exact `payload` string (UTF-8); key is the shared secret (UTF-8). No re-serialization or trimming.
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