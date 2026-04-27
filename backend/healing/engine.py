"""
healing/engine.py
==================
Self-Healing Engine for Phase 5.

Runs INSIDE the simulation tick loop. Every tick it:
  1. Evaluates each shipment for healing triggers
  2. Auto-reroutes if conditions warrant (speed drop, high risk, incident)
  3. Updates ETA based on current speed + distance
  4. Generates alerts for every action taken
  5. Returns list of alerts produced this tick (for WebSocket broadcast)

Healing triggers (checked in priority order)
--------------------------------------------
CRITICAL : speed < 20 km/h for 2+ consecutive ticks  → force reroute
HIGH     : delay_probability > 0.70                   → auto reroute
HIGH     : risk_level == HIGH                          → auto reroute
WARNING  : speed dropped > 40% since last tick        → alert + monitor
INFO     : ETA shifted > 30 min from original         → eta_updated alert
INFO     : shipment delivered                          → delivery_complete alert
"""

from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from healing.alerts import Alert, make_alert, push_alert
from routing.engine import route_for_shipment
from routing.graph import closest_node

log = logging.getLogger("self_healer")

# Track consecutive slow ticks per shipment
_slow_tick_count: Dict[str, int]   = {}
_last_speed:      Dict[str, float] = {}
_original_eta:    Dict[str, str]   = {}
_heal_cooldown:   Dict[str, int]   = {}   # ticks remaining before re-evaluating


def _fmt_eta(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S").strftime("%d %b %H:%M")
    except Exception:
        return iso


def _minutes_diff(eta1: str, eta2: str) -> float:
    try:
        t1 = datetime.strptime(eta1, "%Y-%m-%dT%H:%M:%S")
        t2 = datetime.strptime(eta2, "%Y-%m-%dT%H:%M:%S")
        return abs((t2 - t1).total_seconds() / 60)
    except Exception:
        return 0.0


def heal_shipment(s: dict) -> List[Alert]:
    """
    Evaluate and apply self-healing for one shipment.
    Returns list of alerts generated (may be empty).
    """
    sid    = s["id"]
    alerts = []

    if s["status"] == "Delivered":
        # Fire delivery alert once
        if _slow_tick_count.get(sid) != -999:
            _slow_tick_count[sid] = -999
            a = make_alert(
                "delivery_complete", "INFO",
                f"✅ {sid} Delivered",
                f"Shipment {sid} carrying {s['cargo']} has been successfully delivered to {s['destination']['city']}.",
                shipment_id=sid,
            )
            alerts.append(push_alert(a))
        return alerts

    pred    = s.get("prediction") or {}
    speed   = s.get("speed_kmh", 60.0)
    risk    = pred.get("risk_level", "LOW")
    delay_p = pred.get("delay_probability", 0.0)
    eta_now = pred.get("eta_updated") or s.get("eta", "")

    # Store original ETA on first sight
    if sid not in _original_eta:
        _original_eta[sid] = s.get("eta", "")

    # Cooldown: skip healing evaluation if recently healed
    if _heal_cooldown.get(sid, 0) > 0:
        _heal_cooldown[sid] -= 1
        # Still check ETA drift
        _check_eta_drift(sid, eta_now, alerts)
        return alerts

    # ── 1. Speed drop alert ───────────────────────────────────────────────────
    prev_speed = _last_speed.get(sid, speed)
    speed_drop_pct = (prev_speed - speed) / max(prev_speed, 1) if prev_speed > 0 else 0
    if speed_drop_pct > 0.40 and speed < 40:
        a = make_alert(
            "speed_drop", "WARNING",
            f"⚡ Speed Drop — {sid}",
            f"{sid} speed dropped {round(speed_drop_pct*100)}% to {speed} km/h "
            f"({s['current_location']['city']}). Monitoring for further degradation.",
            shipment_id=sid,
            metadata={"speed": speed, "prev_speed": prev_speed, "drop_pct": round(speed_drop_pct*100)},
        )
        alerts.append(push_alert(a))
    _last_speed[sid] = speed

    # ── 2. Consecutive slow ticks → CRITICAL reroute ──────────────────────────
    if speed < 20:
        _slow_tick_count[sid] = _slow_tick_count.get(sid, 0) + 1
    else:
        _slow_tick_count[sid] = 0

    if _slow_tick_count.get(sid, 0) >= 2:
        healed = _attempt_reroute(s, reason="Vehicle speed critically low (<20 km/h) for 2+ ticks", level="CRITICAL")
        if healed:
            alerts.append(healed)
            _slow_tick_count[sid] = 0
            _heal_cooldown[sid] = 5
            return alerts

    # ── 3. High delay probability → auto reroute ──────────────────────────────
    if delay_p > 0.70:
        healed = _attempt_reroute(s, reason=f"Delay probability {round(delay_p*100)}% exceeds critical threshold", level="CRITICAL")
        if healed:
            alerts.append(healed)
            _heal_cooldown[sid] = 8
            return alerts

    # ── 4. HIGH risk level → auto reroute ─────────────────────────────────────
    if risk == "HIGH" and delay_p > 0.55:
        healed = _attempt_reroute(s, reason="AI risk level HIGH with delay probability >55%", level="WARNING")
        if healed:
            alerts.append(healed)
            _heal_cooldown[sid] = 6
            return alerts

    # ── 5. Delay detected alert ───────────────────────────────────────────────
    if s["status"] == "Delayed" and _heal_cooldown.get(sid, 0) == 0:
        a = make_alert(
            "delay_detected", "WARNING",
            f"⚠ Delay Detected — {sid}",
            f"Shipment {sid} ({s['cargo']}) is delayed near {s['current_location']['city']}. "
            f"Current speed: {speed} km/h. Delay probability: {round(delay_p*100)}%.",
            shipment_id=sid,
            metadata={"speed": speed, "delay_probability": delay_p},
        )
        alerts.append(push_alert(a))
        _heal_cooldown[sid] = 3   # don't spam the same alert

    # ── 6. ETA drift ──────────────────────────────────────────────────────────
    _check_eta_drift(sid, eta_now, alerts)

    return alerts


def _attempt_reroute(s: dict, reason: str, level: str) -> Alert | None:
    """Try to compute and apply a better route. Returns alert or None."""
    sid = s["id"]
    try:
        route_a, route_b = route_for_shipment(s, "balanced")
        if route_b.feasible and route_b.avg_risk < route_a.avg_risk:
            time_saved = round((route_a.total_time_hr - route_b.total_time_hr) * 60)
            risk_saved = round((route_a.avg_risk - route_b.avg_risk) * 100)

            # Apply new ETA to shipment
            from datetime import datetime, timedelta
            new_eta = datetime.utcnow() + timedelta(hours=route_b.total_time_hr)
            s["eta"] = new_eta.strftime("%Y-%m-%dT%H:%M:%S")
            if s.get("prediction"):
                s["prediction"]["eta_updated"] = s["eta"]
                s["prediction"]["eta_minutes_remaining"] = int(route_b.total_time_hr * 60)

            a = make_alert(
                "reroute_applied", level,
                f"🔄 Auto-Rerouted — {sid}",
                f"Self-healing triggered for {sid}. Reason: {reason}. "
                f"Switched to {route_b.route_id}: saves {time_saved} min, "
                f"reduces risk by {risk_saved}%. New ETA: {_fmt_eta(s['eta'])}.",
                shipment_id=sid,
                metadata={
                    "old_route": route_a.route_id,
                    "new_route": route_b.route_id,
                    "time_saved_min": time_saved,
                    "risk_reduction_pct": risk_saved,
                    "reason": reason,
                },
            )
            return push_alert(a)
    except Exception as e:
        log.warning(f"Reroute failed for {sid}: {e}")
    return None


def _check_eta_drift(sid: str, current_eta: str, alerts: list):
    """Generate ETA updated alert if ETA has shifted > 30 min from original."""
    orig = _original_eta.get(sid)
    if not orig or not current_eta:
        return
    drift = _minutes_diff(orig, current_eta)
    if drift > 30:
        # Only alert once per significant shift (update original reference)
        _original_eta[sid] = current_eta
        a = make_alert(
            "eta_updated", "INFO",
            f"🕐 ETA Updated — {sid}",
            f"ETA for shipment {sid} has shifted by {round(drift)} minutes. "
            f"New estimated arrival: {_fmt_eta(current_eta)}.",
            shipment_id=sid,
            metadata={"drift_minutes": round(drift), "new_eta": current_eta},
        )
        push_alert(a)
        alerts.append(a)
