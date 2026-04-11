"""
Scenario definitions + active scenario state.
tools.py reads get_active_scenario() to apply port-condition overrides.
"""
from __future__ import annotations

# ── Active scenario registry ──────────────────────────────────────────────────

_active_scenario_name: str | None = None


def set_active_scenario(name: str | None) -> None:
    global _active_scenario_name
    _active_scenario_name = name


def get_active_scenario() -> dict | None:
    if _active_scenario_name is None:
        return None
    return _SCENARIOS.get(_active_scenario_name)


def get_scenario(name: str) -> dict | None:
    return _SCENARIOS.get(name)


# ── Scenario definitions ──────────────────────────────────────────────────────

_SCENARIOS: dict[str, dict] = {

    # ── 1. Storm at Jebel Ali ─────────────────────────────────────────────────
    "storm_jebel_ali": {
        "title": "Sandstorm — Jebel Ali Port Closure",
        "affected_vessels": ["SHP001", "SHP002", "SHP003"],
        "observation_severity": {
            "SHP001": "critical",   # perishables, tight deadline
            "SHP002": "warning",    # industrial, no urgency
            "SHP003": "warning",    # electronics, moderate urgency
        },
        "incident_message": (
            "INCIDENT REPORT — Sandstorm — Jebel Ali Port Closure\n\n"
            "Port of Jebel Ali (AEJEA) has issued an immediate port closure due to severe "
            "sandstorm conditions. All berthing operations are suspended. Estimated closure "
            "duration: 48 hours.\n\n"
            "Vessels inbound to Jebel Ali requiring immediate assessment:\n"
            "  - SHP001 (MSC AURORA)      — ETA Jebel Ali: 18h\n"
            "  - SHP002 (EVER GIVEN II)   — ETA Jebel Ali: 24h\n"
            "  - SHP003 (MAERSK SENTOSA)  — ETA Jebel Ali: 36h\n\n"
            "Investigate each vessel and submit a recommendation. Vessels may require "
            "different actions depending on their cargo type and downstream dependencies."
        ),
        "port_overrides": {
            "AEJEA": {
                "congestion_level": 10,
                "weather_alert": "closure",
                "weather_detail": "Severe sandstorm (visibility <50m). Port Authority Order #2026-0410.",
                "berth_availability": False,
                "avg_wait_hours": 48,
                "forecast_clear_in_hours": 48,
                "anchorage_capacity": "Limited — 12 vessels already at anchorage",
            },
            "OMSLL": {
                "congestion_level": 2,
                "weather_alert": "none",
                "berth_availability": True,
                "avg_wait_hours": 3,
                "forecast_clear_in_hours": 0,
                "notes": "Salalah operating normally. Good capacity available.",
            },
        },
        "downstream_overrides": {
            "SHP001_48": {
                "factory_orders_at_risk": [
                    {
                        "order_id": "ORD-7741",
                        "customer": "Dubai Florist Group",
                        "cargo": "cut roses (perishable)",
                        "deadline_in_hours": 24,
                        "penalty_usd": 180_000,
                        "note": "Cargo spoils within 28h of departure. Complete loss if delay exceeds 24h.",
                    },
                    {
                        "order_id": "ORD-7742",
                        "customer": "Abu Dhabi Luxury Hotels",
                        "cargo": "mixed cut flowers (perishable)",
                        "deadline_in_hours": 36,
                        "penalty_usd": 60_000,
                        "note": "Floral arrangements for 3 hotel openings. Penalty + reorder cost.",
                    },
                ],
                "sla_breaches": 2,
                "total_penalty_usd": 240_000,
                "recommendation_urgency": "critical",
                "cascade_note": "Both downstream orders will be lost. Cargo spoilage is irreversible.",
            },
            "SHP002_48": {
                "factory_orders_at_risk": [],
                "sla_breaches": 0,
                "total_penalty_usd": 12_000,
                "recommendation_urgency": "low",
                "cascade_note": (
                    "Industrial machinery — no time-sensitive downstream dependencies. "
                    "Only a $12K late delivery fee applies. Customer has confirmed 72h flexibility."
                ),
            },
            "SHP003_48": {
                "factory_orders_at_risk": [
                    {
                        "order_id": "ORD-8801",
                        "customer": "Carrefour Gulf Region",
                        "cargo": "consumer electronics (smartphones)",
                        "deadline_in_hours": 60,
                        "penalty_usd": 95_000,
                        "note": "Retail shelf stocking for product launch. Penalty applies after 60h.",
                    }
                ],
                "sla_breaches": 1,
                "total_penalty_usd": 95_000,
                "recommendation_urgency": "medium",
                "cascade_note": "48h delay exceeds the 60h SLA window — penalty applies but cargo is undamaged.",
            },
        },
    },

    # ── 2. Customs hold at Singapore ──────────────────────────────────────────
    "customs_hold_singapore": {
        "title": "Customs Hold — Singapore",
        "affected_vessels": ["SHP004"],
        "observation_severity": {"SHP004": "critical"},
        "incident_message": (
            "INCIDENT REPORT — Customs Hold — Port of Singapore\n\n"
            "SHP004 (OOCL SINGAPORE) has been placed on customs hold at the Port of Singapore "
            "(SGSIN). Reason: Documentation discrepancy in the bill of lading — cargo manifest "
            "lists automotive parts; customs flagged a description mismatch. Clearance timeline "
            "is currently unknown.\n\n"
            "Vessel on hold:\n"
            "  - SHP004 (OOCL SINGAPORE) — currently berthed at SGSIN\n\n"
            "Investigate and determine the best course of action. Pay particular attention to "
            "any downstream dependencies on this cargo."
        ),
        "port_overrides": {
            "SGSIN": {
                "congestion_level": 5,
                "weather_alert": "none",
                "berth_availability": True,
                "avg_wait_hours": 12,
                "forecast_clear_in_hours": 0,
                "customs_status": "hold",
                "customs_hold_reason": "Bill of lading mismatch — cargo description inconsistency",
                "estimated_clearance_hours": None,
                "expedite_option": {
                    "available": True,
                    "cost_usd": 8_000,
                    "estimated_clearance_hours": 12,
                    "description": "Priority customs lane + documentation correction service",
                },
            },
        },
        "downstream_overrides": {
            "SHP004_24": {
                "factory_orders_at_risk": [
                    {
                        "order_id": "ORD-9910",
                        "customer": "Toyota Assembly Plant, Chennai",
                        "cargo": "brake caliper assemblies (critical component)",
                        "halt_in_hours": 72,
                        "daily_cost_usd": 200_000,
                        "note": "Assembly line halt if parts not received within 72h. Line produces 340 vehicles/day.",
                    },
                    {
                        "order_id": "ORD-9911",
                        "customer": "Toyota Assembly Plant, Chennai",
                        "cargo": "ABS sensor modules (critical component)",
                        "halt_in_hours": 72,
                        "daily_cost_usd": 0,
                        "note": "Same assembly line — both part types required simultaneously.",
                    },
                ],
                "sla_breaches": 1,
                "total_penalty_usd": 400_000,
                "recommendation_urgency": "high",
                "cascade_note": (
                    "Factory halt in 72h. Cost of inaction: $200K/day in lost production. "
                    "Expediting customs costs $8K. The cost asymmetry strongly favours expediting."
                ),
            },
        },
    },

    # ── 3. Carrier capacity drop ──────────────────────────────────────────────
    "carrier_capacity_drop": {
        "title": "Maersk Asia-Europe Capacity Reduction",
        "affected_vessels": ["SHP006", "SHP010"],
        "observation_severity": {
            "SHP006": "critical",   # pharma, high value
            "SHP010": "warning",    # bulk chemicals, low margin
        },
        "incident_message": (
            "INCIDENT REPORT — Carrier Capacity Drop\n\n"
            "Maersk Line has announced a 40% capacity reduction on the Asia-Europe lane "
            "effective immediately for the next 3 weeks, citing equipment rebalancing. "
            "Two of our upcoming shipments have confirmed Maersk bookings that are now at risk.\n\n"
            "Affected vessels:\n"
            "  - SHP006 (HAPAG BERLIN)   — pharmaceuticals, high value\n"
            "  - SHP010 (ZIM EXCELLENCE) — bulk chemicals, standard value\n\n"
            "Assess each vessel and determine whether to switch carriers or hold for "
            "the next available Maersk slot. Consider cargo value, urgency, and "
            "the cost of alternative carriers."
        ),
        "port_overrides": {},
        "downstream_overrides": {
            "SHP006_72": {
                "factory_orders_at_risk": [
                    {
                        "order_id": "ORD-6601",
                        "customer": "St. Mary's Hospital Network, UAE",
                        "cargo": "insulin (temperature-controlled)",
                        "halt_in_hours": 96,
                        "daily_cost_usd": 0,
                        "note": "Medical supply — regulatory SLA requires delivery within 5 days of departure.",
                    },
                    {
                        "order_id": "ORD-6602",
                        "customer": "Aster Pharmacy Chain",
                        "cargo": "oncology drugs",
                        "halt_in_hours": 120,
                        "daily_cost_usd": 0,
                        "note": "Patient prescription fulfilment — delay has direct patient impact.",
                    },
                ],
                "sla_breaches": 2,
                "total_penalty_usd": 330_000,
                "recommendation_urgency": "critical",
                "cascade_note": "Medical cargo with regulatory deadlines. A 72h delay breaches two SLAs.",
            },
            "SHP010_72": {
                "factory_orders_at_risk": [],
                "sla_breaches": 0,
                "total_penalty_usd": 18_000,
                "recommendation_urgency": "low",
                "cascade_note": (
                    "Bulk chemicals — customer has confirmed 2-week delivery flexibility. "
                    "Waiting for next Maersk slot (est. 10 days) is cheaper than switching carriers."
                ),
            },
        },
    },

    # ── 4. Cascade delay at Colombo ───────────────────────────────────────────
    "cascade_colombo": {
        "title": "Transhipment Delay — Colombo Hub",
        "affected_vessels": ["SHP005"],
        "observation_severity": {"SHP005": "warning"},
        "incident_message": (
            "INCIDENT REPORT — Transhipment Delay — Port of Colombo\n\n"
            "A labour dispute at the Port of Colombo (LKCMB) has caused a 6-hour delay "
            "to all transhipment operations. Dispute estimated to resolve within 6 hours.\n\n"
            "Directly affected vessel:\n"
            "  - SHP005 (CMA CGM MARCO POLO) — 6h delay at Colombo transhipment\n\n"
            "Note: This appears to be a minor delay. Please investigate thoroughly "
            "before dismissing — check whether any downstream shipments depend on "
            "cargo from this vessel."
        ),
        "port_overrides": {
            "LKCMB": {
                "congestion_level": 8,
                "weather_alert": "none",
                "berth_availability": True,
                "avg_wait_hours": 6,
                "forecast_clear_in_hours": 6,
                "labour_dispute": True,
                "dispute_resolution_hours": 6,
                "transhipment_queue_backlog_hours": 4,
            },
        },
        "downstream_overrides": {
            "SHP005_6": {
                "affected_shipments": [
                    {
                        "shipment_id": "SHP009",
                        "vessel_name": "EVERGREEN JADE",
                        "vessel_next_port": "LKCMB",
                        "delay_added_hours": 26,
                        "reason": (
                            "SHP009 is waiting at Colombo for transhipment cargo from SHP005. "
                            "The 6h delay pushes SHP009's departure past the Sri Lanka Customs "
                            "pre-clearance window (closes in 30h). The next available customs "
                            "slot is 26h later. A 6h delay becomes a 32h delay for SHP009."
                        ),
                        "customs_window_breach": True,
                        "customs_window_closes_in_hours": 30,
                    }
                ],
                "factory_orders_at_risk": [],
                "sla_breaches": 1,
                "total_penalty_usd": 45_000,
                "recommendation_urgency": "high",
                "cascade_note": (
                    "CRITICAL CASCADE: The 6h delay is not minor. It causes SHP009 to miss its "
                    "customs pre-clearance window, converting a 6h delay into a 32h delay for "
                    "the downstream vessel. Immediate action required to avoid the cascade."
                ),
            },
        },
    },
}
