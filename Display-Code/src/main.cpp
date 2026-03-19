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
#include "hardware.h"


// MQTT topics - use tool ID and prefix from build flags
String mqtt_topic_status = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/status";
String mqtt_topic_operational = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/operational";
String mqtt_topic_task = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/task";
String mqtt_topic_overall = String(MQTT_TOPIC_PREFIX) + "/overall";

// State from separate MQTT messages (operational and task)
bool tool_operational = true;
bool has_task = false;
String task_summary = "";       // Derived from task store (aggregated)
String problem_description = ""; // Derived from task store (aggregated)
bool last_status_enabled = false;  // From last status message; used for border when operational

// Multiple-task store (ESP32 tracks per task_id; VM sends one event per message)
#define MAX_TASKS 6
#define MAX_SUMMARY_LEN 200
#define MAX_DESCRIPTION_LEN 600
struct TaskEntry {
  int64_t id;
  bool used;
  String summary;
  String description;
};
static TaskEntry s_tasks[MAX_TASKS];

static void taskStoreAddOrUpdate(int64_t taskId, const String& summary, const String& description);
static void taskStoreRemove(int64_t taskId);
static void taskStoreClearAll();
static bool taskStoreHasAny();
static int taskStoreCount();
static String taskStoreGetAggregatedSummary();
static String taskStoreGetAggregatedDescription();

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
lv_obj_t *outer_ring = nullptr;             // Outer ring: yellow = task, none/white = no task
lv_obj_t *status_indicator = nullptr;       // Inner ring: green = enabled, red = disabled
lv_obj_t *normal_container = nullptr;       // Shown when tool is operational (red + white text when non-operational)
lv_obj_t *task_summary_label = nullptr;     // Task summary line, visible only when non-operational (same layout as status)
lv_obj_t *problem_description_label = nullptr;
lv_obj_t *details_container = nullptr;   // Details screen (problem description)
lv_obj_t *btn_forward = nullptr;         // Arrow lower-right: go to Details
lv_obj_t *btn_back = nullptr;           // Arrow on Details: back to Status

// Screen state / auto-timeout
static bool details_screen_visible = false;
static unsigned long details_screen_shown_at = 0;
static const unsigned long DETAILS_SCREEN_TIMEOUT_MS = 30000UL;  // 30 seconds on problem description

// Tool name from config
String toolDisplayName = "";

// Function declarations
void setupWiFi();
void setupMQTT();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void processMQTTMessage(const char* topic, const char* payload);
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void touch_read(lv_indev_drv_t *indev_drv, lv_indev_data_t *data);
void create_simple_ui();
String capitalizeToolName(const char* toolName);
void updateConnectionStatus();
void updateStatusIndicator(bool isEnabled);  // Inner ring: enabled (green) / disabled (red)
void updateOuterRing(bool hasTask);          // Outer ring: yellow if task, else none
void applyMainScreenState();  // Show/hide normal vs non-operational, set both rings
void show_status_screen();   // Show status view, hide details
void show_details_screen();  // Show details view, hide status

void setup() {
  Serial.begin(9600);
  Serial.println("NEMO Tool Display - Simple Test Starting...");
  
  // Initialize tool display name from config (for display purposes only)
  toolDisplayName = capitalizeToolName(TARGET_TOOL_NAME);
  Serial.print("Tool Display Name: ");
  Serial.println(toolDisplayName);
  
  // Initialize MQTT topics with tool ID and prefix from build flags
  mqtt_topic_status = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/status";
  mqtt_topic_operational = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/operational";
  mqtt_topic_task = String(MQTT_TOPIC_PREFIX) + "/" + String(TARGET_TOOL_ID) + "/task";
  Serial.print("MQTT Status Topic: ");
  Serial.println(mqtt_topic_status);
  Serial.print("MQTT Operational Topic: ");
  Serial.println(mqtt_topic_operational);
  Serial.print("MQTT Task Topic: ");
  Serial.println(mqtt_topic_task);
  
  // Initialize TFT display
  tft.init();
  tft.setRotation(DISPLAY_ROTATION); // Use rotation from build flags
  tft.fillScreen(TFT_WHITE);
  
  // Initialize LVGL
  lv_init();
  
  // Initialize display buffer
  lv_disp_draw_buf_init(&draw_buf, buf, NULL, DISPLAY_WIDTH * 10);
  
  // Initialize display driver
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = DISPLAY_WIDTH;
  disp_drv.ver_res = DISPLAY_HEIGHT;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);
  
  // Initialize touch input device for LVGL
  static lv_indev_drv_t indev_drv;
  lv_indev_drv_init(&indev_drv);
  indev_drv.type = LV_INDEV_TYPE_POINTER;
  indev_drv.read_cb = touch_read;
  lv_indev_drv_register(&indev_drv);
  Serial.println("Touch input enabled (pointer)");
  
  // Create simple UI
  create_simple_ui();
  
  // Enable WiFi and MQTT so we can show live connection status on the display
  setupWiFi();
  setupMQTT();
  updateConnectionStatus();
  
  Serial.println("Touch input registered with LVGL (T_CS=33)");
  Serial.println("Setup complete - WiFi/MQTT status mode");
}

void loop() {
  // Update LVGL timer (5ms)
  lv_tick_inc(5);
  
  // Handle LVGL tasks
  lv_timer_handler();
  
  // Maintain WiFi/MQTT connectivity and update status label
  {
    static unsigned long lastWifiAttempt = 0;
    static unsigned long lastMqttAttempt = 0;
    static unsigned long lastStatusUpdate = 0;
    unsigned long now = millis();

    // Periodically try to (re)connect WiFi if not connected
    if (WiFi.status() != WL_CONNECTED) {
      if (now - lastWifiAttempt >= WIFI_RECONNECT_INTERVAL) {
        lastWifiAttempt = now;
        Serial.println("WiFi not connected, attempting periodic reconnection...");
        WiFi.disconnect();
        WiFi.begin(ssid, password);
      }
    }
    
    // Periodically try to (re)connect MQTT if WiFi is up
    if (WiFi.status() == WL_CONNECTED && !mqttClient.connected()) {
      if (now - lastMqttAttempt >= MQTT_RECONNECT_INTERVAL) {
        lastMqttAttempt = now;
        connectMQTT();
      }
    }
    
    // Run MQTT client loop when connected
    if (mqttClient.connected()) {
      mqttClient.loop();
    }
    
    // Periodically refresh the consolidated WiFi/MQTT status label
    if (now - lastStatusUpdate >= DISPLAY_UPDATE_INTERVAL) {
      lastStatusUpdate = now;
      updateConnectionStatus();
    }

    // Auto-return from details (problem description) screen after timeout
    if (details_screen_visible && (now - details_screen_shown_at >= DETAILS_SCREEN_TIMEOUT_MS)) {
      Serial.println("Details screen timeout reached, returning to status screen");
      show_status_screen();
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
  int maxAttempts = WIFI_CONNECT_TIMEOUT / 500; // Convert timeout to attempts
  while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts) {
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

// Touch input read callback for LVGL
void touch_read(lv_indev_drv_t *indev_drv, lv_indev_data_t *data) {
  uint16_t x = 0, y = 0;
  bool touched = false;
#ifdef TOUCH_CS
  touched = tft.getTouch(&x, &y);
#endif
  static bool was_pressed = false;
  if (touched) {
    if (x >= DISPLAY_WIDTH) x = DISPLAY_WIDTH - 1;
    if (y >= DISPLAY_HEIGHT) y = DISPLAY_HEIGHT - 1;
    // Touch controller Y is inverted vs LVGL display: physical top reports low Y.
    // Invert Y so touching the visual button position matches LVGL's bottom-right.
    data->point.x = x;
    data->point.y = (DISPLAY_HEIGHT - 1) - y;
    data->state = LV_INDEV_STATE_PRESSED;
    if (!was_pressed) {
      Serial.print("Touch: pressed at (");
      Serial.print(x);
      Serial.print(", ");
      Serial.print(y);
      Serial.println(")");
      was_pressed = true;
    }
  } else {
    data->state = LV_INDEV_STATE_RELEASED;
    data->point.x = 0;
    data->point.y = 0;
    if (was_pressed) {
      Serial.println("Touch: released");
      was_pressed = false;
    }
  }
}

// Create LVGL UI: status view only (no tabs)
void create_simple_ui() {
  const uint32_t backgroundColor = 0xFFFFFF;
  const uint32_t textColor = 0x000000;
  const lv_font_t* titleFont = &lv_font_montserrat_48;
  const lv_font_t* statusFont = &lv_font_montserrat_16;
  const lv_font_t* labelFont = &lv_font_montserrat_16;
  const lv_font_t* valueFont = &lv_font_montserrat_32;
  const int screenMargin = 8;

  lv_obj_t *screen = lv_scr_act();

  // ---- Tab 0: Status ----
  // Normal container (white interior, two rings, user/time labels)
  normal_container = lv_obj_create(screen);
  lv_obj_set_size(normal_container, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  lv_obj_set_pos(normal_container, 0, 0);
  lv_obj_set_style_bg_color(normal_container, lv_color_hex(backgroundColor), 0);
  lv_obj_set_style_border_width(normal_container, 0, 0);
  lv_obj_set_style_pad_all(normal_container, 0, 0);
  lv_obj_set_scrollbar_mode(normal_container, LV_SCROLLBAR_MODE_OFF);

  // Outer ring: always same size so inner content never shifts. Yellow when task, background color when no task.
  const int outerRingWidth = 14;
  const int innerRingWidth = 20;
  int outerW = DISPLAY_WIDTH - 2 * screenMargin;
  int outerH = DISPLAY_HEIGHT - 2 * screenMargin;
  outer_ring = lv_obj_create(normal_container);
  lv_obj_set_size(outer_ring, outerW, outerH);
  lv_obj_set_pos(outer_ring, screenMargin, screenMargin);
  lv_obj_set_style_bg_opa(outer_ring, LV_OPA_TRANSP, 0);  // No fill – only border is visible
  lv_obj_set_style_border_width(outer_ring, outerRingWidth, 0);  // Always same width – updateOuterRing() only changes color
  lv_obj_set_style_border_color(outer_ring, lv_color_hex(backgroundColor), 0);  // Invisible until task (yellow)
  lv_obj_set_style_radius(outer_ring, 0, 0);
  lv_obj_set_style_pad_all(outer_ring, 0, 0);
  lv_obj_set_style_outline_width(outer_ring, 0, 0);
  lv_obj_set_scrollbar_mode(outer_ring, LV_SCROLLBAR_MODE_OFF);
  lv_obj_clear_flag(outer_ring, LV_OBJ_FLAG_SCROLLABLE);

  // Inner ring: green = enabled, red = disabled. Flush with outer ring so only two rings show.
  int innerW = outerW - 2 * outerRingWidth;
  int innerH = outerH - 2 * outerRingWidth;
  status_indicator = lv_obj_create(outer_ring);
  lv_obj_set_size(status_indicator, innerW, innerH);
  lv_obj_set_pos(status_indicator, 0, 0);  // Flush to outer ring content area – no gap
  lv_obj_set_style_bg_color(status_indicator, lv_color_hex(0xFFFFFF), 0);
  lv_obj_set_style_border_width(status_indicator, innerRingWidth, 0);
  lv_obj_set_style_border_color(status_indicator, lv_color_hex(0x00FF00), 0);
  lv_obj_set_style_radius(status_indicator, 0, 0);
  lv_obj_set_style_pad_all(status_indicator, 8, 0);
  lv_obj_set_style_outline_width(status_indicator, 0, 0);
  lv_obj_set_scrollbar_mode(status_indicator, LV_SCROLLBAR_MODE_OFF);
  lv_obj_clear_flag(status_indicator, LV_OBJ_FLAG_SCROLLABLE);

  title_label = lv_label_create(status_indicator);
  lv_label_set_text(title_label, toolDisplayName.c_str());
  lv_obj_set_style_text_font(title_label, titleFont, 0);
  lv_obj_set_style_text_color(title_label, lv_color_hex(textColor), 0);
  lv_obj_align(title_label, LV_ALIGN_TOP_LEFT, 0, 0);

  user_label = lv_label_create(status_indicator);
  lv_label_set_text(user_label, "User");
  lv_obj_set_style_text_font(user_label, labelFont, 0);
  lv_obj_set_style_text_color(user_label, lv_color_hex(textColor), 0);
  lv_obj_align(user_label, LV_ALIGN_TOP_LEFT, 0, 55);

  user_value = lv_label_create(status_indicator);
  lv_label_set_text(user_value, "--");
  lv_obj_set_style_text_font(user_value, valueFont, 0);
  lv_obj_set_style_text_color(user_value, lv_color_hex(textColor), 0);
  lv_obj_align(user_value, LV_ALIGN_TOP_LEFT, 0, 72);

  time_label = lv_label_create(status_indicator);
  lv_label_set_text(time_label, "Enabled/Disabled Since");
  lv_obj_set_style_text_font(time_label, labelFont, 0);
  lv_obj_set_style_text_color(time_label, lv_color_hex(textColor), 0);
  lv_obj_align(time_label, LV_ALIGN_TOP_LEFT, 0, 140);

  time_value = lv_label_create(status_indicator);
  lv_label_set_text(time_value, "--:--");
  lv_obj_set_style_text_font(time_value, valueFont, 0);
  lv_obj_set_style_text_color(time_value, lv_color_hex(textColor), 0);
  lv_obj_align(time_value, LV_ALIGN_TOP_LEFT, 0, 162);

  status_label = lv_label_create(status_indicator);
  lv_label_set_text(status_label, "Initializing...");
  lv_obj_set_style_text_font(status_label, statusFont, 0);
  lv_obj_set_style_text_color(status_label, lv_color_hex(textColor), 0);
  lv_obj_align(status_label, LV_ALIGN_BOTTOM_LEFT, 0, 0);

  // Task summary line (same layout as status; visible only when non-operational, between title and User)
  task_summary_label = lv_label_create(status_indicator);
  lv_label_set_text(task_summary_label, "");
  lv_obj_set_style_text_font(task_summary_label, valueFont, 0);
  lv_obj_set_style_text_color(task_summary_label, lv_color_hex(0xFFFFFF), 0);
  lv_obj_align(task_summary_label, LV_ALIGN_TOP_LEFT, 0, 48);
  lv_label_set_long_mode(task_summary_label, LV_LABEL_LONG_WRAP);
  lv_obj_add_flag(task_summary_label, LV_OBJ_FLAG_HIDDEN);  // Shown only when non-operational

  // Forward arrow (lower right): go to Details screen
  const int arrowSize = 48;
  const int arrowMargin = 12;
  btn_forward = lv_btn_create(screen);
  lv_obj_set_size(btn_forward, arrowSize, arrowSize);
  lv_obj_align(btn_forward, LV_ALIGN_BOTTOM_RIGHT, -arrowMargin, -arrowMargin);
  lv_obj_set_style_radius(btn_forward, arrowSize / 2, 0);
  lv_obj_t *lbl_fwd = lv_label_create(btn_forward);
  lv_label_set_text(lbl_fwd, LV_SYMBOL_RIGHT);
  lv_obj_center(lbl_fwd);
  lv_obj_add_event_cb(btn_forward, [](lv_event_t *e) { show_details_screen(); }, LV_EVENT_CLICKED, NULL);
  lv_obj_add_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);  // Shown only when has_task

  // Details screen (problem description + back arrow) – hidden by default
  details_container = lv_obj_create(screen);
  lv_obj_set_size(details_container, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  lv_obj_set_pos(details_container, 0, 0);
  lv_obj_set_style_bg_color(details_container, lv_color_hex(backgroundColor), 0);
  lv_obj_set_style_border_width(details_container, 0, 0);
  lv_obj_set_style_pad_all(details_container, 0, 0);
  lv_obj_set_scrollbar_mode(details_container, LV_SCROLLBAR_MODE_OFF);
  lv_obj_add_flag(details_container, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t *details_title = lv_label_create(details_container);
  lv_label_set_text(details_title, "Problem description");
  lv_obj_set_style_text_font(details_title, &lv_font_montserrat_16, 0);
  lv_obj_set_style_text_color(details_title, lv_color_hex(textColor), 0);
  lv_obj_set_pos(details_title, 12, 8);

  lv_obj_t *problem_scroll = lv_obj_create(details_container);
  lv_obj_set_size(problem_scroll, DISPLAY_WIDTH - 24, DISPLAY_HEIGHT - arrowSize - arrowMargin - 40);
  lv_obj_set_pos(problem_scroll, 12, 36);
  lv_obj_set_style_border_width(problem_scroll, 0, 0);
  lv_obj_set_scrollbar_mode(problem_scroll, LV_SCROLLBAR_MODE_AUTO);
  problem_description_label = lv_label_create(problem_scroll);
  lv_obj_set_width(problem_description_label, DISPLAY_WIDTH - 48);
  lv_label_set_text(problem_description_label, "No problem description.");
  lv_obj_set_style_text_font(problem_description_label, &lv_font_montserrat_14, 0);
  lv_obj_set_style_text_color(problem_description_label, lv_color_hex(textColor), 0);
  lv_label_set_long_mode(problem_description_label, LV_LABEL_LONG_WRAP);

  btn_back = lv_btn_create(details_container);
  lv_obj_set_size(btn_back, arrowSize, arrowSize);
  lv_obj_align(btn_back, LV_ALIGN_BOTTOM_LEFT, arrowMargin, -arrowMargin);
  lv_obj_set_style_radius(btn_back, arrowSize / 2, 0);
  lv_obj_t *lbl_back = lv_label_create(btn_back);
  lv_label_set_text(lbl_back, LV_SYMBOL_LEFT);
  lv_obj_center(lbl_back);
  lv_obj_add_event_cb(btn_back, [](lv_event_t *e) { show_status_screen(); }, LV_EVENT_CLICKED, NULL);

  applyMainScreenState();
  Serial.println("LVGL UI created (status + details with arrows)");
}

void show_status_screen() {
  if (details_container) lv_obj_add_flag(details_container, LV_OBJ_FLAG_HIDDEN);
  if (btn_forward) {
    if (has_task)
      lv_obj_clear_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);
    else
      lv_obj_add_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);
  }
  if (normal_container) lv_obj_clear_flag(normal_container, LV_OBJ_FLAG_HIDDEN);
  applyMainScreenState();  // Style normal screen (red+white when non-operational, else white+black)
  details_screen_visible = false;
}

void show_details_screen() {
  if (normal_container) lv_obj_add_flag(normal_container, LV_OBJ_FLAG_HIDDEN);
  if (btn_forward) lv_obj_add_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);
  if (details_container) lv_obj_clear_flag(details_container, LV_OBJ_FLAG_HIDDEN);
  details_screen_visible = true;
  details_screen_shown_at = millis();
}

// MQTT Setup
void setupMQTT() {
  mqttClient.setServer(mqtt_broker, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  Serial.println("MQTT client configured");
}

// Map PubSubClient state codes to human-readable text.
static const char* mqttStateToString(int state) {
  switch (state) {
    case 5:  return "MQTT_CONNECT_UNAUTHORIZED";
    case 4:  return "MQTT_CONNECT_BAD_CREDENTIALS";
    case 3:  return "MQTT_CONNECT_UNAVAILABLE";
    case 2:  return "MQTT_CONNECT_BAD_CLIENT_ID";
    case 1:  return "MQTT_CONNECT_BAD_PROTOCOL";
    case 0:  return "MQTT_CONNECTED";
    case -1: return "MQTT_DISCONNECTED";
    case -2: return "MQTT_CONNECT_FAILED";
    case -3: return "MQTT_CONNECTION_LOST";
    case -4: return "MQTT_CONNECTION_TIMEOUT";
    default:  return "MQTT_UNKNOWN_STATE";
  }
}

// MQTT Connection
void connectMQTT() {
  // Only attempt connection if WiFi is connected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping MQTT connection");
    return;
  }
  
  if (!mqttClient.connected()) {
    Serial.println("----- MQTT connect attempt -----");

    Serial.print("WiFi RSSI: ");
    Serial.println(WiFi.RSSI());
    Serial.print("WiFi IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("WiFi gateway: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("WiFi subnet: ");
    Serial.println(WiFi.subnetMask());

    Serial.print("Broker: ");
    Serial.print(mqtt_broker);
    Serial.print(":");
    Serial.println(mqtt_port);

    Serial.print("Client ID: ");
    Serial.println(mqtt_client_id);

    bool useCreds = (mqtt_username && mqtt_username[0] != '\0' && mqtt_password && mqtt_password[0] != '\0');
    Serial.print("Auth mode: ");
    Serial.println(useCreds ? "username+password" : "anonymous/no-auth");
    if (useCreds) {
      // Avoid printing the actual password.
      Serial.print("Username length: ");
      {
        int n = 0;
        while (mqtt_username[n] != '\0') n++;
        Serial.println(n);
      }
      Serial.print("Password length: ");
      {
        int n = 0;
        while (mqtt_password[n] != '\0') n++;
        Serial.println(n);
      }
    }

    Serial.print("WiFiClient connected (before): ");
    Serial.println(wifiClient.connected() ? "YES" : "NO");

    Serial.print("Attempting MQTT connection...");

    bool connected = false;

    unsigned long t0 = millis();
    if (useCreds) {
      connected = mqttClient.connect(mqtt_client_id, mqtt_username, mqtt_password);
    } else {
      connected = mqttClient.connect(mqtt_client_id);
    }
    unsigned long elapsed = millis() - t0;

    if (connected) {
      Serial.print(" connected (elapsed ");
      Serial.print(elapsed);
      Serial.println(" ms)");
      Serial.print("Client ID: ");
      Serial.println(mqtt_client_id);
      Serial.print("Broker: ");
      Serial.print(mqtt_broker);
      Serial.print(":");
      Serial.println(mqtt_port);
      
      // Subscribe to topics (status, operational, task, overall)
      bool sub1 = mqttClient.subscribe(mqtt_topic_status.c_str());
      bool sub2 = mqttClient.subscribe(mqtt_topic_operational.c_str());
      bool sub3 = mqttClient.subscribe(mqtt_topic_task.c_str());
      bool sub4 = mqttClient.subscribe(mqtt_topic_overall.c_str());
      
      Serial.print("Subscribe status: ");
      Serial.println(sub1 ? "OK" : "FAIL");
      Serial.print("Subscribe operational: ");
      Serial.println(sub2 ? "OK" : "FAIL");
      Serial.print("Subscribe task: ");
      Serial.println(sub3 ? "OK" : "FAIL");
      Serial.print("Subscribe overall: ");
      Serial.println(sub4 ? "OK" : "FAIL");
      
      // Update status
      updateConnectionStatus();
    } else {
      int state = mqttClient.state();
      Serial.print(" failed, state=");
      Serial.print(state);
      Serial.print(" (");
      Serial.print(mqttStateToString(state));
      Serial.println(")");

      Serial.print("WiFiClient connected (after): ");
      Serial.println(wifiClient.connected() ? "YES" : "NO");

      Serial.print("Elapsed: ");
      Serial.print(elapsed);
      Serial.println(" ms");

      Serial.println("retrying in 5 seconds");
      
      // Update status
      updateConnectionStatus();
      
      delay(MQTT_RECONNECT_INTERVAL);
    }
  }
}

// MQTT buffer: task payload can include long problem_description
#define MQTT_MESSAGE_BUFFER_SIZE 2048

// ---- Task store helpers ----
static void taskStoreAddOrUpdate(int64_t taskId, const String& summary, const String& description) {
  // Cap lengths to avoid unbounded heap use
  String s = summary.length() > (unsigned)MAX_SUMMARY_LEN ? summary.substring(0, MAX_SUMMARY_LEN) : summary;
  String d = description.length() > (unsigned)MAX_DESCRIPTION_LEN ? description.substring(0, MAX_DESCRIPTION_LEN) : description;

  for (int i = 0; i < MAX_TASKS; i++) {
    if (s_tasks[i].used && s_tasks[i].id == taskId) {
      s_tasks[i].summary = s;
      s_tasks[i].description = d;
      return;
    }
  }
  // New task: find free slot
  for (int i = 0; i < MAX_TASKS; i++) {
    if (!s_tasks[i].used) {
      s_tasks[i].id = taskId;
      s_tasks[i].used = true;
      s_tasks[i].summary = s;
      s_tasks[i].description = d;
      return;
    }
  }
  // Full: drop oldest (index 0), shift left, add at end
  for (int i = 0; i < MAX_TASKS - 1; i++) {
    s_tasks[i] = s_tasks[i + 1];
  }
  s_tasks[MAX_TASKS - 1].id = taskId;
  s_tasks[MAX_TASKS - 1].used = true;
  s_tasks[MAX_TASKS - 1].summary = s;
  s_tasks[MAX_TASKS - 1].description = d;
}

static void taskStoreRemove(int64_t taskId) {
  for (int i = 0; i < MAX_TASKS; i++) {
    if (s_tasks[i].used && s_tasks[i].id == taskId) {
      s_tasks[i].used = false;
      s_tasks[i].summary = "";
      s_tasks[i].description = "";
      // Compact: shift later entries down
      for (int j = i; j < MAX_TASKS - 1; j++) {
        s_tasks[j] = s_tasks[j + 1];
      }
      s_tasks[MAX_TASKS - 1].used = false;
      s_tasks[MAX_TASKS - 1].id = 0;
      s_tasks[MAX_TASKS - 1].summary = "";
      s_tasks[MAX_TASKS - 1].description = "";
      return;
    }
  }
}

static void taskStoreClearAll() {
  for (int i = 0; i < MAX_TASKS; i++) {
    s_tasks[i].used = false;
    s_tasks[i].summary = "";
    s_tasks[i].description = "";
  }
}

static bool taskStoreHasAny() {
  for (int i = 0; i < MAX_TASKS; i++) {
    if (s_tasks[i].used) return true;
  }
  return false;
}

static int taskStoreCount() {
  int n = 0;
  for (int i = 0; i < MAX_TASKS; i++) {
    if (s_tasks[i].used) n++;
  }
  return n;
}

// Summary for status/red screen only: use summary field only (no description fallback),
// so the shut-down screen stays brief and full problem description stays on Details tab.
static String taskStoreGetAggregatedSummary() {
  String out;
  for (int i = 0; i < MAX_TASKS; i++) {
    if (!s_tasks[i].used) continue;
    if (s_tasks[i].summary.length() == 0) continue;
    if (out.length() > 0) out += " | ";
    out += s_tasks[i].summary;
  }
  return out;
}

static String taskStoreGetAggregatedDescription() {
  String out;
  for (int i = 0; i < MAX_TASKS; i++) {
    if (!s_tasks[i].used) continue;
    if (out.length() > 0) out += "\n\n---\n\n";
    if (s_tasks[i].description.length() > 0)
      out += s_tasks[i].description;
    else if (s_tasks[i].summary.length() > 0)
      out += s_tasks[i].summary;
  }
  return out;
}

// MQTT Callback
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  static char message[MQTT_MESSAGE_BUFFER_SIZE];
  
  if (length >= sizeof(message)) {
    Serial.print("Message too large: ");
    Serial.print(length);
    Serial.println(" bytes");
    return;
  }
  
  memcpy(message, payload, length);
  message[length] = '\0';
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] (");
  Serial.print(length);
  Serial.println(" bytes)");
  
  processMQTTMessage(topic, message);
}

// Process MQTT Message (branch by topic: status, operational, task, overall)
void processMQTTMessage(const char* topic, const char* payload) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // ---- Operational: independent message ----
  if (strcmp(topic, mqtt_topic_operational.c_str()) == 0) {
    tool_operational = doc["operational"] | true;
    if (doc["tool_name"].is<const char*>()) {
      toolDisplayName = capitalizeToolName(doc["tool_name"].as<const char*>());
      if (title_label)
        lv_label_set_text(title_label, toolDisplayName.c_str());
    }
    applyMainScreenState();
    Serial.print("Operational: ");
    Serial.println(tool_operational ? "true" : "false");
    return;
  }
  
  // ---- Task: independent message (can be large - problem_description) ----
  if (strcmp(topic, mqtt_topic_task.c_str()) == 0) {
    String msg_summary = "";
    String msg_description = "";
    if (doc["task_summary"].is<const char*>())
      msg_summary = doc["task_summary"].as<const char*>();
    if (doc["problem_description"].is<const char*>())
      msg_description = doc["problem_description"].as<const char*>();

    // Parse task_id (integer or string from JSON)
    bool has_task_id = doc.containsKey("task_id") && !doc["task_id"].isNull();
    int64_t task_id_val = 0;
    if (has_task_id) {
      if (doc["task_id"].is<int>() || doc["task_id"].is<long>() || doc["task_id"].is<long long>())
        task_id_val = doc["task_id"].as<int64_t>();
      else if (doc["task_id"].is<const char*>())
        task_id_val = (int64_t)atoll(doc["task_id"].as<const char*>());
    }

    const bool both_empty = (msg_summary.length() == 0 && msg_description.length() == 0);

    if (both_empty && has_task_id && (doc["task_id"].is<int>() || doc["task_id"].is<long>() || doc["task_id"].is<long long>() || doc["task_id"].is<const char*>())) {
      // Clear-one: remove this task_id from the store
      taskStoreRemove(task_id_val);
      Serial.print("Task remove id=");
      Serial.println((long)task_id_val);
    } else if (both_empty && !has_task_id) {
      // Clear-all (backward compat): empty payload without task_id
      taskStoreClearAll();
      Serial.println("Tasks clear");
    } else {
      // Add or update: sanitize internal event names, then add/update
      if (msg_summary.equalsIgnoreCase("task_shutdown") || msg_summary.equalsIgnoreCase("task_updated") ||
          msg_summary.equalsIgnoreCase("task") || msg_summary.equalsIgnoreCase("task_created"))
        msg_summary = "";
      taskStoreAddOrUpdate(task_id_val, msg_summary, msg_description);
      Serial.print("Task add/update id=");
      Serial.println((long)task_id_val);
    }

    has_task = taskStoreHasAny();
    task_summary = taskStoreGetAggregatedSummary();
    problem_description = taskStoreGetAggregatedDescription();

    if (problem_description_label) {
      if (problem_description.length() > 0)
        lv_label_set_text(problem_description_label, problem_description.c_str());
      else
        lv_label_set_text(problem_description_label, "No problem description.");
    }

    if (btn_forward) {
      if (has_task)
        lv_obj_clear_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);
      else
        lv_obj_add_flag(btn_forward, LV_OBJ_FLAG_HIDDEN);
    }

    applyMainScreenState();
    Serial.print("Task: has_task=");
    Serial.print(has_task ? "1" : "0");
    Serial.print(" tasks count=");
    Serial.println(taskStoreCount());
    return;
  }
  
  // ---- Status: enable/disable, user, time (existing) ----
  if (strcmp(topic, mqtt_topic_status.c_str()) == 0) {
    if (doc["user_name"].is<const char*>()) {
      const char* userName = doc["user_name"];
      if (user_value)
        lv_label_set_text(user_value, userName);
    }
    if (doc["timestamp"].is<const char*>()) {
      const char* timestamp = doc["timestamp"];
      if (time_value)
        lv_label_set_text(time_value, timestamp);
    }
    if (doc["time_label"].is<const char*>()) {
      const char* timeLabelFromPayload = doc["time_label"];
      if (time_label) lv_label_set_text(time_label, timeLabelFromPayload);
    }
    if (doc["user_label"].is<const char*>()) {
      const char* userLabelFromPayload = doc["user_label"];
      if (user_label) lv_label_set_text(user_label, userLabelFromPayload);
    }
    if (doc["tool_name"].is<const char*>()) {
      const char* toolNameFromPayload = doc["tool_name"];
      String newDisplayName = capitalizeToolName(toolNameFromPayload);
      if (newDisplayName != toolDisplayName && title_label) {
        toolDisplayName = newDisplayName;
        lv_label_set_text(title_label, toolDisplayName.c_str());
      }
    }
    if (doc["event_type"].is<const char*>()) {
      const char* eventType = doc["event_type"];
      last_status_enabled = (strcmp(eventType, "enabled") == 0);
      updateStatusIndicator(last_status_enabled);
      if (user_label) {
        lv_label_set_text(user_label, last_status_enabled ? "Current User" : "Last User");
      }
    }
    return;
  }
  
  if (strcmp(topic, mqtt_topic_overall.c_str()) == 0) {
    Serial.println("Received overall status update");
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

// Update consolidated connection status (text only; applyMainScreenState sets color by operational state)
void updateConnectionStatus() {
  if (!status_label) return;

  bool wifiConnected = (WiFi.status() == WL_CONNECTED);
  bool mqttConnected = mqttClient.connected();

  String statusText = "Status: ";

  if (wifiConnected && mqttConnected) {
    statusText += "Connected";
  } else if (wifiConnected && !mqttConnected) {
    statusText += "WiFi OK, No MQTT";
  } else if (!wifiConnected && mqttConnected) {
    statusText += "No WiFi, MQTT OK";
  } else {
    statusText += "No WiFi, No MQTT";
  }

  lv_label_set_text(status_label, statusText.c_str());
  // Color is set by applyMainScreenState (white when non-operational, black when operational)
  uint32_t statusColor = tool_operational ? 0x000000 : 0xFFFFFF;
  lv_obj_set_style_text_color(status_label, lv_color_hex(statusColor), 0);

  Serial.print("Updated status: ");
  Serial.println(statusText.c_str());
}

// Same layout for operational and non-operational; non-operational = red bg + white text
void applyMainScreenState() {
  if (!normal_container || !status_indicator || !outer_ring) return;

  const uint32_t white = 0xFFFFFF;
  const uint32_t black = 0x000000;
  const uint32_t red = 0xFF0000;

  if (!tool_operational) {
    // Same screen, red background, white text, same info (last user, disabled since, connection status)
    lv_obj_clear_flag(normal_container, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_bg_color(normal_container, lv_color_hex(red), 0);
    lv_obj_set_style_bg_color(status_indicator, lv_color_hex(red), 0);
    lv_obj_set_style_border_color(outer_ring, lv_color_hex(red), 0);
    lv_obj_set_style_border_color(status_indicator, lv_color_hex(red), 0);

    if (title_label) {
      lv_label_set_text(title_label, (toolDisplayName + " shut down").c_str());
      lv_obj_set_style_text_color(title_label, lv_color_hex(white), 0);
    }
    if (user_label) lv_obj_set_style_text_color(user_label, lv_color_hex(white), 0);
    if (user_value) lv_obj_set_style_text_color(user_value, lv_color_hex(white), 0);
    if (time_label) lv_obj_set_style_text_color(time_label, lv_color_hex(white), 0);
    if (time_value) lv_obj_set_style_text_color(time_value, lv_color_hex(white), 0);
    if (status_label) lv_obj_set_style_text_color(status_label, lv_color_hex(white), 0);

    if (task_summary_label) {
      lv_label_set_text(task_summary_label, task_summary.c_str());
      lv_obj_set_style_text_color(task_summary_label, lv_color_hex(white), 0);
      lv_obj_clear_flag(task_summary_label, LV_OBJ_FLAG_HIDDEN);
    }
  } else {
    lv_obj_clear_flag(normal_container, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_bg_color(normal_container, lv_color_hex(white), 0);
    lv_obj_set_style_bg_color(status_indicator, lv_color_hex(white), 0);
    updateOuterRing(has_task);
    updateStatusIndicator(last_status_enabled);

    if (title_label) {
      lv_label_set_text(title_label, toolDisplayName.c_str());
      lv_obj_set_style_text_color(title_label, lv_color_hex(black), 0);
    }
    if (user_label) lv_obj_set_style_text_color(user_label, lv_color_hex(black), 0);
    if (user_value) lv_obj_set_style_text_color(user_value, lv_color_hex(black), 0);
    if (time_label) lv_obj_set_style_text_color(time_label, lv_color_hex(black), 0);
    if (time_value) lv_obj_set_style_text_color(time_value, lv_color_hex(black), 0);
    if (status_label) lv_obj_set_style_text_color(status_label, lv_color_hex(black), 0);

    if (task_summary_label)
      lv_obj_add_flag(task_summary_label, LV_OBJ_FLAG_HIDDEN);
  }
}

// Outer ring: yellow when task, background color when no task (border width always same so layout never shifts)
void updateOuterRing(bool hasTask) {
  if (!outer_ring) return;
  if (hasTask) {
    lv_obj_set_style_border_color(outer_ring, lv_color_hex(0xFFFF00), 0);
    Serial.println("Outer ring: YELLOW (task)");
  } else {
    lv_obj_set_style_border_color(outer_ring, lv_color_hex(0xFFFFFF), 0);  // Match normal_container background
    Serial.println("Outer ring: none (no task)");
  }
}

// Inner ring: green = enabled, red = disabled
void updateStatusIndicator(bool isEnabled) {
  if (!status_indicator) return;
  if (isEnabled) {
    lv_obj_set_style_border_color(status_indicator, lv_color_hex(0x00FF00), 0);
    Serial.println("Inner ring: GREEN (enabled)");
  } else {
    lv_obj_set_style_border_color(status_indicator, lv_color_hex(0xFF0000), 0);
    Serial.println("Inner ring: RED (disabled)");
  }
}
