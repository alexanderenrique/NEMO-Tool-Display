#!/usr/bin/env python3
"""
NEMO Tool Display - Comprehensive System Test
Consolidated test script for all system components
"""

import json
import time
import socket
import subprocess
import sys
from datetime import datetime, timedelta
from paho.mqtt import client as mqtt_client
from config_parser import get_esp32_port, get_nemo_port, get_mqtt_broker

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.BLUE}================================{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}================================{Colors.NC}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.NC}")

def check_port_listening(port):
    """Check if a port is listening"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def test_ports():
    """Test if required ports are listening"""
    print_header("Port Connectivity Test")
    
    esp32_port = get_esp32_port()
    nemo_port = get_nemo_port()
    
    ports = {
        f"ESP32 ({esp32_port})": check_port_listening(esp32_port),
        f"NEMO ({nemo_port})": check_port_listening(nemo_port),
        "WebSocket (9001)": check_port_listening(9001)
    }
    
    all_good = True
    for port_name, is_listening in ports.items():
        if is_listening:
            print_success(f"{port_name}: Listening")
        else:
            print_error(f"{port_name}: Not listening")
            all_good = False
    
    return all_good

def test_mqtt_connection(port, client_name):
    """Test MQTT connection to a specific port"""
    print_info(f"Testing MQTT connection to port {port}...")
    
    broker = get_mqtt_broker()
    client = mqtt_client.Client(client_name)
    client.connect(broker, port, 60)
    
    # Test publish
    result = client.publish(f"test/{client_name}", "test message", qos=1)
    if result.rc == 0:
        print_success(f"MQTT publish to port {port}: Success")
    else:
        print_error(f"MQTT publish to port {port}: Failed (rc={result.rc})")
    
    client.disconnect()
    return result.rc == 0

def test_message_parsing():
    """Test message parsing and trimming logic"""
    print_header("Message Parsing Test")
    
    # Test start event
    start_message = {
        "event": "tool_usage_start",
        "usage_id": 234,
        "user_id": 1,
        "user_name": "Alex Denton (admin)",
        "tool_id": 1,
        "tool_name": "woollam",
        "start_time": "2025-10-14T19:15:14.691967+00:00"
    }
    
    # Test end event
    end_message = {
        "event": "tool_usage_end",
        "usage_id": 235,
        "user_id": 1,
        "user_name": "Alex Denton (admin)",
        "tool_id": 1,
        "tool_name": "woollam",
        "start_time": "2025-10-14T19:15:14.691967+00:00",
        "end_time": "2025-10-14T19:16:30.123456+00:00"
    }
    
    config = {'timezone_offset_hours': -7, 'max_name_length': 14}
    
    def parse_message(message, event_type):
        # Parse user name (trim role)
        full_user_name = message.get('user_name', '')
        user_display_name = full_user_name.split('(')[0].strip() if '(' in full_user_name else full_user_name
        
        # Parse timestamp
        timestamp_field = 'start_time' if event_type == 'start' else 'end_time'
        timestamp_value = message.get(timestamp_field)
        dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
        dt = dt + timedelta(hours=config['timezone_offset_hours'])
        formatted_time = dt.strftime("%b %d, %I:%M %p")
        
        return {
            "event_type": event_type,
            "timestamp": formatted_time,
            "time_label": "Started" if event_type == 'start' else "Ended",
            "user_label": "Current User" if event_type == 'start' else "Last User",
            "user_name": user_display_name
        }
    
    # Test start event parsing
    start_result = parse_message(start_message, "start")
    print_info("Start Event Parsing:")
    print(json.dumps(start_result, indent=2))
    
    # Test end event parsing
    end_result = parse_message(end_message, "end")
    print_info("End Event Parsing:")
    print(json.dumps(end_result, indent=2))
    
    # Validate results
    assert start_result["event_type"] == "start"
    assert start_result["user_name"] == "Alex Denton"
    assert start_result["time_label"] == "Started"
    
    assert end_result["event_type"] == "end"
    assert end_result["user_name"] == "Alex Denton"
    assert end_result["time_label"] == "Ended"
    
    print_success("Message parsing test passed")
    return True

def test_esp32_connection():
    """Test ESP32 MQTT connection and publishing"""
    print_header("ESP32 Connection Test")
    
    esp32_port = get_esp32_port()
    broker = get_mqtt_broker()
    
    # Create ESP32 client
    client = mqtt_client.Client("test_esp32_client")
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print_success(f"ESP32 client connected to {broker}:{esp32_port}")
        else:
            print_error(f"ESP32 client connection failed: {rc}")
    
    def on_publish(client, userdata, mid):
        print_success(f"ESP32 message published (mid: {mid})")
    
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        client.connect(broker, esp32_port, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Test publish
        test_message = {
            "event_type": "start",
            "timestamp": "Oct 14, 07:15 PM",
            "time_label": "Started",
            "user_label": "Current User",
            "user_name": "Test User"
        }
        
        result = client.publish("nemo/esp32/woollam/status", json.dumps(test_message), qos=1)
        
        if result.rc == 0:
            print_success("ESP32 publish test successful")
            success = True
        else:
            print_error(f"ESP32 publish failed: {result.rc}")
            success = False
        
        client.loop_stop()
        client.disconnect()
        return success
        
    except Exception as e:
        print_error(f"ESP32 connection test failed: {e}")
        return False

def test_nemo_connection():
    """Test NEMO MQTT connection"""
    print_header("NEMO Connection Test")
    
    nemo_port = get_nemo_port()
    broker = get_mqtt_broker()
    
    try:
        client = mqtt_client.Client("test_nemo_client")
        client.connect(broker, nemo_port, 60)
        
        # Test subscribe
        result = client.subscribe("nemo/tools/+/status", qos=1)
        if result[0] == 0:
            print_success(f"NEMO subscription successful")
        else:
            print_error(f"NEMO subscription failed: {result[0]}")
        
        client.disconnect()
        return result[0] == 0
        
    except Exception as e:
        print_error(f"NEMO connection test failed: {e}")
        return False

def test_system_processes():
    """Test if system processes are running"""
    print_header("System Processes Test")
    
    processes = {
        "MQTT Broker": "mosquitto.*mqtt/config/mosquitto.conf",
        "NEMO Server": r"python.*main\.py"
    }
    
    all_running = True
    for process_name, pattern in processes.items():
        try:
            result = subprocess.run(['pgrep', '-f', pattern], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print_success(f"{process_name}: Running (PIDs: {', '.join(pids)})")
            else:
                print_error(f"{process_name}: Not running")
                all_running = False
        except Exception as e:
            print_error(f"{process_name}: Error checking ({e})")
            all_running = False
    
    return all_running

def run_all_tests():
    """Run all system tests"""
    print_header("NEMO Tool Display - System Test Suite")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("System Processes", test_system_processes),
        ("Port Connectivity", test_ports),
        ("Message Parsing", test_message_parsing),
        ("NEMO Connection", test_nemo_connection),
        ("ESP32 Connection", test_esp32_connection)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"{test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print_header("Test Results Summary")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
            passed += 1
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! System is working correctly.")
        return True
    else:
        print_error("Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
