# Smart Supply Chain Dashboard — Phase 1

A real-time shipment tracking dashboard with FastAPI backend and React frontend.

---

## Project Structure

```
smart-supply-chain/
├── backend/
│   ├── main.py              ← FastAPI app + CORS
│   ├── requirements.txt
│   ├── routes/
│   │   └── shipments.py     ← GET /shipments, GET /shipments/{id}
│   └── models/
│       ├── shipment.py      ← Pydantic model
│       └── mock_data.py     ← 8 mock shipments (Indian cities)
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── services/
        │   └── api.js           ← Axios API calls
        ├── pages/
        │   └── Dashboard.jsx    ← Main layout + data fetching
        └── components/
            ├── MapView.jsx      ← Leaflet map with markers + route lines
            ├── ShipmentTable.jsx ← Filterable shipment table
            ├── StatusBadge.jsx  ← Colored status pill
            ├── RiskBar.jsx      ← Risk score progress bar
            └── StatsBar.jsx     ← Summary stat cards
```

---

## Setup & Run

### 1. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

### 2. Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:5173

---

## API Endpoints

| Method | Endpoint                   | Description           |
|--------|----------------------------|-----------------------|
| GET    | /shipments/                | All shipments         |
| GET    | /shipments/{id}            | Single shipment       |
| GET    | /shipments/status/{status} | Filter by status      |
| GET    | /shipments/stats/summary   | Aggregate stats       |
| GET    | /health                    | Health check          |

---

## Features (Phase 1)

- Live map with color-coded markers (blue/red/green by status)
- Dashed route lines from origin → destination
- Click any marker or table row to select & highlight shipment
- Map auto-pans to selected shipment
- Filter table by status (All / In Transit / Delayed / Delivered)
- Risk score bar (green/amber/red)
- Auto-refresh every 8 seconds to simulate real-time
- Stats bar: total, in transit, delayed, delivered counts
- Dark theme throughout

---

## What's Next (Phase 2 ideas)

- Real weather API integration (OpenWeatherMap)
- Disruption prediction model
- Dynamic rerouting engine
- WebSocket for true real-time updates
- Alert notification center
