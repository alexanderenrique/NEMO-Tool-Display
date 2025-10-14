#!/usr/bin/env python3
"""
Configuration Parser for NEMO Tool Display
Reads configuration from include/config.h to ensure consistency between ESP32 and VM server
"""

import re
import os
from pathlib import Path

class ConfigParser:
    """Parse configuration from config.h file"""
    
    def __init__(self, config_h_path=None):
        if config_h_path is None:
            # Default to include/config.h relative to this script
            script_dir = Path(__file__).parent
            config_h_path = script_dir.parent / "include" / "config.h"
        
        self.config_h_path = Path(config_h_path)
        self._config = {}
        self._parse_config()
    
    def _parse_config(self):
        """Parse the config.h file and extract #define values"""
        if not self.config_h_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_h_path}")
        
        with open(self.config_h_path, 'r') as f:
            content = f.read()
        
        # Parse #define statements
        define_pattern = r'#define\s+(\w+)\s+(.+)'
        matches = re.findall(define_pattern, content)
        
        for key, value in matches:
            # Remove quotes and convert to appropriate type
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                # String value
                self._config[key] = value[1:-1]
            elif value.lower() in ('true', 'false'):
                # Boolean value
                self._config[key] = value.lower() == 'true'
            elif value.isdigit():
                # Integer value
                self._config[key] = int(value)
            else:
                # Keep as string
                self._config[key] = value
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self._config.get(key, default)
    
    def get_mqtt_ports(self):
        """Get MQTT port configuration"""
        return {
            'esp32_port': self.get('MQTT_PORT_ESP32', 1883),
            'nemo_port': self.get('MQTT_PORT_NEMO', 1886),
            'broker': self.get('MQTT_BROKER', 'localhost')
        }
    
    def get_topic_prefix(self):
        """Get MQTT topic prefix"""
        return self.get('MQTT_TOPIC_PREFIX', 'nemo/esp32')
    
    def get_display_config(self):
        """Get display configuration"""
        return {
            'width': self.get('DISPLAY_WIDTH', 480),
            'height': self.get('DISPLAY_HEIGHT', 320),
            'rotation': self.get('DISPLAY_ROTATION', 1)
        }

# Global config instance
config = ConfigParser()

# Convenience functions
def get_mqtt_ports():
    """Get MQTT port configuration"""
    return config.get_mqtt_ports()

def get_esp32_port():
    """Get ESP32 MQTT port"""
    return config.get('MQTT_PORT_ESP32', 1883)

def get_nemo_port():
    """Get NEMO MQTT port"""
    return config.get('MQTT_PORT_NEMO', 1886)

def get_mqtt_broker():
    """Get MQTT broker address"""
    return config.get('MQTT_BROKER', 'localhost')

if __name__ == "__main__":
    # Test the parser
    print("MQTT Configuration:")
    print(f"  ESP32 Port: {get_esp32_port()}")
    print(f"  NEMO Port: {get_nemo_port()}")
    print(f"  Broker: {get_mqtt_broker()}")
    print(f"  Topic Prefix: {config.get_topic_prefix()}")
    print(f"  Display: {config.get_display_config()}")
