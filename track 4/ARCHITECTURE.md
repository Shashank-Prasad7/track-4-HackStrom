# Supply Chain Control Tower — Architecture

## System Overview

A single Claude agent with structured tool use, broadcasting typed events over WebSocket to a React dashboard. The agent runs in an async loop: it observes shipment state, calls tools to gather information, reasons across multiple factors, and emits discrete typed events at each step. The frontend renders each event type as a distinct UI component in a live log panel.

---

## Event Schema

Every message over the WebSocket is a typed `AgentEvent`. The frontend switches on `type` to render the correct component.

```typescript
// Shared types — replicate in backend/events.py (Pydantic) and frontend/types.ts

type EventType =
  | "observation"
  | "tool_call"
  | "tool_result"
  | "decision"
  | "explanation"
  | "heartbeat"
  | "counterfactual"
  | "system"

interface BaseEvent {
  id: string           // uuid4
  type: EventType
  timestamp: string    // ISO 8601
  session_id?: string  // links all events from one scenario trigger
}

interface ObservationEvent extends BaseEvent {
  type: "observation"
  shipment_id: string
  vessel_name: string
  severity: "info" | "warning" | "critical"
  message: string
  data: {
    position: { lat: number; lng: number }
    current_port?: string
    next_port: string
    eta_original: string    // ISO 8601
    eta_revised?: string    // ISO 8601
    delay_hours?: number
    cargo_type: string
    cargo_value_usd?: number
  }
}

interface ToolCallEvent extends BaseEvent {
  type: "tool_call"
  tool_name: string
  arguments: Record<string, unknown>
}

interface ToolResultEvent extends BaseEvent {
  type: "tool_result"
  tool_name: string
  result: Record<string, unknown>
  duration_ms: number
  success: boolean
}

interface DecisionEvent extends BaseEvent {
  type: "decision"
  shipment_id: string
  vessel_name: string
  recommended_action: string          // human-readable, e.g. "Reroute via Salalah"
  action_type: "reroute" | "vendor_switch" | "expedite" | "hold" | "notify" | "escalate"
  confidence: number                  // 0.0–1.0
  urgency: "low" | "medium" | "high" | "critical"
  reasoning_summary: string           // 1–2 sentence LLM summary
  factors_considered: string[]        // e.g. ["cargo perishability", "downstream dependency"]
  alternatives: Array<{
    action: string
    confidence: number
    tradeoff: string                  // why this wasn't picked
  }>
  estimated_cost_usd?: number
  estimated_time_saving_hours?: number
}

interface ExplanationEvent extends BaseEvent {
  type: "explanation"
  text: string     // LLM-generated prose, markdown supported, ~2–4 sentences
}

interface HeartbeatEvent extends BaseEvent {
  type: "heartbeat"
  active_shipments: number
  at_risk_count: number
  nominal_count: number
  system_status: "nominal" | "degraded" | "fallback"
  brewing_risks: Array<{
    shipment_id: string
    vessel_name: string
    risk_type: string
    eta_hours: number   // how soon this risk materializes
  }>
}

interface CounterfactualEvent extends BaseEvent {
  type: "counterfactual"
  trigger_shipment_id: string
  scenario_description: string
  projected_outcomes: {
    additional_delay_hours: number
    cascade_affected_shipments: number
    estimated_penalty_usd: number
    sla_breaches: number
    cargo_at_risk: Array<{ shipment_id: string; cargo_type: string; risk: string }>
  }
}

interface SystemEvent extends BaseEvent {
  type: "system"
  status: "agent_start" | "agent_end" | "fallback_activated" | "reconnected"
  message: string
}
```

---

## Tool Definitions

The agent makes **real** Claude tool-use API calls. Tools return mocked but structurally realistic data. Four tools — chosen so every demo scenario exercises at least two.

### Tool 1: `get_shipment_status`
```python
{
  "name": "get_shipment_status",
  "description": (
    "Get current position, ETA, cargo details, and risk flags for a specific shipment. "
    "Call this first when investigating any anomaly."
  ),
  "input_schema": {
    "type": "object",
    "properties": {
      "shipment_id": {"type": "string"},
      "include_cargo_manifest": {
        "type": "boolean",
        "default": False,
        "description": "Set true if cargo perishability or value is relevant to the decision"
      }
    },
    "required": ["shipment_id"]
  }
}
# Returns: position, eta_original, eta_revised, delay_hours, cargo_type,
#          cargo_value_usd, perishable, downstream_orders: [order_id, ...]
```

### Tool 2: `check_port_conditions`
```python
{
  "name": "check_port_conditions",
  "description": (
    "Get congestion level, active weather alerts, and berth availability for a port. "
    "Use before recommending a reroute to avoid sending ships into another bottleneck."
  ),
  "input_schema": {
    "type": "object",
    "properties": {
      "port_code": {
        "type": "string",
        "description": "UN/LOCODE e.g. AEJEA (Jebel Ali), SGSIN (Singapore), OMSLL (Salalah)"
      },
      "lookahead_hours": {
        "type": "integer",
        "default": 48,
        "description": "Forecast window in hours"
      }
    },
    "required": ["port_code"]
  }
}
# Returns: congestion_level (0–10), weather_alert (none/advisory/warning/closure),
#          berth_availability, avg_wait_hours, forecast_clear_in_hours
```

### Tool 3: `get_alternative_routes`
```python
{
  "name": "get_alternative_routes",
  "description": (
    "Get 2–3 ranked alternative routing options for a shipment, with cost, transit time, "
    "and reliability tradeoffs. Always call check_port_conditions on the proposed alternative "
    "port before finalizing a recommendation."
  ),
  "input_schema": {
    "type": "object",
    "properties": {
      "shipment_id": {"type": "string"},
      "avoid_ports": {
        "type": "array",
        "items": {"type": "string"},
        "description": "LOCODEs to exclude from routes"
      },
      "priority": {
        "type": "string",
        "enum": ["speed", "cost", "reliability"],
        "description": "Optimization target for ranking"
      }
    },
    "required": ["shipment_id", "priority"]
  }
}
# Returns: routes[] = { route_id, via_port, transit_days, cost_delta_usd,
#                       reliability_score, carrier_options: [name, available] }
```

### Tool 4: `assess_downstream_impact`
```python
{
  "name": "assess_downstream_impact",
  "description": (
    "Calculate cascade effects of a delay: which downstream shipments, factory orders, "
    "or SLA commitments are at risk. This is the most important tool — always call it "
    "before finalizing a decision to understand the true cost of inaction."
  ),
  "input_schema": {
    "type": "object",
    "properties": {
      "shipment_id": {"type": "string"},
      "delay_hours": {
        "type": "number",
        "description": "Projected additional delay to assess"
      },
      "include_financial_impact": {"type": "boolean", "default": True}
    },
    "required": ["shipment_id", "delay_hours"]
  }
}
# Returns: affected_shipments: [id, vessel, delay_added_hours],
#          factory_orders_at_risk: [order_id, halt_in_hours, daily_cost_usd],
#          sla_breaches: count, total_penalty_usd, recommendation_urgency
```

**Tool call sequence for a typical scenario:**
```
get_shipment_status(id, include_cargo_manifest=true)
  → check_port_conditions(current_port)
  → get_alternative_routes(id, avoid_ports=[blocked], priority="speed")
  → assess_downstream_impact(id, delay_hours=projected)
  → [emit DecisionEvent]
```

---

## Decision Quality — Prompt Strategy

### Why "if delayed > 2h, reroute" is wrong

A rule-based threshold ignores: cargo perishability, congestion at the alternative port, whether the delay crosses a downstream deadline boundary, and the cost asymmetry between action and inaction. The agent must surface these tradeoffs explicitly — that's what makes it agentic.

### System Prompt Structure

```
You are a supply chain operations agent monitoring a live fleet of 11 vessels.
Your job: when an event occurs, investigate, reason across multiple factors,
and recommend the best corrective action.

FLEET STATE (injected at session start, refreshed each heartbeat):
{full fleet JSON — all 11 shipments with position, ETA, cargo type, value,
 downstream order dependencies, current risk flags}

DECISION FRAMEWORK — consider ALL of these before recommending:
1. Cargo perishability — perishable cargo has zero tolerance for delay
2. Downstream dependency — does another shipment or factory order depend on this one?
3. Delay boundary crossing — does the delay push past a customs window, SLA cutoff, 
   or vessel booking deadline? A 5h delay that crosses a deadline is worse than a 20h
   delay that doesn't.
4. Alternative port congestion — never recommend rerouting into a congested port without
   calling check_port_conditions first
5. Cost asymmetry — compare rerouting cost vs. delay penalty + downstream impact
6. Weather window — if the blockage clears in <12h, holding may beat rerouting
7. Vendor reliability on the alternative lane — a cheaper route with an unreliable
   carrier may not be the right call

RESPONSE FORMAT:
- Use tools to gather data before deciding
- Emit an explanation event summarizing your reasoning
- Your confidence score must reflect genuine uncertainty — don't emit 0.95 if you
  haven't checked the alternative port conditions
- Always provide 2 alternatives with honest tradeoffs
- If two shipments are affected differently (e.g. different cargo types), recommend
  different actions for each — don't give a single blanket recommendation
```

### Making decisions non-obvious

The prompt seeds the fleet with deliberate asymmetries:
- Vessel A: perishable cargo (flowers), downstream factory halt in 48h → high urgency
- Vessel B: industrial parts, no downstream dependency, delay penalty is small → hold
- Vessel C: high-value electronics, multiple alternatives available → vendor switch preferred
- The agent must call `assess_downstream_impact` and reason about these differences to get a non-trivial result

---

## Scenario Triggers

Four scenarios. Each has different characteristics. The agent's recommendation depends on live fleet state — if a second vessel is already delayed when a scenario fires, the cascade is worse.

### Scenario 1: `storm_jebel_ali`
**Trigger:** Port of Jebel Ali (AEJEA) closed for 48h due to sandstorm
**Affected:** 3 inbound vessels at different stages
**Non-obvious element:** One carries perishables (urgent reroute), one carries machinery (hold is cheaper), one is already 12h delayed (rerouting now compounds losses vs. waiting for clearance)
**Expected tool calls:** `get_shipment_status` × 3, `check_port_conditions(AEJEA)`, `check_port_conditions(OMSLL)`, `get_alternative_routes` × 2, `assess_downstream_impact` × 2
**Decision differentiation:** Different actions for different vessels based on cargo type

### Scenario 2: `customs_hold_singapore`
**Trigger:** Vessel held at Singapore customs, documentation issue, unknown clearance time
**Affected:** 1 vessel directly, 1 downstream vessel waiting for transhipment
**Non-obvious element:** The direct vessel carries a critical component for a factory assembly line that halts in 72h. Expediting customs ($8K) vs. factory halt ($200K/day) — the math is obvious once surfaced, but the agent must call `assess_downstream_impact` to find the factory dependency
**Expected tool calls:** `get_shipment_status(include_cargo_manifest=true)`, `assess_downstream_impact`, `get_alternative_routes`

### Scenario 3: `carrier_capacity_drop`
**Trigger:** Maersk reduces Asia-Europe lane capacity 40% next 3 weeks, 5 upcoming shipments affected
**Affected:** Multiple future bookings
**Non-obvious element:** High-margin cargo → switch to MSC immediately (costs more but protects revenue). Low-margin cargo → wait for next Maersk slot. Mixed recommendation based on cargo value.
**Expected tool calls:** `get_shipment_status` × 5, `get_alternative_routes` (priority=cost) × 2, `get_alternative_routes` (priority=reliability) × 2

### Scenario 4: `cascade_colombo`
**Trigger:** 6-hour delay at Colombo transhipment hub (labor dispute)
**Affected:** Appears minor — only 1 vessel, only 6h
**Non-obvious element:** That 6h pushes one downstream shipment past a customs pre-clearance window (which closes at 48h), converting a 6h delay into a 32h delay for the downstream vessel. A judge watching the agent reason through this will see exactly why the "small delay" required urgent action.
**Expected tool calls:** `get_shipment_status`, `assess_downstream_impact(delay_hours=6)` → reveals customs window breach, then `get_alternative_routes`

---

## Failure Modes & Fallbacks

### Claude API Timeout
```python
async def run_agent_with_fallback(scenario, fleet_state, ws_broadcast):
    try:
        await asyncio.wait_for(
            run_claude_agent(scenario, fleet_state, ws_broadcast),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        await activate_fallback(scenario, fleet_state, ws_broadcast)
    except anthropic.APIError:
        await activate_fallback(scenario, fleet_state, ws_broadcast)
```

### Fallback Mode
- Pre-computed rule-based decisions for each scenario type (stored in `fallback_rules.py`)
- Decisions are structurally identical (same `DecisionEvent` schema) — UI renders normally
- Log panel shows a `SystemEvent` with `status: "fallback_activated"` and a yellow "FALLBACK MODE" badge
- `explanation` events use template strings, not LLM-generated prose
- The demo continues. Judges may not notice unless they're reading carefully.

### WebSocket Disconnect
- Frontend: exponential backoff reconnect (1s, 2s, 4s, max 5 retries)
- On reconnect: backend replays last 60s of events from in-memory buffer
- UI shows a "Reconnecting…" badge, not a blank screen

### Mid-stream Tool Failure
- If a tool call returns an error, agent logs a `ToolResultEvent` with `success: false`
- Agent prompt instructs: "if a tool fails, reason from available data and note the limitation in your explanation"
- Demo continues with partial data — the agent's transparency about uncertainty is actually a feature

---

## Demo-Critical UX Requirements

### (a) Confidence Score + Alternatives
Every `DecisionEvent` card in the UI must show:
- A confidence meter (e.g., `87% confidence`)
- The recommended action (highlighted)
- 2 alternatives with "why not picked" text
- Factors considered as tags (e.g., `cargo: perishable`, `downstream: factory halt`)

### (b) "What if we don't act?" Counterfactual Button
- Appears on every `DecisionEvent` card
- Fires `POST /events/counterfactual` with the shipment ID and current delay
- Backend triggers a second short agent run (or rule-based calc) to estimate cascade
- Returns a `CounterfactualEvent` with: additional delay hours, affected shipments, penalty USD, SLA breaches
- UI renders this as a red "cost of inaction" panel below the decision card

### (c) Heartbeat — System Feels Alive
- Backend emits a `HeartbeatEvent` every 10 seconds
- Log panel renders heartbeat as a subtle single-line pulse: `◉ 11 vessels active · 2 at risk · next ETA check in 8s`
- Between events, judges see the system is continuously watching
- If `brewing_risks` is non-empty, heartbeat line turns amber

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                            │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │   react-leaflet  │  │         Agent Log Panel              │ │
│  │   Map View       │  │  ┌──────────────────────────────┐   │ │
│  │                  │  │  │ HeartbeatRow (every 10s)     │   │ │
│  │  [vessel icons]  │  │  │ ObservationCard              │   │ │
│  │  [route lines]   │  │  │ ToolCallRow → ToolResultRow  │   │ │
│  │  [risk alerts]   │  │  │ ExplanationBlock             │   │ │
│  │                  │  │  │ DecisionCard + Alternatives  │   │ │
│  └──────────────────┘  │  │   └─ [What if we don't act?] │   │ │
│                         │  └──────────────────────────────┘   │ │
│  ┌──────────────────┐  └──────────────────────────────────────┘ │
│  │ Scenario Triggers│                                            │
│  │ [Storm Jebel Ali]│                                            │
│  │ [Customs Hold]   │                                            │
│  │ [Carrier Drop]   │                                            │
│  │ [Cascade]        │                                            │
│  └──────────────────┘                                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │ WebSocket (ws://localhost:8000/ws)
                              │ JSON AgentEvent stream
┌─────────────────────────────▼───────────────────────────────────┐
│                       FastAPI Backend                            │
│                                                                  │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  WebSocket    │  │  Shipment    │  │   Scenario          │  │
│  │  Manager      │  │  Simulator   │  │   Trigger API       │  │
│  │               │  │  (asyncio    │  │   POST /events/     │  │
│  │  broadcast()  │  │   loop, 3s)  │  │   trigger           │  │
│  └───────┬───────┘  └──────┬───────┘  └──────────┬──────────┘  │
│          │                 │                      │              │
│          └─────────────────▼──────────────────────┘             │
│                            │                                     │
│                    ┌───────▼────────┐                           │
│                    │  Agent Runner  │                            │
│                    │                │                            │
│                    │  run_agent()   │                            │
│                    │  ├ emit()      │  ◄── asyncio.wait_for     │
│                    │  └ fallback()  │       timeout=30s          │
│                    └───────┬────────┘                           │
│                            │                                     │
│                    ┌───────▼────────┐                           │
│                    │  Tool Router   │                            │
│                    │                │                            │
│                    │  get_shipment_ │                            │
│                    │  check_port_   │                            │
│                    │  get_alt_routes│                            │
│                    │  assess_impact │                            │
│                    └───────┬────────┘                           │
│                            │                                     │
│                    ┌───────▼────────┐                           │
│                    │  Claude API    │                            │
│                    │  (tool_use)    │                            │
│                    └────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
track4-supply-chain/
├── backend/
│   ├── main.py            # FastAPI app + WebSocket endpoint + REST routes
│   ├── agent.py           # Claude agent loop: observe → tool_call → decide → emit
│   ├── tools.py           # Tool implementations (mocked data, real signatures)
│   ├── simulator.py       # Shipment position simulator (background asyncio task)
│   ├── scenarios.py       # 4 scenario definitions + fleet seed data
│   ├── events.py          # Pydantic models for all AgentEvent types
│   ├── fallback.py        # Rule-based fallback decisions + template explanations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.tsx
│   │   │   ├── LogPanel/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── HeartbeatRow.tsx
│   │   │   │   ├── ObservationCard.tsx
│   │   │   │   ├── ToolCallRow.tsx
│   │   │   │   ├── DecisionCard.tsx       # confidence + alternatives + counterfactual btn
│   │   │   │   └── ExplanationBlock.tsx
│   │   │   ├── ScenarioTriggers.tsx
│   │   │   └── CounterfactualPanel.tsx
│   │   ├── hooks/
│   │   │   └── useAgentSocket.ts          # WebSocket conn + event queue + reconnect
│   │   ├── types.ts                       # All AgentEvent TypeScript types
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.js
├── ARCHITECTURE.md        ← this file
├── PLAN.md
├── DEMO_SCRIPT.md
└── PROGRESS.md
```

---

## Architecture Pitch (Memorize This)

> "We built a single orchestrating agent on Claude's tool-use API, not a rigid multi-agent pipeline. The agent has four tools — it checks shipment status, queries port conditions, evaluates alternative routes, and models downstream cascade impact. When an event fires, the agent decides which tools to call and in what order based on what it finds — that's the agentic behavior. The key insight is that every step of that reasoning is a structured typed event that streams to the dashboard in real time. Judges aren't looking at a terminal or a log file — they're watching the agent think. We deliberately kept it single-agent because adding more agents in 24 hours adds failure points without adding reasoning quality. The intelligence is in the prompt, the tools, and the event schema — not in the number of agents."

---

## What "Multi-Agent" Would Mean Here (For Q&A)

If a judge asks: *"Is this multi-agent?"*

Honest answer: *"No — it's a single agent with structured tool use, which we think is the right call for this problem. Multi-agent makes sense when you need parallel specialization — e.g., a dedicated pricing agent running concurrently with a routing agent. Our bottleneck is sequential reasoning quality, not parallelism. The named stages you see in the log — observation, tool investigation, impact assessment, decision — show the agent's reasoning depth. We can extend to multi-agent in production, but for a 24h demo, single-agent with four tools gives us more reliability and visibility."*
