# NEMO Tool Display - Step-by-Step Setup Guide

This guide will walk you through setting up the NEMO Tool Display system with wired internet connection and LAN MQTT distribution.

## Prerequisites

- Computer with wired internet connection
- ESP32 development board
- TFT display (480x320) with SPI interface
- Jumper wires
- MQTT broker (we'll set this up)

## Step 1: VM Server Setup (Computer with Wired Internet)

### 1.1 Install Dependencies
```bash
cd vm_server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 1.2 Configure Network Settings
```bash
# Run network discovery to find MQTT broker
python network_discovery.py

# Or manually edit .env file
cp config.env.example .env
# Edit .env with your settings
```

### 1.3 Start MQTT Broker
```bash
# Option 1: Using Docker (recommended)
docker-compose up -d mosquitto

# Option 2: Install Mosquitto locally
# On Ubuntu/Debian: sudo apt install mosquitto mosquitto-clients
# On macOS: brew install mosquitto
# On Windows: Download from https://mosquitto.org/download/
```

### 1.4 Test MQTT Broker
```bash
# Test MQTT broker is running
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT"
mosquitto_sub -h localhost -t "test/topic"
```

### 1.5 Start the VM Server
```bash
python main.py
```

You should see:
```
2024-01-15 10:30:00 - NEMOToolServer - INFO - Starting NEMO Tool Display Server
2024-01-15 10:30:01 - NEMOToolServer - INFO - HTTP session initialized
2024-01-15 10:30:01 - NEMOToolServer - INFO - Connected to MQTT broker at 192.168.1.100:1883
2024-01-15 10:30:01 - NEMOToolServer - INFO - Successfully connected to MQTT broker for LAN distribution
```

## Step 2: ESP32 Display Node Setup

### 2.1 Hardware Connections

Connect your TFT display to ESP32:

```
ESP32 Pin  →  TFT Display
GPIO 21    →  SDA (MOSI)
GPIO 22    →  SCL (SCK)  
GPIO 5     →  CS
GPIO 17    →  DC
GPIO 16    →  RST
3.3V       →  VCC
GND        →  GND
```

### 2.2 Configure WiFi and MQTT

Edit `platformio.ini`:
```ini
build_flags = 
    -DWIFI_SSID="your_wifi_ssid"
    -DWIFI_PASSWORD="your_wifi_password"
    -DMQTT_BROKER="192.168.1.100"  # Your computer's IP
```

### 2.3 Upload Firmware
```bash
# Install PlatformIO if not already installed
pip install platformio

# Upload to ESP32
pio run --target upload

# Monitor serial output
pio device monitor
```

## Step 3: Test the System

### 3.1 Test API Data Generation
```bash
cd vm_server
python test_api.py
```

### 3.2 Test MQTT Communication
```bash
# In one terminal - start the server
python main.py

# In another terminal - test MQTT
python mqtt_test.py 192.168.1.100 30
```

### 3.3 Monitor MQTT Messages
```bash
# Subscribe to all NEMO topics
mosquitto_sub -h 192.168.1.100 -t "nemo/#" -v
```

## Step 4: Verify End-to-End Communication

### 4.1 Check VM Server Logs
Look for messages like:
```
2024-01-15 10:30:30 - NEMOToolServer - INFO - Published status for 4 tools to LAN
```

### 4.2 Check ESP32 Display
The display should show:
- WiFi connection status
- MQTT connection status  
- Tool information (when data is available)

### 4.3 Test Tool Status Updates
The display should update in real-time when tool status changes.

## Troubleshooting

### VM Server Issues

**Problem**: "MQTT connection failed"
**Solution**: 
- Check if MQTT broker is running: `docker ps | grep mosquitto`
- Verify IP address in `.env` file
- Check firewall settings

**Problem**: "API request failed"
**Solution**:
- Verify API_URL in `.env` file
- Check if API server is running
- Test API with: `curl http://your-api-url/api/tools`

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

**Problem**: Display not working
**Solution**:
- Check wiring connections
- Verify TFT_eSPI library is installed
- Check power supply (3.3V)

### Network Issues

**Problem**: ESP32 can't reach MQTT broker
**Solution**:
- Ensure both devices are on same subnet
- Check router settings
- Try pinging from ESP32 to computer IP

## Configuration Files

### VM Server (.env)
```env
API_URL=http://your-api-server/api/tools
API_KEY=your_api_key
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
POLL_INTERVAL=30
```

### ESP32 (platformio.ini)
```ini
build_flags = 
    -DWIFI_SSID="your_wifi"
    -DWIFI_PASSWORD="your_password"
    -DMQTT_BROKER="192.168.1.100"
```

## Next Steps

1. **Customize Display**: Modify the display layout in `src/main.cpp`
2. **Add More Tools**: Update your API to include additional tools
3. **Scale Up**: Add more ESP32 display nodes
4. **Monitoring**: Set up logging and monitoring for production use

## Support

If you encounter issues:
1. Check the logs in `vm_server/nemo_server.log`
2. Monitor ESP32 serial output
3. Test MQTT with `mosquitto_sub` and `mosquitto_pub`
4. Verify network connectivity with `ping`
