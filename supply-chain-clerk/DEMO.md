# DEMO.md — 3-Minute Demo Script
# Supply Chain Clerk · Agentic AI Warehouse Intake System

---

## Setup Checklist (before demo)
- [ ] `docker compose up -d` — Neo4j + Mosquitto running
- [ ] Backend: `uvicorn app.main:app --reload` → green at localhost:8000/health
- [ ] Frontend: `npm run dev` → dashboard open at localhost:5173
- [ ] MQTT Explorer connected to localhost:1883
- [ ] Crumpled handwritten invoice ready to photograph

---

## 0:00 — Problem Introduction
> "Every day, warehouses like this one process hundreds of intake documents —
> printed invoices, handwritten packing slips, crumpled delivery notes.
> Right now, a worker reads each one and types the data manually.
> That's 6+ person-hours of zero-value work, with a 2% error rate that
> compounds into audit risk and expiry mismanagement."

**Action:** Hold up the crumpled handwritten invoice to the camera.

---

## 0:30 — Document Capture
> "Watch what happens when we capture this document."

**Action:**
1. Click the **Document Capture** panel on the dashboard
2. Drop the invoice image into the upload zone
3. Press **⚡ Capture & Process**

> "The image goes to Gemini 1.5 Flash — a multimodal Vision-Language Model.
> In under 2 seconds, it extracts batch number, expiry date, quantity,
> supplier name — with a per-field confidence score.
> This one shows 91% overall confidence."

**Point to:** the confidence pills next to each extracted field.

---

## 1:00 — LED Bin Guidance
> "Simultaneously, the system ran the FEFO bin assignment algorithm
> against our Neo4j graph database and published an MQTT command
> to the ESP32 on the warehouse floor."

**Action:** Watch the bin card on the dashboard turn green (AWAITING state).

> "Bin A02 is now lit green on the physical shelf.
> No thinking required — the worker places the product in the illuminated bin."

**Action:** Press the confirmation button on the physical bin (or simulate in MQTT Explorer:
publish `{"bin_id":"A02","ts":1234567890}` to `warehouse/bin/confirm`).

> "The bin confirms placement. The digital twin updates instantly."

**Point to:** the bin card flashing cyan → off.

---

## 1:30 — Digital Twin Update
> "The dashboard reflects the real world. Bin A02 is now occupied.
> The intake event appears in the Live Feed with timestamp,
> confidence score, and batch number."

**Point to:** the live feed entry with green confidence badge.

---

## 2:00 — Supplier Graph
> "Let's look at what the graph database captured."

**Action:** Open Neo4j browser at localhost:7474. Run:
```cypher
MATCH (s:Supplier)-[:SUPPLIED]->(b:Batch)-[:IS_A]->(p:Product)-[:STORED_IN]->(bin:StorageBin)
RETURN s, b, p, bin LIMIT 25
```

> "Every relationship is captured: which supplier sent which batch,
> which product it is, which bin it's in.
> This is the graph that makes instant recall queries possible."

---

## 2:30 — Expiry Alert
> "Now watch what happens when we query for near-expiry stock."

**Action:** Run in Neo4j browser:
```cypher
MATCH (b:Batch)-[:STORED_IN]->(bin:StorageBin)
WHERE b.expiry_date < date() + duration('P30D')
RETURN b.batch_no, b.product_name, b.expiry_date, bin.bin_code
ORDER BY b.expiry_date ASC
```

> "Instant. No manual audit needed. In a real deployment,
> this query runs on a schedule and the backend publishes MQTT alerts —
> the physical bin starts pulsing amber at 1Hz."

---

## 3:00 — Summary
> "From crumpled invoice to confirmed bin placement in under 3 seconds.
> Zero templates. Zero pre-registration. Full audit trail.
> Look at the status bar — 94ms average end-to-end latency."

**Point to:** the latency badge in the top status bar.

> "This is the Supply Chain Clerk."

---

## Fallback Plans
| Risk | Mitigation |
|---|---|
| WiFi drops | USB serial fallback activates in < 3s automatically |
| Gemini rate limit | System returns graceful error, retries with exponential backoff |
| Neo4j down | Backend returns 503, frontend shows red Neo4j indicator |
| LED strip fails | Dashboard still shows bin state — demo continues digitally |
