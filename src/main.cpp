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
// MQTT topics - use tool name from config
String mqtt_topic_status = "nemo/esp32/" + String(TARGET_TOOL_NAME) + "/status";
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
lv_obj_t *user_value = nullptr;
lv_obj_t *time_label = nullptr;
lv_obj_t *time_value = nullptr;
lv_obj_t *status_indicator = nullptr;

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
void updateStatusIndicator(bool isEnabled);

void setup() {
  Serial.begin(9600);
  Serial.println("NEMO Tool Display - Simple Test Starting...");
  
  // Initialize tool display name from config
  toolDisplayName = capitalizeToolName(TARGET_TOOL_NAME);
  Serial.print("Tool Display Name: ");
  Serial.println(toolDisplayName);
  
  // Initialize MQTT topic with tool name
  mqtt_topic_status = "nemo/esp32/" + String(TARGET_TOOL_NAME) + "/status";
  Serial.print("MQTT Status Topic: ");
  Serial.println(mqtt_topic_status);
  
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
  
  // Font size configuration variables
  const lv_font_t* titleFont = &lv_font_montserrat_48;
  const lv_font_t* statusFont = &lv_font_montserrat_16;
  
  // Label fonts (for field names)
  const lv_font_t* labelFont = &lv_font_montserrat_16;
  
  // Value fonts (for field values)
  const lv_font_t* valueFont = &lv_font_montserrat_32;
  
  // Create main container - use full screen
  lv_obj_t *cont = lv_obj_create(lv_scr_act());
  lv_obj_set_size(cont, 480, 320);  // Full screen size
  lv_obj_set_pos(cont, 0, 0);       // Position at top-left corner
  lv_obj_set_style_bg_color(cont, lv_color_hex(backgroundColor), 0);
  lv_obj_set_style_border_width(cont, 0, 0);  // No border
  lv_obj_set_style_radius(cont, 0, 0);        // No rounded corners
  lv_obj_set_scrollbar_mode(cont, LV_SCROLLBAR_MODE_OFF);  // Disable scrollbars
  
  // Create status indicator block (180px wide, full height on left side)
  status_indicator = lv_obj_create(cont);
  lv_obj_set_size(status_indicator, 180, 320);  // 180px wide, full height
  lv_obj_set_pos(status_indicator, 0, 0);       // Position at left edge
  lv_obj_set_style_bg_color(status_indicator, lv_color_hex(0xFF0000), 0); // Start with red (disabled)
  lv_obj_set_style_border_width(status_indicator, 0, 0);  // No border
  lv_obj_set_style_radius(status_indicator, 0, 0);        // No rounded corners
  lv_obj_set_scrollbar_mode(status_indicator, LV_SCROLLBAR_MODE_OFF);  // Disable scrollbars
  
  // Title label - use dynamic tool name (positioned on right side)
  title_label = lv_label_create(cont);
  lv_label_set_text(title_label, toolDisplayName.c_str());
  lv_obj_set_style_text_font(title_label, titleFont, 0);
  lv_obj_set_style_text_color(title_label, lv_color_hex(textColor), 0);
  lv_obj_align(title_label, LV_ALIGN_TOP_MID, 90, 20); // Offset by 90px to center in right area
  
  // Status label - consolidated WiFi and MQTT status (positioned at bottom left, moved up 10px)
  status_label = lv_label_create(cont);
  lv_label_set_text(status_label, "Initializing...");
  lv_obj_set_style_text_font(status_label, statusFont, 0);
  lv_obj_set_style_text_color(status_label, lv_color_hex(textColor), 0);
  lv_obj_set_pos(status_label, 185, 280); // Position at 185px from left, 280px from top (was 290, moved up 10px)
  
  // User label (positioned at 185px from left, moved down 20px)
  user_label = lv_label_create(cont);
  lv_label_set_text(user_label, "User");
  lv_obj_set_style_text_font(user_label, labelFont, 0);
  lv_obj_set_style_text_color(user_label, lv_color_hex(textColor), 0);
  lv_obj_set_pos(user_label, 185, 100); // Position at 185px from left, 100px from top (was 80)
  
  // User value (positioned below user label, reduced gap by 10px)
  user_value = lv_label_create(cont);
  lv_label_set_text(user_value, "--");
  lv_obj_set_style_text_font(user_value, valueFont, 0);
  lv_obj_set_style_text_color(user_value, lv_color_hex(textColor), 0);
  lv_obj_set_pos(user_value, 185, 120); // Position at 185px from left, 120px from top (was 130, now 20px gap)
  
  // Time label (positioned at 185px from left, with additional 20px spacing)
  time_label = lv_label_create(cont);
  lv_label_set_text(time_label, "Enabled/Disabled Since");
  lv_obj_set_style_text_font(time_label, labelFont, 0);
  lv_obj_set_style_text_color(time_label, lv_color_hex(textColor), 0);
  lv_obj_set_pos(time_label, 185, 190); // Position at 185px from left, 190px from top (was 150, now 60px gap)
  
  // Time value (positioned below time label, reduced gap by 10px)
  time_value = lv_label_create(cont);
  lv_label_set_text(time_value, "--:--");
  lv_obj_set_style_text_font(time_value, valueFont, 0);
  lv_obj_set_style_text_color(time_value, lv_color_hex(textColor), 0);
  lv_obj_set_pos(time_value, 185, 210); // Position at 185px from left, 210px from top (was 220, now 20px gap)
  
  
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
      bool sub1 = mqttClient.subscribe(mqtt_topic_status.c_str());
      bool sub2 = mqttClient.subscribe(mqtt_topic_overall);
      
      Serial.print("Subscribe to status: ");
      Serial.println(sub1 ? "SUCCESS" : "FAILED");
      Serial.print("Subscribe to overall: ");
      Serial.println(sub2 ? "SUCCESS" : "FAILED");
      
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_status.c_str());
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
  
  // Debug: Show message size
  Serial.print("ESP32 received message size: ");
  Serial.print(length);
  Serial.println(" bytes");
  
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
  if (strcmp(topic, mqtt_topic_status.c_str()) == 0) {
    Serial.println("Processing tool status message...");
    
    // Extract user name (now pre-joined from main.py)
    if (doc["user_name"].is<const char*>()) {
      const char* userName = doc["user_name"];
      
      if (user_value) {
        lv_label_set_text(user_value, userName);
        lv_obj_set_style_text_color(user_value, lv_color_hex(0x000000), 0);
        Serial.print("Updated user: ");
        Serial.println(userName);
      }
    }
    
    
    // Extract timestamp and time label
    if (doc["timestamp"].is<const char*>()) {
      const char* timestamp = doc["timestamp"];
      const char* timeLabel = doc["time_label"].as<const char*>();
      
      if (time_value) {
        lv_label_set_text(time_value, timestamp);
        lv_obj_set_style_text_color(time_value, lv_color_hex(0x000000), 0);
        Serial.print("Updated time: ");
        Serial.println(timestamp);
      }
    }
    
    
    // Extract tool status from event_type field and in_use status
    if (doc["event_type"].is<const char*>()) {
      const char* eventType = doc["event_type"];
      bool inUse = doc["in_use"].as<bool>();
      
      // Debug output
      Serial.print("Tool status: ");
      Serial.println(eventType);
      
      // Update time label based on tool status
      if (time_label) {
        String timeLabelText = "";
        if (strcmp(eventType, "enabled") == 0 || strcmp(eventType, "idle") == 0) {
          timeLabelText = "Enabled Since";
        } else if (strcmp(eventType, "disabled") == 0) {
          timeLabelText = "Disabled Since";
        } else {
          timeLabelText = "Change Time"; // Fallback for other statuses
        }
        lv_label_set_text(time_label, timeLabelText.c_str());
        Serial.print("Updated time label: ");
        Serial.println(timeLabelText.c_str());
      }
      
      // Update user label based on tool status
      if (user_label) {
        String userLabelText = "";
        if (strcmp(eventType, "enabled") == 0 || strcmp(eventType, "idle") == 0) {
          userLabelText = "User";
        } else if (strcmp(eventType, "disabled") == 0) {
          userLabelText = "Last User";
        } else {
          userLabelText = "User"; // Fallback for other statuses
        }
        lv_label_set_text(user_label, userLabelText.c_str());
        Serial.print("Updated user label: ");
        Serial.println(userLabelText.c_str());
      }
      
      // Update status indicator based on tool state
      // Consider "enabled" and "idle" as enabled states, "disabled" as disabled
      bool isToolEnabled = (strcmp(eventType, "enabled") == 0 || strcmp(eventType, "idle") == 0);
      updateStatusIndicator(isToolEnabled);
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

// Update status indicator color based on tool state
void updateStatusIndicator(bool isEnabled) {
  if (!status_indicator) return;
  
  if (isEnabled) {
    // Green for enabled
    lv_obj_set_style_bg_color(status_indicator, lv_color_hex(0x00FF00), 0);
    Serial.println("Status indicator: GREEN (enabled)");
  } else {
    // Red for disabled
    lv_obj_set_style_bg_color(status_indicator, lv_color_hex(0xFF0000), 0);
    Serial.println("Status indicator: RED (disabled)");
  }
}
