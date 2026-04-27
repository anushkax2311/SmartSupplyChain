"""
routes/phase4_api.py
=====================
Phase 4 API endpoints:

POST /simulate                → what-if scenario simulation
POST /cascade/analyze         → cascading impact analysis
POST /ai/explain-impact       → AI explanation of simulation result
POST /ai/ask                  → chat assistant
GET  /cascade/dependency-graph→ full dependency graph
GET  /simulate/events         → list available event types
"""

from __future__ import annotations
import dataclasses
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from cascading.engine import (
    compute_cascade, build_dependency_graph,
    DisruptionEvent, EVENT_PROFILES, WAREHOUSE_HUBS
)
from routing.engine import route_for_shipment
from routing.graph import NODES
from models.mock_data import LIVE_SHIPMENTS
from ai.gemma_service import generate_explanation, generate_chat_response

router = APIRouter(tags=["Phase 4 - Simulation & AI"])


# ─── Input schemas ────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    event: str              # warehouse_shutdown | traffic_spike | weather_event | road_closure | port_congestion
    location: str           # city name
    duration: int           # hours
    severity: float = 1.0   # 0.5 mild | 1.0 normal | 1.5 severe

class CascadeRequest(BaseModel):
    event: str
    location: str
    duration: int
    severity: float = 1.0

class ExplainImpactRequest(BaseModel):
    simulation_result: dict

class AskRequest(BaseModel):
    question: str
    context: Optional[dict] = None   # optional extra context from frontend


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _cascade_to_dict(result) -> dict:
    d = dataclasses.asdict(result)
    # Flatten nested event dataclass
    d["event"] = dataclasses.asdict(result.event)
    d["affected_shipments"] = [dataclasses.asdict(a) for a in result.affected_shipments]
    return d


def _build_context_from_cascade(cascade_dict: dict, event_type: str, location: str, duration: int) -> dict:
    cargo_types = list({a["cargo"] for a in cascade_dict.get("affected_shipments", [])})
    return {
        "event":                   event_type,
        "location":                location,
        "duration_hours":          duration,
        "affected_shipments":      cascade_dict.get("total_affected_count", 0),
        "delay_hours":             cascade_dict.get("avg_delay_hours", 0),
        "sla_risk":                cascade_dict.get("sla_risk", "UNKNOWN"),
        "affected_warehouses":     cascade_dict.get("affected_warehouses", []),
        "total_cost_impact_inr":   cascade_dict.get("total_cost_impact_inr", 0),
        "cargo_types":             cargo_types,
        "dependency_chain":        cascade_dict.get("dependency_chain", []),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/simulate/events")
def list_events():
    """Return available disruption event types for the UI dropdown."""
    return {
        "events": [
            {"value": "warehouse_shutdown", "label": "🏭 Warehouse Shutdown",  "icon": "🏭"},
            {"value": "traffic_spike",      "label": "🚗 Traffic Spike",        "icon": "🚗"},
            {"value": "weather_event",      "label": "🌧️ Weather Event",        "icon": "🌧️"},
            {"value": "road_closure",       "label": "🚧 Road Closure",          "icon": "🚧"},
            {"value": "port_congestion",    "label": "⚓ Port Congestion",       "icon": "⚓"},
        ],
        "locations": sorted(list(set(
            [n.city for n in NODES.values()] +
            [s["origin"]["city"] for s in LIVE_SHIPMENTS] +
            [s["destination"]["city"] for s in LIVE_SHIPMENTS]
        ))),
        "severity_options": [
            {"value": 0.5,  "label": "Mild"},
            {"value": 1.0,  "label": "Moderate"},
            {"value": 1.5,  "label": "Severe"},
        ]
    }


@router.post("/simulate")
def simulate_disruption(req: SimulateRequest):
    """
    Run a what-if simulation for a disruption event.
    Returns cascade impact + rerouting suggestions + AI explanation.
    """
    if req.event not in EVENT_PROFILES:
        raise HTTPException(400, f"Unknown event type: {req.event}. Valid: {list(EVENT_PROFILES.keys())}")

    # 1. Compute cascade
    event = DisruptionEvent(
        event_type     = req.event,
        location       = req.location,
        duration_hours = req.duration,
        severity       = req.severity,
    )
    cascade = compute_cascade(event)
    cascade_dict = _cascade_to_dict(cascade)

    # 2. Compute new routes for affected shipments
    new_routes = []
    eta_changes = []
    affected_ids = {a["shipment_id"] for a in cascade_dict["affected_shipments"]}

    for s in LIVE_SHIPMENTS:
        if s["id"] not in affected_ids or s["status"] == "Delivered":
            continue
        try:
            route_a, route_b = route_for_shipment(s, "balanced")
            new_routes.append({
                "shipment_id":  s["id"],
                "recommended":  route_b.route_id if route_b.avg_risk < route_a.avg_risk else route_a.route_id,
                "route_summary": route_b.summary if route_b.avg_risk < route_a.avg_risk else route_a.summary,
            })
        except Exception:
            pass

        # ETA change
        affected_entry = next((a for a in cascade_dict["affected_shipments"] if a["shipment_id"] == s["id"]), None)
        if affected_entry:
            eta_changes.append({
                "shipment_id":  s["id"],
                "cargo":        s["cargo"],
                "original_eta": affected_entry["original_eta"],
                "new_eta":      affected_entry["new_eta"],
                "delay_hours":  affected_entry["delay_hours"],
                "sla_breach":   affected_entry["sla_breach"],
            })

    # 3. AI explanation
    context = _build_context_from_cascade(cascade_dict, req.event, req.location, req.duration)
    explanation = generate_explanation(context)

    return {
        "simulation_id":  f"SIM-{datetime.utcnow().strftime('%H%M%S')}",
        "event":          req.event,
        "location":       req.location,
        "duration_hours": req.duration,
        "severity":       req.severity,
        "impact":         cascade_dict,
        "new_routes":     new_routes,
        "eta_changes":    eta_changes,
        "explanation":    explanation,
        "timestamp":      datetime.utcnow().isoformat(),
    }


@router.post("/cascade/analyze")
def analyze_cascade(req: CascadeRequest):
    """Analyze cascade impact without full simulation (faster, no routing)."""
    if req.event not in EVENT_PROFILES:
        raise HTTPException(400, f"Unknown event: {req.event}")

    event = DisruptionEvent(req.event, req.location, req.duration, req.severity)
    cascade = compute_cascade(event)
    return _cascade_to_dict(cascade)


@router.get("/cascade/dependency-graph")
def get_dependency_graph():
    """Return the full warehouse dependency graph."""
    graph = build_dependency_graph()
    return {
        "nodes": [
            {
                "id":       nid,
                "city":     n.city,
                "lat":      n.lat,
                "lng":      n.lng,
                "is_warehouse": n.city in WAREHOUSE_HUBS,
                "criticality":  WAREHOUSE_HUBS.get(n.city, {}).get("criticality", "LOW"),
            }
            for nid, n in NODES.items()
        ],
        "edges": [
            {"from": src, "to": dst}
            for src, dsts in graph.items()
            for dst in dsts
        ],
        "warehouses": WAREHOUSE_HUBS,
    }


@router.post("/ai/explain-impact")
def explain_impact(req: ExplainImpactRequest):
    """Generate AI explanation for an existing simulation result."""
    sim = req.simulation_result
    impact = sim.get("impact", {})
    cargo_types = list({a["cargo"] for a in impact.get("affected_shipments", [])})

    context = {
        "event":                   sim.get("event", "disruption"),
        "location":                sim.get("location", "unknown"),
        "duration_hours":          sim.get("duration_hours", 0),
        "affected_shipments":      impact.get("total_affected_count", 0),
        "delay_hours":             impact.get("avg_delay_hours", 0),
        "sla_risk":                impact.get("sla_risk", "UNKNOWN"),
        "affected_warehouses":     impact.get("affected_warehouses", []),
        "total_cost_impact_inr":   impact.get("total_cost_impact_inr", 0),
        "cargo_types":             cargo_types,
    }
    return {"explanation": generate_explanation(context)}


@router.post("/ai/ask")
def ask_assistant(req: AskRequest):
    """
    Chat assistant — answers free-form supply chain questions.
    Automatically runs a simulation if the question implies a what-if scenario.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty")

    # Parse intent — does the question imply a simulation?
    q_lower = question.lower()
    sim_result = None

    # Intent: warehouse shutdown
    if any(kw in q_lower for kw in ["shutdown", "shut down", "closes", "closed", "offline"]):
        # Extract city
        city = _extract_city(q_lower) or "Delhi"
        event = DisruptionEvent("warehouse_shutdown", city, 48, 1.0)
        cascade = compute_cascade(event)
        cascade_dict = _cascade_to_dict(cascade)
        sim_result = _build_context_from_cascade(cascade_dict, "warehouse_shutdown", city, 48)

    elif any(kw in q_lower for kw in ["flood", "rain", "storm", "weather", "cyclone"]):
        city = _extract_city(q_lower) or "Mumbai"
        event = DisruptionEvent("weather_event", city, 24, 1.2)
        cascade = compute_cascade(event)
        cascade_dict = _cascade_to_dict(cascade)
        sim_result = _build_context_from_cascade(cascade_dict, "weather_event", city, 24)

    elif any(kw in q_lower for kw in ["traffic", "congestion", "jam", "blocked"]):
        city = _extract_city(q_lower) or "Delhi"
        event = DisruptionEvent("traffic_spike", city, 6, 1.0)
        cascade = compute_cascade(event)
        cascade_dict = _cascade_to_dict(cascade)
        sim_result = _build_context_from_cascade(cascade_dict, "traffic_spike", city, 6)

    # Build context from live shipment data if no sim was needed
    if not sim_result:
        active = [s for s in LIVE_SHIPMENTS if s["status"] != "Delivered"]
        delayed = [s for s in LIVE_SHIPMENTS if s["status"] == "Delayed"]
        sim_result = {
            "event":                 "general_query",
            "location":              "network-wide",
            "duration_hours":        0,
            "affected_shipments":    len(delayed),
            "delay_hours":           round(sum(s["speed_kmh"] for s in delayed) / max(len(delayed), 1), 1),
            "sla_risk":              "HIGH" if len(delayed) >= 3 else "MEDIUM",
            "affected_warehouses":   [],
            "total_cost_impact_inr": len(delayed) * 45000,
            "cargo_types":           list({s["cargo"] for s in delayed}),
        }

    answer = generate_chat_response(question, sim_result)

    return {
        "question":    question,
        "answer":      answer,
        "context_used": sim_result,
        "timestamp":   datetime.utcnow().isoformat(),
    }


def _extract_city(text: str) -> Optional[str]:
    """Simple city name extraction from question text."""
    cities = [n.city for n in NODES.values()]
    for city in cities:
        if city.lower() in text:
            return city
    return None
