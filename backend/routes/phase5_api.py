"""
routes/phase5_api.py
=====================
Phase 5 endpoints:

GET  /alerts                    → paginated alert list
GET  /alerts/unacked-count      → badge counter for UI
POST /alerts/{id}/acknowledge   → mark one alert read
POST /alerts/acknowledge-all    → clear all badges
GET  /analytics/kpis            → live KPI dashboard data
GET  /analytics/carrier-performance → carrier scorecards
GET  /analytics/delay-trend     → 12-hour trend data
GET  /analytics/cost-savings    → cost savings breakdown
POST /healing/trigger/{sid}     → manually trigger self-heal
"""

from fastapi import APIRouter, HTTPException
from healing.alerts import (
    get_alerts, acknowledge_alert, acknowledge_all,
    get_unacked_count, alert_to_dict
)
from healing.engine import heal_shipment, _attempt_reroute
from analytics.engine import (
    compute_kpis, compute_carrier_performance,
    compute_delay_trend, compute_cost_savings_breakdown
)
from models.mock_data import LIVE_SHIPMENTS

router = APIRouter(tags=["Phase 5 - Self-Healing & Analytics"])


# ─── Alerts ──────────────────────────────────────────────────────────────────

@router.get("/alerts")
def list_alerts(limit: int = 50, level: str = None, unacked_only: bool = False):
    alerts = get_alerts(limit=limit, level=level, unacked_only=unacked_only)
    return {
        "count":        len(alerts),
        "unacked":      get_unacked_count(),
        "alerts":       [alert_to_dict(a) for a in alerts],
    }


@router.get("/alerts/unacked-count")
def unacked_count():
    return {"count": get_unacked_count()}


@router.post("/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str):
    ok = acknowledge_alert(alert_id)
    if not ok:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return {"acknowledged": True, "alert_id": alert_id}


@router.post("/alerts/acknowledge-all")
def ack_all():
    count = acknowledge_all()
    return {"acknowledged": count}


# ─── Analytics ───────────────────────────────────────────────────────────────

@router.get("/analytics/kpis")
def get_kpis():
    return compute_kpis()


@router.get("/analytics/carrier-performance")
def carrier_performance():
    return {"carriers": compute_carrier_performance()}


@router.get("/analytics/delay-trend")
def delay_trend():
    return {"trend": compute_delay_trend()}


@router.get("/analytics/cost-savings")
def cost_savings():
    kpis = compute_kpis()
    breakdown = compute_cost_savings_breakdown()
    return {
        "total_saved_inr":     kpis["cost_saved_inr"],
        "time_saved_minutes":  kpis["time_saved_minutes"],
        "delay_reduction_pct": kpis["delay_reduction_pct"],
        "breakdown":           breakdown,
    }


# ─── Manual self-heal trigger ─────────────────────────────────────────────────

@router.post("/healing/trigger/{shipment_id}")
def manual_heal(shipment_id: str):
    s = next((s for s in LIVE_SHIPMENTS if s["id"] == shipment_id), None)
    if not s:
        raise HTTPException(404, f"Shipment {shipment_id} not found")
    if s["status"] == "Delivered":
        return {"message": "Shipment already delivered", "healed": False}

    alert = _attempt_reroute(s, reason="Manual self-heal triggered by operator", level="INFO")
    return {
        "healed":  alert is not None,
        "alert":   alert_to_dict(alert) if alert else None,
        "message": "Reroute applied successfully" if alert else "No better route found — current route maintained",
    }
