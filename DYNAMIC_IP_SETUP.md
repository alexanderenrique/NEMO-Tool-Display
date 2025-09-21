# Dynamic IP Setup for NEMO Tool Display

This system automatically detects your current IP address and configures all components to use it, eliminating the need to manually update IP addresses when switching networks.

## Quick Start

1. **Run the dynamic setup script:**
   ```bash
   ./setup_dynamic_ip.sh
   ```

2. **Compile and upload ESP32 code:**
   ```bash
   pio run -t upload
   ```

3. **Start the system:**
   ```bash
   ./vm_server/quick_restart.sh
   ```

## How It Works

### Automatic IP Detection
The system uses multiple methods to detect your current IP address:

1. **Primary method**: Connects to a remote server (8.8.8.8) to determine the local IP
2. **Fallback method**: Uses hostname resolution
3. **System command method**: Parses `ifconfig`/`ipconfig` output

### Dynamic Configuration Updates
The setup script automatically updates:

- **ESP32 configuration** (`include/config.h`, `platformio.ini`)
- **VM server configuration** (`vm_server/config.env`)
- **Example configurations** (`vm_server/config.env.example`)

### VM Server Auto-Detection
The VM server automatically detects its IP address on startup if not explicitly configured in `config.env`.

## Manual Configuration

If you need to manually set an IP address:

### Option 1: Environment Variable
```bash
export MQTT_BROKER="192.168.1.100"
cd vm_server && python main.py
```

### Option 2: Config File
Edit `vm_server/config.env`:
```env
MQTT_BROKER=192.168.1.100
```

### Option 3: ESP32 Build Flags
```bash
pio run -e esp32dev -t upload -- -DMQTT_BROKER="192.168.1.100"
```

## Network Requirements

- **MQTT Broker**: Must be running on the detected IP address
- **Port 1883**: Used for non-SSL MQTT communication
- **Port 8883**: Used for SSL MQTT communication (if enabled)
- **Firewall**: Ensure ports are open for MQTT communication

## Troubleshooting

### IP Detection Issues
If the system can't detect your IP:

1. **Check network connection**: Ensure you're connected to a network
2. **Manual IP setting**: Use one of the manual configuration options above
3. **Network interface**: Check if you have multiple network interfaces

### MQTT Connection Issues
If MQTT connection fails:

1. **Verify IP address**: Check if the detected IP is correct
2. **Check MQTT broker**: Ensure mosquitto is running
3. **Firewall settings**: Ensure ports 1883/8883 are open
4. **Network connectivity**: Test with `ping` and `telnet`

### ESP32 Connection Issues
If ESP32 can't connect:

1. **WiFi credentials**: Update SSID and password in `src/main.cpp`
2. **IP address**: Ensure ESP32 is using the correct MQTT broker IP
3. **Network range**: Ensure ESP32 and server are on the same network

## Files Modified by Dynamic Setup

- `include/config.h` - ESP32 configuration
- `platformio.ini` - ESP32 build configuration
- `vm_server/config.env` - VM server configuration
- `vm_server/config.env.example` - Example configuration

## Advanced Usage

### Custom IP Detection
Modify `vm_server/dynamic_ip_setup.py` to add custom IP detection logic.

### Multiple Network Interfaces
The system automatically selects the first non-loopback IP address. For custom selection, modify the `get_local_ip()` function.

### SSL Configuration
To enable SSL MQTT communication:

1. Set `MQTT_USE_SSL=true` in `vm_server/config.env`
2. Update port to 8883
3. Configure SSL certificates

## Network Discovery

The system includes a network discovery script (`vm_server/network_discovery.py`) that can:

- Scan the local network for MQTT brokers
- Test MQTT connections
- Generate configuration files

Run it manually:
```bash
cd vm_server && python network_discovery.py
```

## Support

If you encounter issues:

1. Check the logs in `vm_server/nemo_server.log`
2. Verify network connectivity
3. Ensure all required services are running
4. Check firewall and port settings
