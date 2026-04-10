# Progress Log

## H0–H2 · Foundation ✅

**Completed:** All scaffold files written.

### Backend
- `main.py` — FastAPI app, `/ws` WebSocket, `/health`, `/events/trigger`, `/events/counterfactual`
- `events.py` — Pydantic models for all 7 event types
- `simulator.py` — 11-vessel fleet seed data + `get_fleet_state()` + `run_simulator()` stub
- `agent.py` — stubs for `run_agent_with_fallback` and `run_counterfactual_analysis`
- `requirements.txt`, `.env.example`

### Frontend
- Vite + React 18 + TypeScript + Tailwind CSS configured
- `types.ts` — all AgentEvent TypeScript types (mirrors backend exactly)
- `useAgentSocket.ts` — WebSocket hook with reconnect, event queue, vessel state
- `App.tsx` — dark 3-panel layout: header · map placeholder · log panel · scenario buttons
- All 4 scenario trigger buttons wired to `POST /events/trigger`
- Log panel renders all 7 event types (placeholder-quality, full polish in H4-H8)

### Smoke tests (run these now)
- [ ] `cd backend && pip install -r requirements.txt`
- [ ] `cp .env.example .env && echo ANTHROPIC_API_KEY=<your_key> >> .env`
- [ ] `uvicorn main:app --reload` → `curl localhost:8000/health` returns `{"status":"ok",...}`
- [ ] `cd frontend && npm install && npm run dev`
- [ ] Open `http://localhost:5173` → dark 3-panel layout, no console errors
- [ ] Connect to `ws://localhost:8000/ws` (use a WS client) → heartbeat JSON every 10s

---

## H2–H4 · Data layer + Map ✅

### Backend
- `simulator.py` — background loop moves all 11 vessels every 3s toward next port
- `simulator.py` — broadcasts `FleetSnapshotEvent` every 3s over WebSocket
- `events.py` — added `VesselSnapshot` + `FleetSnapshotEvent` models

### Frontend
- `types.ts` — added `FleetSnapshotEvent`, `VesselSnapshot`, updated `AgentEvent` union
- `useAgentSocket.ts` — handles `fleet_snapshot`: updates vessel map state, does NOT push to log panel
- `useAgentSocket.ts` — updates vessel risk level on `observation` events
- `components/MapView.tsx` — react-leaflet map with CartoDB dark tiles
  - 11 vessel `CircleMarker` components, color-coded by risk level (green/amber/red)
  - 4 port markers (Jebel Ali, Singapore, Colombo, Salalah) with permanent labels
  - Highlighted port turns red when a scenario fires (auto-clears after 30s)
  - Tooltips: vessel name, cargo type, next port, risk level
  - `FitBoundsOnLoad` fits all vessels into view on first data
- `App.tsx` — MapView wired with live vessel state + highlightedPort
- `index.css` — dark Leaflet tooltip styles

### Smoke tests (run these now)
- [ ] `uvicorn main:app --reload` — check WS broadcasts fleet_snapshot every 3s
- [ ] `npm run dev` — map renders with 11 vessel dots, vessels animate toward ports
- [ ] Click "Storm · Jebel Ali" — Jebel Ali port marker turns red on map

---

## H4–H6 · Agent core + Log Panel ✅

### Backend
- `scenarios.py` — 4 scenario definitions with incident messages, port overrides, and downstream impact data seeded for non-obvious differentiated decisions
- `tools.py` — 4 async tool implementations (get_shipment_status, check_port_conditions, get_alternative_routes, assess_downstream_impact) + submit_recommendation dispatcher; scenario-aware mocked data
- `agent.py` — full Claude tool-use loop (AsyncAnthropic, claude-sonnet-4-6):
  - Emits ObservationEvent per affected vessel at start
  - Emits ToolCallEvent + ToolResultEvent for each tool invocation
  - Emits ExplanationEvent for Claude's text reasoning
  - Emits DecisionEvent when submit_recommendation tool is called
  - 30s timeout handled by main.py; API errors fall to rule-based fallback
  - `run_counterfactual_analysis` implemented (fast, no LLM call)
  - `_FALLBACK_DECISIONS` covers all 4 scenarios

### Frontend
- `App.tsx` — DecisionCard now shows alternatives with confidence %, "What if we don't act?" button
- `App.tsx` — CounterfactualEvent renderer (red "Cost of Inaction" panel)
- `triggerCounterfactual` wired to POST /events/counterfactual

### Smoke tests (run these now)
- [ ] `uvicorn main:app --reload` starts without import errors
- [ ] `POST localhost:8000/events/trigger {"scenario": "storm_jebel_ali"}` → see events flow in WS
- [ ] Log panel shows: ObservationCard × 3, ToolCallRow, ToolResultRow, ExplanationBlock, DecisionCard × 3
- [ ] DecisionCard shows confidence bar, alternatives with %, "What if we don't act?" button
- [ ] Click "What if we don't act?" on a DecisionCard → red panel appears in log
## H6–H8 · First full demo run ✅

### Frontend
- `components/LogPanel.tsx` — extracted full component:
  - Auto-scroll to bottom on every new event (smooth)
  - Session dividers between scenario runs
  - Proper typed renderers for all 8 event types:
    - HeartbeatRow (compact, pulse animation, turns amber on brewing risks)
    - SystemRow (styled by status: sky/amber/gray)
    - ObservationCard (red/amber/gray by severity, with delay hours)
    - ToolCallRow (indigo, truncated argument preview)
    - ToolResultRow (✓/✗ + duration_ms)
    - ExplanationBlock (gray prose card)
    - DecisionCard (full: urgency dot, action badge, confidence bar, factors, alternatives with %, counterfactual button, cost estimates)
    - CounterfactualCard (red grid: delay, penalty, SLA breaches, cascade vessels)
- `App.tsx` — cleaned: EventRow removed, LogPanel imported, ~100 lines shorter

### Planning
- `DEMO_SCRIPT.md` — full 3-minute judge walkthrough with timing marks, Q&A prep, pre-demo checklist

### Smoke tests (run these now)
- [ ] All 4 scenarios trigger without errors
- [ ] Log panel auto-scrolls on each new event
- [ ] Session dividers appear between runs
- [ ] DecisionCard: confidence bar fills, alternatives show %, counterfactual button works
- [ ] CounterfactualCard: red panel with penalty numbers
- [ ] `npm run build` exits 0 (no TypeScript errors)
## H10–H14 · Frontend polish sprint ✅

### Frontend
- `useAgentSocket.ts` — exposes `systemStatus` ('ok' | 'fallback'), `lastAgentRunAt` (ISO string after agent completes)
- `App.tsx` — FALLBACK MODE amber banner when Claude API is unreachable; last agent run time (Clock icon) in header; active scenario button highlights only the running scenario
- `LogPanel.tsx` — HH:MM:SS timestamps on every event row; pulsing sky-blue left-border + "Live" dot while agent running; Clear log button (trash icon) in header; empty state with symmetric pulse dots; ObservationCard delay hours use proj-number
- `index.css` — proj-number bumped to 18px (projector-readable); proj-label to 13px

### Smoke tests
- [x] `npm run build` exits 0 (verified)
- [ ] Dashboard reads clearly on projected screen at back of room
- [ ] FALLBACK banner appears if API key is invalid
- [ ] Timestamps visible on every event
- [ ] Active scenario button highlights while agent is running
## H14–H16 · Demo rehearsal · Pending
## H16–H20 · Buffer + stretch · Pending
## H20–H24 · Lockdown · Pending
