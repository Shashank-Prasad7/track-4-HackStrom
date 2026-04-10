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

## H2–H4 · Data layer + Map · ⏳ Next

Tasks:
- BE: Full simulator background loop (vessel positions move every 3s)
- FE: react-leaflet MapView with 11 vessel markers
- FS: Connect map vessel positions to WebSocket events

---

## H4–H6 · Agent core + Log Panel · Pending
## H6–H8 · First full demo run · Pending
## H8–H10 · Counterfactual + map animations · Pending
## H10–H14 · Frontend polish sprint · Pending
## H14–H16 · Demo rehearsal · Pending
## H16–H20 · Buffer + stretch · Pending
## H20–H24 · Lockdown · Pending
