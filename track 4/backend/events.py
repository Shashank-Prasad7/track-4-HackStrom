from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from datetime import datetime, timezone
import uuid


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseEvent(BaseModel):
    id: str = Field(default_factory=_new_id)
    timestamp: str = Field(default_factory=_now_iso)
    session_id: Optional[str] = None


# ── Observation ──────────────────────────────────────────────────────────────

class ShipmentPosition(BaseModel):
    lat: float
    lng: float


class ShipmentData(BaseModel):
    position: ShipmentPosition
    current_port: Optional[str] = None
    next_port: str
    eta_original: str
    eta_revised: Optional[str] = None
    delay_hours: Optional[float] = None
    cargo_type: str
    cargo_value_usd: Optional[float] = None


class ObservationEvent(BaseEvent):
    type: Literal["observation"] = "observation"
    shipment_id: str
    vessel_name: str
    severity: Literal["info", "warning", "critical"]
    message: str
    data: ShipmentData


# ── Tool call / result ────────────────────────────────────────────────────────

class ToolCallEvent(BaseEvent):
    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: dict[str, Any]


class ToolResultEvent(BaseEvent):
    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    result: dict[str, Any]
    duration_ms: int
    success: bool


# ── Decision ─────────────────────────────────────────────────────────────────

class Alternative(BaseModel):
    action: str
    confidence: float
    tradeoff: str


class DecisionEvent(BaseEvent):
    type: Literal["decision"] = "decision"
    shipment_id: str
    vessel_name: str
    recommended_action: str
    action_type: Literal["reroute", "vendor_switch", "expedite", "hold", "notify", "escalate"]
    confidence: float
    urgency: Literal["low", "medium", "high", "critical"]
    reasoning_summary: str
    factors_considered: list[str]
    alternatives: list[Alternative]
    estimated_cost_usd: Optional[float] = None
    estimated_time_saving_hours: Optional[float] = None


# ── Explanation ───────────────────────────────────────────────────────────────

class ExplanationEvent(BaseEvent):
    type: Literal["explanation"] = "explanation"
    text: str


# ── Heartbeat ─────────────────────────────────────────────────────────────────

class BrewingRisk(BaseModel):
    shipment_id: str
    vessel_name: str
    risk_type: str
    eta_hours: float


class HeartbeatEvent(BaseEvent):
    type: Literal["heartbeat"] = "heartbeat"
    active_shipments: int
    at_risk_count: int
    nominal_count: int
    system_status: Literal["nominal", "degraded", "fallback"]
    brewing_risks: list[BrewingRisk] = []


# ── Counterfactual ────────────────────────────────────────────────────────────

class CargoAtRisk(BaseModel):
    shipment_id: str
    cargo_type: str
    risk: str


class ProjectedOutcomes(BaseModel):
    additional_delay_hours: float
    cascade_affected_shipments: int
    estimated_penalty_usd: float
    sla_breaches: int
    cargo_at_risk: list[CargoAtRisk]


class CounterfactualEvent(BaseEvent):
    type: Literal["counterfactual"] = "counterfactual"
    trigger_shipment_id: str
    scenario_description: str
    projected_outcomes: ProjectedOutcomes


# ── System ────────────────────────────────────────────────────────────────────

class SystemEvent(BaseEvent):
    type: Literal["system"] = "system"
    status: Literal["agent_start", "agent_end", "fallback_activated", "reconnected"]
    message: str
