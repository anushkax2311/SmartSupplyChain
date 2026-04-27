"""
ai/gemma_service.py
====================
Gemma AI integration for Phase 4.

Architecture
------------
1. PRIMARY  : Google Gemma via google-generativeai SDK (gemma-3-12b-it)
2. FALLBACK : Rich rule-based template engine (no external dependency)

The fallback produces analyst-quality text that reads as if it were
AI-generated — structured, quantified, and actionable.

Set env var GEMMA_API_KEY to enable live Gemma calls.
"""

from __future__ import annotations
import os
import logging
from typing import Optional

log = logging.getLogger("gemma")

# ─── Try importing Google GenAI SDK ──────────────────────────────────────────

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

_client = None

def _init_client():
    global _client
    if _client:
        return _client
    api_key = os.getenv("GEMMA_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key and _GENAI_AVAILABLE:
        genai.configure(api_key=api_key)
        _client = genai.GenerativeModel("gemma-3-12b-it")
        log.info("Gemma AI client initialized")
    return _client


# ─── Prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(context: dict) -> str:
    event          = context.get("event", "unknown")
    location       = context.get("location", "unknown")
    affected       = context.get("affected_shipments", 0)
    delay          = context.get("delay_hours", 0)
    sla_risk       = context.get("sla_risk", "UNKNOWN")
    duration       = context.get("duration_hours", 0)
    warehouses     = context.get("affected_warehouses", [])
    cost           = context.get("total_cost_impact_inr", 0)
    cargo_types    = context.get("cargo_types", [])
    question       = context.get("question", "")

    if question:
        return f"""You are a supply chain operations expert at a major Indian logistics company.

A manager has asked: "{question}"

Current system state:
- Active disruption: {event.replace('_', ' ').title()} at {location}
- Shipments affected: {affected}
- Average delay: {delay} hours
- SLA Risk: {sla_risk}
- Warehouses impacted: {', '.join(warehouses) if warehouses else 'None'}
- Estimated cost impact: ₹{cost:,}

Answer the manager's question directly and concisely. Be specific with numbers.
Provide 1-2 actionable recommendations. Keep response under 150 words."""

    return f"""You are a supply chain expert analyzing a disruption event.

Event: {event.replace('_', ' ').title()}
Location: {location}
Duration: {duration} hours
Affected Shipments: {affected}
Average Delay: {delay} hours
SLA Risk Level: {sla_risk}
Impacted Warehouses: {', '.join(warehouses) if warehouses else 'None identified'}
Cargo Types: {', '.join(cargo_types) if cargo_types else 'Mixed'}
Estimated Cost Impact: ₹{cost:,}

Provide a concise professional analysis with:
1. Impact summary (2 sentences)
2. Key business implications (2 bullet points)
3. Recommended actions (2 bullet points)

Keep total response under 200 words. Be specific and quantitative."""


# ─── Fallback rule-based generator ───────────────────────────────────────────

def _rule_based_explanation(context: dict) -> str:
    event      = context.get("event", "disruption").replace("_", " ")
    location   = context.get("location", "the affected area")
    affected   = context.get("affected_shipments", 0)
    delay      = context.get("delay_hours", 0)
    sla_risk   = context.get("sla_risk", "MEDIUM")
    duration   = context.get("duration_hours", 0)
    warehouses = context.get("affected_warehouses", [])
    cost       = context.get("total_cost_impact_inr", 0)
    cargo      = context.get("cargo_types", [])
    question   = context.get("question", "")

    wh_text = f"{', '.join(warehouses[:3])}" if warehouses else "no major hubs"
    cargo_text = f"{', '.join(cargo[:3])}" if cargo else "multiple cargo types"

    risk_color = {
        "CRITICAL": "severe and immediate",
        "HIGH":     "significant",
        "MEDIUM":   "moderate",
        "LOW":      "minimal",
    }.get(sla_risk, "moderate")

    if question:
        q = question.lower()
        if "warehouse" in q and "shut" in q:
            city = location
            return (
                f"A {city} warehouse shutdown would have {risk_color} impact on your supply chain. "
                f"Based on current shipment data, {affected} active shipments would be affected, "
                f"with an average delay of {delay} hours per shipment. "
                f"Downstream hubs including {wh_text} would face inventory pressure within "
                f"{max(1, duration//24)} days. "
                f"Recommended actions: (1) Activate contingency stock from nearest hub, "
                f"(2) Reroute in-transit shipments via alternate corridors immediately."
            )
        if "delay" in q or "delayed" in q:
            return (
                f"Current delays are primarily driven by the {event} at {location}. "
                f"This has reduced effective throughput by approximately "
                f"{min(90, int(delay * 4))}% on affected routes. "
                f"The {affected} impacted shipments carry {cargo_text}, "
                f"with an estimated recovery window of {max(2, duration // 4)} hours "
                f"once conditions normalize. "
                f"Priority action: focus rerouting efforts on time-critical pharmaceutical "
                f"and perishable cargo first."
            )
        if "cost" in q or "impact" in q:
            return (
                f"The financial impact of this disruption is estimated at ₹{cost:,}. "
                f"This comprises direct delay penalties across {affected} shipments "
                f"averaging {delay} hours each, plus secondary costs from emergency "
                f"rerouting and expedited handling. "
                f"SLA breach risk is {sla_risk}, which could trigger penalty clauses "
                f"with key customers. "
                f"Mitigation through proactive customer communication and partial credit "
                f"offers is recommended to protect long-term relationships."
            )
        # Generic question
        return (
            f"Based on the current {event} disruption at {location}: "
            f"{affected} shipments are impacted with {delay}h average delay. "
            f"SLA risk is {sla_risk}. Estimated cost: ₹{cost:,}. "
            f"Recommend immediate rerouting of high-priority shipments and "
            f"proactive customer notifications for all affected deliveries."
        )

    # Standard explanation
    return f"""**Impact Summary**
A {event} at {location} lasting {duration} hours has created {risk_color} disruption across the supply chain. {affected} active shipments are affected, with an average delay of {delay} hours per shipment. Impacted warehouse hubs include {wh_text}.

**Business Implications**
• **Financial exposure**: Estimated cost impact of ₹{cost:,} from delays, rerouting costs, and potential SLA penalties. Risk level is classified as **{sla_risk}**.
• **Inventory risk**: Downstream hubs dependent on {location} — particularly those carrying {cargo_text} — face stock depletion within {max(1, duration // 24) + 1} days if disruption continues.

**Recommended Actions**
• **Immediate**: Reroute all in-transit shipments through alternate corridors. Prioritise pharmaceuticals and perishables. Trigger safety stock replenishment from secondary hubs.
• **Short-term**: Notify affected customers proactively with revised ETAs. Activate carrier contingency agreements. Monitor cascade propagation to {wh_text} and pre-position buffer stock."""


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_explanation(context: dict) -> str:
    """
    Generate a natural-language explanation for a disruption/simulation context.
    Tries Gemma first; falls back to rule-based engine.
    """
    client = _init_client()

    if client:
        try:
            prompt   = _build_prompt(context)
            response = client.generate_content(prompt)
            text = response.text.strip()
            if text:
                log.info("Gemma response generated successfully")
                return text
        except Exception as e:
            log.warning(f"Gemma call failed: {e} — using fallback")

    return _rule_based_explanation(context)


def generate_chat_response(question: str, system_state: dict) -> str:
    """
    Answer a free-form manager question given the current system state.
    """
    context = {**system_state, "question": question}
    return generate_explanation(context)
