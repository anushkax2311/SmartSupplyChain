"""
analytics/engine.py
====================
Phase 5 Analytics Engine.

Computes KPIs from live shipment data and alert history:
  - On-time delivery rate
  - Average delay per shipment
  - Cost savings from self-healing reroutes
  - Delay reduction trend (simulated rolling window)
  - Carrier performance scores
  - Route efficiency metrics
"""

from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import List, Dict

from models.mock_data import LIVE_SHIPMENTS
from healing.alerts import get_alerts


# ─── KPI computation ─────────────────────────────────────────────────────────

def compute_kpis() -> dict:
    total    = len(LIVE_SHIPMENTS)
    active   = [s for s in LIVE_SHIPMENTS if s["status"] != "Delivered"]
    delayed  = [s for s in LIVE_SHIPMENTS if s["status"] == "Delayed"]
    delivered= [s for s in LIVE_SHIPMENTS if s["status"] == "Delivered"]

    # On-time rate
    on_time_rate = round((total - len(delayed)) / max(total, 1) * 100, 1)

    # Avg speed of active shipments
    avg_speed = round(sum(s["speed_kmh"] for s in active) / max(len(active), 1), 1)

    # Avg risk score
    avg_risk = round(sum(s["risk_score"] for s in LIVE_SHIPMENTS) / max(total, 1), 1)

    # Reroutes applied (from alerts)
    alerts       = get_alerts(limit=100)
    reroute_count= sum(1 for a in alerts if a.type == "reroute_applied")
    delay_alerts = sum(1 for a in alerts if a.type == "delay_detected")

    # Cost savings from reroutes (extract from alert metadata)
    cost_saved = 0
    time_saved_total = 0
    for a in alerts:
        if a.type == "reroute_applied":
            meta = a.metadata or {}
            time_saved_total += meta.get("time_saved_min", 0)
            cost_saved += meta.get("time_saved_min", 0) * 800  # ₹800 per minute saved

    # Delay reduction (simulated rolling 24h trend)
    delay_reduction_pct = min(85, reroute_count * 12 + random.randint(20, 35))

    return {
        "total_shipments":       total,
        "active_shipments":      len(active),
        "delayed_shipments":     len(delayed),
        "delivered_shipments":   len(delivered),
        "on_time_rate_pct":      on_time_rate,
        "avg_speed_kmh":         avg_speed,
        "avg_risk_score":        avg_risk,
        "reroutes_applied":      reroute_count,
        "delay_alerts_fired":    delay_alerts,
        "cost_saved_inr":        round(cost_saved),
        "time_saved_minutes":    round(time_saved_total),
        "delay_reduction_pct":   delay_reduction_pct,
        "self_heal_success_rate":round(min(100, reroute_count * 15 + 60), 1),
    }


def compute_carrier_performance() -> List[dict]:
    """Score each carrier based on speed, delay rate, risk."""
    carrier_stats: Dict[str, dict] = {}

    for s in LIVE_SHIPMENTS:
        c = s["carrier"]
        if c not in carrier_stats:
            carrier_stats[c] = {"shipments": 0, "delayed": 0, "speed_sum": 0, "risk_sum": 0}
        carrier_stats[c]["shipments"] += 1
        carrier_stats[c]["speed_sum"] += s["speed_kmh"]
        carrier_stats[c]["risk_sum"]  += s["risk_score"]
        if s["status"] == "Delayed":
            carrier_stats[c]["delayed"] += 1

    result = []
    for carrier, stats in carrier_stats.items():
        n            = stats["shipments"]
        delay_rate   = round(stats["delayed"] / n * 100, 1)
        avg_speed    = round(stats["speed_sum"] / n, 1)
        avg_risk     = round(stats["risk_sum"] / n, 1)
        score        = round(max(0, 100 - delay_rate * 1.5 - avg_risk * 0.3 + (avg_speed - 50) * 0.2), 1)
        result.append({
            "carrier":      carrier,
            "shipments":    n,
            "delay_rate":   delay_rate,
            "avg_speed":    avg_speed,
            "avg_risk":     avg_risk,
            "score":        min(100, score),
            "grade":        "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D",
        })

    return sorted(result, key=lambda x: x["score"], reverse=True)


def compute_delay_trend() -> List[dict]:
    """Simulate a 12-hour delay trend (rolling hourly buckets)."""
    now    = datetime.utcnow()
    trend  = []
    base   = len([s for s in LIVE_SHIPMENTS if s["status"] == "Delayed"])

    for i in range(12, 0, -1):
        hour    = (now - timedelta(hours=i)).strftime("%H:00")
        delayed = max(0, base + random.randint(-2, 2))
        rerouted= random.randint(0, 2)
        trend.append({
            "hour":         hour,
            "delayed":      delayed,
            "rerouted":     rerouted,
            "on_time":      8 - delayed,
        })

    # Last bucket = current real state
    trend.append({
        "hour":     now.strftime("%H:%M"),
        "delayed":  base,
        "rerouted": sum(1 for a in get_alerts(20) if a.type == "reroute_applied"),
        "on_time":  8 - base,
    })
    return trend


def compute_cost_savings_breakdown() -> List[dict]:
    """Break down cost savings by category."""
    alerts       = get_alerts(100)
    reroute_alerts = [a for a in alerts if a.type == "reroute_applied"]

    fuel_saved    = sum(a.metadata.get("time_saved_min", 0) * 250 for a in reroute_alerts)
    penalty_saved = sum(1 for a in alerts if a.type == "sla_breach") * 0 * 50000   # avoided
    toll_saved    = len(reroute_alerts) * random.randint(800, 2500)
    idle_saved    = sum(a.metadata.get("time_saved_min", 0) * 180 for a in reroute_alerts)

    return [
        {"category": "Fuel Savings",          "amount_inr": round(fuel_saved),    "icon": "⛽"},
        {"category": "Toll Optimization",      "amount_inr": round(toll_saved),    "icon": "🛣️"},
        {"category": "Idle Time Reduction",    "amount_inr": round(idle_saved),    "icon": "⏱️"},
        {"category": "SLA Penalty Avoidance",  "amount_inr": round(penalty_saved), "icon": "📋"},
    ]
