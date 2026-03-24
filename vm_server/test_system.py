#!/usr/bin/env python3
"""
NEMO Tool Display — system tests (ports, processes, parsing, MQTT).
Run `--forward` to verify NEMO → main.py → ESP32 topics (requires server running).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

from paho.mqtt import client as mqtt_client

from config_parser import get_esp32_port, get_mqtt_broker, get_nemo_port, load_config_env

load_config_env()


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


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


def _mqtt_credentials():
    return (os.getenv("MQTT_USERNAME", "") or ""), (os.getenv("MQTT_PASSWORD", "") or "")


def _apply_mqtt_auth(client):
    user, password = _mqtt_credentials()
    if user and password:
        client.username_pw_set(user, password)


def _mqtt_client_id(prefix: str) -> str:
    return f"{prefix}_{os.getpid()}"


def check_port_listening(port):
    """Check if a port is listening on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("localhost", port))
            return result == 0
    except OSError:
        return False


def mqtt_hmac_envelope(inner: dict, hmac_key: str) -> str:
    """Build the same JSON envelope main.py verifies (payload string, hmac, algo)."""
    payload_str = json.dumps(inner)
    sig = hmac.new(
        hmac_key.strip().encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return json.dumps({"payload": payload_str, "hmac": sig, "algo": "sha256"})


def test_ports():
    """Test if required ports are listening."""
    print_header("Port Connectivity Test")

    esp32_port = get_esp32_port()
    nemo_port = get_nemo_port()

    ports = {
        f"ESP32 ({esp32_port})": check_port_listening(esp32_port),
        f"NEMO ({nemo_port})": check_port_listening(nemo_port),
    }

    all_good = True
    for port_name, is_listening in ports.items():
        if is_listening:
            print_success(f"{port_name}: Listening")
        else:
            print_error(f"{port_name}: Not listening")
            all_good = False

    return all_good


def test_message_parsing():
    """Test message parsing and trimming logic (offline)."""
    print_header("Message Parsing Test")

    start_message = {
        "event": "tool_usage_start",
        "usage_id": 234,
        "user_id": 1,
        "user_name": "Alex Denton (admin)",
        "tool_id": 1,
        "tool_name": "woollam",
        "start_time": "2025-10-14T19:15:14.691967+00:00",
    }

    end_message = {
        "event": "tool_usage_end",
        "usage_id": 235,
        "user_id": 1,
        "user_name": "Alex Denton (admin)",
        "tool_id": 1,
        "tool_name": "woollam",
        "start_time": "2025-10-14T19:15:14.691967+00:00",
        "end_time": "2025-10-14T19:16:30.123456+00:00",
    }

    config = {"timezone_offset_hours": -7, "max_name_length": 14}

    def parse_message(message, event_type):
        full_user_name = message.get("user_name", "")
        user_display_name = (
            full_user_name.split("(")[0].strip()
            if "(" in full_user_name
            else full_user_name
        )

        timestamp_field = "start_time" if event_type == "start" else "end_time"
        timestamp_value = message.get(timestamp_field)
        dt = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        dt = dt + timedelta(hours=config["timezone_offset_hours"])
        formatted_time = dt.strftime("%b %d, %I:%M %p")

        return {
            "event_type": event_type,
            "timestamp": formatted_time,
            "time_label": "Started" if event_type == "start" else "Ended",
            "user_label": "Current User" if event_type == "start" else "Last User",
            "user_name": user_display_name,
        }

    start_result = parse_message(start_message, "start")
    print_info("Start Event Parsing:")
    print(json.dumps(start_result, indent=2))

    end_result = parse_message(end_message, "end")
    print_info("End Event Parsing:")
    print(json.dumps(end_result, indent=2))

    assert start_result["event_type"] == "start"
    assert start_result["user_name"] == "Alex Denton"
    assert start_result["time_label"] == "Started"

    assert end_result["event_type"] == "end"
    assert end_result["user_name"] == "Alex Denton"
    assert end_result["time_label"] == "Ended"

    print_success("Message parsing test passed")
    return True


def test_esp32_connection():
    """MQTT publish to ESP32 listener (validates broker + credentials on ESP32 port)."""
    print_header("ESP32 MQTT Test")

    esp32_port = get_esp32_port()
    broker = get_mqtt_broker()
    client = mqtt_client.Client(_mqtt_client_id("test_esp32"))
    _apply_mqtt_auth(client)
    ok = {"connected": False}

    def on_connect(cl, userdata, flags, rc):
        ok["connected"] = rc == 0
        if rc == 0:
            print_success(f"ESP32 client connected to {broker}:{esp32_port}")
        else:
            print_error(f"ESP32 client connection failed: {rc}")

    def on_publish(cl, userdata, mid):
        print_success(f"ESP32 message published (mid: {mid})")

    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(broker, esp32_port, 60)
        client.loop_start()
        time.sleep(2)

        if not ok["connected"]:
            client.loop_stop()
            client.disconnect()
            return False

        test_message = {
            "event_type": "start",
            "timestamp": "Oct 14, 07:15 PM",
            "time_label": "Started",
            "user_label": "Current User",
            "user_name": "Test User",
        }

        result = client.publish(
            "nemo/esp32/woollam/status", json.dumps(test_message), qos=1
        )

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
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        return False


def test_nemo_connection():
    """MQTT subscribe on NEMO listener (same topic patterns as main.py)."""
    print_header("NEMO MQTT Test")

    nemo_port = get_nemo_port()
    broker = get_mqtt_broker()
    client = None

    try:
        client = mqtt_client.Client(_mqtt_client_id("test_nemo"))
        _apply_mqtt_auth(client)

        client.connect(broker, nemo_port, 60)
        client.loop_start()
        time.sleep(0.8)

        subs = [
            ("nemo/tools/+/+", 1),
            ("nemo/tools/+", 1),
            ("nemo/tools/overall", 1),
        ]
        sub_ok = True
        for topic, qos in subs:
            rc, _mid = client.subscribe(topic, qos)
            if rc != 0:
                print_error(f"Subscribe {topic!r} failed rc={rc}")
                sub_ok = False

        if sub_ok:
            print_success("NEMO subscription successful")
        else:
            print_error("NEMO subscription failed for one or more topics")

        client.loop_stop()
        client.disconnect()
        return sub_ok

    except Exception as e:
        print_error(f"NEMO connection test failed: {e}")
        if client is not None:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass
        return False


def test_system_processes():
    """Check Mosquitto and NEMO server processes."""
    print_header("System Processes Test")

    processes = {
        "MQTT Broker": "mosquitto.*mqtt/config/mosquitto.conf",
        "NEMO Server": r"python.*main\.py",
    }

    all_running = True
    for process_name, pattern in processes.items():
        try:
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                print_success(f"{process_name}: Running (PIDs: {', '.join(pids)})")
            else:
                print_error(f"{process_name}: Not running")
                all_running = False
        except Exception as e:
            print_error(f"{process_name}: Error checking ({e})")
            all_running = False

    return all_running


def run_mqtt_forward_test(wait_seconds: float = 4.0) -> bool:
    """
    Publish on NEMO topics (as main.py expects) and listen for forwarded ESP32 topics.
    Requires main.py running to forward; uses same broker/listener as NEMO inbound traffic.
    """
    print_header("MQTT Forward Test (NEMO topics → ESP32 topics)")
    broker = get_mqtt_broker()
    nemo_port = get_nemo_port()
    esp32_port = get_esp32_port()
    hmac_key = (os.getenv("MQTT_HMAC_KEY") or "").strip()

    print_info(f"Broker: {broker}  NEMO listener: {nemo_port}  ESP32 listener: {esp32_port}")
    if hmac_key:
        print_info("MQTT_HMAC_KEY is set — publishing signed envelopes.")
    else:
        print_info("MQTT_HMAC_KEY unset — publishing plain JSON (dev only).")

    received = []
    lock = threading.Lock()

    def on_msg(cl, userdata, msg):
        with lock:
            received.append((msg.topic, msg.payload.decode(errors="replace")[:200]))

    sub = mqtt_client.Client(_mqtt_client_id("test_fwd_sub"))
    _apply_mqtt_auth(sub)
    sub.on_message = on_msg
    sub.connect(broker, nemo_port, 60)
    sub.subscribe("nemo/esp32/+/status", qos=1)
    sub.subscribe("nemo/esp32/overall", qos=1)
    sub.loop_start()
    time.sleep(1)

    pub = mqtt_client.Client(_mqtt_client_id("test_fwd_pub"))
    _apply_mqtt_auth(pub)
    pub.connect(broker, nemo_port, 60)

    inner_start = {
        "event": "tool_usage_start",
        "usage_id": 999001,
        "user_id": 1,
        "user_name": "Forward Test (admin)",
        "tool_id": 1,
        "tool_name": "woollam",
        "start_time": datetime.utcnow().isoformat() + "+00:00",
    }
    topic_start = "nemo/tools/woollam/start"
    body_start = (
        mqtt_hmac_envelope(inner_start, hmac_key) if hmac_key else json.dumps(inner_start)
    )
    pr = pub.publish(topic_start, body_start, qos=1)
    if pr.rc != 0:
        print_error(f"Publish {topic_start} failed rc={pr.rc}")
    else:
        print_success(f"Published {topic_start}")

    inner_overall = {
        "total_tools": 1,
        "active_tools": 0,
        "idle_tools": 1,
        "maintenance_tools": 0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    topic_overall = "nemo/tools/overall"
    body_overall = (
        mqtt_hmac_envelope(inner_overall, hmac_key)
        if hmac_key
        else json.dumps(inner_overall)
    )
    pr2 = pub.publish(topic_overall, body_overall, qos=1)
    if pr2.rc != 0:
        print_error(f"Publish {topic_overall} failed rc={pr2.rc}")
    else:
        print_success(f"Published {topic_overall}")

    pub.disconnect()
    time.sleep(wait_seconds)
    sub.loop_stop()
    sub.disconnect()

    print_header("Forward Test Summary")
    if received:
        print_success(f"Received {len(received)} message(s) on ESP32-side topics:")
        for topic, preview in received:
            print(f"     {topic}  ({preview}{'…' if len(preview) >= 200 else ''})")
        return True

    print_error(
        "No ESP32-topic messages received. Is main.py running and forwarding "
        "(and do auth/HMAC settings match config.env)?"
    )
    return False


def run_all_tests():
    """Default suite: processes, ports, parsing, MQTT listeners."""
    print_header("NEMO Tool Display — System Test Suite")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("System Processes", test_system_processes),
        ("Port Connectivity", test_ports),
        ("Message Parsing", test_message_parsing),
        ("NEMO Connection", test_nemo_connection),
        ("ESP32 Connection", test_esp32_connection),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"{test_name} failed with exception: {e}")
            results[test_name] = False

    print_header("Test Results Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print_success("All tests passed.")
        return True
    print_error("Some tests failed. See output above.")
    return False


def main():
    parser = argparse.ArgumentParser(description="NEMO VM server tests")
    parser.add_argument(
        "--forward",
        action="store_true",
        help="Run MQTT forward check (needs main.py; then run default suite)",
    )
    args = parser.parse_args()

    if args.forward:
        forward_ok = run_mqtt_forward_test()
        rest_ok = run_all_tests()
        sys.exit(0 if forward_ok and rest_ok else 1)

    sys.exit(0 if run_all_tests() else 1)


if __name__ == "__main__":
    main()
