#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ── WiFi Config ───────────────────────────────────────────────────────────────
const char* ssid = "can't you afford?";
const char* password = "Abcdefgh";

// ── Backend Config ────────────────────────────────────────────────────────────
String serverName = "https://supply-chain-clerk.onrender.com/intake/capture";

// ── Hardware Pins ────────────────────────────────────────────────────────────
// Push button to trigger photo capture. Connect one side to GPIO 13, other to GND.
const int TRIGGER_PIN = 13; 

// Select camera model (AI Thinker is the most common ESP32-CAM module)
#define CAMERA_MODEL_AI_THINKER

#if defined(CAMERA_MODEL_AI_THINKER)
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27
  
  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22
#endif

void setup() {
  Serial.begin(115200);
  Serial.println();

  // Setup Trigger Pin
  pinMode(TRIGGER_PIN, INPUT_PULLUP);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");

  // Configure Camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG; 
  
  // High resolution for OCR
  config.frame_size = FRAMESIZE_UXGA; 
  config.jpeg_quality = 10;
  config.fb_count = 1;

  // Initialize Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  Serial.println("Camera Ready! Press the trigger button (GPIO 13 to GND) to take a photo.");
}

void sendPhotoToCloud() {
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }
  
  Serial.println("Photo captured! Uploading to Render Backend...");

  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    
    // We are connecting to https, so we need to set insecure to bypass cert validation
    // Warning: Only for prototyping. In prod, provide a root CA cert.
    http.begin(serverName);
    
    // Set headers for multipart form data
    String boundary = "----ESP32Boundary";
    String contentType = "multipart/form-data; boundary=" + boundary;
    http.addHeader("Content-Type", contentType);

    // Build the body
    String bodyStart = "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"file\"; filename=\"document.jpg\"\r\n";
    bodyStart += "Content-Type: image/jpeg\r\n\r\n";
    
    String bodyEnd = "\r\n--" + boundary + "--\r\n";

    uint32_t imageLen = fb->len;
    uint32_t totalLen = bodyStart.length() + imageLen + bodyEnd.length();
    
    // Send POST
    http.addHeader("Content-Length", String(totalLen));
    
    int httpResponseCode = http.POST((uint8_t *)bodyStart.c_str(), bodyStart.length());
    
    // Note: The HTTPClient POST() function only takes a single buffer.
    // To send multipart data efficiently without loading the whole image + strings into a single huge RAM buffer,
    // we need to write directly to the stream.
    // However, for simplicity and since ESP32 has enough RAM for 1 UXGA jpeg, we can do it via streaming:
    
    WiFiClient * stream = http.getStreamPtr();
    if(httpResponseCode == 0) {
      // Actually POST starts the request but to send custom raw bytes sequentially:
    }
  }

  // To do a proper Multipart POST with raw bytes sequentially:
  sendMultipartForm(fb->buf, fb->len);
  
  esp_camera_fb_return(fb); 
}

void sendMultipartForm(uint8_t* imageBuf, size_t imageLen) {
  HTTPClient http;
  http.begin(serverName);
  
  String boundary = "----ESP32Boundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  
  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";
  
  String tail = "\r\n--" + boundary + "--\r\n";
  
  uint32_t totalLen = head.length() + imageLen + tail.length();
  
  // We have to stream it
  WiFiClient *client = http.getStreamPtr();
  http.addHeader("Content-Length", String(totalLen));
  
  int res = http.POST(NULL, 0); // Open connection
  
  if(res == 200 || res == 0) {
    client->print(head);
    
    // Send image data in chunks
    size_t chunkSize = 1024;
    for (size_t i = 0; i < imageLen; i += chunkSize) {
      size_t toSend = (imageLen - i) < chunkSize ? (imageLen - i) : chunkSize;
      client->write(imageBuf + i, toSend);
    }
    
    client->print(tail);
    
    int statusCode = http.GET(); // Read response code
    Serial.print("HTTP Response code: ");
    Serial.println(statusCode);
    
    if (statusCode > 0) {
      String payload = http.getString();
      Serial.println(payload);
    }
  } else {
    Serial.print("Error opening connection: ");
    Serial.println(res);
  }
  
  http.end();
}

void loop() {
  // If the trigger button is pressed (LOW due to INPUT_PULLUP)
  if (digitalRead(TRIGGER_PIN) == LOW) {
    Serial.println("Trigger activated!");
    sendPhotoToCloud();
    
    // Wait so we don't take 100 photos if the button is held
    delay(5000); 
  }
  
  delay(100);
}
