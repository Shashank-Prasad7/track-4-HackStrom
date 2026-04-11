"""
Claude agent with tool-use loop.
Emits typed AgentEvents over WebSocket at each reasoning step.
"""
from __future__ import annotations
import asyncio
import json
import os
import time
from typing import Callable, Awaitable

import anthropic

from events import (
    ObservationEvent, ShipmentData, ShipmentPosition,
    ToolCallEvent, ToolResultEvent,
    DecisionEvent, Alternative,
    ExplanationEvent, SystemEvent, CounterfactualEvent,
    ProjectedOutcomes, CargoAtRisk,
)
from tools import execute_tool
from scenarios import get_scenario, set_active_scenario

# ── Client ────────────────────────────────────────────────────────────────────

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# ── Tool definitions (sent to Claude) ────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "get_shipment_status",
        "description": (
            "Get current position, ETA, cargo details, and risk flags for a shipment. "
            "Call this first when investigating any vessel. Use include_cargo_manifest=true "
            "when cargo perishability or value might affect the decision."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "include_cargo_manifest": {
                    "type": "boolean",
                    "default": False,
                    "description": "Set true if cargo type or perishability is relevant.",
                },
            },
            "required": ["shipment_id"],
        },
    },
    {
        "name": "check_port_conditions",
        "description": (
            "Get real-time congestion level, weather alerts, and berth availability for a port. "
            "Always call this before recommending a reroute to avoid sending vessels into "
            "another bottleneck."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "port_code": {
                    "type": "string",
                    "description": "UN/LOCODE. Examples: AEJEA (Jebel Ali), SGSIN (Singapore), OMSLL (Salalah), LKCMB (Colombo).",
                },
                "lookahead_hours": {
                    "type": "integer",
                    "default": 48,
                    "description": "Forecast window in hours.",
                },
            },
            "required": ["port_code"],
        },
    },
    {
        "name": "get_alternative_routes",
        "description": (
            "Get 2-3 ranked alternative routing options with cost, transit time, and "
            "reliability tradeoffs. Call check_port_conditions on the alternative port "
            "before finalising a reroute recommendation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "avoid_ports": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Port LOCODEs to exclude from route options.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["speed", "cost", "reliability"],
                    "description": "Optimisation target for ranking alternatives.",
                },
            },
            "required": ["shipment_id", "priority"],
        },
    },
    {
        "name": "assess_downstream_impact",
        "description": (
            "Calculate cascade effects: which downstream shipments, factory orders, "
            "or SLAs are at risk if this vessel is delayed. This is the most important "
            "tool — always call it before finalising a decision to understand the true "
            "cost of inaction."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "delay_hours": {
                    "type": "number",
                    "description": "Projected delay in hours to assess.",
                },
                "include_financial_impact": {"type": "boolean", "default": True},
            },
            "required": ["shipment_id", "delay_hours"],
        },
    },
    {
        "name": "submit_recommendation",
        "description": (
            "Submit your final recommendation for a vessel. Call this once per affected "
            "vessel after completing your investigation. Be honest about confidence — "
            "don't submit 0.95 if you haven't checked all relevant factors."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "vessel_name": {"type": "string"},
                "recommended_action": {
                    "type": "string",
                    "description": "Human-readable action, e.g. 'Reroute via Salalah (OMSLL) with MSC'.",
                },
                "action_type": {
                    "type": "string",
                    "enum": ["reroute", "vendor_switch", "expedite", "hold", "notify", "escalate"],
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Your confidence in this recommendation (0.0–1.0).",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "reasoning_summary": {
                    "type": "string",
                    "description": "1–2 sentence summary of the key reasoning.",
                },
                "factors_considered": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of factors that influenced this decision.",
                },
                "alternatives": {
                    "type": "array",
                    "description": "Exactly 2 alternatives with honest tradeoffs.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "confidence": {"type": "number"},
                            "tradeoff": {"type": "string"},
                        },
                        "required": ["action", "confidence", "tradeoff"],
                    },
                },
                "estimated_cost_usd": {"type": "number"},
                "estimated_time_saving_hours": {"type": "number"},
            },
            "required": [
                "shipment_id", "vessel_name", "recommended_action",
                "action_type", "confidence", "urgency",
                "reasoning_summary", "factors_considered", "alternatives",
            ],
        },
    },
]


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt(fleet_state: dict) -> str:
    fleet_summary = json.dumps(
        {
            sid: {
                "vessel_name": v["vessel_name"],
                "next_port": v["next_port"],
                "cargo_type": v["cargo_type"],
                "perishable": v.get("perishable", False),
                "downstream_orders": v.get("downstream_orders", []),
                "risk_level": v.get("risk_level", "nominal"),
            }
            for sid, v in fleet_state.items()
        },
        indent=2,
    )

    return f"""You are an expert supply chain operations agent monitoring a live global freight fleet.

CURRENT FLEET STATE:
{fleet_summary}

DECISION FRAMEWORK — you must consider ALL of these before submitting a recommendation:

1. CARGO PERISHABILITY — perishable cargo (flowers, pharmaceuticals, food) has zero delay tolerance. Prioritise these vessels.
2. DOWNSTREAM DEPENDENCY — always call assess_downstream_impact before deciding. A 6h delay can halt a factory. The cost of inaction is often far higher than the cost of action.
3. DELAY BOUNDARY CROSSING — a delay that crosses a customs window, SLA deadline, or cargo spoilage threshold is categorically worse than one that doesn't. Check for boundary effects.
4. ALTERNATIVE PORT CONGESTION — never recommend rerouting without first calling check_port_conditions on the destination. You may be sending a vessel into a worse situation.
5. COST ASYMMETRY — compare rerouting cost vs (delay penalty + downstream impact). A $40K reroute that avoids a $240K loss is obvious. Surface this maths explicitly.
6. DISRUPTION WINDOW — if the disruption clears in <12h, holding may beat rerouting. Factor in the forecast_clear_in_hours.
7. DIFFERENTIATED RECOMMENDATIONS — if multiple vessels are affected, they may need different actions based on cargo type, deadline pressure, and downstream dependencies. Do not give a blanket recommendation.

INVESTIGATION PROTOCOL for each affected vessel:
1. get_shipment_status (with include_cargo_manifest=true)
2. check_port_conditions on the affected port
3. get_alternative_routes (pick priority based on urgency)
4. assess_downstream_impact (always — this is the most critical step)
5. submit_recommendation

Your confidence score must reflect genuine uncertainty. Low confidence if you see conflicting signals or haven't checked all factors. Provide exactly 2 alternatives with honest tradeoffs.
"""


# ── Agent entry point ─────────────────────────────────────────────────────────

async def run_agent_with_fallback(
    scenario_name: str,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None = None,
) -> None:
    scenario = get_scenario(scenario_name)
    if not scenario:
        await broadcast(SystemEvent(
            session_id=session_id,
            status="fallback_activated",
            message=f"Unknown scenario: {scenario_name}",
        ).model_dump())
        return

    set_active_scenario(scenario_name)

    try:
        await _run_claude_agent(scenario, fleet_state, broadcast, session_id)
    except anthropic.APIError as e:
        await broadcast(SystemEvent(
            session_id=session_id,
            status="fallback_activated",
            message=f"Claude API error: {type(e).__name__}. Activating rule-based fallback.",
        ).model_dump())
        await _run_fallback(scenario, fleet_state, broadcast, session_id)
    finally:
        set_active_scenario(None)


# ── Core agent loop ───────────────────────────────────────────────────────────

async def _run_claude_agent(
    scenario: dict,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None,
) -> None:
    client = _get_client()

    # Emit observation events for each affected vessel
    for vessel_id in scenario["affected_vessels"]:
        vessel = fleet_state.get(vessel_id)
        if not vessel:
            continue
        severity = scenario.get("observation_severity", {}).get(vessel_id, "warning")
        await broadcast(ObservationEvent(
            session_id=session_id,
            shipment_id=vessel_id,
            vessel_name=vessel["vessel_name"],
            severity=severity,
            message=f"Affected by {scenario['title']}",
            data=ShipmentData(
                position=ShipmentPosition(**vessel["position"]),
                next_port=vessel["next_port"],
                current_port=vessel.get("current_port"),
                eta_original=vessel["eta_original"],
                cargo_type=vessel["cargo_type"],
                cargo_value_usd=vessel.get("cargo_value_usd"),
            ),
        ).model_dump())
        await asyncio.sleep(0.4)

    # Build initial conversation
    system_prompt = _build_system_prompt(fleet_state)
    messages: list[dict] = [
        {"role": "user", "content": scenario["incident_message"]}
    ]

    # Tool-use loop (max 12 iterations as safety guard)
    for _ in range(12):
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        tool_results: list[dict] = []

        for block in response.content:
            if block.type == "text" and block.text.strip():
                await broadcast(ExplanationEvent(
                    session_id=session_id,
                    text=block.text.strip(),
                ).model_dump())
                await asyncio.sleep(0.3)

            elif block.type == "tool_use":
                # Emit tool call
                await broadcast(ToolCallEvent(
                    session_id=session_id,
                    tool_name=block.name,
                    arguments=block.input,
                ).model_dump())
                await asyncio.sleep(0.3)

                # Execute tool (async, with simulated latency)
                t0 = time.monotonic()
                result = await execute_tool(block.name, block.input, fleet_state)
                duration_ms = int((time.monotonic() - t0) * 1000)

                # If this is a recommendation, also emit a DecisionEvent
                if block.name == "submit_recommendation":
                    try:
                        alts = [
                            Alternative(**a) for a in block.input.get("alternatives", [])
                        ]
                        decision = DecisionEvent(
                            session_id=session_id,
                            shipment_id=block.input["shipment_id"],
                            vessel_name=block.input["vessel_name"],
                            recommended_action=block.input["recommended_action"],
                            action_type=block.input["action_type"],
                            confidence=float(block.input["confidence"]),
                            urgency=block.input["urgency"],
                            reasoning_summary=block.input["reasoning_summary"],
                            factors_considered=block.input.get("factors_considered", []),
                            alternatives=alts,
                            estimated_cost_usd=block.input.get("estimated_cost_usd"),
                            estimated_time_saving_hours=block.input.get("estimated_time_saving_hours"),
                        )
                        await broadcast(decision.model_dump())
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass  # malformed input — continue loop

                # Emit tool result
                await broadcast(ToolResultEvent(
                    session_id=session_id,
                    tool_name=block.name,
                    result=result if isinstance(result, dict) else {"data": str(result)},
                    duration_ms=duration_ms,
                    success="error" not in result,
                ).model_dump())
                await asyncio.sleep(0.25)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        # Done when Claude stops calling tools
        if response.stop_reason == "end_turn":
            break

        if tool_results:
            messages.append({"role": "user", "content": tool_results})


# ── Rule-based fallback ───────────────────────────────────────────────────────

_FALLBACK_DECISIONS: dict[str, list[dict]] = {
    "storm_jebel_ali": [
        {
            "shipment_id": "SHP001", "vessel_name": "MSC AURORA",
            "recommended_action": "Reroute via Salalah (OMSLL) — perishable cargo",
            "action_type": "reroute", "confidence": 0.91, "urgency": "critical",
            "reasoning_summary": "Perishable cargo will spoil before port reopens. Rerouting via Salalah avoids $240K loss.",
            "factors_considered": ["cargo perishability", "downstream deadline", "Salalah availability"],
            "alternatives": [
                {"action": "Hold at anchorage", "confidence": 0.12, "tradeoff": "Cargo spoils before port reopens"},
                {"action": "Reroute via Muscat", "confidence": 0.44, "tradeoff": "Cheaper but less reliable carrier"},
            ],
        },
        {
            "shipment_id": "SHP002", "vessel_name": "EVER GIVEN II",
            "recommended_action": "Hold at anchorage — wait for port reopening",
            "action_type": "hold", "confidence": 0.88, "urgency": "low",
            "reasoning_summary": "Industrial machinery with no downstream dependencies. $4.5K anchorage fee is far cheaper than $42K rerouting cost.",
            "factors_considered": ["cargo type (non-perishable)", "no downstream orders", "cost asymmetry"],
            "alternatives": [
                {"action": "Reroute via Salalah", "confidence": 0.45, "tradeoff": "$42K cost for cargo with no urgency"},
                {"action": "Reroute via Muscat", "confidence": 0.30, "tradeoff": "Cheaper but still unnecessary for this cargo"},
            ],
        },
    ],
    "customs_hold_singapore": [
        {
            "shipment_id": "SHP004", "vessel_name": "OOCL SINGAPORE",
            "recommended_action": "Expedite customs clearance — pay priority lane fee",
            "action_type": "expedite", "confidence": 0.95, "urgency": "high",
            "reasoning_summary": "Factory halt in 72h costs $200K/day. Priority clearance costs $8K. Cost asymmetry strongly favours expediting.",
            "factors_considered": ["factory halt risk", "cost asymmetry ($8K vs $200K/day)", "clearance timeline"],
            "alternatives": [
                {"action": "Wait for standard clearance", "confidence": 0.08, "tradeoff": "Unknown timeline — factory halt likely"},
                {"action": "Source alternative parts", "confidence": 0.25, "tradeoff": "Slower and more expensive than expediting"},
            ],
        },
    ],
    "carrier_capacity_drop": [
        {
            "shipment_id": "SHP006", "vessel_name": "HAPAG BERLIN",
            "recommended_action": "Switch to MSC — same route, confirmed capacity",
            "action_type": "vendor_switch", "confidence": 0.89, "urgency": "critical",
            "reasoning_summary": "Medical cargo with regulatory SLA. $28K vendor switch avoids $330K in SLA penalties.",
            "factors_considered": ["medical SLA deadlines", "cost asymmetry", "MSC availability"],
            "alternatives": [
                {"action": "Wait for Maersk next slot (10 days)", "confidence": 0.11, "tradeoff": "10-day delay breaches medical SLAs"},
                {"action": "Switch to CMA CGM", "confidence": 0.55, "tradeoff": "$31K vs $28K for MSC, similar reliability"},
            ],
        },
        {
            "shipment_id": "SHP010", "vessel_name": "ZIM EXCELLENCE",
            "recommended_action": "Hold for next Maersk slot in 10 days",
            "action_type": "hold", "confidence": 0.82, "urgency": "low",
            "reasoning_summary": "Bulk chemicals with 2-week customer flexibility. Waiting is free; vendor switch costs $31K unnecessarily.",
            "factors_considered": ["customer flexibility", "no downstream urgency", "cost of switching vs holding"],
            "alternatives": [
                {"action": "Switch to MSC now", "confidence": 0.45, "tradeoff": "$31K cost for cargo that can wait"},
                {"action": "Partial shipment via MSC", "confidence": 0.30, "tradeoff": "Complexity not justified by urgency"},
            ],
        },
    ],
    "cascade_colombo": [
        {
            "shipment_id": "SHP005", "vessel_name": "CMA CGM MARCO POLO",
            "recommended_action": "Expedite transhipment — priority dock allocation",
            "action_type": "expedite", "confidence": 0.87, "urgency": "high",
            "reasoning_summary": "6h delay triggers cascade: SHP009 misses customs window, becoming a 32h delay. Expediting avoids $45K penalty.",
            "factors_considered": ["customs window breach", "cascade to SHP009", "dispute resolution timeline"],
            "alternatives": [
                {"action": "Wait for labour dispute resolution (6h)", "confidence": 0.40, "tradeoff": "SHP009 misses customs window — 32h cascade delay"},
                {"action": "Reroute SHP009 to alternative port", "confidence": 0.35, "tradeoff": "SHP009 can't reroute mid-voyage without major cost"},
            ],
        },
    ],
}


async def _run_fallback(
    scenario: dict,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None,
) -> None:
    """Emit pre-canned decisions matching the full DecisionEvent schema."""
    scenario_name = next(
        (k for k, v in _FALLBACK_DECISIONS.items() if v),
        None
    )
    # Find which scenario we're running by matching affected vessels
    for name, decisions in _FALLBACK_DECISIONS.items():
        vessel_ids = {d["shipment_id"] for d in decisions}
        if vessel_ids & set(scenario.get("affected_vessels", [])):
            scenario_name = name
            break

    decisions = _FALLBACK_DECISIONS.get(scenario_name or "", [])
    for d in decisions:
        await asyncio.sleep(1.0)
        vessel = fleet_state.get(d["shipment_id"], {})
        await broadcast(ObservationEvent(
            session_id=session_id,
            shipment_id=d["shipment_id"],
            vessel_name=d["vessel_name"],
            severity="warning",
            message="[FALLBACK MODE] Rule-based assessment",
            data=ShipmentData(
                position=ShipmentPosition(**vessel.get("position", {"lat": 0, "lng": 0})),
                next_port=vessel.get("next_port", ""),
                eta_original=vessel.get("eta_original", ""),
                cargo_type=vessel.get("cargo_type", "unknown"),
            ),
        ).model_dump())
        await asyncio.sleep(0.5)

        alts = [Alternative(**a) for a in d["alternatives"]]
        await broadcast(DecisionEvent(
            session_id=session_id,
            shipment_id=d["shipment_id"],
            vessel_name=d["vessel_name"],
            recommended_action=d["recommended_action"],
            action_type=d["action_type"],
            confidence=d["confidence"],
            urgency=d["urgency"],
            reasoning_summary=d["reasoning_summary"],
            factors_considered=d["factors_considered"],
            alternatives=alts,
        ).model_dump())


# ── Counterfactual analysis ───────────────────────────────────────────────────

async def run_counterfactual_analysis(
    shipment_id: str,
    delay_hours: float,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None = None,
) -> None:
    """
    Rule-based counterfactual: what happens if we don't act?
    Runs fast — no LLM call, just applies downstream impact data.
    """
    result = await execute_tool(
        "assess_downstream_impact",
        {"shipment_id": shipment_id, "delay_hours": delay_hours},
        fleet_state,
    )

    vessel = fleet_state.get(shipment_id, {})
    cascade_note = result.get("cascade_note", "No cascade effects identified.")

    cargo_at_risk = [
        CargoAtRisk(
            shipment_id=o.get("shipment_id", shipment_id),
            cargo_type=o.get("cargo", vessel.get("cargo_type", "unknown")),
            risk=o.get("note", o.get("reason", "delay risk")),
        )
        for o in (
            result.get("factory_orders_at_risk", []) +
            result.get("affected_shipments", [])
        )
    ]

    event = CounterfactualEvent(
        session_id=session_id,
        trigger_shipment_id=shipment_id,
        scenario_description=f"If no action taken: {delay_hours:.0f}h delay on {vessel.get('vessel_name', shipment_id)}",
        projected_outcomes=ProjectedOutcomes(
            additional_delay_hours=float(delay_hours),
            cascade_affected_shipments=len(result.get("affected_shipments", [])),
            estimated_penalty_usd=float(result.get("total_penalty_usd", 0)),
            sla_breaches=int(result.get("sla_breaches", 0)),
            cargo_at_risk=cargo_at_risk,
        ),
    )
    await broadcast(event.model_dump())
