"""
cascading/engine.py
====================
Cascading Intelligence Engine for Phase 4.

Models the dependency graph between warehouses, routes, and shipments.
When a disruption event occurs, computes which shipments / warehouses
are affected and by how much.

Key concepts
------------
- Every city node is also a potential warehouse hub
- Shipments that pass THROUGH an affected city are impacted
- Impact severity depends on event type + duration
- SLA risk escalates with delay hours
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from models.mock_data import LIVE_SHIPMENTS
from routing.graph import NODES, ADJACENCY


# ─── Event types ─────────────────────────────────────────────────────────────

EVENT_PROFILES = {
    "warehouse_shutdown": {
        "speed_penalty":    0.0,    # vehicles can't move through hub
        "delay_multiplier": 3.5,
        "radius_km":        50,
        "affects_hub":      True,
    },
    "traffic_spike": {
        "speed_penalty":    0.45,   # 45% speed reduction
        "delay_multiplier": 1.8,
        "radius_km":        80,
        "affects_hub":      False,
    },
    "weather_event": {
        "speed_penalty":    0.55,
        "delay_multiplier": 2.2,
        "radius_km":        150,
        "affects_hub":      False,
    },
    "road_closure": {
        "speed_penalty":    1.0,
        "delay_multiplier": 4.0,
        "radius_km":        30,
        "affects_hub":      False,
    },
    "port_congestion": {
        "speed_penalty":    0.3,
        "delay_multiplier": 2.5,
        "radius_km":        100,
        "affects_hub":      True,
    },
}

# Warehouse hubs with stock/capacity metadata
WAREHOUSE_HUBS = {
    "Delhi":     {"id": "DEL", "capacity": 5000, "stock_days": 7,  "criticality": "HIGH"},
    "Mumbai":    {"id": "MUM", "capacity": 8000, "stock_days": 10, "criticality": "HIGH"},
    "Bangalore": {"id": "BLR", "capacity": 4000, "stock_days": 5,  "criticality": "HIGH"},
    "Hyderabad": {"id": "HYD", "capacity": 3500, "stock_days": 6,  "criticality": "MEDIUM"},
    "Chennai":   {"id": "CHN", "capacity": 3000, "stock_days": 5,  "criticality": "MEDIUM"},
    "Kolkata":   {"id": "KOL", "capacity": 4500, "stock_days": 8,  "criticality": "HIGH"},
    "Nagpur":    {"id": "NGP", "capacity": 2000, "stock_days": 4,  "criticality": "MEDIUM"},
    "Ahmedabad": {"id": "AHM", "capacity": 2500, "stock_days": 5,  "criticality": "MEDIUM"},
    "Jaipur":    {"id": "JAI", "capacity": 1800, "stock_days": 4,  "criticality": "LOW"},
    "Lucknow":   {"id": "LKO", "capacity": 2200, "stock_days": 5,  "criticality": "MEDIUM"},
    "Pune":      {"id": "PNE", "capacity": 2800, "stock_days": 6,  "criticality": "MEDIUM"},
}


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class DisruptionEvent:
    event_type: str       # warehouse_shutdown | traffic_spike | weather_event | road_closure | port_congestion
    location: str         # city name
    duration_hours: int   # how long the disruption lasts
    severity: float = 1.0 # 0.5 = mild, 1.0 = normal, 1.5 = severe


@dataclass
class AffectedShipment:
    shipment_id: str
    cargo: str
    carrier: str
    delay_hours: float
    original_eta: str
    new_eta: str
    impact_reason: str
    sla_breach: bool


@dataclass
class CascadeResult:
    event: DisruptionEvent
    affected_shipments: List[AffectedShipment]
    affected_warehouses: List[str]
    total_affected_count: int
    total_warehouse_count: int
    sla_risk: str                  # LOW | MEDIUM | HIGH | CRITICAL
    avg_delay_hours: float
    total_cost_impact_inr: float
    cascade_depth: int             # how many hops the disruption propagates
    dependency_chain: List[str]    # ordered list of impacted cities


# ─── Geo helper ──────────────────────────────────────────────────────────────

def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(max(0, a)))


def _city_coords(city: str) -> Optional[tuple]:
    """Look up lat/lng for a city name from the graph nodes."""
    for node in NODES.values():
        if node.city.lower() == city.lower():
            return node.lat, node.lng
    return None


# ─── Dependency graph ─────────────────────────────────────────────────────────

def build_dependency_graph() -> Dict[str, List[str]]:
    """
    Build a city → downstream cities dependency graph.
    A city B depends on A if there is a direct edge A→B in ADJACENCY.
    """
    graph: Dict[str, List[str]] = {}
    for node_id, edges in ADJACENCY.items():
        city = NODES[node_id].city
        deps = [NODES[e.to_node].city for e in edges]
        graph[city] = deps
    return graph


def _propagate_cascade(start_city: str, depth: int = 2) -> List[str]:
    """BFS from start_city up to `depth` hops — returns all impacted cities."""
    graph = build_dependency_graph()
    visited, queue = set(), [start_city]
    chain = []
    for _ in range(depth):
        next_queue = []
        for city in queue:
            for dep in graph.get(city, []):
                if dep not in visited:
                    visited.add(dep)
                    chain.append(dep)
                    next_queue.append(dep)
        queue = next_queue
    return chain


# ─── Core cascade computation ─────────────────────────────────────────────────

def compute_cascade(event: DisruptionEvent) -> CascadeResult:
    """
    Given a disruption event, compute the full cascade impact.
    """
    profile = EVENT_PROFILES.get(event.event_type, EVENT_PROFILES["traffic_spike"])
    coords  = _city_coords(event.location)
    radius  = profile["radius_km"] * event.severity

    # 1. Find which shipments are within the disruption radius
    affected: List[AffectedShipment] = []
    for s in LIVE_SHIPMENTS:
        if s["status"] == "Delivered":
            continue

        # Check if origin, destination, or current location is in radius
        impact_points = [
            (s["origin"]["lat"],           s["origin"]["lng"],           "origin"),
            (s["destination"]["lat"],       s["destination"]["lng"],       "destination"),
            (s["current_location"]["lat"],  s["current_location"]["lng"],  "current position"),
        ]

        hit_reason = None
        if coords:
            for lat, lng, label in impact_points:
                dist = _haversine(coords[0], coords[1], lat, lng)
                if dist <= radius:
                    hit_reason = f"{label} within {round(dist)} km of {event.location}"
                    break

        # Also check if city name matches any shipment city
        if not hit_reason:
            for city_key in ["origin", "destination"]:
                if event.location.lower() in s[city_key]["city"].lower():
                    hit_reason = f"shipment {city_key} is {event.location}"
                    break

        if not hit_reason:
            continue

        # Compute delay
        base_delay = event.duration_hours * profile["delay_multiplier"] * event.severity
        # Heavier cargo = harder to reroute = more delay
        cargo_factor = 1.3 if s["cargo"] in ["Steel Products", "Auto Parts"] else 1.0
        delay_hours  = round(base_delay * cargo_factor, 1)

        from datetime import datetime, timedelta
        try:
            orig_eta = datetime.strptime(s["eta"], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            orig_eta = datetime.utcnow() + timedelta(hours=6)
        new_eta = orig_eta + timedelta(hours=delay_hours)

        sla_breach = delay_hours > 12

        affected.append(AffectedShipment(
            shipment_id  = s["id"],
            cargo        = s["cargo"],
            carrier      = s["carrier"],
            delay_hours  = delay_hours,
            original_eta = orig_eta.strftime("%Y-%m-%dT%H:%M:%S"),
            new_eta      = new_eta.strftime("%Y-%m-%dT%H:%M:%S"),
            impact_reason= hit_reason,
            sla_breach   = sla_breach,
        ))

    # 2. Cascade to downstream warehouses
    dependency_chain = _propagate_cascade(event.location, depth=2)
    affected_warehouses = [
        city for city in dependency_chain
        if city in WAREHOUSE_HUBS
    ]
    if event.location in WAREHOUSE_HUBS:
        affected_warehouses = [event.location] + affected_warehouses

    # 3. SLA risk
    avg_delay = sum(a.delay_hours for a in affected) / max(len(affected), 1)
    breach_count = sum(1 for a in affected if a.sla_breach)

    if breach_count >= 3 or avg_delay > 36:
        sla_risk = "CRITICAL"
    elif breach_count >= 2 or avg_delay > 18:
        sla_risk = "HIGH"
    elif breach_count >= 1 or avg_delay > 8:
        sla_risk = "MEDIUM"
    else:
        sla_risk = "LOW"

    # 4. Cost impact (rough estimate)
    cost_per_delay_hour = 15000  # ₹ per shipment per hour
    total_cost = sum(a.delay_hours * cost_per_delay_hour for a in affected)

    return CascadeResult(
        event               = event,
        affected_shipments  = affected,
        affected_warehouses = affected_warehouses,
        total_affected_count= len(affected),
        total_warehouse_count=len(affected_warehouses),
        sla_risk            = sla_risk,
        avg_delay_hours     = round(avg_delay, 1),
        total_cost_impact_inr=round(total_cost),
        cascade_depth       = 2,
        dependency_chain    = dependency_chain[:8],
    )


def calculate_sla_risk(affected_count: int, avg_delay: float, breach_count: int) -> str:
    if breach_count >= 3 or avg_delay > 36: return "CRITICAL"
    if breach_count >= 2 or avg_delay > 18: return "HIGH"
    if breach_count >= 1 or avg_delay > 8:  return "MEDIUM"
    return "LOW"
