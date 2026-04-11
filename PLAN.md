# Supply Chain Control Tower — Build Plan

## Time Budget (24 hours, 3 people)

| Role | Person | Frontend Hours | Backend Hours | Integration Hours |
|------|--------|---------------|---------------|-------------------|
| Python/Backend | BE | 0 | 10 | 2 |
| React/Frontend | FE | 16 | 0 | 2 |
| Full-stack + Design | FS | 8 | 2 | 6 |
| **Total** | | **24 (44%)** | **12 (22%)** | **10 (18%) + 6h buffer** |

**Rule: Backend is feature-frozen at H10. After H10, BE is on bug-fix and support only.**
**Rule: Every milestone ends with a smoke test. If it doesn't render, it didn't happen.**

---

## Milestones

### H0–H2 · Foundation (all 3 in parallel)

**BE — Backend scaffold**
- `pip install fastapi uvicorn anthropic pydantic python-dotenv websockets`
- `main.py`: FastAPI app, `/ws` WebSocket endpoint, `/health` REST endpoint
- `events.py`: Pydantic models for all 7 event types (copy schema from ARCHITECTURE.md exactly)
- `requirements.txt` committed
- ✅ Test: `curl localhost:8000/health` returns `{"status": "ok"}`

**FE — Frontend scaffold**
- `npm create vite@latest frontend -- --template react-ts`
- Install: `tailwindcss`, `shadcn/ui` (init), `react-leaflet`, `leaflet`, `recharts`, `lucide-react`
- Create layout skeleton: 3-panel grid (left: map placeholder, right: log panel placeholder, bottom: scenario buttons)
- Dark theme via Tailwind config
- ✅ Test: `npm run dev` renders a dark 3-panel layout, no errors in console

**FS — Repo + shared types**
- Create monorepo folder structure (see ARCHITECTURE.md)
- `frontend/src/types.ts`: All AgentEvent TypeScript types (copy from ARCHITECTURE.md exactly)
- `.gitignore`: node_modules, __pycache__, .env, *.pyc
- `.env.example`: `ANTHROPIC_API_KEY=`, `PORT=8000`
- ✅ Test: Both `npm run dev` and `uvicorn main:app` start without errors

---

### H2–H4 · Data layer (BE + FS parallel, FE builds map)

**BE — Simulator + seed data**
- `scenarios.py`: 11 vessel definitions (name, position, route, cargo_type, ETA, downstream_deps)
  - Include deliberate asymmetries: 2 perishable, 2 high-value electronics, 3 industrial, 2 bulk
  - 3 vessels positioned near Jebel Ali (for storm scenario)
  - 1 vessel at Singapore (for customs scenario)
- `simulator.py`: Background asyncio task, moves each vessel ~0.01° lat/lng every 3s, broadcasts `HeartbeatEvent` every 10s
- ✅ Test: Connect to ws://localhost:8000/ws, see heartbeat JSON every 10s

**FE — Map component**
- `MapView.tsx`: react-leaflet `MapContainer` centered on Indian Ocean / Gulf region
- Tile layer: OpenStreetMap (free, offline-capable — important for demo)
- Vessel markers with custom icons (color-coded by status: green/amber/red)
- Route polylines between current position and next port
- ✅ Test: Map renders 11 static vessel markers from hardcoded data

**FS — WebSocket hook**
- `hooks/useAgentSocket.ts`: connects to `ws://localhost:8000/ws`, parses JSON, appends to event queue state, reconnect logic (exponential backoff, max 5 retries)
- Pass vessel positions from socket events to `MapView`
- ✅ Test: Map vessel positions update when simulator moves them

---

### H4–H6 · Agent core + Log Panel (most critical chunk)

**BE — Agent loop + tools (ONE scenario working)**
- `tools.py`: Implement all 4 tools with mocked but realistic return data
  - `get_shipment_status`: returns from simulator state (live data)
  - `check_port_conditions`: mocked per port_code, returns congestion/weather
  - `get_alternative_routes`: mocked 2-3 routes with cost/time/reliability
  - `assess_downstream_impact`: mocked cascade data, includes factory halt scenarios
- `agent.py`: Claude API call with tool_use, agentic loop (observe → tool_calls → decide)
  - After each step: emit typed `AgentEvent` over WebSocket via broadcast()
  - System prompt: inject live fleet state, decision framework (see ARCHITECTURE.md)
  - Implement `asyncio.wait_for(timeout=30.0)` + fallback
- Wire `scenarios.py` scenario 1 (storm_jebel_ali) to `POST /events/trigger`
- ✅ Test: `POST /events/trigger {"scenario": "storm_jebel_ali"}` → see tool_call + tool_result + decision events in ws://localhost:8000/ws

**FE — Log Panel with typed renderers**
- `LogPanel/index.tsx`: scrollable panel, auto-scrolls to bottom on new event
- `HeartbeatRow.tsx`: single line, pulse animation, shows at_risk count, turns amber if brewing_risks non-empty
- `ObservationCard.tsx`: vessel name, severity badge (info/warning/critical), message, delay hours
- `ToolCallRow.tsx`: tool name + collapsed argument preview (expandable)
- `ToolResultRow.tsx`: tool name + collapsed result preview, duration_ms, success indicator
- `ExplanationBlock.tsx`: LLM prose, monospace or serif, subtle background
- `DecisionCard.tsx`: placeholder — full implementation in H6-H8
- ✅ Test: Manually paste mock events into a test harness, verify each renders correctly

**FS — Wire log panel to backend**
- Connect `useAgentSocket` events to `LogPanel`
- ✅ Test: Trigger scenario 1 from Postman/curl, watch log panel populate live

---

### H6–H8 · First full demo run (integration milestone)

**BE — All 4 scenarios + fallback**
- Wire scenarios 2, 3, 4 to `/events/trigger`
- `fallback.py`: Rule-based decisions for each scenario type, emit same event schema
- ✅ Test: All 4 scenario triggers produce valid event streams with no errors

**FE — DecisionCard complete + Scenario buttons**
- `DecisionCard.tsx` (full implementation):
  - Recommended action with action_type badge
  - Confidence meter (progress bar, color-coded: green >80%, amber 60-80%, red <60%)
  - `factors_considered` as small tag chips
  - Alternatives section: 2 rows, each with action + tradeoff text + lower confidence
  - "What if we don't act?" button (fires counterfactual request, placeholder for now)
- `ScenarioTriggers.tsx`: 4 styled buttons with scenario names + brief description
  - Each button shows a loading spinner while agent is running (disable during run)
- ✅ Test: Run all 4 scenarios. Every DecisionCard shows confidence score and 2 alternatives.

**FS — End-to-end integration test**
- Run all 4 scenarios back to back
- Verify: heartbeat pulses between events, log panel auto-scrolls, map updates during scenario
- Log any broken event types or rendering issues as a bug list
- Fix top 3 bugs before H8

---

### H8–H10 · Counterfactual + map animations (BE wraps up)

**BE — Counterfactual endpoint (last backend feature)**
- `POST /events/counterfactual {"shipment_id": "...", "delay_hours": N}`
- Runs shortened agent call or rule-based calc, returns `CounterfactualEvent`
- Emit over WebSocket + return in response body
- ✅ **Backend is now feature-frozen. No new endpoints after H10.**

**FE — Map animations + risk overlays**
- Vessel markers animate smoothly between position updates (lerp or CSS transition)
- At-risk vessels: pulsing amber ring around marker
- Port markers for the 4 demo ports (Jebel Ali, Singapore, Salalah, Colombo)
- When scenario fires, highlight the affected port with a red overlay
- ✅ Test: Storm scenario → Jebel Ali port turns red on map

**FS — Counterfactual panel UI**
- `CounterfactualPanel.tsx`: slides in below DecisionCard on button click
  - Shows: additional delay hours, cascade affected shipments, penalty USD, SLA breaches
  - Red background tone, "cost of inaction" header
  - Animate in (fade + slide)
- ✅ Test: Click "What if we don't act?" on a DecisionCard → panel appears with data

---

### H10–H14 · Frontend polish sprint (BE on bug-fix only)

**BE — Bug fixes only. No new features. Help FE/FS if blocked.**

**FE — Visual polish (4 hours, this is the demo)**
- Projector readiness: minimum 16px body font, 20px+ for key numbers, high contrast
- Scenario buttons: color-coded by severity (storm=orange, customs=blue, carrier=purple, cascade=red)
- Log panel: timestamp on every event (HH:MM:SS), smooth scroll animation
- Heartbeat row: subtle CSS pulse animation on the ◉ indicator
- FALLBACK MODE badge: yellow banner across top if system_status is "fallback"
- Reconnecting badge: animated spinner if WebSocket is reconnecting
- Empty state: before any scenario fires, log panel shows "Monitoring 11 vessels · System nominal" with a slow heartbeat
- ✅ Test: Screenshot the dashboard. Ask: "Would this read clearly on a projector at the back of a room?"

**FS — Final integration + polish**
- Decision card confidence meter: add a subtle animation when it first renders
- Map: fit bounds to show all vessels on load
- System status header bar: shows active vessel count, at-risk count, last agent run time
- ✅ Test: Run demo scenario 3 times end-to-end. Time each run (target: <45s from button click to full decision rendered)

---

### H14–H16 · Demo rehearsal (all 3 together)

- Run all 4 scenarios in sequence as if presenting to judges
- Time each scenario: observation → first tool call → decision should be <20s
- Identify the 2 most visually impressive moments and make sure they're reliable
- Write `DEMO_SCRIPT.md` together (see template below)
- Fix any rough edges found during rehearsal
- ✅ Test: 3 full clean demo runs with no crashes

---

### H16–H20 · Buffer + stretch (prioritized)

Priority 1: Fix anything that broke in rehearsal
Priority 2: `PROGRESS.md` updated
Priority 3 (stretch): Vercel/Railway deploy — only if H16-H18 is clean
Priority 4 (stretch): Add a simple line chart (Recharts) in the header showing cumulative delays over the session

---

### H20–H24 · Lockdown

- **No new features. No refactoring. Bug fixes only.**
- 3 final full demo runs
- Verify `.env` is not committed
- Verify the app starts cleanly from a fresh terminal with only `ANTHROPIC_API_KEY` set
- Prepare backup: screen recording of one clean demo run (insurance if laptop dies)
- Submit

---

## Top 3 Demo-Killing Risks

### Risk 1: Claude API latency ruins the live moment
The hero demo is judges watching the agent think in real time. If the API takes 15s to start streaming, the room goes quiet in a bad way.
- **Mitigation A:** 30s timeout + fallback (already in architecture). Judges won't know.
- **Mitigation B:** Pre-warm the connection — make a trivial API call 60s before your demo slot.
- **Mitigation C:** Have a screen recording of one perfect run as a backup. If API dies, play the recording and narrate live. Judges care about the concept, not live vs. recorded.

### Risk 2: Dashboard looks janky on a projector
Track 4 is a dashboard track. A polished UI with a mediocre backend beats a brilliant backend with a confusing UI. Projectors wash out colors, reduce contrast, and make small text illegible.
- **Mitigation A:** Dark theme (works better on projectors than white).
- **Mitigation B:** Test at 1280×720 (simulate projector resolution) during H10-H14.
- **Mitigation C:** Minimum 16px fonts everywhere. Key numbers (confidence %, delay hours, penalty USD) at 24px+.
- **Mitigation D:** During H10-H14, show a screenshot to someone not on the team and ask: "What does this do?" If they can't answer in 5 seconds, simplify.

### Risk 3: WebSocket drops mid-demo, blank screen
Conference rooms have unpredictable network environments, even for localhost apps. A crash during the hero moment is unrecoverable without a plan.
- **Mitigation A:** Everything runs on localhost — no dependency on WiFi once the app is started.
- **Mitigation B:** Reconnect logic already in architecture (exponential backoff, last 60s event replay).
- **Mitigation C:** Know the recovery procedure: Cmd+R (page reload) → WebSocket reconnects in <3s → backend replays recent events. Practice this during rehearsal so it's muscle memory.

---

## Time Allocation at a Glance

```
H0  ──── Foundation (all 3) ────────────────────────── H2
H2  ──── Data layer + Map ──────────────────────────── H4
H4  ──── Agent core + Log Panel ────────────────────── H6  ← most critical
H6  ──── First full demo run ───────────────────────── H8  ← must work by here
H8  ──── Counterfactual + map animations ───────────── H10
H10 ──── BACKEND FROZEN ────────────────────────────── 
H10 ──── Frontend polish sprint ────────────────────── H14 ← 40% of total time
H14 ──── Demo rehearsal ────────────────────────────── H16
H16 ──── Buffer + stretch ──────────────────────────── H20
H20 ──── Lockdown (no new features) ────────────────── H24
```

**Frontend hours by role:**
- FE: H0–H2 (setup) + H2–H10 (features) + H10–H14 (polish) = 14h
- FS: H2–H4 (hook) + H6–H8 (wire) + H8–H10 (counterfactual UI) + H10–H14 (integration polish) = 10h
- **Total frontend: 24h out of 58h active hours = 41%** ✓
