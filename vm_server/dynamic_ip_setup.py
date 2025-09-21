#!/usr/bin/env python3
"""
Dynamic IP Setup for NEMO Tool Display
Automatically detects current IP address and updates all configuration files
"""

import socket
import subprocess
import os
import re
import platform
from pathlib import Path

def get_local_ip():
    """Get the local IP address dynamically"""
    try:
        # Method 1: Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        try:
            # Method 2: Use hostname resolution
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                raise Exception("Got loopback address")
            return local_ip
        except Exception:
            # Method 3: Parse ifconfig/ipconfig output
            return get_ip_from_system_command()

def get_ip_from_system_command():
    """Get IP from system network commands"""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and '127.0.0.1' not in line:
                    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
        elif platform.system() == "Linux":
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and '127.0.0.1' not in line and 'scope global' in line:
                    match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
        elif platform.system() == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4 Address' in line or 'IP Address' in line:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if match and not match.group(1).startswith('127.'):
                        return match.group(1)
    except Exception:
        pass
    
    return "127.0.0.1"  # Fallback

def update_config_file(file_path, old_ip, new_ip):
    """Update IP address in a configuration file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace the old IP with new IP
        updated_content = content.replace(old_ip, new_ip)
        
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print(f"✓ Updated {file_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to update {file_path}: {e}")
        return False

def update_vm_server_config(new_ip):
    """Update VM server configuration files only (not ESP32)"""
    config_files = [
        "vm_server/config.env",
        "vm_server/config.env.example"
    ]
    
    # IP patterns to replace
    ip_patterns = [
        r'192\.168\.\d+\.\d+',
        r'10\.0\.0\.\d+',
        r'172\.\d+\.\d+\.\d+'
    ]
    
    updated_files = []
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                
                original_content = content
                
                # Replace any IP address pattern with the new IP
                for pattern in ip_patterns:
                    content = re.sub(pattern, new_ip, content)
                
                if content != original_content:
                    with open(config_file, 'w') as f:
                        f.write(content)
                    updated_files.append(config_file)
                    print(f"✓ Updated {config_file}")
                
            except Exception as e:
                print(f"✗ Failed to update {config_file}: {e}")
    
    return updated_files

# ESP32 configuration is now handled manually in platformio.ini
# The broker IP should be set to a fixed, stable IP address

def main():
    print("NEMO Tool Display - Dynamic IP Setup")
    print("=" * 40)
    
    # Get current IP
    current_ip = get_local_ip()
    print(f"Detected IP address: {current_ip}")
    
    if current_ip == "127.0.0.1":
        print("⚠️  Warning: Could not detect external IP, using localhost")
        print("   Make sure you're connected to a network")
    
    # Update configuration files
    print("\nUpdating VM server configuration files...")
    
    # Update VM server config files only
    updated_files = update_vm_server_config(current_ip)
    
    # Update VM server config.env specifically
    config_env_path = "vm_server/config.env"
    if os.path.exists(config_env_path):
        update_config_file(config_env_path, "192.168.2.181", current_ip)
        update_config_file(config_env_path, "192.168.1.100", current_ip)
    
    print(f"\n✅ VM server configuration updated with IP: {current_ip}")
    print("\n📝 ESP32 Configuration:")
    print("   The ESP32 uses a fixed broker IP in platformio.ini")
    print("   Update the MQTT_BROKER value in platformio.ini if needed")
    print(f"   Current ESP32 broker IP: Check platformio.ini")
    print("\nNext steps:")
    print("1. Update ESP32 broker IP in platformio.ini if needed")
    print("2. Compile and upload ESP32 code: pio run -t upload")
    print("3. Start MQTT broker: ./vm_server/quick_restart.sh")
    print("4. Start VM server: cd vm_server && python main.py")

if __name__ == "__main__":
    main()
