#!/usr/bin/env python3
"""
Configuration Parser for NEMO Tool Display
Reads display-firmware/src/config.h (or NEMO_CONFIG_H) for consistency between ESP32 and VM server.
"""

import re
import os
from pathlib import Path

from dotenv import load_dotenv

_CONFIG_ENV_LOADED: bool = False


def _default_config_h_path() -> Path:
    override = os.getenv("NEMO_CONFIG_H", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "display-firmware" / "src" / "config.h"


def load_config_env() -> None:
    """Load vm-server/config.env once (same directory as this module). Idempotent.

    Mirrors main.py resolution: ``config.env`` is canonical; ``.env`` is legacy fallback.
    """
    global _CONFIG_ENV_LOADED
    if _CONFIG_ENV_LOADED:
        return
    base = Path(__file__).resolve().parent
    env_path = base / "config.env"
    legacy_dotenv = base / ".env"
    if env_path.is_file():
        try:
            if os.access(env_path, os.R_OK):
                load_dotenv(env_path)
            else:
                load_dotenv()
        except PermissionError:
            load_dotenv()
        _CONFIG_ENV_LOADED = True
        return
    if legacy_dotenv.is_file():
        load_dotenv(legacy_dotenv)
        _CONFIG_ENV_LOADED = True
        return
    load_dotenv()
    _CONFIG_ENV_LOADED = True

class ConfigParser:
    """Parse configuration from display-firmware/src/config.h (or path from NEMO_CONFIG_H)."""

    def __init__(self, config_h_path=None):
        if config_h_path is None:
            config_h_path = _default_config_h_path()

        self.config_h_path = Path(config_h_path)
        self._config = {}
        self._parse_config()
    
    def _parse_config(self):
        """Parse the config.h file and extract #define values"""
        if not self.config_h_path.exists():
            # If the config file is missing (e.g. on a VM that only runs
            # the broker/display server), fall back to environment variables
            # and hard-coded defaults instead of failing hard.
            self._config = {}
            return
        
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
    """Get ESP32 MQTT port (env MQTT_PORT_ESP32 overrides config.h)"""
    val = os.getenv('MQTT_PORT_ESP32')
    if val is not None and str(val).strip() != '':
        try:
            return int(val)
        except ValueError:
            pass
    return config.get('MQTT_PORT_ESP32', 1883)

def get_nemo_port():
    """Get NEMO MQTT port (env MQTT_PORT overrides config.h)"""
    val = os.getenv('MQTT_PORT')
    if val is not None and str(val).strip() != '':
        try:
            return int(val)
        except ValueError:
            pass
    return config.get('MQTT_PORT_NEMO', 1886)

def get_mqtt_broker():
    """Get MQTT broker host (MQTT_BROKER in config.env overrides config.h default)."""
    val = os.getenv("MQTT_BROKER")
    if val is not None and str(val).strip() != "":
        return str(val).strip().strip('"').strip("'")
    return config.get("MQTT_BROKER", "localhost")


def get_target_tool_id() -> int:
    """Display ``TARGET_TOOL_ID`` from firmware config (optional env overrides). Not used by the VM MQTT bridge for reservations (broadcast-only)."""
    load_config_env()
    val = os.getenv("NEMO_TOOL_ID") or os.getenv("TARGET_TOOL_ID")
    if val is not None and str(val).strip() != "":
        try:
            return int(str(val).strip())
        except ValueError:
            pass
    tid = config.get("TARGET_TOOL_ID")
    if isinstance(tid, int):
        return tid
    if tid is not None:
        try:
            return int(str(tid).strip())
        except (ValueError, TypeError):
            pass
    return 0


def get_target_tool_name() -> str:
    """Display ``TARGET_TOOL_NAME`` from firmware config (optional env overrides). Not used by the VM MQTT bridge for reservations (broadcast-only)."""
    load_config_env()
    val = os.getenv("NEMO_TOOL_NAME")
    if val is not None and str(val).strip() != "":
        return str(val).strip().strip('"').strip("'")
    name = config.get("TARGET_TOOL_NAME")
    return str(name) if name else ""


def get_topic_prefix_str() -> str:
    """MQTT topic prefix without trailing slash."""
    load_config_env()
    val = os.getenv("MQTT_TOPIC_PREFIX")
    if val is not None and str(val).strip() != "":
        return str(val).strip().strip('"').strip("'").strip("/")
    return str(config.get("MQTT_TOPIC_PREFIX", "nemo/esp32")).strip().strip("/")

if __name__ == "__main__":
    # Test the parser
    print("MQTT Configuration:")
    print(f"  ESP32 Port: {get_esp32_port()}")
    print(f"  NEMO Port: {get_nemo_port()}")
    print(f"  Broker: {get_mqtt_broker()}")
    print(f"  Topic Prefix: {config.get_topic_prefix()}")
    print(f"  Display: {config.get_display_config()}")
