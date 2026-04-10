// Shared AgentEvent types — mirrors backend/events.py exactly.
// Keep these in sync when adding new event fields.

export type EventType =
  | 'observation'
  | 'tool_call'
  | 'tool_result'
  | 'decision'
  | 'explanation'
  | 'heartbeat'
  | 'counterfactual'
  | 'system'

export interface BaseEvent {
  id: string
  type: EventType
  timestamp: string   // ISO 8601
  session_id?: string
}

// ── Shipment data ────────────────────────────────────────────────────────────

export interface ShipmentPosition {
  lat: number
  lng: number
}

export interface ShipmentData {
  position: ShipmentPosition
  current_port?: string
  next_port: string
  eta_original: string
  eta_revised?: string
  delay_hours?: number
  cargo_type: string
  cargo_value_usd?: number
}

export interface ObservationEvent extends BaseEvent {
  type: 'observation'
  shipment_id: string
  vessel_name: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  data: ShipmentData
}

// ── Tool call / result ────────────────────────────────────────────────────────

export interface ToolCallEvent extends BaseEvent {
  type: 'tool_call'
  tool_name: string
  arguments: Record<string, unknown>
}

export interface ToolResultEvent extends BaseEvent {
  type: 'tool_result'
  tool_name: string
  result: Record<string, unknown>
  duration_ms: number
  success: boolean
}

// ── Decision ──────────────────────────────────────────────────────────────────

export interface Alternative {
  action: string
  confidence: number
  tradeoff: string
}

export type ActionType = 'reroute' | 'vendor_switch' | 'expedite' | 'hold' | 'notify' | 'escalate'
export type Urgency = 'low' | 'medium' | 'high' | 'critical'

export interface DecisionEvent extends BaseEvent {
  type: 'decision'
  shipment_id: string
  vessel_name: string
  recommended_action: string
  action_type: ActionType
  confidence: number
  urgency: Urgency
  reasoning_summary: string
  factors_considered: string[]
  alternatives: Alternative[]
  estimated_cost_usd?: number
  estimated_time_saving_hours?: number
}

// ── Explanation ───────────────────────────────────────────────────────────────

export interface ExplanationEvent extends BaseEvent {
  type: 'explanation'
  text: string
}

// ── Heartbeat ─────────────────────────────────────────────────────────────────

export interface BrewingRisk {
  shipment_id: string
  vessel_name: string
  risk_type: string
  eta_hours: number
}

export interface HeartbeatEvent extends BaseEvent {
  type: 'heartbeat'
  active_shipments: number
  at_risk_count: number
  nominal_count: number
  system_status: 'nominal' | 'degraded' | 'fallback'
  brewing_risks: BrewingRisk[]
}

// ── Counterfactual ────────────────────────────────────────────────────────────

export interface CargoAtRisk {
  shipment_id: string
  cargo_type: string
  risk: string
}

export interface ProjectedOutcomes {
  additional_delay_hours: number
  cascade_affected_shipments: number
  estimated_penalty_usd: number
  sla_breaches: number
  cargo_at_risk: CargoAtRisk[]
}

export interface CounterfactualEvent extends BaseEvent {
  type: 'counterfactual'
  trigger_shipment_id: string
  scenario_description: string
  projected_outcomes: ProjectedOutcomes
}

// ── System ────────────────────────────────────────────────────────────────────

export interface SystemEvent extends BaseEvent {
  type: 'system'
  status: 'agent_start' | 'agent_end' | 'fallback_activated' | 'reconnected'
  message: string
}

// ── Union ─────────────────────────────────────────────────────────────────────

export type AgentEvent =
  | ObservationEvent
  | ToolCallEvent
  | ToolResultEvent
  | DecisionEvent
  | ExplanationEvent
  | HeartbeatEvent
  | CounterfactualEvent
  | SystemEvent

// ── Vessel state (from simulator, for map) ────────────────────────────────────

export interface VesselState {
  shipment_id: string
  vessel_name: string
  position: ShipmentPosition
  next_port: string
  current_port?: string
  cargo_type: string
  risk_level: 'nominal' | 'warning' | 'critical'
  eta_original: string
}
