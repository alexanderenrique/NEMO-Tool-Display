# NEMO Tool Display - VM Setup Guide

This guide explains how to set up and run the NEMO Tool Display system on a VM.

## Quick Start

1. **Start the complete system:**
   ```bash
   ./start_nemo_system.sh
   ```

2. **Test the system:**
   ```bash
   python3 test_mqtt_system.py
   ```

## Manual Setup

### 1. Install Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients python3 python3-pip python3-venv
```

**CentOS/RHEL:**
```bash
sudo yum install mosquitto mosquitto-clients python3 python3-pip
```

**macOS:**
```bash
brew install mosquitto python3
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example configuration
cp config.env.example config.env

# Edit configuration
nano config.env
```

### 4. Start MQTT Broker Only

```bash
./start_mqtt_broker.sh
```

### 5. Start NEMO Server Only

```bash
source venv/bin/activate
python3 main.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER` | MQTT broker hostname/IP | `192.168.1.100` |
| `MQTT_PORT` | MQTT broker port | `8883` |
| `MQTT_USE_SSL` | Enable SSL/TLS | `true` |
| `MQTT_USERNAME` | MQTT username (optional) | `` |
| `MQTT_PASSWORD` | MQTT password (optional) | `` |
| `ESP32_DISPLAY_TOOLS` | Comma-separated list of tools | `woollam,fiji2,savannah` |

### MQTT Topics

**Input Topics (from NEMO backend):**
- `nemo/backend/tools/{tool_id}/status` - Individual tool status
- `nemo/backend/tools/overall` - Overall system status

**Output Topics (to ESP32 displays):**
- `nemo/esp32/{tool_id}/status` - Individual tool status
- `nemo/esp32/overall` - Overall system status
- `nemo/server/status` - Server online/offline status

## SSL Certificates

The system automatically generates self-signed SSL certificates for testing:
- CA Certificate: `mqtt/certs/ca.crt`
- Server Certificate: `mqtt/certs/server.crt`
- Server Private Key: `mqtt/certs/server.key`

For production, replace these with proper certificates.

## Testing

### Test MQTT Broker

```bash
# Non-SSL test
mosquitto_pub -h localhost -p 1883 -t "test/topic" -m "Hello World"

# SSL test
mosquitto_pub -h localhost -p 8883 -t "test/topic" -m "Hello World" --cafile mqtt/certs/ca.crt
```

### Test Complete System

```bash
python3 test_mqtt_system.py
```

## Troubleshooting

### Check if MQTT broker is running
```bash
ps aux | grep mosquitto
```

### Check MQTT broker logs
```bash
tail -f mqtt/log/mosquitto.log
```

### Check NEMO server logs
```bash
tail -f nemo_server.log
```

### Test MQTT connection
```bash
mosquitto_sub -h localhost -p 8883 -t "nemo/esp32/+/status" --cafile mqtt/certs/ca.crt
```

## Stopping the System

```bash
# Stop everything
pkill -f "mosquitto.*mqtt/config/mosquitto.conf"
pkill -f "main.py"

# Or use Ctrl+C if running start_nemo_system.sh
```

## Architecture

```
NEMO Backend → MQTT Broker → NEMO Server → ESP32 Displays
     ↓              ↓              ↓
  Tool Status   SSL/TLS        Filter & Forward
  Updates       Port 8883      to ESP32 Topics
```

The system acts as a bridge between the NEMO backend and ESP32 displays, filtering and forwarding only the relevant tool status updates.
