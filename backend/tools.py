"""
Tool implementations for the Claude agent.
All data is mocked but structurally realistic.
Tools read the active scenario from scenarios.py to return context-appropriate data.
"""
from __future__ import annotations
import asyncio
import random
from scenarios import get_active_scenario

# ── Base port conditions (non-crisis baseline) ────────────────────────────────

_BASE_PORT_CONDITIONS: dict[str, dict] = {
    "AEJEA": {
        "port_name": "Jebel Ali, UAE",
        "congestion_level": 5,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 8,
        "forecast_clear_in_hours": 0,
        "notes": "Normal operations.",
    },
    "SGSIN": {
        "port_name": "Singapore",
        "congestion_level": 6,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 12,
        "forecast_clear_in_hours": 0,
        "notes": "Moderate congestion typical for this port.",
    },
    "LKCMB": {
        "port_name": "Colombo, Sri Lanka",
        "congestion_level": 4,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 6,
        "forecast_clear_in_hours": 0,
        "notes": "Normal operations.",
    },
    "OMSLL": {
        "port_name": "Salalah, Oman",
        "congestion_level": 2,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 3,
        "forecast_clear_in_hours": 0,
        "notes": "Low congestion. Good carrier availability.",
    },
    "OMMCT": {
        "port_name": "Muscat, Oman",
        "congestion_level": 3,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 6,
        "forecast_clear_in_hours": 0,
        "notes": "Normal operations. Fewer carrier options than Salalah.",
    },
}

# ── Alternative routes base data ──────────────────────────────────────────────

_ALTERNATIVE_ROUTES: dict[str, list[dict]] = {
    # Routes for vessels avoiding AEJEA
    "SHP001_avoid_AEJEA": [
        {
            "route_id": "RT-SHP001-A",
            "via_port": "OMSLL",
            "port_name": "Salalah, Oman",
            "transit_days_added": 2.0,
            "cost_delta_usd": 38_000,
            "reliability_score": 0.92,
            "carrier_options": [
                {"name": "MSC",    "available": True,  "cost_usd": 38_000},
                {"name": "Maersk", "available": True,  "cost_usd": 41_000},
            ],
            "notes": "Recommended. Salalah has low congestion and confirmed carrier availability.",
        },
        {
            "route_id": "RT-SHP001-B",
            "via_port": "OMMCT",
            "port_name": "Muscat, Oman",
            "transit_days_added": 3.5,
            "cost_delta_usd": 22_000,
            "reliability_score": 0.74,
            "carrier_options": [
                {"name": "Hapag-Lloyd", "available": True, "cost_usd": 22_000},
            ],
            "notes": "Lower cost but fewer carriers and lower reliability.",
        },
        {
            "route_id": "RT-SHP001-C",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali (anchorage wait)",
            "transit_days_added": 2.0,
            "cost_delta_usd": 4_500,
            "reliability_score": 0.95,
            "carrier_options": [],
            "notes": "Wait at anchorage until port reopens. Lowest cost but guarantees 48h delay.",
        },
    ],
    "SHP002_avoid_AEJEA": [
        {
            "route_id": "RT-SHP002-A",
            "via_port": "OMSLL",
            "port_name": "Salalah, Oman",
            "transit_days_added": 2.5,
            "cost_delta_usd": 42_000,
            "reliability_score": 0.91,
            "carrier_options": [
                {"name": "MSC", "available": True, "cost_usd": 42_000},
            ],
            "notes": "Viable but expensive for non-urgent cargo.",
        },
        {
            "route_id": "RT-SHP002-B",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali (anchorage wait)",
            "transit_days_added": 2.0,
            "cost_delta_usd": 4_500,
            "reliability_score": 0.95,
            "carrier_options": [],
            "notes": "Wait 48h. No downstream time pressure — most cost-effective option.",
        },
    ],
    "SHP003_avoid_AEJEA": [
        {
            "route_id": "RT-SHP003-A",
            "via_port": "OMSLL",
            "port_name": "Salalah, Oman",
            "transit_days_added": 2.0,
            "cost_delta_usd": 36_000,
            "reliability_score": 0.93,
            "carrier_options": [
                {"name": "MSC",   "available": True, "cost_usd": 36_000},
                {"name": "COSCO", "available": True, "cost_usd": 39_000},
            ],
            "notes": "Good option if SLA penalty exceeds rerouting cost.",
        },
        {
            "route_id": "RT-SHP003-B",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali (anchorage wait)",
            "transit_days_added": 2.0,
            "cost_delta_usd": 4_500,
            "reliability_score": 0.95,
            "carrier_options": [],
            "notes": "48h wait. 60h SLA window — this will breach the SLA.",
        },
    ],
    # Routes for carrier capacity drop scenarios
    "SHP006_vendor_switch": [
        {
            "route_id": "RT-SHP006-A",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali, UAE (same route)",
            "transit_days_added": 0,
            "cost_delta_usd": 28_000,
            "reliability_score": 0.91,
            "carrier_options": [
                {"name": "MSC",         "available": True, "cost_usd": 28_000},
                {"name": "CMA CGM",     "available": True, "cost_usd": 31_000},
            ],
            "notes": "Vendor switch on same route. MSC has confirmed capacity. +$28K vs Maersk.",
        },
        {
            "route_id": "RT-SHP006-B",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali (next Maersk slot)",
            "transit_days_added": 10.0,
            "cost_delta_usd": 0,
            "reliability_score": 0.85,
            "carrier_options": [
                {"name": "Maersk", "available": False, "next_slot_days": 10},
            ],
            "notes": "Wait 10 days for next Maersk slot. Free but 10-day delay.",
        },
    ],
    "SHP010_vendor_switch": [
        {
            "route_id": "RT-SHP010-A",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali, UAE (vendor switch)",
            "transit_days_added": 0,
            "cost_delta_usd": 31_000,
            "reliability_score": 0.88,
            "carrier_options": [
                {"name": "MSC", "available": True, "cost_usd": 31_000},
            ],
            "notes": "Switch to MSC. Same timeline but $31K premium.",
        },
        {
            "route_id": "RT-SHP010-B",
            "via_port": "AEJEA",
            "port_name": "Jebel Ali (next Maersk slot)",
            "transit_days_added": 10.0,
            "cost_delta_usd": 0,
            "reliability_score": 0.85,
            "carrier_options": [
                {"name": "Maersk", "available": False, "next_slot_days": 10},
            ],
            "notes": "Customer confirmed 2-week flexibility. Free option is viable.",
        },
    ],
}


# ── Tool dispatcher ───────────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict, fleet_state: dict) -> dict:
    """Dispatch to the correct tool implementation. All tools are async."""
    await asyncio.sleep(random.uniform(0.15, 0.45))  # simulated data fetch latency
    dispatch = {
        "get_shipment_status":    _get_shipment_status,
        "check_port_conditions":  _check_port_conditions,
        "get_alternative_routes": _get_alternative_routes,
        "assess_downstream_impact": _assess_downstream_impact,
        "submit_recommendation":  lambda a, f: {"status": "recommendation_recorded"},
    }
    fn = dispatch.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    return fn(args, fleet_state)


# ── Tool implementations ──────────────────────────────────────────────────────

def _get_shipment_status(args: dict, fleet_state: dict) -> dict:
    shipment_id = args.get("shipment_id", "")
    include_manifest = args.get("include_cargo_manifest", False)

    vessel = fleet_state.get(shipment_id)
    if not vessel:
        return {"error": f"Shipment {shipment_id} not found"}

    result: dict = {
        "shipment_id": shipment_id,
        "vessel_name": vessel["vessel_name"],
        "current_position": vessel["position"],
        "next_port": vessel["next_port"],
        "current_port": vessel.get("current_port"),
        "eta_original": vessel["eta_original"],
        "risk_level": vessel.get("risk_level", "nominal"),
    }

    if include_manifest:
        result["cargo_manifest"] = {
            "cargo_type": vessel["cargo_type"],
            "cargo_value_usd": vessel.get("cargo_value_usd"),
            "perishable": vessel.get("perishable", False),
            "downstream_orders": vessel.get("downstream_orders", []),
            "handling_requirements": (
                "Temperature-controlled (2–8°C). Time-critical."
                if vessel.get("perishable") else "Standard handling."
            ),
        }

    return result


def _check_port_conditions(args: dict, _fleet_state: dict) -> dict:
    port_code = args.get("port_code", "").upper()
    lookahead = args.get("lookahead_hours", 48)

    base = dict(_BASE_PORT_CONDITIONS.get(port_code, {
        "port_name": port_code,
        "congestion_level": 5,
        "weather_alert": "none",
        "berth_availability": True,
        "avg_wait_hours": 12,
        "notes": "No data available for this port.",
    }))
    base["lookahead_hours"] = lookahead

    # Apply scenario-specific overrides
    scenario = get_active_scenario()
    if scenario:
        overrides = scenario.get("port_overrides", {}).get(port_code)
        if overrides:
            base.update(overrides)

    return base


def _get_alternative_routes(args: dict, _fleet_state: dict) -> dict:
    shipment_id = args.get("shipment_id", "")
    priority = args.get("priority", "speed")
    avoid_ports: list[str] = [p.upper() for p in args.get("avoid_ports", [])]

    # Build lookup key
    avoid_str = "_avoid_" + avoid_ports[0] if avoid_ports else "_vendor_switch"
    key = f"{shipment_id}{avoid_str}"

    routes = list(_ALTERNATIVE_ROUTES.get(key, []))

    # Filter out explicitly avoided ports from results
    routes = [r for r in routes if r.get("via_port") not in avoid_ports or
              "anchorage" in r.get("notes", "").lower()]

    # Sort by priority
    if priority == "speed":
        routes.sort(key=lambda r: r["transit_days_added"])
    elif priority == "cost":
        routes.sort(key=lambda r: r["cost_delta_usd"])
    elif priority == "reliability":
        routes.sort(key=lambda r: -r["reliability_score"])

    if not routes:
        return {
            "routes": [],
            "note": f"No alternative routes found for {shipment_id} with given constraints.",
        }

    return {"routes": routes, "priority_used": priority}


def _assess_downstream_impact(args: dict, _fleet_state: dict) -> dict:
    shipment_id = args.get("shipment_id", "")
    delay_hours = float(args.get("delay_hours", 24))
    include_financial = args.get("include_financial_impact", True)

    scenario = get_active_scenario()
    if not scenario:
        return {
            "affected_shipments": [],
            "factory_orders_at_risk": [],
            "sla_breaches": 0,
            "total_penalty_usd": 0,
            "recommendation_urgency": "low",
        }

    # Find matching override key (rounded to nearest 6h)
    overrides = scenario.get("downstream_overrides", {})
    delay_bucket = int(round(delay_hours / 6) * 6)
    key = f"{shipment_id}_{delay_bucket}"

    # Try exact match, then fall back to closest
    data = overrides.get(key)
    if not data:
        for k, v in overrides.items():
            if k.startswith(shipment_id):
                data = v
                break

    if not data:
        return {
            "affected_shipments": [],
            "factory_orders_at_risk": [],
            "sla_breaches": 0,
            "total_penalty_usd": 0,
            "recommendation_urgency": "low",
            "note": f"No downstream dependencies found for {shipment_id}.",
        }

    result = dict(data)
    result["delay_assessed_hours"] = delay_hours
    if not include_financial:
        result.pop("total_penalty_usd", None)

    return result
