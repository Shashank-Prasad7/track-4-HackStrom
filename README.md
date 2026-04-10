# Tradewind

**Real-time AI supply chain control tower.**

A single Claude agent monitors a live fleet of 11 vessels across the Indian Ocean and Arabian Gulf. When a disruption fires — port closure, customs hold, carrier failure, cascade delay — the agent investigates with structured tool calls, reasons about downstream impact, and streams differentiated decisions to an operator dashboard in under 20 seconds.

Built for Hackstorm '26 · Track 4: Agentic Systems.

---

## What it does

```
Disruption fires
      │
      ▼
Agent observes affected vessels
      │
      ▼
Tool loop: get_shipment_status → check_port_conditions
         → get_alternative_routes → assess_downstream_impact
      │
      ▼
submit_recommendation (one per vessel — differentiated by cargo type, urgency, cost)
      │
      ▼
Typed events stream to dashboard over WebSocket
```

Every step — observation, tool call, tool result, reasoning, decision — appears as a live event in the log panel. Judges can watch the agent think.

---

## The key demo moment

Two vessels, same storm, different decisions:

| Vessel | Cargo | Decision | Reasoning |
|--------|-------|----------|-----------|
| MSC AURORA | Perishable flowers | **Reroute via Salalah** · $38K | Cargo spoils in 24h · $240K loss if inaction |
| EVER GIVEN II | Industrial machinery | **Hold at anchorage** · $4.5K | No downstream deps · reroute costs $42K for cargo that can wait |

Same disruption. Different answer. That's the judgement call.

---

## Tech stack

| Layer | Stack |
|-------|-------|
| Agent | Claude `claude-sonnet-4-6` · tool-use loop · 5 tools |
| Backend | FastAPI · AsyncIO WebSocket · Pydantic event schema |
| Frontend | React 18 · TypeScript · Tailwind CSS · react-leaflet · Recharts |
| Transport | WebSocket with reconnect + 50-event replay buffer |
| Fallback | Rule-based decisions, same event schema, 30s timeout |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Backend                      │
│                                                          │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────┐  │
│  │Simulator │──▶│ WebSocket  │◀──│   Claude Agent   │  │
│  │ 11 vessels│  │  Manager   │   │  (tool-use loop) │  │
│  └──────────┘   └────────────┘   └──────────────────┘  │
│                      │                    │              │
│               fleet_snapshot        typed events         │
│               (every 3s)            (streamed)           │
└──────────────────────┼────────────────────┘              
                       │                                    
                       ▼                                    
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                         │
│                                                          │
│  ┌─────────────────────┐   ┌──────────────────────────┐ │
│  │   MapView           │   │       LogPanel           │ │
│  │  · 11 vessel dots   │   │  · ObservationCard       │ │
│  │  · Dashed routes    │   │  · ToolCallRow           │ │
│  │  · Port hot ring    │   │  · ExplanationBlock      │ │
│  │  · Risk glow anim   │   │  · DecisionCard          │ │
│  └─────────────────────┘   │  · CounterfactualCard    │ │
│                             └──────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Scenario Buttons: Storm · Customs · Carrier · Cascade │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Features

- **Live vessel map** — 11 vessels on CartoDB dark tiles, colour-coded by risk level (green / amber / red), pulsing glow animations on at-risk vessels, dashed route polylines to next port
- **Typed event stream** — every agent action emits a structured event over WebSocket; log panel renders each type distinctly with HH:MM:SS timestamps
- **Differentiated decisions** — agent applies a 7-factor decision framework; same disruption produces different recommendations based on cargo type, downstream dependency, and cost asymmetry
- **Counterfactual panel** — "What if we don't act?" button triggers a fast rule-based calc; shows penalty estimate, cascade affected vessels, SLA breaches
- **Fallback mode** — 30s timeout; rule-based fallback fires with identical event schema; amber banner appears in UI; zero visible failure to judges
- **Live risk sparkline** — Recharts area chart in header tracking fleet risk over the last 24 heartbeats
- **Reconnect + replay** — WebSocket client reconnects with exponential backoff; backend replays last 50 events on reconnect

---

## Scenarios

| Scenario | Trigger | Key insight |
|----------|---------|-------------|
| **Storm · Jebel Ali** | 48h port closure · 3 vessels | Perishable vs industrial cargo → different decisions |
| **Customs Hold · Singapore** | Documentation hold | $8K expedite vs $200K/day factory halt |
| **Carrier Capacity Drop** | Maersk –40% capacity | Medical SLA → vendor switch; bulk chemicals → wait |
| **Cascade · Colombo** | 6h delay → customs window breach | 6h delay becomes 32h downstream — agent finds it |

---

## Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your Anthropic API key to .env
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Both servers must be running.

---

## Project structure

```
tradewind/
├── backend/
│   ├── main.py          # FastAPI app, WebSocket manager, /events/trigger
│   ├── agent.py         # Claude tool-use loop + rule-based fallback
│   ├── tools.py         # 4 async tool implementations
│   ├── scenarios.py     # 4 scenario definitions with seeded data
│   ├── simulator.py     # 11-vessel fleet, background movement loop
│   ├── events.py        # Pydantic models for all event types
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── MapView.tsx    # react-leaflet map with animations
│       │   └── LogPanel.tsx   # typed event renderers
│       ├── hooks/
│       │   └── useAgentSocket.ts  # WebSocket hook with reconnect
│       ├── App.tsx            # layout, scenario buttons, sparkline
│       └── types.ts           # TypeScript event types
├── ARCHITECTURE.md      # full system design
├── DEMO_SCRIPT.md       # 3-minute judge walkthrough
└── PLAN.md              # 24h milestone plan
```

---

## Environment variables

```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-...
PORT=8000                  # optional, default 8000
```

The app runs fully on `localhost` — no external network required after startup (tiles are cached, API key is the only external call).

---

*Hackstorm '26 — DeepFrog · Track 4: Agentic Systems*
