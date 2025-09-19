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

// WiFi credentials
const char* ssid = "ALVA";
const char* password = "AAAAABBBBB";

// MQTT Configuration - Using non-SSL for local testing
const char* mqtt_broker = "192.168.2.181";
const int mqtt_port = 1883;  // Non-SSL port for local development
const char* mqtt_client_id = "nemo_display_001";
const char* mqtt_topic_status = "nemo/esp32/woollam/status";
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
lv_obj_t *wifi_label = nullptr;
lv_obj_t *user_label = nullptr;
lv_obj_t *time_label = nullptr;
lv_obj_t *tool_status_label = nullptr;

// Function declarations
void setupWiFi();
void setupMQTT();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void processMQTTMessage(const char* topic, const char* payload);
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void create_simple_ui();

void setup() {
  Serial.begin(9600);
  Serial.println("NEMO Tool Display - Simple Test Starting...");
  
  // Initialize TFT display
  tft.init();
  tft.setRotation(1); // Use working rotation from lvgl_test
  tft.fillScreen(TFT_BLACK);
  
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
    connectMQTT();
  }
  mqttClient.loop();
  
  delay(5); // Reduced delay for LVGL responsiveness
}

void setupWiFi() {
  Serial.println("Starting WiFi connection...");
  Serial.print("SSID: ");
  Serial.println(ssid);
  
  if (status_label) {
    lv_label_set_text(status_label, "Connecting to WiFi...");
    lv_obj_set_style_text_color(status_label, lv_color_hex(0xFFFF00), 0);
  }
  
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
    
    if (status_label) {
      lv_label_set_text(status_label, "WiFi Connected!");
      lv_obj_set_style_text_color(status_label, lv_color_hex(0x00FF00), 0);
    }
    if (wifi_label) {
      String ipStr = "IP: " + WiFi.localIP().toString();
      lv_label_set_text(wifi_label, ipStr.c_str());
      lv_obj_set_style_text_color(wifi_label, lv_color_hex(0x00FF00), 0);
    }
  } else {
    Serial.println("");
    Serial.println("WiFi connection failed!");
    Serial.print("Status: ");
    Serial.println(WiFi.status());
    
    if (status_label) {
      lv_label_set_text(status_label, "WiFi Failed");
      lv_obj_set_style_text_color(status_label, lv_color_hex(0xFF0000), 0);
    }
    if (wifi_label) {
      lv_label_set_text(wifi_label, "Connection Failed");
      lv_obj_set_style_text_color(wifi_label, lv_color_hex(0xFF0000), 0);
    }
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
  // Create main container - use full screen
  lv_obj_t *cont = lv_obj_create(lv_scr_act());
  lv_obj_set_size(cont, 480, 320);  // Full screen size
  lv_obj_set_pos(cont, 0, 0);       // Position at top-left corner
  lv_obj_set_style_bg_color(cont, lv_color_hex(0x1A1A1A), 0);
  lv_obj_set_style_border_width(cont, 0, 0);  // No border
  lv_obj_set_style_radius(cont, 0, 0);        // No rounded corners
  
  // Title label
  title_label = lv_label_create(cont);
  lv_label_set_text(title_label, "NEMO Tool Display");
  lv_obj_set_style_text_font(title_label, &lv_font_montserrat_24, 0);
  lv_obj_set_style_text_color(title_label, lv_color_hex(0x00AAFF), 0);
  lv_obj_align(title_label, LV_ALIGN_TOP_MID, 0, 10);
  
  // Status label
  status_label = lv_label_create(cont);
  lv_label_set_text(status_label, "Initializing...");
  lv_obj_set_style_text_font(status_label, &lv_font_montserrat_18, 0);
  lv_obj_set_style_text_color(status_label, lv_color_hex(0xFFFF00), 0);
  lv_obj_align(status_label, LV_ALIGN_CENTER, 0, -20);
  
  // WiFi info label
  wifi_label = lv_label_create(cont);
  lv_label_set_text(wifi_label, "Waiting for WiFi...");
  lv_obj_set_style_text_font(wifi_label, &lv_font_montserrat_16, 0);
  lv_obj_set_style_text_color(wifi_label, lv_color_hex(0xCCCCCC), 0);
  lv_obj_align(wifi_label, LV_ALIGN_CENTER, 0, 20);
  
  // User name label
  user_label = lv_label_create(cont);
  lv_label_set_text(user_label, "User: --");
  lv_obj_set_style_text_font(user_label, &lv_font_montserrat_18, 0);
  lv_obj_set_style_text_color(user_label, lv_color_hex(0x00FF00), 0);
  lv_obj_align(user_label, LV_ALIGN_CENTER, 0, 50);
  
  // Time label
  time_label = lv_label_create(cont);
  lv_label_set_text(time_label, "Time: --:--");
  lv_obj_set_style_text_font(time_label, &lv_font_montserrat_16, 0);
  lv_obj_set_style_text_color(time_label, lv_color_hex(0x00AAFF), 0);
  lv_obj_align(time_label, LV_ALIGN_CENTER, 0, 80);
  
  // Tool status label
  tool_status_label = lv_label_create(cont);
  lv_label_set_text(tool_status_label, "Status: Offline");
  lv_obj_set_style_text_font(tool_status_label, &lv_font_montserrat_14, 0);
  lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFF0000), 0);
  lv_obj_align(tool_status_label, LV_ALIGN_CENTER, 0, 110);
  
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
      
      // Subscribe to topics
      mqttClient.subscribe(mqtt_topic_status);
      mqttClient.subscribe(mqtt_topic_overall);
      
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_status);
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_overall);
      
      // Update status
      if (status_label) {
        lv_label_set_text(status_label, "MQTT Connected!");
        lv_obj_set_style_text_color(status_label, lv_color_hex(0x00FF00), 0);
      }
    } else {
      Serial.print(" failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retrying in 5 seconds");
      
      // Update status
      if (status_label) {
        lv_label_set_text(status_label, "MQTT Failed");
        lv_obj_set_style_text_color(status_label, lv_color_hex(0xFF0000), 0);
      }
      
      delay(5000);
    }
  }
}

// MQTT Callback
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);
  
  processMQTTMessage(topic, message);
}

// Process MQTT Message
void processMQTTMessage(const char* topic, const char* payload) {
  // Parse JSON
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Handle tool status messages
  if (strcmp(topic, mqtt_topic_status) == 0) {
    // Extract user information
    if (doc.containsKey("user") && doc["user"].containsKey("first_name")) {
      const char* firstName = doc["user"]["first_name"];
      if (user_label) {
        String userText = "User: ";
        userText += firstName;
        lv_label_set_text(user_label, userText.c_str());
        lv_obj_set_style_text_color(user_label, lv_color_hex(0x00FF00), 0);
      }
    }
    
    // Extract enable time
    if (doc.containsKey("enable_time")) {
      const char* enableTime = doc["enable_time"];
      if (time_label) {
        String timeText = "Time: ";
        timeText += enableTime;
        lv_label_set_text(time_label, timeText.c_str());
        lv_obj_set_style_text_color(time_label, lv_color_hex(0x00AAFF), 0);
      }
    }
    
    // Extract tool status
    if (doc.containsKey("status")) {
      const char* status = doc["status"];
      if (tool_status_label) {
        String statusText = "Status: ";
        statusText += status;
        lv_label_set_text(tool_status_label, statusText.c_str());
        
        // Color code based on status
        if (strcmp(status, "active") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0x00FF00), 0);
        } else if (strcmp(status, "idle") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFFFF00), 0);
        } else if (strcmp(status, "maintenance") == 0) {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFF8800), 0);
        } else {
          lv_obj_set_style_text_color(tool_status_label, lv_color_hex(0xFF0000), 0);
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