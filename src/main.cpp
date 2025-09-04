/*
 * NEMO Tool Display - ESP32 Display Node
 * Receives tool status via MQTT and displays on OLED screen
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <U8g2lib.h>
#include <Wire.h>

// WiFi credentials
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// MQTT configuration
const char* mqtt_server = MQTT_BROKER;
const int mqtt_port = MQTT_PORT;
const char* mqtt_client_id = MQTT_CLIENT_ID;
const char* mqtt_topic_prefix = MQTT_TOPIC_PREFIX;

// Display configuration
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, DISPLAY_SCL, DISPLAY_SDA);

// MQTT client
WiFiClient espClient;
PubSubClient client(espClient);

// Tool data structure
struct ToolStatus {
  String id;
  String name;
  String status;
  String user;
  String lastUpdated;
  bool valid;
};

// Global variables
ToolStatus currentTool;
bool displayUpdateNeeded = false;
unsigned long lastReconnectAttempt = 0;
const unsigned long reconnectInterval = 5000; // 5 seconds

void setup() {
  Serial.begin(115200);
  Serial.println("NEMO Tool Display Starting...");
  
  // Initialize display
  u8g2.begin();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.clearBuffer();
  u8g2.drawStr(0, 20, "NEMO Tool Display");
  u8g2.drawStr(0, 40, "Initializing...");
  u8g2.sendBuffer();
  
  // Initialize tool status
  currentTool.valid = false;
  
  // Connect to WiFi
  setupWiFi();
  
  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  
  Serial.println("Setup complete");
}

void loop() {
  // Handle MQTT connection
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > reconnectInterval) {
      lastReconnectAttempt = now;
      if (reconnectMQTT()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client.loop();
  }
  
  // Update display if needed
  if (displayUpdateNeeded) {
    updateDisplay();
    displayUpdateNeeded = false;
  }
  
  delay(100);
}

void setupWiFi() {
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection failed");
    displayError("WiFi Failed");
  }
}

bool reconnectMQTT() {
  if (client.connect(mqtt_client_id)) {
    Serial.println("MQTT connected");
    
    // Subscribe to tool status topics
    String toolTopic = String(mqtt_topic_prefix) + "/+/status";
    client.subscribe(toolTopic.c_str());
    
    String overallTopic = String(mqtt_topic_prefix) + "/overall";
    client.subscribe(overallTopic.c_str());
    
    return true;
  } else {
    Serial.print("MQTT connection failed, rc=");
    Serial.print(client.state());
    Serial.println(" retrying in 5 seconds");
    return false;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  // Convert payload to string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
  
  // Parse JSON
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Check if this is a tool status message
  String topicStr = String(topic);
  if (topicStr.indexOf("/status") > 0) {
    // Extract tool ID from topic
    int lastSlash = topicStr.lastIndexOf('/');
    int secondLastSlash = topicStr.lastIndexOf('/', lastSlash - 1);
    String toolId = topicStr.substring(secondLastSlash + 1, lastSlash);
    
    // Update tool status
    currentTool.id = toolId;
    currentTool.name = doc["name"].as<String>();
    currentTool.status = doc["status"].as<String>();
    currentTool.user = doc["user"].as<String>();
    currentTool.lastUpdated = doc["last_updated"].as<String>();
    currentTool.valid = true;
    
    displayUpdateNeeded = true;
    
    Serial.println("Tool status updated:");
    Serial.println("  ID: " + currentTool.id);
    Serial.println("  Name: " + currentTool.name);
    Serial.println("  Status: " + currentTool.status);
    Serial.println("  User: " + currentTool.user);
  }
}

void updateDisplay() {
  u8g2.clearBuffer();
  
  if (!currentTool.valid) {
    u8g2.setFont(u8g2_font_ncenB10_tr);
    u8g2.drawStr(0, 20, "No Tool Data");
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(0, 40, "Waiting for MQTT...");
  } else {
    // Display tool name
    u8g2.setFont(u8g2_font_ncenB10_tr);
    String displayName = currentTool.name;
    if (displayName.length() > 15) {
      displayName = displayName.substring(0, 12) + "...";
    }
    u8g2.drawStr(0, 15, displayName.c_str());
    
    // Display status with color indication
    u8g2.setFont(u8g2_font_ncenB08_tr);
    String statusText = "Status: " + currentTool.status;
    u8g2.drawStr(0, 30, statusText.c_str());
    
    // Display user if available
    if (currentTool.user.length() > 0) {
      String userText = "User: " + currentTool.user;
      if (userText.length() > 20) {
        userText = userText.substring(0, 17) + "...";
      }
      u8g2.drawStr(0, 45, userText.c_str());
    }
    
    // Display last updated time
    u8g2.setFont(u8g2_font_ncenB06_tr);
    String timeText = "Updated: " + currentTool.lastUpdated.substring(11, 19);
    u8g2.drawStr(0, 60, timeText.c_str());
  }
  
  u8g2.sendBuffer();
}

void displayError(String error) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB10_tr);
  u8g2.drawStr(0, 30, error.c_str());
  u8g2.sendBuffer();
}
