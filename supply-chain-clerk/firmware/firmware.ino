#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <FastLED.h>

// ── WiFi / MQTT config ────────────────────────────────────────────────────────
const char* SSID        = "can't you afford?";
const char* WIFI_PASS   = "Abcdefgh";
const char* MQTT_SERVER = "da26c5b9a71a4180ae338a5ffb38070a.s1.eu.hivemq.cloud";
const int   MQTT_PORT   = 8883;
const char* MQTT_USER   = "MoSDGo";
const char* MQTT_PASS   = "aERTdfr!67%34&*^%rdfsyt";
const char* CLIENT_ID   = "esp32-conveyor-01";

// ── Hardware Pins ────────────────────────────────────────────────────────────
// Servos (Conveyor Routing)
const int SERVO_PIN_1 = 13;
const int SERVO_PIN_2 = 12;
const int SERVO_PIN_3 = 14;

// IR Sensors (Placement Confirmation)
const int IR_PIN_1 = 25;
const int IR_PIN_2 = 26;
const int IR_PIN_3 = 27;

// WS2812B LEDs
#define LED_PIN     15
#define NUM_LEDS    3
#define BRIGHTNESS  100
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];
Servo servo1, servo2, servo3;

WiFiClientSecure espClient;
PubSubClient client(espClient);

// ── Variables ─────────────────────────────────────────────────────────────────
unsigned long lastHeartbeat = 0;
bool expectingConfirmation1 = false;
bool expectingConfirmation2 = false;
bool expectingConfirmation3 = false;
String pendingBatch1 = "";
String pendingBatch2 = "";
String pendingBatch3 = "";

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(SSID);
  
  WiFi.begin(SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(CLIENT_ID, MQTT_USER, MQTT_PASS)) {
      Serial.println("connected");
      client.subscribe("warehouse/bin/light");
      
      // Publish alive status immediately on connect
      publishStatus();
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void publishStatus() {
  StaticJsonDocument<200> doc;
  doc["esp32_alive"] = true;
  doc["status"] = "online";
  
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish("warehouse/bin/status", buffer);
}

void publishConfirmation(int binIndex, String batchNo) {
  StaticJsonDocument<200> doc;
  doc["bin_id"] = "A0" + String(binIndex + 1); // e.g., A01, A02, A03
  doc["confirmed"] = true;
  doc["batch_no"] = batchNo;
  
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish("warehouse/bin/confirm", buffer);
  Serial.print("Confirmed placement in Bin ");
  Serial.println(binIndex + 1);
}

void resetBin(int binIndex) {
  // Turn off LED
  leds[binIndex] = CRGB::Black;
  FastLED.show();
  
  // Reset Servo to 0 degrees (straight)
  if (binIndex == 0) servo1.write(0);
  if (binIndex == 1) servo2.write(0);
  if (binIndex == 2) servo3.write(0);
}

void activateBin(int binIndex, const char* colorStr) {
  // Light up LED
  if (strcmp(colorStr, "green") == 0) leds[binIndex] = CRGB::Green;
  else if (strcmp(colorStr, "amber") == 0) leds[binIndex] = CRGB::Orange;
  else if (strcmp(colorStr, "red") == 0) leds[binIndex] = CRGB::Red;
  else leds[binIndex] = CRGB::White; // Default
  FastLED.show();
  
  // Trigger Servo to 90 degrees (divert)
  if (binIndex == 0) servo1.write(90);
  if (binIndex == 1) servo2.write(90);
  if (binIndex == 2) servo3.write(90);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String msg = "";
  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(msg);

  if (strcmp(topic, "warehouse/bin/light") == 0) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, msg);
    if (error) return;

    const char* bin_id = doc["bin_id"];
    const char* color = doc["color"];
    const char* batch_no = doc["batch_no"];
    
    // Map bin_id (e.g. "A01", "A02", "A03") to integer indices (0, 1, 2)
    int binIndex = -1;
    if (strcmp(bin_id, "A01") == 0) binIndex = 0;
    else if (strcmp(bin_id, "A02") == 0) binIndex = 1;
    else if (strcmp(bin_id, "A03") == 0) binIndex = 2;

    if (binIndex != -1) {
      activateBin(binIndex, color);
      
      // Mark as expecting confirmation
      if (binIndex == 0) { expectingConfirmation1 = true; pendingBatch1 = String(batch_no); }
      if (binIndex == 1) { expectingConfirmation2 = true; pendingBatch2 = String(batch_no); }
      if (binIndex == 2) { expectingConfirmation3 = true; pendingBatch3 = String(batch_no); }
    }
  }
}

void setup() {
  Serial.begin(115200);

  // Setup LEDs
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(BRIGHTNESS);
  for(int i=0; i<NUM_LEDS; i++) leds[i] = CRGB::Black;
  FastLED.show();

  // Setup Servos
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo3.setPeriodHertz(50);
  servo1.attach(SERVO_PIN_1, 500, 2400);
  servo2.attach(SERVO_PIN_2, 500, 2400);
  servo3.attach(SERVO_PIN_3, 500, 2400);
  resetBin(0); resetBin(1); resetBin(2);

  // Setup IR Sensors
  pinMode(IR_PIN_1, INPUT);
  pinMode(IR_PIN_2, INPUT);
  pinMode(IR_PIN_3, INPUT);

  // Secure connection setup (skipping cert validation for demo simplicity)
  espClient.setInsecure();

  setup_wifi();
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(mqttCallback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Heartbeat every 10 seconds
  unsigned long now = millis();
  if (now - lastHeartbeat > 10000) {
    lastHeartbeat = now;
    publishStatus();
  }

  // Check IR sensors for confirmations (IR sensors typically read LOW when object detected)
  if (expectingConfirmation1 && digitalRead(IR_PIN_1) == LOW) {
    publishConfirmation(0, pendingBatch1);
    expectingConfirmation1 = false;
    resetBin(0);
    delay(500); // Debounce
  }
  
  if (expectingConfirmation2 && digitalRead(IR_PIN_2) == LOW) {
    publishConfirmation(1, pendingBatch2);
    expectingConfirmation2 = false;
    resetBin(1);
    delay(500); // Debounce
  }

  if (expectingConfirmation3 && digitalRead(IR_PIN_3) == LOW) {
    publishConfirmation(2, pendingBatch3);
    expectingConfirmation3 = false;
    resetBin(2);
    delay(500); // Debounce
  }
}
