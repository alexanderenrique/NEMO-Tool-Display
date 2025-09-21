/*
 * NEMO Tool Display - Simple Test
 * Basic WiFi connection and LVGL display test
 */

#include <WiFi.h>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <lvgl.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"

// WiFi credentials
const char* ssid = "Zucotti Manicotti";
const char* password = "100BoiledEggs";

// MQTT Configuration
const char* mqtt_broker = "10.0.0.31";
const int mqtt_port = 1883;
const char* mqtt_client_id = "nemo_display_001";
const char* mqtt_topic_status = "nemo/esp32/1/status";
const char* mqtt_topic_overall = "nemo/esp32/overall";

// Display configuration (TFT 480x320)
TFT_eSPI tft = TFT_eSPI();

// MQTT client
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// LVGL display buffer
static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[480 * 10]; // 10 lines buffer

// LVGL display driver
static lv_disp_drv_t disp_drv;

// LVGL UI elements
lv_obj_t *title_label = nullptr;
lv_obj_t *status_label = nullptr;
lv_obj_t *user_label = nullptr;
lv_obj_t *time_label = nullptr;
lv_obj_t *tool_status_label = nullptr;

// Tool name from config
String toolDisplayName = "";

// Function declarations
void setupWiFi();
void setupMQTT();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void processMQTTMessage(const char* topic, const char* payload);
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void create_simple_ui();
String capitalizeToolName(const char* toolName);
void updateConnectionStatus();

void setup() {
  Serial.begin(9600);
  Serial.println("NEMO Tool Display - Simple Test Starting...");
  
  // Initialize tool display name from config
  toolDisplayName = capitalizeToolName(TARGET_TOOL_NAME);
  Serial.print("Tool Display Name: ");
  Serial.println(toolDisplayName);
  
  // Initialize TFT display
  tft.init();
  tft.setRotation(1); // Use working rotation from lvgl_test
  tft.fillScreen(TFT_WHITE);
  
  // Initialize LVGL
  lv_init();
  
  // Initialize display buffer
  lv_disp_draw_buf_init(&draw_buf, buf, NULL, 480 * 10);
  
  // Initialize display driver
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = 480;
  disp_drv.ver_res = 320;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);
  
  // Create simple UI
  create_simple_ui();
  
  // Connect to WiFi
  setupWiFi();
  
  // Setup MQTT
  setupMQTT();
  
  Serial.println("Setup complete");
}

void loop() {
  // Update LVGL timer (5ms)
  lv_tick_inc(5);
  
  // Handle LVGL tasks
  lv_timer_handler();
  
  // Handle MQTT
  if (!mqttClient.connected()) {
    Serial.println("MQTT disconnected, attempting reconnect...");
    connectMQTT();
  }
  mqttClient.loop();
  
  // Periodic status check (every 10 seconds)
  static unsigned long lastStatusCheck = 0;
  if (millis() - lastStatusCheck > 10000) {
    lastStatusCheck = millis();
    Serial.print("MQTT Status: ");
    Serial.println(mqttClient.connected() ? "CONNECTED" : "DISCONNECTED");
    if (mqttClient.connected()) {
      Serial.print("Waiting for messages on: ");
      Serial.println(mqtt_topic_status);
    }
  }
  
  delay(5); // Reduced delay for LVGL responsiveness
}

void setupWiFi() {
  Serial.println("Starting WiFi connection...");
  Serial.print("SSID: ");
  Serial.println(ssid);
  
  updateConnectionStatus();
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
    
    // Update status every 5 attempts
    if (attempts % 5 == 0) {
      Serial.print(" (attempt ");
      Serial.print(attempts);
      Serial.println(")");
    }
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    
    updateConnectionStatus();
  } else {
    Serial.println("");
    Serial.println("WiFi connection failed!");
    Serial.print("Status: ");
    Serial.println(WiFi.status());
    
    updateConnectionStatus();
  }
}


// LVGL display flush function
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
  uint32_t w = (area->x2 - area->x1 + 1);
  uint32_t h = (area->y2 - area->y1 + 1);
  
  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.pushColors((uint16_t*)&color_p->full, w * h, true);
  tft.endWrite();
  
  lv_disp_flush_ready(disp);
}

// Create simple LVGL UI
void create_simple_ui() {
  // Color configuration variables
  const uint32_t backgroundColor = 0xFFFFFF;  // White background
  const uint32_t textColor = 0x000000;        // Black text
  
  // Create main container - use full screen
  lv_obj_t *cont = lv_obj_create(lv_scr_act());
  lv_obj_set_size(cont, 480, 320);  // Full screen size
  lv_obj_set_pos(cont, 0, 0);       // Position at top-left corner
  lv_obj_set_style_bg_color(cont, lv_color_hex(backgroundColor), 0);
  lv_obj_set_style_border_width(cont, 0, 0);  // No border
  lv_obj_set_style_radius(cont, 0, 0);        // No rounded corners
  
  // Title label - use dynamic tool name
  title_label = lv_label_create(cont);
  lv_label_set_text(title_label, toolDisplayName.c_str());
  lv_obj_set_style_text_font(title_label, &lv_font_montserrat_24, 0);
  lv_obj_set_style_text_color(title_label, lv_color_hex(textColor), 0);
  lv_obj_align(title_label, LV_ALIGN_TOP_MID, 0, 20);
  
  // Status label - consolidated WiFi and MQTT status
  status_label = lv_label_create(cont);
  lv_label_set_text(status_label, "Initializing...");
  lv_obj_set_style_text_font(status_label, &lv_font_montserrat_18, 0);
  lv_obj_set_style_text_color(status_label, lv_color_hex(textColor), 0);
  lv_obj_align(status_label, LV_ALIGN_CENTER, 0, -20);
  
  // User name label
  user_label = lv_label_create(cont);
  lv_label_set_text(user_label, "User: --");
  lv_obj_set_style_text_font(user_label, &lv_font_montserrat_18, 0);
  lv_obj_set_style_text_color(user_label, lv_color_hex(textColor), 0);
  lv_obj_align(user_label, LV_ALIGN_CENTER, 0, 20);
  
  // Time label
  time_label = lv_label_create(cont);
  lv_label_set_text(time_label, "Time: --:--");
  lv_obj_set_style_text_font(time_label, &lv_font_montserrat_16, 0);
  lv_obj_set_style_text_color(time_label, lv_color_hex(textColor), 0);
  lv_obj_align(time_label, LV_ALIGN_CENTER, 0, 50);
  
  // Tool status label
  tool_status_label = lv_label_create(cont);
  lv_label_set_text(tool_status_label, "Status: Offline");
  lv_obj_set_style_text_font(tool_status_label, &lv_font_montserrat_14, 0);
  lv_obj_set_style_text_color(tool_status_label, lv_color_hex(textColor), 0);
  lv_obj_align(tool_status_label, LV_ALIGN_CENTER, 0, 80);
  
  Serial.println("Simple LVGL UI created successfully!");
}

// MQTT Setup
void setupMQTT() {
  mqttClient.setServer(mqtt_broker, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  Serial.println("MQTT client configured");
}

// MQTT Connection
void connectMQTT() {
  // Only attempt connection if WiFi is connected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping MQTT connection");
    return;
  }
  
  if (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    if (mqttClient.connect(mqtt_client_id)) {
      Serial.println(" connected");
      Serial.print("Client ID: ");
      Serial.println(mqtt_client_id);
      Serial.print("Broker: ");
      Serial.print(mqtt_broker);
      Serial.print(":");
      Serial.println(mqtt_port);
      
      // Subscribe to topics
      bool sub1 = mqttClient.subscribe(mqtt_topic_status);
      bool sub2 = mqttClient.subscribe(mqtt_topic_overall);
      
      Serial.print("Subscribe to status: ");
      Serial.println(sub1 ? "SUCCESS" : "FAILED");
      Serial.print("Subscribe to overall: ");
      Serial.println(sub2 ? "SUCCESS" : "FAILED");
      
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_status);
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_overall);
      
      // Update status
      updateConnectionStatus();
    } else {
      Serial.print(" failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retrying in 5 seconds");
      
      // Update status
      updateConnectionStatus();
      
      delay(5000);
    }
  }
}

// MQTT Callback
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Use a smaller buffer since we're now sending optimized messages
  static char message[512]; // Optimized buffer size for lightweight messages
  
  // Check if message fits in buffer
  if (length >= sizeof(message)) {
    Serial.print("Message too large: ");
    Serial.print(length);
    Serial.println(" bytes");
    return;
  }
  
  // Convert payload to string
  memcpy(message, payload, length);
  message[length] = '\0';
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] (");
  Serial.print(length);
  Serial.print(" bytes) ");
  Serial.println(message);
  
  processMQTTMessage(topic, message);
}

// Process MQTT Message
void processMQTTMessage(const char* topic, const char* payload) {
  // Parse JSON with optimized buffer size
  StaticJsonDocument<512> doc; // Optimized size for lightweight messages
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Handle tool status messages (simplified format)
  if (strcmp(topic, mqtt_topic_status) == 0) {
    Serial.println("Processing tool status message...");
    
    // Extract user name and label
    if (doc["user_name"].is<const char*>()) {
      const char* userName = doc["user_name"];
      const char* userLabel = doc["user_label"].as<const char*>();
      
      if (user_label) {
        String userText = "";
        if (userLabel && strlen(userLabel) > 0) {
          userText += userLabel;
          userText += ": ";
        } else {
          userText += "User: ";
        }
        userText += userName;
        
        lv_label_set_text(user_label, userText.c_str());
        lv_obj_set_style_text_color(user_label, lv_color_hex(0x000000), 0);
        Serial.print("Updated user: ");
        Serial.println(userText.c_str());
      }
    }
    
    
    // Extract timestamp
    if (doc["timestamp"].is<const char*>()) {
      const char* timestamp = doc["timestamp"];
      if (time_label) {
        String timeText = "Time: ";
        timeText += timestamp;
        lv_label_set_text(time_label, timeText.c_str());
        lv_obj_set_style_text_color(time_label, lv_color_hex(0x000000), 0);
      }
    }
    
    
    // Extract tool status from event_type field and in_use status
    if (doc["event_type"].is<const char*>()) {
      const char* eventType = doc["event_type"];
      bool inUse = doc["in_use"].as<bool>();
      
      if (tool_status_label) {
        String statusText = "Status: ";
        statusText += eventType;
        
        // Add in_use indicator
        if (inUse) {
          statusText += " (In Use)";
        }
        
        lv_label_set_text(tool_status_label, statusText.c_str());
        
        // Debug output
        Serial.print("Updated tool status: ");
        Serial.println(statusText.c_str());
        
        // Color code based on event type and usage
        if (strcmp(eventType, "enabled") == 0) {
          if (inUse) {
            lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0x00AAFF), 0); // Blue for in use
          } else {
            lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0x00FF00), 0); // Green for enabled
          }
        } else if (strcmp(eventType, "disabled") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFF0000), 0); // Red for disabled
        } else if (strcmp(eventType, "in_use") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0x00AAFF), 0); // Blue for in use
        } else if (strcmp(eventType, "idle") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFFFF00), 0); // Yellow for idle
        } else {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFF8800), 0); // Orange for unknown
        }
      }
    }
  }
  
  // Handle overall status messages
  if (strcmp(topic, mqtt_topic_overall) == 0) {
    Serial.println("Received overall status update");
    // Could process overall system status here if needed
  }
}

// Capitalize tool name for display
String capitalizeToolName(const char* toolName) {
  if (!toolName || strlen(toolName) == 0) {
    return "Unknown Tool";
  }
  
  String result = "";
  bool capitalizeNext = true;
  
  for (int i = 0; toolName[i] != '\0'; i++) {
    char c = toolName[i];
    
    if (c == '_' || c == '-') {
      result += ' ';
      capitalizeNext = true;
    } else if (capitalizeNext && c >= 'a' && c <= 'z') {
      result += (char)(c - 32); // Convert to uppercase
      capitalizeNext = false;
    } else if (capitalizeNext && c >= 'A' && c <= 'Z') {
      result += c; // Already uppercase
      capitalizeNext = false;
    } else {
      result += c;
      capitalizeNext = false;
    }
  }
  
  return result;
}

// Update consolidated connection status
void updateConnectionStatus() {
  if (!status_label) return;
  
  bool wifiConnected = (WiFi.status() == WL_CONNECTED);
  bool mqttConnected = mqttClient.connected();
  
  String statusText = "Status: ";
  uint32_t statusColor = 0x000000; // Black text for all statuses
  
  if (wifiConnected && mqttConnected) {
    // Both connected
    statusText += "Connected";
  } else if (wifiConnected && !mqttConnected) {
    // WiFi connected but MQTT not connected
    statusText += "WiFi OK, No MQTT";
  } else if (!wifiConnected && mqttConnected) {
    // MQTT connected but WiFi not connected (shouldn't happen, but just in case)
    statusText += "No WiFi, MQTT OK";
  } else {
    // Neither connected
    statusText += "No WiFi, No MQTT";
  }
  
  lv_label_set_text(status_label, statusText.c_str());
  lv_obj_set_style_text_color(status_label, lv_color_hex(statusColor), 0);
  
  Serial.print("Updated status: ");
  Serial.println(statusText.c_str());
}
