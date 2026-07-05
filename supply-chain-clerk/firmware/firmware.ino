#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h> 

// ── WiFi / MQTT config (100% LOCAL) ──────────────────────────────────────────
const char* SSID        = "can't you afford?";
const char* WIFI_PASS   = "Abcdefgh"; 
const char* MQTT_SERVER = "10.117.196.80";      
const int   MQTT_PORT   = 1883;                 

// ── Hardware Pins ────────────────────────────────────────────────────────────
const int MOTOR_ENA = 14; 
const int MOTOR_IN1 = 27; 
const int MOTOR_IN2 = 26; 
const int MOTOR_IN3 = 25; 
const int MOTOR_IN4 = 33; 
const int MOTOR_ENB = 32; 

const int IR_SENSOR_PIN = 19; 
const int CAM_TRIGGER_PIN = 5;
const int SERVO_PIN = 13; 

WiFiClient espClient;
PubSubClient client(espClient);
Servo sortingServo; 

// ── Variables ─────────────────────────────────────────────────────────────────
unsigned long lastHeartbeat = 0;
bool conveyorRunning = false;
bool processingBox = false;
unsigned long processingStartTime = 0;
const unsigned long CLEARANCE_DELAY_MS = 4000; 

// ── CONVEYOR SPEED CONTROL ────────────────────────────────────────────────────
// 0 is completely stopped, 255 is maximum speed. 
// Try values between 100 and 200 to find the sweet spot!
const int CONVEYOR_SPEED = 140; 
// ──────────────────────────────────────────────────────────────────────────────

void startConveyor() {
  Serial.println("Conveyor STARTING...");
  
  // Use analogWrite (PWM) to control the speed instead of digitalWrite(HIGH)
  analogWrite(MOTOR_ENA, CONVEYOR_SPEED);
  analogWrite(MOTOR_ENB, CONVEYOR_SPEED);
  
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, HIGH);
  conveyorRunning = true;
  Serial.println("Conveyor STARTED.");
}

void stopConveyor() {
  Serial.println("Conveyor STOPPING...");
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
  Serial.print("Connecting to WiFi: ");
  Serial.println(SSID);
  
  WiFi.begin(SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting local MQTT connection to ");
    Serial.print(MQTT_SERVER);
    Serial.print("...");
    String randomClientId = "esp32-conveyor-" + String(random(0xffff), HEX);
    
    if (client.connect(randomClientId.c_str())) {
      Serial.println("connected!");
      client.subscribe("warehouse/bin/light");
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
  doc["conveyor_running"] = conveyorRunning;
  doc["processing_box"] = processingBox;
  
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish("warehouse/bin/status", buffer);
}

void publishConfirmation(const char* bin_id, const char* batch_no) {
  StaticJsonDocument<200> doc;
  doc["bin_id"] = bin_id;
  doc["confirmed"] = true;
  doc["batch_no"] = batch_no;
  
  char buffer[200];
  serializeJson(doc, buffer);
  client.publish("warehouse/bin/confirm", buffer);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(msg);

  if (strcmp(topic, "warehouse/bin/light") == 0) {
    Serial.println("AI Response Received! BLIND ACTUATION STARTING...");

    // ── BLIND SERVO MOVEMENT (IGNORING EVERYTHING) ──────────────────────────
    for (int pos = 0; pos <= 190; pos += 1) { 
      sortingServo.write(pos);              // Tell servo to go to position in variable 'pos'
      delay(4);                       // Wait 4ms for the servo to reach the position
    }
    
    // Sweep back from 190 to 0 degrees
    for (int pos = 190; pos >= 0; pos -= 1) { 
      sortingServo.write(pos);              // Tell servo to go to position in variable 'pos'
      delay(4);                       // Wait 4ms for the servo to reach the position
    }
    // ────────────────────────────────────────────────────────────────────────
    
    Serial.println("Servo movement complete. Restarting Conveyor.");
    startConveyor();
    processingStartTime = millis();
    processingBox = false;
    
    // Try to parse JSON just for confirmation, but don't let it stop us
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, msg);
    if (!error) {
      const char* bin_id = doc["bin_id"] | "unknown";
      const char* batch_no = doc["batch_no"] | "unknown";
      publishConfirmation(bin_id, batch_no);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=========================================");
  Serial.println("ESP32 CONVEYOR CONTROLLER STARTING...");
  Serial.println("=========================================");

  // ── FIX FOR SERVO LIBRARY ON ESP32 ────────────────────────────────────────
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  sortingServo.setPeriodHertz(50); // Standard 50Hz servo
  sortingServo.attach(SERVO_PIN, 500, 2400); 
  sortingServo.write(90); // Center position
  // ──────────────────────────────────────────────────────────────────────────

  pinMode(IR_SENSOR_PIN, INPUT_PULLUP);
  pinMode(CAM_TRIGGER_PIN, OUTPUT);
  digitalWrite(CAM_TRIGGER_PIN, HIGH);

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT);
  pinMode(MOTOR_IN4, OUTPUT);
  
  // Set ENA and ENB as outputs
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(MOTOR_ENB, OUTPUT);

  setup_wifi();
  
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(mqttCallback);

  startConveyor();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  
  if (now - lastHeartbeat > 10000) {
    lastHeartbeat = now;
    publishStatus();
  }

  bool rawSensorValue = digitalRead(IR_SENSOR_PIN);

  bool boxDetected = false;
  static unsigned long sensorDetectionStartTime = 0;

  if (rawSensorValue == LOW) {
    if (sensorDetectionStartTime == 0) {
      sensorDetectionStartTime = millis();
    } else if (millis() - sensorDetectionStartTime > 150) { 
      boxDetected = true;
    }
  } else {
    sensorDetectionStartTime = 0;
  }

  if (conveyorRunning && !processingBox && boxDetected && (now - processingStartTime > CLEARANCE_DELAY_MS)) {
    Serial.println(">>> IR SENSOR DETECTED BOX! Waiting 1 sec for it to reach camera...");
    
    // Allow the conveyor to keep running for 1 second so the box reaches the camera
    delay(1000); 
    
    stopConveyor();
    processingBox = true;
    delay(500); // Wait half a second for the box to completely stop shaking
    
    Serial.println(">>> Triggering ESP32-CAM...");
    digitalWrite(CAM_TRIGGER_PIN, LOW);
    delay(100);
    digitalWrite(CAM_TRIGGER_PIN, HIGH);
  }
}
