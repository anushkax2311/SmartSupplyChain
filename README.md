# ChainGuard AI — Smart Supply Chain Dashboard

> **An AI-powered, self-healing supply chain control tower built for the Google Solution Challenge 2026.**
> Transforms reactive logistics into a predictive, intelligent, and autonomous system.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev)
[![Gemma](https://img.shields.io/badge/Gemma-3%2012B-orange?logo=google)](https://ai.google.dev)
[![Tests](https://img.shields.io/badge/Tests-174%20passing-brightgreen)](./backend/tests)

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Live Demo](#live-demo)
- [Features by Phase](#features-by-phase)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [API Reference](#api-reference)
- [Running Locally](#running-locally)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [How Gemma AI Is Used](#how-gemma-ai-is-used)
- [Team](#team)

---

## Problem Statement

Global supply chains lose **$1.5 trillion annually** to disruptions. 73% of logistics managers say their systems are **purely reactive** — they find out about delays only after they have already cascaded into missed SLAs. Indian freight loses **₹4.8 lakh crore per year** to inefficiency. Existing enterprise tools cost ₹40 lakh+/year and still cannot predict or self-heal.

**ChainGuard AI solves this** with a closed-loop system that predicts disruptions before they happen, routes around them automatically, and explains every decision in plain English.

---

## Solution

ChainGuard AI is a **5-phase intelligent supply chain control tower** that:

- Tracks live shipments across Indian NH highway corridors in real time via WebSocket
- Predicts delay probability, risk level, and updated ETA every 4 seconds
- Routes shipments using Dijkstra on a real 18-node Indian highway graph
- Simulates what-if disruptions and propagates cascading impact across warehouse hubs
- Auto-reroutes in 4 seconds when disruption thresholds are crossed
- Explains every decision in plain English using Gemma 3 (12B)
- Shows live alerts, carrier analytics, cost savings KPIs, and a 12-hour delay trend

---

## Live Demo

| Resource | Link |
|----------|------|
| GitHub | https://github.com/anushkax2311/SmartSupplyChain |
| Live Prototype | https://smartsupplychain.onrender.com |
| Demo Video | https://youtu.be/[link] |
| API Docs | http://localhost:8000/docs *(run locally)* |

---

## Features by Phase

### Phase 1 — Real-Time Dashboard
- FastAPI backend with 8 mock Indian city shipments (Delhi, Mumbai, Bangalore, etc.)
- React + Leaflet live map with color-coded risk markers
- Shipment table with status badges, ETA, speed, risk score
- REST endpoints: `GET /shipments/`, `GET /shipments/{id}`, `GET /shipments/stats/summary`

### Phase 2 — Live Simulation + AI Predictions
- WebSocket tick engine updates every 4 seconds via `/ws/shipments`
- GPS interpolation moves shipments along routes in real time
- AI predictor computes: updated ETA, delay probability (0–1), risk level, current speed
- Realistic speed drift simulation: 70% small tweak, 20% traffic slowdown, 10% recovery
- Auto-reconnecting React WebSocket hook with 25s keep-alive pings

### Phase 3 — Graph-Based Routing Engine
- 18 Indian city hub nodes, 30+ NH highway edges with distance, time, cost, risk weights
- Dijkstra algorithm with live dynamic traffic and weather condition weights
- Multi-objective optimization: `time` / `cost` / `balanced`
- `find_two_routes()` forces genuinely alternate corridor by excluding riskiest highway
- Decision engine with 5 prioritized rules → `REROUTE` or `KEEP` with confidence score
- Explainable AI: full natural-language paragraph for every routing decision

### Phase 4 — Cascading Intelligence + Gemma AI
- 5 disruption event types: warehouse shutdown, traffic spike, weather event, road closure, port congestion
- BFS dependency graph propagates disruption 2 hops downstream across 11 warehouse hubs
- What-if simulator: `POST /simulate` → cascade impact + new routes + Gemma AI explanation in one call
- Gemma AI chat assistant at `POST /ai/ask` with intent detection that auto-triggers simulations
- Rich rule-based NL fallback when API key is not configured

### Phase 5 — Self-Healing Control Tower
- Self-healing engine runs inside every simulation tick with 6 prioritized triggers:
  1. Speed critically low (<20 km/h) for 2+ consecutive ticks → force reroute
  2. Delay probability >70% → auto reroute
  3. Risk level HIGH with delay prob >55% → auto reroute
  4. Speed dropped >40% since last tick → warning alert
  5. Delayed status detected → alert and monitor
  6. ETA drifted >30 min from original → ETA updated alert
- Per-shipment cooldown timers prevent alert spam
- Central alert registry (ring buffer of 100) with CRITICAL / WARNING / INFO levels
- Analytics: on-time rate, cost savings (₹800/min), carrier A–D grading, 12h delay bar chart
- Toast notification system auto-pops live alerts from WebSocket feed
- 10-tab control tower dashboard

---

## System Architecture

```
User Browser (React 18 + Vite)
        │
        ├── WebSocket ws://localhost:8000/ws/shipments
        │       └── Broadcasts every 4s: { shipments, alerts, timestamp }
        │
        └── HTTP REST  http://localhost:8000
                │
        ┌───────────────────────────────────────┐
        │         FastAPI (Python 3.11)          │
        │                                       │
        │  ┌──────────┐  ┌───────────────────┐  │
        │  │Simulation│  │   Routing Engine  │  │
        │  │ Engine   │  │  Dijkstra + Graph │  │
        │  │ asyncio  │  │  NH Highway Map   │  │
        │  └────┬─────┘  └────────┬──────────┘  │
        │       │                 │              │
        │  ┌────▼─────────────────▼──────────┐  │
        │  │         AI Layer                │  │
        │  │  Predictor · Explainer · Gemma  │  │
        │  └────────────────────────────────┘  │
        │       │                               │
        │  ┌────▼───────────────────────────┐   │
        │  │  Self-Healing + Cascade Engine │   │
        │  │  Alerts · Analytics · Healing  │   │
        │  └───────────────────────────────┘   │
        └───────────────────────────────────────┘
                        │
               LIVE_SHIPMENTS (mutable dict store)
```

**Key design decisions:**
- Shipments stored as mutable Python dicts so the simulation engine can update them in-place each tick without Pydantic re-validation overhead
- WebSocket broadcasts the full snapshot every tick — clients always have consistent state
- Dijkstra runs on demand at query time with live condition weights — routes are never stale
- Self-healing engine co-located inside the simulation tick loop for zero-latency response

---

## Project Structure

```
SmartSupplyChain/
├── backend/
│   ├── main.py                      # FastAPI app, startup, CORS, all router registration
│   ├── requirements.txt             # Python dependencies
│   ├── pytest.ini                   # Test configuration
│   ├── .env                         # Your GEMMA_API_KEY goes here (create this file)
│   │
│   ├── models/
│   │   ├── shipment.py              # Pydantic: Shipment, AIPrediction, Location
│   │   └── mock_data.py             # 8 live shipment dicts across Indian cities
│   │
│   ├── simulation/
│   │   └── engine.py                # asyncio tick loop, GPS interpolation, speed drift
│   │
│   ├── ai/
│   │   ├── predictor.py             # ETA calc, delay detection, risk scoring, drift
│   │   ├── explainer.py             # NL explanation templates for routing decisions
│   │   └── gemma_service.py         # Gemma 3 API integration + rule-based fallback
│   │
│   ├── routing/
│   │   ├── graph.py                 # 18 hub nodes, 30+ NH edges, haversine, closest_node()
│   │   ├── conditions.py            # Dynamic traffic/weather weights, refreshes every 15s
│   │   └── engine.py                # Dijkstra, find_route(), find_two_routes(), RouteResult
│   │
│   ├── decision/
│   │   └── engine.py                # 5-rule decision engine → REROUTE / KEEP
│   │
│   ├── cascading/
│   │   └── engine.py                # Dependency graph, BFS propagation, SLA risk calc
│   │
│   ├── healing/
│   │   ├── alerts.py                # Alert registry, push/get/acknowledge, ring buffer
│   │   └── engine.py                # 6-trigger self-healing engine, cooldowns, ETA drift
│   │
│   ├── analytics/
│   │   └── engine.py                # KPIs, carrier grading A-D, delay trend, cost savings
│   │
│   ├── ws/
│   │   ├── manager.py               # ConnectionManager: connect/broadcast/prune dead clients
│   │   └── routes.py                # /ws/shipments WebSocket endpoint + ping/pong
│   │
│   ├── routes/
│   │   ├── shipments.py             # Phase 1-2: shipment REST endpoints
│   │   ├── routing_api.py           # Phase 3: routing, decision, explain-route
│   │   ├── phase4_api.py            # Phase 4: simulate, cascade, ai/ask, ai/explain-impact
│   │   └── phase5_api.py            # Phase 5: alerts, analytics, healing/trigger
│   │
│   └── tests/
│       ├── conftest.py              # Shared pytest fixtures (3 shipment types)
│       ├── test_predictor.py        # 58 tests — AI predictor engine
│       ├── test_simulation.py       # 25 tests — simulation + self-healing
│       ├── test_api.py              # 35 tests — all REST endpoints + CORS
│       ├── test_websocket.py        # 20 tests — ConnectionManager + WS endpoint
│       ├── test_mock_data.py        # 22 tests — data integrity + India bounding box
│       └── test_e2e_flow.py         # 14 tests — full frontend boot flow
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── package.json
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css                # Tailwind directives + Leaflet dark map overrides
        │
        ├── hooks/
        │   └── useShipmentSocket.js # WS lifecycle, auto-reconnect, liveAlerts state
        │
        ├── services/
        │   └── api.js               # Axios: shipmentService, routingService, phase4Service
        │
        ├── pages/
        │   └── Dashboard.jsx        # 10-tab layout, all state, handler functions
        │
        └── components/
            ├── MapView.jsx           # Leaflet map, markers, route A/B polylines
            ├── ShipmentTable.jsx     # Filterable table: status, ETA, speed, risk, progress
            ├── StatsBar.jsx          # 5 KPI cards: total, transit, delayed, delivered, high risk
            ├── StatusBadge.jsx       # In Transit / Delayed / Delivered colored pill
            ├── RiskBadge.jsx         # LOW / MEDIUM / HIGH colored badge
            ├── RiskBar.jsx           # 0-100 risk progress bar
            ├── ProgressBar.jsx       # Route completion 0-100%
            ├── PredictionPanel.jsx   # Full AI prediction detail: ETA, speed, delay%, recommendation
            ├── RouteComparison.jsx   # Route A vs B metrics table + segment condition pills
            ├── DecisionPanel.jsx     # Action banner, rule fired, confidence, detail text
            ├── ExplanationPanel.jsx  # Gemma AI explanation with inline bold rendering
            ├── SimulationPanel.jsx   # Event dropdown, location, duration slider, severity, run
            ├── CascadeImpact.jsx     # SLA risk banner, metrics, cascade chain, ETA diff table
            ├── ChatAssistant.jsx     # Full chat UI: history, suggestions, typing indicator
            ├── AlertsPanel.jsx       # Alert center: filter tabs, dismiss, unread badge
            ├── AnalyticsDashboard.jsx# KPIs, 12h bar chart, carrier grades, cost breakdown
            └── ToastNotifications.jsx# Bottom-right live toasts from WS alerts, auto-dismiss 5s
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend language | Python | 3.11 |
| Web framework | FastAPI | 0.111 |
| Data validation | Pydantic | v2.7 |
| ASGI server | Uvicorn | 0.29 |
| Real-time | WebSockets | 12.0 |
| Frontend framework | React | 18 |
| Build tool | Vite | 5 |
| CSS framework | Tailwind CSS | v3 |
| Map library | React-Leaflet | 4.2 |
| Map tiles | OpenStreetMap | — |
| HTTP client | Axios | 1.7 |
| Icons | lucide-react | 0.383 |
| AI — Google | Gemma 3 12B | via AI Studio API |
| AI — SDK | google-generativeai | latest |
| Routing algorithm | Dijkstra | heapq (stdlib) |
| Geo algorithm | Haversine | custom impl |
| Cascade algorithm | BFS | custom impl |
| Testing | pytest + pytest-asyncio | 8.2 + 0.23 |
| HTTP testing | httpx | 0.27 |
| Deployment target | Google Cloud Run | — |

---

## API Reference

### Core (Phases 1–2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check + version |
| GET | `/health` | `{ status: ok, version: 5.0.0 }` |
| GET | `/shipments/` | All shipments with live predictions |
| GET | `/shipments/{id}` | Single shipment |
| GET | `/shipments/stats/summary` | Counts: total, in_transit, delayed, delivered, high_risk |
| WS | `/ws/shipments` | Live updates every 4s. Payload: `{ type, timestamp, shipments[], alerts[] }` |

### Routing & Decision (Phase 3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/routes/{id}?optimize_for=balanced` | Route A + B for shipment |
| POST | `/routes/optimize` | `{ shipment_id, optimize_for }` → routes + decision |
| POST | `/decision/reroute` | Run decision engine, apply reroute if warranted |
| POST | `/ai/explain-route` | Gemma NL explanation for routing decision |
| GET | `/routes/conditions/live` | Current highway conditions (traffic/weather/incidents) |
| GET | `/routes/nodes/list` | All 18 graph hub nodes |

### Simulation & AI (Phase 4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/simulate/events` | Available event types + locations for UI |
| POST | `/simulate` | `{ event, location, duration, severity }` → full what-if |
| POST | `/cascade/analyze` | Fast cascade-only (no routing) |
| GET | `/cascade/dependency-graph` | Full warehouse dependency graph |
| POST | `/ai/explain-impact` | `{ simulation_result }` → Gemma explanation |
| POST | `/ai/ask` | `{ question }` → chat response with auto-simulation |

### Self-Healing & Analytics (Phase 5)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts?limit=50&level=CRITICAL` | Paginated alert list |
| GET | `/alerts/unacked-count` | Count for badge |
| POST | `/alerts/{id}/acknowledge` | Dismiss one alert |
| POST | `/alerts/acknowledge-all` | Clear all badges |
| GET | `/analytics/kpis` | on_time_rate, reroutes, cost_saved, delay_reduction |
| GET | `/analytics/carrier-performance` | Carrier scorecards A–D |
| GET | `/analytics/delay-trend` | 12-hour rolling hourly buckets |
| GET | `/analytics/cost-savings` | Total + breakdown by category |
| POST | `/healing/trigger/{id}` | Manually trigger self-heal for a shipment |

---

## Running Locally

### Prerequisites

- Python 3.11 *(not 3.12+ — pydantic-core wheel issue)*
- Node.js 18+
- Git

### Step 1 — Clone

```bash
git clone https://github.com/anushkax2311/SmartSupplyChain.git
cd SmartSupplyChain
```

### Step 2 — Backend

```bash
cd backend

# Create venv
python -m venv venv

# Activate — Windows PowerShell
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --port 8000
```

✅ Backend running at `http://localhost:8000`
✅ Swagger docs at `http://localhost:8000/docs`
✅ You'll see `Simulation engine started (Phase 5 — self-healing active)` in the terminal

### Step 3 — Frontend (new terminal)

```bash
cd frontend

npm install
npm run dev
```

✅ Frontend running at `http://localhost:5173`

### Step 4 — Use the dashboard

Open `http://localhost:5173`. The WebSocket connects automatically.
Within 3 seconds you'll see **Live** in green and all 8 shipments appear.

**Quick tour:**
1. Click any shipment row → jumps to **AI Predict** tab with live ETA + risk
2. Click **Routes** tab → hit "Compute Routes" to see Route A vs B on the map
3. Click **Decision** tab → "Run Decision Engine" to trigger reroute logic
4. Click **Simulate** tab → choose an event, pick a city, run What-If simulation
5. Click **AI Chat** tab → ask "What if Delhi warehouse shuts down?"
6. Click **Alerts** tab → see live self-healing notifications
7. Click **Analytics** tab → view carrier grades and cost savings

---

## Running Tests

```bash
cd backend

# Activate venv first
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Run all 174 tests
pytest

# Verbose output
pytest -v

# Specific test file
pytest tests/test_predictor.py -v
pytest tests/test_api.py -v
pytest tests/test_websocket.py -v

# With coverage
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
```

### Test suite summary

| File | Tests | What is tested |
|------|-------|---------------|
| `test_predictor.py` | 58 | haversine_km, interpolate_location, drift_speed, compute_prediction, all cargo types, edge cases |
| `test_api.py` | 35 | Every REST endpoint, CORS headers, response shapes, field types, 404 handling |
| `test_simulation.py` | 25 | _advance_shipment, _city_label quartile labels, simulation_loop async broadcast |
| `test_websocket.py` | 20 | ConnectionManager lifecycle, WS endpoint, initial snapshot, ping/pong, multi-client |
| `test_mock_data.py` | 22 | Data integrity, lat/lng valid ranges, India bounding box, delivered shipment constraints |
| `test_e2e_flow.py` | 14 | Frontend boot flow, REST→WS consistency, progression, ETA trend, status transitions |
| **Total** | **174** | |

---

## Environment Variables

Create `backend/.env`:

```env
# Get your key from https://aistudio.google.com/apikey
GEMMA_API_KEY=AIzaSy_your_key_here
```

The `.env` file is loaded automatically by `python-dotenv` on startup.

**Without a key:** A rich rule-based NL fallback runs automatically. The full system works with no API key — routing, self-healing, cascade simulation, and explanations all function. Only the live Gemma API call is skipped.

**Verify Gemma is active:** Look for this in the backend terminal after startup:
```
INFO:gemma:Gemma AI client initialized
```

**Set temporarily in PowerShell** (without .env file):
```powershell
$env:GEMMA_API_KEY = "AIzaSy_your_key"
uvicorn main:app --reload --port 8000
```

---

## How Gemma AI Is Used

Gemma is used **only for reasoning and explanation** — never for numerical calculations.

All hard logic (ETA, delay probability, Dijkstra, cascade propagation, risk scoring) is computed deterministically by our own engines. Gemma receives a clean structured context and produces a professional natural-language response.

**Where Gemma is called:**

| Endpoint | What it explains |
|----------|-----------------|
| `POST /ai/explain-route` | Why Route A or B was chosen, quantified improvement |
| `POST /ai/explain-impact` | Cascade disruption impact, business implications, recommended actions |
| `POST /ai/ask` | Free-form chat — auto-detects intent (warehouse shutdown? weather? delays?) and runs the right simulation before answering |

**Google model:** `gemma-3-12b-it` via `google-generativeai` SDK and Google AI Studio API

**Example context sent to Gemma:**
```
Event: Warehouse Shutdown
Location: Delhi
Duration: 48 hours
Affected Shipments: 3
Average Delay: 36 hours
SLA Risk: HIGH
Impacted Warehouses: Jaipur, Agra, Lucknow

Provide: impact summary, business implications, recommended actions.
```

---

## Pulling Latest Changes (for collaborators)

```bash
# Already have the repo?
git pull origin main

cd backend
venv\Scripts\activate
pip install -r requirements.txt   # picks up any new packages

cd ../frontend
npm install                        # picks up any new packages

# Run as normal
```

---

## Team

**Team Name:** ChainGuard AI
**Challenge:** Google Solution Challenge 2026

| Name | Role |
|------|------|
| Anushka Patel | Team Lead · Full-Stack Development |

---

## Acknowledgements

- [Google AI Studio](https://aistudio.google.com) — Gemma 3 API
- [FastAPI](https://fastapi.tiangolo.com) — Python async web framework
- [React-Leaflet](https://react-leaflet.js.org) — Interactive map rendering
- [OpenStreetMap](https://openstreetmap.org) — Free map tiles
- [lucide-react](https://lucide.dev) — Icon library
- National Highway Authority of India — NH corridor reference data

---

*Built with ❤️ for Google Solution Challenge 2026*
