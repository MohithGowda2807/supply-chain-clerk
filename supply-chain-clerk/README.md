# Supply Chain Clerk 📦

> Agentic AI-powered warehouse intake system — VLM document parsing + Neo4j graph inventory + ESP32 IoT bin guidance

---

## Architecture

```
[Camera / Upload] → [Gemini 1.5 Flash VLM] → [FastAPI Backend]
                                                    │
                                          ┌─────────┼─────────┐
                                       [Neo4j]   [MQTT]   [WebSocket]
                                      (Graph)   (ESP32)  (Dashboard)
```

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop

### 2. Start Infrastructure
```bash
cd supply-chain-clerk
docker compose up -d
# Neo4j opens at http://localhost:7474  (user: neo4j / smartguard123)
```

### 3. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:5173
```

### 5. Verify
```
GET  http://localhost:8000/health      → {"status": "ok"}
GET  http://localhost:8000/status      → service health
POST http://localhost:8000/intake/capture  (multipart: file=<image>)
WS   ws://localhost:8000/ws            → event stream
```

---

## Neo4j Seed Queries

Open http://localhost:7474 and paste these:

```cypher
// All batches from a supplier in last 30 days
MATCH (s:Supplier {name:'Himalaya Herbs'})-[:SUPPLIED]->(b:Batch)
WHERE b.intake_timestamp > datetime() - duration('P30D')
RETURN b;

// Products expiring within 30 days
MATCH (b:Batch)-[:STORED_IN]->(bin:StorageBin)
WHERE b.expiry_date < date() + duration('P30D')
RETURN b, bin;

// Full history of bin A01
MATCH (b:Batch)-[:STORED_IN]->(bin:StorageBin {bin_code:'A01'})
RETURN b ORDER BY b.intake_timestamp DESC;

// Quarantine impact — all bins for a supplier
MATCH (s:Supplier {name:'Himalaya Herbs'})-[:SUPPLIED]->(b:Batch)-[:STORED_IN]->(bin:StorageBin)
RETURN DISTINCT bin.bin_code, b.batch_no, b.expiry_date;
```

---

## Environment Variables

Copy `.env.example` → `.env` and fill in:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key |
| `OPENAI_API_KEY` | OpenAI key (optional benchmark) |
| `NEO4J_URI` | `bolt://localhost:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j credentials |
| `MQTT_BROKER` / `MQTT_PORT` | Mosquitto address |
| `SERIAL_PORT` | USB port for ESP32 fallback (e.g. `COM3`) |

---

## ESP32 Firmware

Open `firmware/main.ino` in Arduino IDE.

**Required libraries** (install via Library Manager):
- `PubSubClient` by Nick O'Leary
- `FastLED` by Daniel Garcia
- `ArduinoJson` by Benoît Blanchon

Update WiFi SSID/password and `MQTT_SERVER` IP before flashing.

---

## E2E Test

```bash
cd supply-chain-clerk
pytest tests/e2e/test_full_flow.py -v
# Requires: backend running, docker up, fixture image in tests/fixtures/documents/
```

---

## MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `warehouse/bin/light` | Backend → ESP32 | `{"bin_id":"A01","colour":"green","led_index":0}` |
| `warehouse/bin/confirm` | ESP32 → Backend | `{"bin_id":"A01","ts":1234567890}` |
| `warehouse/bin/status` | ESP32 → Backend | `{"device":"esp32-warehouse-01","ts":...}` |

---

## LED States

| State | Colour | Pattern |
|---|---|---|
| `awaiting` | 🟢 Green | Solid |
| `confirmed` | 🔵 Cyan | 2s flash → off |
| `expiry` | 🟡 Amber | 1 Hz pulse |
| `quarantine` | 🔴 Red | 4 Hz blink |
| `off` | ⚫ Black | Off |
