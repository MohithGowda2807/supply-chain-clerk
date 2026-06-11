#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WebServer.h>
// ── WiFi Config ───────────────────────────────────────────────────────────────
const char* ssid = "can't you afford?";
const char* password = "Abcdefgh";
// ── Backend Config ────────────────────────────────────────────────────────────
String serverName = "https://unknownjunkspam-supply-chain-backend.hf.space/intake/capture";
// ── Camera Model ──────────────────────────────────────────────────────────────
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
WebServer server(80);
// ── Live Stream Handler ───────────────────────────────────────────────────────
void handleStream() {
  WiFiClient client = server.client();
  String response = "HTTP/1.1 200 OK\r\n";
  response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  client.print(response);
  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) continue;
    client.printf("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    client.write(fb->buf, fb->len);
    client.print("\r\n");
    esp_camera_fb_return(fb);
    if (!client.connected()) break;
    delay(30); // ~30 FPS
  }
}
// ── Single Photo Handler (for testing in browser) ─────────────────────────────
void handleCapture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}
// ── Capture + Upload to Backend ───────────────────────────────────────────────
void handleUpload() {
  Serial.println("Upload triggered from browser!");
  // Warm-up frame
  camera_fb_t *fb = esp_camera_fb_get();
  if (fb) esp_camera_fb_return(fb);
  delay(300);
  fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  Serial.print("Photo size: ");
  Serial.print(fb->len);
  Serial.println(" bytes");
  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(30);
  HTTPClient http;
  http.setTimeout(60000);
  http.begin(client, serverName);
  String boundary = "----ESP32Boundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";
  uint32_t totalLen = head.length() + fb->len + tail.length();
  uint8_t *payload = (uint8_t*)ps_malloc(totalLen);
  if (!payload) {
    esp_camera_fb_return(fb);
    server.send(500, "text/plain", "Memory allocation failed");
    return;
  }
  memcpy(payload, head.c_str(), head.length());
  memcpy(payload + head.length(), fb->buf, fb->len);
  memcpy(payload + head.length() + fb->len, tail.c_str(), tail.length());
  esp_camera_fb_return(fb);
  String result = "";
  bool success = false;
  for (int attempt = 1; attempt <= 3; attempt++) {
    Serial.print("Upload attempt ");
    Serial.println(attempt);
    int res = http.POST(payload, totalLen);
    if (res > 0) {
      result = http.getString();
      Serial.println("SUCCESS!");
      Serial.println(result);
      success = true;
      break;
    } else {
      Serial.print("Failed: ");
      Serial.println(http.errorToString(res));
      delay(2000);
    }
  }
  free(payload);
  http.end();
  if (success) {
    server.send(200, "application/json", result);
  } else {
    server.send(500, "text/plain", "Upload failed after 3 retries");
  }
}
// ── Dashboard Page ────────────────────────────────────────────────────────────
void handleRoot() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32-CAM Live View</title>
  <style>
    body { font-family: Arial; background: #111; color: #fff; text-align: center; margin: 0; padding: 20px; }
    h1 { color: #0af; }
    img { max-width: 100%; border: 3px solid #0af; border-radius: 10px; margin: 10px 0; }
    .btn { padding: 15px 40px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; margin: 10px; }
    .capture { background: #0a0; color: white; }
    .capture:hover { background: #0c0; }
    .capture:disabled { background: #555; cursor: wait; }
    #result { background: #222; padding: 15px; border-radius: 8px; text-align: left; margin-top: 15px; white-space: pre-wrap; word-break: break-all; display: none; }
    .success { border-left: 4px solid #0a0; }
    .error { border-left: 4px solid #f00; }
    #status { font-size: 14px; color: #aaa; margin: 5px; }
  </style>
</head>
<body>
  <h1>ESP32-CAM Live Preview</h1>
  <p>Adjust the camera position until the text is clear and readable below:</p>
  <img id="stream" src="/stream" />
  <br>
  <button class="btn capture" id="uploadBtn" onclick="doUpload()">Capture & Send to AI</button>
  <p id="status"></p>
  <div id="result"></div>
  <script>
    function doUpload() {
      var btn = document.getElementById('uploadBtn');
      var status = document.getElementById('status');
      var result = document.getElementById('result');
      btn.disabled = true;
      btn.innerText = 'Processing...';
      status.innerText = 'Capturing photo and uploading to Hugging Face AI...';
      result.style.display = 'none';
      // Stop the stream temporarily to free up camera
      document.getElementById('stream').src = '';
      fetch('/upload')
        .then(r => r.text())
        .then(data => {
          result.style.display = 'block';
          result.className = 'success';
          try {
            var json = JSON.parse(data);
            result.innerText = 'Assigned Bin: ' + json.assigned_bin + '\n'
              + 'Product: ' + json.record.product_name.value + '\n'
              + 'Batch: ' + (json.record.batch_no.value || 'N/A') + '\n'
              + 'Expiry: ' + (json.record.expiry_date.value || 'N/A') + '\n'
              + 'Quantity: ' + (json.record.quantity.value || 'N/A') + '\n'
              + 'Confidence: ' + (json.overall_confidence * 100).toFixed(1) + '%\n'
              + 'Latency: ' + json.latency_ms + 'ms';
            status.innerText = 'Done! Check your Firebase website too.';
          } catch(e) {
            result.innerText = data;
            status.innerText = 'Response received (see below).';
          }
        })
        .catch(err => {
          result.style.display = 'block';
          result.className = 'error';
          result.innerText = 'Error: ' + err;
          status.innerText = 'Upload failed. Try again.';
        })
        .finally(() => {
          btn.disabled = false;
          btn.innerText = 'Capture & Send to AI';
          // Restart the stream
          document.getElementById('stream').src = '/stream?' + Date.now();
        });
    }
  </script>
</body>
</html>
)rawliteral";
  server.send(200, "text/html", html);
}
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=========================================");
  Serial.println("  ESP32-CAM LIVE PREVIEW + UPLOAD TEST");
  Serial.println("=========================================");
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi connected! IP: ");
  Serial.println(WiFi.localIP());
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
  config.frame_size = FRAMESIZE_SVGA;
  config.jpeg_quality = 12;
  config.fb_count = 2; // 2 framebuffers for smooth streaming
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("CAMERA INIT FAILED with error 0x%x\n", err);
    return;
  }
  Serial.println("Camera initialized!");
  // Setup web server routes
  server.on("/", handleRoot);
  server.on("/stream", handleStream);
  server.on("/capture", handleCapture);
  server.on("/upload", handleUpload);
  server.begin();
  Serial.println();
  Serial.println("=========================================");
  Serial.print("  Open this URL in your browser: http://");
  Serial.println(WiFi.localIP());
  Serial.println("=========================================");
  Serial.println("You will see a LIVE camera feed!");
  Serial.println("Adjust the camera, then click 'Capture & Send to AI'.");
}
void loop() {
  server.handleClient();
  delay(1);
}
