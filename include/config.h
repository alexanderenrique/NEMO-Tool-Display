/*
 * NEMO Tool Display - Configuration Header
 * Centralized configuration for the display node
 */

#ifndef CONFIG_H
#define CONFIG_H

// MQTT Configuration - These are defined via build flags in platformio.ini
// Fallback definitions if not provided via build flags
#ifndef MQTT_BROKER
#define MQTT_BROKER "10.0.0.31"
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883
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

// Tool Configuration - Set this to the specific tool name this display should show
#ifndef TARGET_TOOL_NAME
#define TARGET_TOOL_NAME "woollam"  // Fallback if not defined in build flags
#endif

// Display Configuration - SPI Interface
// Display pins and dimensions are handled by TFT_eSPI library in User_Setup.h

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

