"""
healing/alerts.py
==================
Central alert registry for Phase 5.

Every self-healing action, delay detection, reroute, and SLA breach
produces an Alert that gets stored here and broadcast to the frontend.

Alert levels  : INFO | WARNING | CRITICAL
Alert types   : delay_detected | reroute_applied | eta_updated |
                sla_breach | self_heal | delivery_complete | speed_drop
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from collections import deque

# ─── Alert model ─────────────────────────────────────────────────────────────

@dataclass
class Alert:
    id:           str
    type:         str        # delay_detected | reroute_applied | eta_updated | sla_breach | self_heal | delivery_complete | speed_drop
    level:        str        # INFO | WARNING | CRITICAL
    shipment_id:  Optional[str]
    title:        str
    message:      str
    timestamp:    str
    acknowledged: bool = False
    metadata:     dict = field(default_factory=dict)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def make_alert(
    alert_type: str,
    level: str,
    title: str,
    message: str,
    shipment_id: str = None,
    metadata: dict = None,
) -> Alert:
    return Alert(
        id          = str(uuid.uuid4())[:8].upper(),
        type        = alert_type,
        level       = level,
        shipment_id = shipment_id,
        title       = title,
        message     = message,
        timestamp   = _now(),
        metadata    = metadata or {},
    )


# ─── Alert store ─────────────────────────────────────────────────────────────
# Keep last 100 alerts (FIFO ring buffer)

_ALERTS: deque[Alert] = deque(maxlen=100)


def push_alert(alert: Alert) -> Alert:
    _ALERTS.appendleft(alert)
    return alert


def get_alerts(limit: int = 50, level: str = None, unacked_only: bool = False) -> List[Alert]:
    alerts = list(_ALERTS)
    if level:
        alerts = [a for a in alerts if a.level == level]
    if unacked_only:
        alerts = [a for a in alerts if not a.acknowledged]
    return alerts[:limit]


def acknowledge_alert(alert_id: str) -> bool:
    for alert in _ALERTS:
        if alert.id == alert_id:
            alert.acknowledged = True
            return True
    return False


def acknowledge_all() -> int:
    count = 0
    for alert in _ALERTS:
        if not alert.acknowledged:
            alert.acknowledged = True
            count += 1
    return count


def get_unacked_count() -> int:
    return sum(1 for a in _ALERTS if not a.acknowledged)


def alert_to_dict(a: Alert) -> dict:
    return {
        "id":           a.id,
        "type":         a.type,
        "level":        a.level,
        "shipment_id":  a.shipment_id,
        "title":        a.title,
        "message":      a.message,
        "timestamp":    a.timestamp,
        "acknowledged": a.acknowledged,
        "metadata":     a.metadata,
    }
