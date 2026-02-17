/*
 * NEMO Tool Display - Configuration Header
 * Centralized configuration for the display node
 * All configuration is now handled via build flags in platformio.ini
 */

#ifndef CONFIG_H
#define CONFIG_H

// All configuration values are now defined via build flags in platformio.ini
// This file provides fallback definitions if build flags are not provided

// WiFi Configuration - Fallback definitions
#ifndef WIFI_SSID
#define WIFI_SSID "your_wifi"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "your_password"
#endif

// MQTT Configuration - Fallback definitions (overridden by platformio.ini build flags)
#ifndef MQTT_BROKER
#define MQTT_BROKER "localhost"
#endif
#ifndef MQTT_PORT_ESP32
#define MQTT_PORT_ESP32 1883
#endif
#ifndef MQTT_PORT_NEMO
#define MQTT_PORT_NEMO 1886
#endif
#ifndef MQTT_CLIENT_ID
#define MQTT_CLIENT_ID "nemo_display_001"
#endif
#ifndef MQTT_TOPIC_PREFIX
#define MQTT_TOPIC_PREFIX "nemo/esp32"
#endif
#ifndef MQTT_USE_SSL
#define MQTT_USE_SSL false
#endif

// Tool Configuration - Fallback definitions
#ifndef TARGET_TOOL_NAME
#define TARGET_TOOL_NAME "woollam"
#endif

// Display Configuration - Fallback definitions
#ifndef DISPLAY_WIDTH
#define DISPLAY_WIDTH 480
#endif
#ifndef DISPLAY_HEIGHT
#define DISPLAY_HEIGHT 320
#endif
#ifndef DISPLAY_ROTATION
#define DISPLAY_ROTATION 1
#endif

// Timing Configuration - Fallback definitions
#ifndef MQTT_RECONNECT_INTERVAL
#define MQTT_RECONNECT_INTERVAL 5000
#endif
#ifndef MQTT_MAX_RETRIES
#define MQTT_MAX_RETRIES 10
#endif
#ifndef DISPLAY_UPDATE_INTERVAL
#define DISPLAY_UPDATE_INTERVAL 1000
#endif
#ifndef WIFI_CONNECT_TIMEOUT
#define WIFI_CONNECT_TIMEOUT 10000
#endif

// Tool Status Values - Fallback definitions
#ifndef STATUS_ACTIVE
#define STATUS_ACTIVE "active"
#endif
#ifndef STATUS_IDLE
#define STATUS_IDLE "idle"
#endif
#ifndef STATUS_MAINTENANCE
#define STATUS_MAINTENANCE "maintenance"
#endif
#ifndef STATUS_OFFLINE
#define STATUS_OFFLINE "offline"
#endif

#endif // CONFIG_H

