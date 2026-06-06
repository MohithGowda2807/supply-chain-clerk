/*
 * Supply Chain Clerk — ESP32 Firmware
 * 
 * Hardware:
 *   - ESP32 (any variant)
 *   - WS2812B LED strip (5 segments, one per bin)
 *   - 5 confirmation buttons (or IR sensors) — GPIO 32–36
 *   - WiFi connection to same LAN as backend
 *
 * MQTT Topics:
 *   Subscribe: warehouse/bin/light    (bin lighting commands)
 *   Subscribe: warehouse/bin/confirm  (not used from ESP32 Rx side)
 *   Publish:   warehouse/bin/confirm  (button presses)
 *   Publish:   warehouse/bin/status   (heartbeat every 10 s)
 *
 * USB Serial Fallback:
 *   Listens at 115200 baud for the same JSON commands as MQTT.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <FastLED.h>
#include <ArduinoJson.h>

// ── WiFi / MQTT config ────────────────────────────────────────────────────────
const char* SSID        = "YOUR_WIFI_SSID";
const char* WIFI_PASS   = "YOUR_WIFI_PASSWORD";
const char* MQTT_SERVER = "192.168.1.100";   // ← replace with host IP
const int   MQTT_PORT   = 1883;
const char* CLIENT_ID   = "esp32-warehouse-01";

// ── LED config ────────────────────────────────────────────────────────────────
#define LED_PIN        5
#define NUM_LEDS      20     // 20 bins × 1 LED each (or use segments)
#define LED_TYPE   WS2812B
#define COLOR_ORDER    GRB

CRGB leds[NUM_LEDS];

// ── Bin map: bin_code → led_index, button_gpio ────────────────────────────────
struct BinDef {
  const char* bin_code;
  int         led_index;
  int         button_gpio;
};

const BinDef BIN_MAP[] = {
  {"A01", 0,  32}, // GPIO 32 has internal pull-up
  {"A02", 1,  33}, // GPIO 33 has internal pull-up
  {"A03", 2,  25}, // GPIO 25 has internal pull-up (replaces GPIO 34 which is input-only)
  {"A04", 3,  26}, // GPIO 26 has internal pull-up (replaces GPIO 35 which is input-only)
  {"A05", 4,  27}, // GPIO 27 has internal pull-up (replaces GPIO 36 which is input-only)
};
const int NUM_BINS = sizeof(BIN_MAP) / sizeof(BIN_MAP[0]);

// ── LED State Machine ─────────────────────────────────────────────────────────
enum LedState { LED_OFF, AWAITING, CONFIRMED, ALERT_EXPIRY, ALERT_QUARANTINE };

struct BinState {
  LedState state        = LED_OFF;
  unsigned long timer   = 0;
  bool          active  = false;
};

BinState binStates[NUM_BINS];

// ── Button debounce ───────────────────────────────────────────────────────────
unsigned long lastButtonTime[NUM_BINS] = {0};
const unsigned long DEBOUNCE_MS = 50;

// ── MQTT ──────────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// ── Heartbeat ─────────────────────────────────────────────────────────────────
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 10000;

// ── Forward declarations ──────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length);
void connectMQTT();
void setLedForBin(int idx, LedState state);
void pollButtons();
void updateLeds();
void processSerialCommand(const String& line);

// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // LED strip
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS)
         .setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(100);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();

  // Button pins
  for (int i = 0; i < NUM_BINS; i++) {
    pinMode(BIN_MAP[i].button_gpio, INPUT_PULLUP);
  }

  // WiFi
  WiFi.begin(SSID, WIFI_PASS);
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 10000) {
    delay(250);
  }

  // MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  connectMQTT();
}

// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  if (WiFi.status() == WL_CONNECTED && !mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  pollButtons();
  updateLeds();

  // USB serial fallback
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) processSerialCommand(line);
  }

  // Heartbeat
  if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
    lastHeartbeat = millis();
    StaticJsonDocument<128> doc;
    doc["device"] = CLIENT_ID;
    doc["ts"]     = millis() / 1000;
    doc["wifi_rssi"] = WiFi.RSSI();
    String out;
    serializeJson(doc, out);
    mqttClient.publish("warehouse/bin/status", out.c_str());
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MQTT callback — handle warehouse/bin/light commands
// ─────────────────────────────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) return;

  const char* bin_id = doc["bin_id"];
  const char* colour = doc["colour"] | "green";

  for (int i = 0; i < NUM_BINS; i++) {
    if (strcmp(BIN_MAP[i].bin_code, bin_id) == 0) {
      LedState state = AWAITING;
      if (strcmp(colour, "amber")     == 0) state = ALERT_EXPIRY;
      if (strcmp(colour, "red")       == 0) state = ALERT_QUARANTINE;
      binStates[i].state = state;
      binStates[i].timer = millis();
      break;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Poll confirmation buttons (non-blocking, millis-based)
// ─────────────────────────────────────────────────────────────────────────────
void pollButtons() {
  unsigned long now = millis();
  for (int i = 0; i < NUM_BINS; i++) {
    if (binStates[i].state != AWAITING) continue;
    if (digitalRead(BIN_MAP[i].button_gpio) == LOW) {
      if (now - lastButtonTime[i] > DEBOUNCE_MS) {
        lastButtonTime[i] = now;

        // Transition to CONFIRMED
        binStates[i].state = CONFIRMED;
        binStates[i].timer = now;

        // Publish confirmation
        StaticJsonDocument<128> doc;
        doc["bin_id"] = BIN_MAP[i].bin_code;
        doc["ts"]     = now / 1000;
        String out;
        serializeJson(doc, out);
        mqttClient.publish("warehouse/bin/confirm", out.c_str());
      }
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// LED State Machine update (called every loop)
// ─────────────────────────────────────────────────────────────────────────────
void updateLeds() {
  unsigned long now = millis();
  bool changed = false;

  for (int i = 0; i < NUM_BINS; i++) {
    int idx = BIN_MAP[i].led_index;
    CRGB colour;

    switch (binStates[i].state) {
      case LED_OFF:
        colour = CRGB::Black;
        break;

      case AWAITING:
        colour = CRGB::Green;
        break;

      case CONFIRMED:
        // 2-second green flash, then off
        if (now - binStates[i].timer < 2000) {
          colour = CRGB::Lime;
        } else {
          binStates[i].state = LED_OFF;
          colour = CRGB::Black;
        }
        break;

      case ALERT_EXPIRY:
        // Slow amber pulse 1 Hz
        colour = ((now / 500) % 2 == 0) ? CRGB::Orange : CRGB::Black;
        break;

      case ALERT_QUARANTINE:
        // Fast red blink 4 Hz
        colour = ((now / 125) % 2 == 0) ? CRGB::Red : CRGB::Black;
        break;
    }

    if (leds[idx] != colour) {
      leds[idx] = colour;
      changed = true;
    }
  }

  if (changed) FastLED.show();
}

// ─────────────────────────────────────────────────────────────────────────────
// USB Serial command processor (same schema as MQTT)
// ─────────────────────────────────────────────────────────────────────────────
void processSerialCommand(const String& line) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, line) != DeserializationError::Ok) return;
  // Reuse the same handler
  char topicBuf[] = "warehouse/bin/light";
  mqttCallback(topicBuf, (byte*)line.c_str(), line.length());
}

// ─────────────────────────────────────────────────────────────────────────────
void connectMQTT() {
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 5) {
    if (mqttClient.connect(CLIENT_ID)) {
      mqttClient.subscribe("warehouse/bin/light");
    } else {
      delay(1000);
      attempts++;
    }
  }
}
