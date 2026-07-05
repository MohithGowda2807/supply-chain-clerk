# 🚀 VISTA Supply Chain — Team Setup Guide

This guide explains exactly how to run the VISTA Supply Chain project on a new laptop from scratch. 

Since the project runs entirely locally on your Wi-Fi network for maximum speed and privacy, you **must update the IP addresses** in the code to match the new laptop's IP address.

---

## 🛑 Step 1: Find Your Laptop's Local IP
Because your laptop will be acting as the central server (running the AI, Database, and MQTT Broker), the ESP32 boards need to know exactly where to find it on your Wi-Fi.

1. Connect your laptop to your Wi-Fi (the ESP32s will connect to this same Wi-Fi).
2. Open **Command Prompt** or **PowerShell**.
3. Type `ipconfig` and press Enter.
4. Look for the `IPv4 Address` under your active Wi-Fi adapter. It usually looks something like `192.168.1.X` or `10.X.X.X`. 
   *(Write this IP down, you will use it everywhere below!)*

---

## 🛠️ Step 2: Update the Hardware Code (ESP32 & ESP32-CAM)
When you clone the repo, the code is hardcoded to Mohit's IP (`10.117.196.80`). You must change this to your IP.

1. Open `firmware/firmware.ino` in your Arduino IDE.
2. Change the `SSID` and `WIFI_PASS` to your local Wi-Fi credentials.
3. Change `MQTT_SERVER` to your laptop's IPv4 address from Step 1.
4. **Upload** this code to your ESP32 Main Board.

5. Now, open `esp32_cam_firmware/esp32_cam_firmware.ino` in your Arduino IDE.
6. Change the `ssid` and `password` to your Wi-Fi credentials.
7. Find `serverName` and change the IP address to your laptop's IP. Leave the `:8000/intake/capture` part intact. 
   *(Example: `http://192.168.1.5:8000/intake/capture`)*
8. **Upload** this code to your ESP32-CAM.

---

## 🐳 Step 3: Start the Backend (Docker)
Your laptop will run Mosquitto (MQTT), Neo4j (Database), and the FastAPI backend all inside Docker containers.

1. Install and open **Docker Desktop**.
2. Open PowerShell, navigate to the `supply-chain-clerk` root folder.
3. Run the following command:
   ```bash
   docker-compose up -d
   ```
4. This will download and start all necessary services in the background.

---

## 🌐 Step 4: Start the Frontend Dashboard
The frontend `.env` file is hidden and ignored by GitHub for security, so you must create it yourself!

1. In the `supply-chain-clerk/frontend` folder, create a new file named `.env`
2. Add exactly this one line to the file, replacing the IP with your laptop's IP from Step 1:
   ```text
   VITE_API_BASE_URL=http://YOUR_LAPTOP_IP:8000
   ```
3. Open PowerShell inside the `frontend` folder and run:
   ```bash
   npm install
   npm run dev -- --host
   ```
4. Leave this terminal open. 

---

## 🎉 Step 5: You're Done!
Open your browser and go to `http://localhost:5173`. 
Power up your ESP32 hardware. Everything will now instantly connect to your laptop's IP, process AI data locally, and show up on your dashboard!
