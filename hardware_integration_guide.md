# Hardware & Software Integration Master Guide

This guide covers exactly what you need to do, step-by-step, to take your cloud software and physical hardware and merge them into a fully working Agentic Supply Chain Clerk with a conveyor belt.

---

## Phase 1: Software Verification (The "Sanity Check")
Before touching the hardware, make sure the cloud infrastructure is doing its job.

1. **Verify Backend API:** Open your browser and go to `https://supply-chain-clerk.onrender.com/docs`. You should see the FastAPI documentation.
2. **Verify Frontend UI:** Open `https://supply-chain-clerk-998.web.app`. You should see your dashboard and it should say it's connected to the WebSocket.
3. **Verify MQTT:** 
   - Go to your [HiveMQ Cloud Dashboard](https://console.hivemq.cloud/).
   - Click on the **Web Client** tab.
   - Enter your credentials (`MoSDGo` / `aERTdfr!67%34&*^%rdfsyt`) and click **Connect**.
   - Subscribe to the topic: `warehouse/bin/light`.
   - Now, on your Render backend (`/docs`), try triggering a test intake. You should see a message pop up in your HiveMQ Web Client. If you do, your cloud is perfect.

---

## Phase 2: The "Hands" (ESP32 Dev Module)
This board runs the conveyor belt sorting (servo motor) and the bin LEDs.

### 1. Wiring the Hardware
- **Servo Motor (Sorting Mechanism):**
  - Connect **VCC (Red)** to the ESP32 `VIN` (5V pin).
  - Connect **GND (Brown/Black)** to the ESP32 `GND`.
  - Connect **Signal (Yellow/Orange)** to a GPIO pin (e.g., `GPIO 13`).
- **IR Sensor (Confirmation Sensor):**
  - Connect **VCC** to `3.3V`.
  - Connect **GND** to `GND`.
  - Connect **OUT** to a GPIO pin (e.g., `GPIO 14`).
- **LEDs (Bin Indicators):**
  - Connect the long leg (+) of your LED to `GPIO 12` (through a 220-ohm resistor).
  - Connect the short leg (-) to `GND`.

### 2. Updating the Firmware
Open the `firmware/firmware.ino` file I wrote for you. You need to make a few additions to integrate the servo and sensors:
```cpp
#include <ESP32Servo.h> // Add this library

Servo sortServo;
const int servoPin = 13;
const int irSensorPin = 14;
const int ledPin = 12;

void setup() {
  // Existing setup code...
  
  // Add your hardware setup:
  sortServo.attach(servoPin);
  pinMode(irSensorPin, INPUT);
  pinMode(ledPin, OUTPUT);
}

// Inside the MQTT callback() function where it receives the Bin ID:
void callback(char* topic, byte* payload, unsigned int length) {
  // If the backend tells us to light up Bin 1:
  digitalWrite(ledPin, HIGH); // Turn on the Bin LED
  sortServo.write(90);        // Move servo to 90 degrees to route item to Bin 1
}

void loop() {
  // Existing loop code...
  
  // Check if the item fell into the bin (IR sensor blocked)
  if (digitalRead(irSensorPin) == LOW) { 
    // Turn off LED and reset servo
    digitalWrite(ledPin, LOW);
    sortServo.write(0); 

    // Tell the backend the item was placed
    publishConfirmation("bin_1"); 
    delay(2000); // Wait so it doesn't trigger multiple times
  }
}
```

### 3. Testing Phase 2
- Flash this code to your ESP32 Dev Module using VS Code / PlatformIO.
- Open the Serial Monitor. Wait for it to connect to Wi-Fi and HiveMQ.
- Go to your HiveMQ Web Client and manually **Publish** a message to `warehouse/bin/light`.
- **Result:** Your servo should move, and your LED should light up! Wave your hand in front of the IR sensor, and watch the Serial Monitor to ensure it sends a confirmation back.

---

## Phase 3: The "Eye" (ESP32-CAM)
This board hangs above the start of the conveyor belt and takes a picture of the document.

### 1. Wiring
- Wire the ESP32-CAM to an FTDI programmer or use the ESP32-CAM-MB adapter board to plug it into your computer via USB.

### 2. The Code Logic
You need to write a script for the ESP32-CAM. You can use the standard Arduino ESP32-CAM examples as a base, but you must modify the `loop()` to wait for a trigger (like a button press or an ultrasonic sensor detecting a box), take a photo, and send an `HTTP POST` request.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

// Set your WiFi credentials here
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
String serverName = "https://supply-chain-clerk.onrender.com/intake/capture";

void sendImageToCloud() {
  camera_fb_t * fb = esp_camera_fb_get(); // Take the picture
  
  HTTPClient http;
  http.begin(serverName);
  http.addHeader("Content-Type", "image/jpeg");
  
  // Send the image bytes to your Render Backend
  int httpResponseCode = http.POST(fb->buf, fb->len);
  
  esp_camera_fb_return(fb); // Clear memory
  http.end();
}
```

### 3. Testing Phase 3
- Point the camera at a test invoice.
- Trigger the camera to take a photo.
- Look at your React Dashboard (`https://supply-chain-clerk-998.web.app`). Within a few seconds, the UI should magically update with the extracted JSON data!

---

## Phase 4: Physical Integration (The Conveyor Belt)
Now you put it all together mechanically.

1. **The Starting Gate:** Mount the ESP32-CAM aiming downward at a flat spot at the start of your conveyor belt. Place a bright LED or ring light around it to ensure the invoices are brightly lit (AI hates dark shadows).
2. **The Sorting Gate:** Mount your Servo Motor at a junction on the conveyor belt. Attach a piece of plastic or cardboard to the servo arm to act as a "flipper" or "diverter arm".
3. **The Destination:** At the end of the routed path, place a small plastic box (the Storage Bin). Mount the IR Sensor so it points across the opening of the box, and tape the WS2812B LED to the front of the box.

## Phase 5: The End-to-End Demo Run

> [!IMPORTANT]
> **The Final Test Walkthrough**

1. Turn on the Conveyor Belt motor so it is moving.
2. Place a small box with a printed packing slip on top of it under the ESP32-CAM.
3. Trigger the ESP32-CAM (press the button).
4. Watch the Dashboard. It will extract the data and the Render backend will assign it to Bin 1.
5. The ESP32 Dev Module receives the command via MQTT. The servo motor swings the diverter arm across the conveyor belt. The LED on Bin 1 lights up.
6. The physical box hits the diverter arm and is pushed into Bin 1.
7. As it falls into Bin 1, it trips the IR Sensor.
8. The ESP32 publishes a confirmation. The LED turns off.
9. On your screen, the React dashboard turns green and says "Item Confirmed".

**You are done.** You have built a fully autonomous, AI-driven, physical supply chain intake pipeline.
