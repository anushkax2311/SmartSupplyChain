"""
simulation/engine.py  (Phase 5 upgrade)
=========================================
Background asyncio tick loop.
Now also runs the self-healing engine each tick and broadcasts
alerts alongside shipment updates.
"""

import asyncio
import json
import logging
from datetime import datetime

from models.mock_data import LIVE_SHIPMENTS
from ai.predictor import drift_speed, interpolate_location, compute_prediction
from healing.engine import heal_shipment
from healing.alerts import alert_to_dict

log = logging.getLogger("simulator")

TICK_SECONDS    = 4
PROGRESS_PER_TICK = 0.004

_ws_manager = None

def set_ws_manager(manager):
    global _ws_manager
    _ws_manager = manager


def _advance_shipment(s: dict) -> dict:
    if s["status"] == "Delivered":
        return s

    speed_factor = s["speed_kmh"] / 70.0
    step = PROGRESS_PER_TICK * speed_factor
    s["progress"] = round(min(1.0, s["progress"] + step), 4)

    orig = s["origin"]
    dest = s["destination"]
    lat, lng = interpolate_location(
        orig["lat"], orig["lng"],
        dest["lat"], dest["lng"],
        s["progress"],
    )
    s["current_location"] = {"lat": lat, "lng": lng, "city": _city_label(s)}

    s["speed_kmh"] = drift_speed(s["speed_kmh"], s["cargo"])

    pred = compute_prediction(s)
    s["prediction"] = {k: v for k, v in pred.items() if not k.startswith("_")}
    s["risk_score"]  = pred.get("_risk_score", s["risk_score"])

    if s["progress"] >= 1.0:
        s["status"] = "Delivered"
        s["speed_kmh"] = 0.0
        s["current_location"] = {**dest, "city": dest["city"]}
        s["prediction"]["delay_status"] = False
        s["prediction"]["risk_level"] = "LOW"
        s["prediction"]["eta_minutes_remaining"] = 0
    elif pred["delay_status"]:
        s["status"] = "Delayed"
    else:
        s["status"] = "In Transit"

    return s


def _city_label(s: dict) -> str:
    p    = s["progress"]
    orig = s["origin"]["city"]
    dest = s["destination"]["city"]
    if p < 0.25:   return f"Near {orig}"
    elif p < 0.50: return f"Midway to {dest}"
    elif p < 0.75: return f"Approaching {dest}"
    elif p < 0.95: return f"Near {dest}"
    else:          return dest


async def simulation_loop():
    log.info("Simulation engine started (Phase 5 — self-healing active)")
    while True:
        await asyncio.sleep(TICK_SECONDS)

        tick_alerts = []
        for shipment in LIVE_SHIPMENTS:
            _advance_shipment(shipment)
            # ── Phase 5: self-heal each shipment ──────────────────────────────
            alerts = heal_shipment(shipment)
            tick_alerts.extend(alerts)

        if _ws_manager:
            snapshot = {
                "type":      "shipment_update",
                "timestamp": datetime.utcnow().isoformat(),
                "shipments": LIVE_SHIPMENTS,
                "alerts":    [alert_to_dict(a) for a in tick_alerts],
            }
            await _ws_manager.broadcast(json.dumps(snapshot))
