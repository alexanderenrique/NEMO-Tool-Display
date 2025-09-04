/*
 * NEMO Tool Display - Configuration Header
 * Centralized configuration for the display node
 */

#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"

// MQTT Configuration
#define MQTT_BROKER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_CLIENT_ID "nemo_display_%d"
#define MQTT_TOPIC_PREFIX "nemo/tools"

// Display Configuration
#define DISPLAY_WIDTH 480
#define DISPLAY_HEIGHT 320
#define DISPLAY_SDA 21
#define DISPLAY_SCL 22

// Timing Configuration
#define MQTT_RECONNECT_INTERVAL 5000
#define DISPLAY_UPDATE_INTERVAL 1000
#define WIFI_CONNECT_TIMEOUT 10000

// Tool Status Values
#define STATUS_ACTIVE "active"
#define STATUS_IDLE "idle"
#define STATUS_MAINTENANCE "maintenance"
#define STATUS_OFFLINE "offline"

#endif // CONFIG_H
