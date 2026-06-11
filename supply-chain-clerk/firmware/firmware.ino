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
const int SERVO_PIN_2 = 16; // Changed from 12 to 16 because 12 causes a boot crash!
const int SERVO_PIN_3 = 14;

// L298N DC Motor Driver Pins (Conveyor Belt)
const int MOTOR_IN1 = 18;
const int MOTOR_IN2 = 19;
const int MOTOR_IN3 = 21;
const int MOTOR_IN4 = 22;
const int MOTOR_ENA = 23; // Speed Control Motor A
const int MOTOR_ENB = 32; // Speed Control Motor B
const int CONVEYOR_SPEED = 255; // MUST BE 255! 150 is not enough power to spin loaded motors.

// Entry Ultrasonic Sensor (Box Detection)
const int TRIG_PIN = 4;
const int ECHO_PIN = 33;
const int DETECTION_DISTANCE_CM = 15; // Trigger when box is closer than 15cm

// Camera Trigger (Wired to GPIO 13 of ESP32-CAM)
const int CAM_TRIGGER_PIN = 5;

// Destination IR Sensors (Placement Confirmation)
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

bool conveyorRunning = false;
bool processingBox = false;

void startConveyor() {
  Serial.println("--- DEBUG: startConveyor() CALLED ---");
  
  // Use digitalWrite instead of analogWrite!
  // The ESP32Servo library uses up the ESP32's internal PWM timers, which can cause analogWrite to silently fail.
  // Setting ENA/ENB to HIGH gives 100% speed safely without needing PWM timers.
  digitalWrite(MOTOR_ENA, HIGH);
  digitalWrite(MOTOR_ENB, HIGH);
  
  // Motor A Forward
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  
  // Motor B Forward
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, HIGH);
  
  conveyorRunning = true;
  processingBox = false;
  Serial.println("Conveyor STARTED.");
}

void stopConveyor() {
  Serial.println("--- DEBUG: stopConveyor() CALLED ---");
  digitalWrite(MOTOR_ENA, LOW);
  digitalWrite(MOTOR_ENB, LOW);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
  conveyorRunning = false;
  Serial.println("Conveyor STOPPED.");
}

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
    
    // Create a random client ID to prevent HiveMQ from rejecting us if it thinks we are already connected!
    String randomClientId = "esp32-conveyor-" + String(random(0xffff), HEX);
    
    if (client.connect(randomClientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println("connected!");
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
  
  // AI processing complete! Restart conveyor to push box into bin
  Serial.println("Decision received. Restarting conveyor...");
  startConveyor();
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
  delay(1000); // Give serial monitor time to connect

  Serial.println("=========================================");
  Serial.println("ESP32 DEV MODULE BOOTING UP...");
  
  // Print Reset Reason to check if it's crashing from a power issue
  esp_reset_reason_t reason = esp_reset_reason();
  Serial.print("Last Reset Reason: ");
  Serial.println((int)reason); // 1=PowerOn, 3=SoftwareReset, 4=Watchdog, 12=Brownout (Power Drop)
  Serial.println("=========================================");

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

  // Setup Destination IR Sensors
  pinMode(IR_PIN_1, INPUT);
  pinMode(IR_PIN_2, INPUT);
  pinMode(IR_PIN_3, INPUT);

  // Setup Entry Ultrasonic Sensor
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Setup Camera Trigger Pin
  pinMode(CAM_TRIGGER_PIN, OUTPUT);
  digitalWrite(CAM_TRIGGER_PIN, HIGH); // Default HIGH, trigger is LOW

  // Setup DC Motor Pins
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT);
  pinMode(MOTOR_IN4, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(MOTOR_ENB, OUTPUT);

  // Secure connection setup (skipping cert validation for demo simplicity)
  espClient.setInsecure();

  setup_wifi();
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(mqttCallback);

  // Start the conveyor!
  startConveyor();
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

  // ── Conveyor & Camera Trigger Logic ──────────────────────────────────────────
  
  // Measure distance with Ultrasonic Sensor
  long duration;
  int distance = 999; // Default to far away
  
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // CRITICAL FIX: Reduced timeout from 20000us to 3000us (3 milliseconds)
  // 3000us is enough time for sound to travel ~50cm.
  // If we wait 20ms every loop, it feels laggy. 3ms makes it lightning fast like the IR sensor!
  duration = pulseIn(ECHO_PIN, HIGH, 3000); 
  
  if (duration > 0) {
    distance = duration * 0.034 / 2;
  }

  // If the conveyor is running, we are NOT currently processing a box, 
  // AND the Ultrasonic sensor detects a box closer than the threshold
  if (conveyorRunning && !processingBox && distance < DETECTION_DISTANCE_CM) {
    Serial.print(">>> ULTRASONIC SENSOR TRIGGERED! Box detected at ");
    Serial.print(distance);
    Serial.println(" cm.");
    stopConveyor();
    processingBox = true;
    
    Serial.println(">>> Waiting 500ms for box to settle...");
    delay(500); 
    
    Serial.println(">>> Sending LOW pulse to ESP32-CAM on GPIO 5...");
    digitalWrite(CAM_TRIGGER_PIN, LOW);
    delay(100);
    digitalWrite(CAM_TRIGGER_PIN, HIGH);
    Serial.println(">>> Pulse sent! Camera should be uploading now.");
    Serial.println(">>> Waiting patiently for MQTT response from Hugging Face AI...");
    
    // Now we wait. The ESP32-CAM uploads the photo, Hugging Face AI processes it,
    // and sends an MQTT message back which calls activateBin(), which restarts the conveyor!
  }

  // Check Destination IR sensors for confirmations (object detected = LOW)
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
