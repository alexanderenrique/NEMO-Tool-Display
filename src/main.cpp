/*
 * NEMO Tool Display - ESP32 Display Node
 * Receives tool status via MQTT and displays on OLED screen
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <SPI.h>

// WiFi credentials
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// MQTT configuration
const char* mqtt_server = MQTT_BROKER;
const int mqtt_port = MQTT_PORT;
const char* mqtt_client_id = MQTT_CLIENT_ID;
const char* mqtt_topic_prefix = MQTT_TOPIC_PREFIX;

// Display configuration (TFT 480x320)
TFT_eSPI tft = TFT_eSPI();

// MQTT client
WiFiClient espClient;
PubSubClient client(espClient);

// Tool data structure
struct ToolStatus {
  String id;
  String name;
  String status;
  String category;
  bool operational;
  bool problematic;
  String timestamp;
  
  // User information (only when tool is in use)
  String userName;
  String userUsername;
  String userId;
  
  // Usage information (only when tool is in use)
  String usageStartTime;
  String usageStartTimeFormatted;
  String usageId;
  
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
  
  // Initialize TFT display
  tft.init();
  tft.setRotation(1); // Landscape orientation
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.drawString("NEMO Tool Display", 10, 50);
  tft.setTextSize(1);
  tft.drawString("Initializing...", 10, 100);
  
  // Initialize tool status
  currentTool.valid = false;
  
  // Connect to WiFi
  setupWiFi();
  
  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setKeepAlive(60);
  client.setSocketTimeout(15);
  
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
  tft.setTextSize(1);
  tft.drawString("Connecting to WiFi...", 10, 120);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    tft.drawString(".", 10 + (attempts * 8), 140);
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
    
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("WiFi Connected!", 10, 160);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("IP: " + WiFi.localIP().toString(), 10, 180);
  } else {
    Serial.println("WiFi connection failed");
    displayError("WiFi Failed");
  }
}

bool reconnectMQTT() {
  tft.setTextSize(1);
  tft.drawString("Connecting to MQTT...", 10, 200);
  
  if (client.connect(mqtt_client_id)) {
    Serial.println("MQTT connected");
    
    // Subscribe to tool status topics
    String toolTopic = String(mqtt_topic_prefix) + "/+/status";
    client.subscribe(toolTopic.c_str());
    
    String overallTopic = String(mqtt_topic_prefix) + "/overall";
    client.subscribe(overallTopic.c_str());
    
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("MQTT Connected!", 10, 220);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    
    return true;
  } else {
    Serial.print("MQTT connection failed, rc=");
    Serial.print(client.state());
    Serial.println(" retrying in 5 seconds");
    
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("MQTT Failed: " + String(client.state()), 10, 220);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    
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
  DynamicJsonDocument doc(2048); // Increased size for enhanced messages
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
    
    // Update basic tool status
    currentTool.id = toolId;
    currentTool.name = doc["name"].as<String>();
    currentTool.status = doc["status"].as<String>();
    currentTool.category = doc["category"].as<String>();
    currentTool.operational = doc["operational"].as<bool>();
    currentTool.problematic = doc["problematic"].as<bool>();
    currentTool.timestamp = doc["timestamp"].as<String>();
    
    // Parse user information if tool is in use
    if (doc["user"] != nullptr && !doc["user"].isNull()) {
      currentTool.userName = doc["user"]["name"].as<String>();
      currentTool.userUsername = doc["user"]["username"].as<String>();
      currentTool.userId = doc["user"]["id"].as<String>();
    } else {
      currentTool.userName = "";
      currentTool.userUsername = "";
      currentTool.userId = "";
    }
    
    // Parse usage information if tool is in use
    if (doc["usage"] != nullptr && !doc["usage"].isNull()) {
      currentTool.usageStartTime = doc["usage"]["start_time"].as<String>();
      currentTool.usageStartTimeFormatted = doc["usage"]["start_time_formatted"].as<String>();
      currentTool.usageId = doc["usage"]["usage_id"].as<String>();
    } else {
      currentTool.usageStartTime = "";
      currentTool.usageStartTimeFormatted = "";
      currentTool.usageId = "";
    }
    
    currentTool.valid = true;
    displayUpdateNeeded = true;
    
    Serial.println("Tool status updated:");
    Serial.println("  ID: " + currentTool.id);
    Serial.println("  Name: " + currentTool.name);
    Serial.println("  Status: " + currentTool.status);
    Serial.println("  User: " + currentTool.userName);
    if (currentTool.usageStartTimeFormatted.length() > 0) {
      Serial.println("  Started: " + currentTool.usageStartTimeFormatted);
    }
  }
}

void updateDisplay() {
  tft.fillScreen(TFT_BLACK);
  
  if (!currentTool.valid) {
    tft.setTextSize(3);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("No Tool Data", 50, 100);
    
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Waiting for MQTT...", 50, 150);
  } else {
    // Clear screen and draw header
    tft.fillScreen(TFT_BLACK);
    tft.drawRect(5, 5, 470, 310, TFT_WHITE);
    
    // Tool name (large, centered)
    tft.setTextSize(4);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    String displayName = currentTool.name;
    if (displayName.length() > 20) {
      displayName = displayName.substring(0, 17) + "...";
    }
    tft.drawString(displayName, 20, 30);
    
    // Status with color coding
    tft.setTextSize(3);
    String statusText = "Status: " + currentTool.status;
    if (currentTool.status == "active") {
      tft.setTextColor(TFT_GREEN, TFT_BLACK);
    } else if (currentTool.status == "idle") {
      tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    } else if (currentTool.status == "maintenance") {
      tft.setTextColor(TFT_ORANGE, TFT_BLACK);
    } else {
      tft.setTextColor(TFT_RED, TFT_BLACK);
    }
    tft.drawString(statusText, 20, 80);
    
    // User information (enhanced)
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    if (currentTool.userName.length() > 0) {
      // Show user name
      String userText = "User: " + currentTool.userName;
      if (userText.length() > 30) {
        userText = userText.substring(0, 27) + "...";
      }
      tft.drawString(userText, 20, 120);
      
      // Show start time if tool is in use
      if (currentTool.usageStartTimeFormatted.length() > 0) {
        tft.setTextSize(1);
        tft.setTextColor(TFT_GRAY, TFT_BLACK);
        tft.drawString("Started: " + currentTool.usageStartTimeFormatted, 20, 150);
        tft.setTextSize(2);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
      }
    } else {
      tft.drawString("Available for use", 20, 120);
    }
    
    // Tool ID and category
    tft.setTextSize(1);
    tft.setTextColor(TFT_GRAY, TFT_BLACK);
    tft.drawString("ID: " + currentTool.id + " | " + currentTool.category, 20, 190);
    
    // Last updated time
    String timeText = "Updated: " + currentTool.timestamp.substring(11, 19);
    tft.drawString(timeText, 20, 210);
    
    // Draw status indicator box
    int boxX = 350;
    int boxY = 80;
    int boxW = 100;
    int boxH = 60;
    
    if (currentTool.status == "active") {
      tft.fillRect(boxX, boxY, boxW, boxH, TFT_GREEN);
    } else if (currentTool.status == "idle") {
      tft.fillRect(boxX, boxY, boxW, boxH, TFT_YELLOW);
    } else if (currentTool.status == "maintenance") {
      tft.fillRect(boxX, boxY, boxW, boxH, TFT_ORANGE);
    } else {
      tft.fillRect(boxX, boxY, boxW, boxH, TFT_RED);
    }
    
    tft.setTextColor(TFT_BLACK, TFT_WHITE);
    tft.setTextSize(2);
    tft.drawString(currentTool.status.toUpperCase(), boxX + 10, boxY + 20);
  }
}

void displayError(String error) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextSize(3);
  tft.setTextColor(TFT_RED, TFT_BLACK);
  tft.drawString("ERROR", 150, 100);
  tft.setTextSize(2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString(error, 50, 150);
}
