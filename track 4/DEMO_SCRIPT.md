# Demo Script — 3-Minute Judge Walkthrough

**Setup before judges arrive:**
- Both servers running: `uvicorn main:app --reload` + `npm run dev`
- Browser open at `http://localhost:5173`, fullscreen, map already loaded
- All 11 vessel dots visible on the map, gently moving
- Log panel shows heartbeat pulse (the ◉ indicator)
- Practice this script 3× minimum before presenting

---

## T+0:00 — Open (15 seconds)

*Point to the dashboard.*

> "This is a real-time supply chain control tower. What you're looking at are 11 live vessels across the Indian Ocean and Arabian Gulf — each one is moving, each one has cargo, and each one has downstream dependencies: factories waiting, SLAs ticking.
>
> The system is continuously evaluating fleet state. You can see that pulse in the log panel — that's the agent checking in every 10 seconds. Nothing is waiting for someone to click a button."

*Let the heartbeat pulse once. Then:*

---

## T+0:15 — Set up the scenario (20 seconds)

*Point to the scenario buttons at the bottom.*

> "We have four real-world disruptions we can trigger. I'm going to show you the most complex one: a sandstorm that closes the Port of Jebel Ali for 48 hours. Three of our vessels are inbound. Watch what happens."

*Click **Storm · Jebel Ali**.*

*Jebel Ali port marker turns red on the map.*

---

## T+0:35 — Agent reasoning (60 seconds — the hero moment)

*Watch the log panel. Narrate as events appear.*

> "The agent immediately flags all three affected vessels — you can see the observations pop in."

*ObservationCards appear.*

> "Now watch the tools. The agent isn't guessing — it's calling our port conditions API to confirm the closure, then checking alternative routes, then — this is the critical step — it calls `assess_downstream_impact` for each vessel."

*Tool calls appear. Slow down here.*

> "This is where it gets interesting."

*Wait for the first DecisionCard to appear.*

> "MSC AURORA is carrying **perishable flowers** — downstream orders expire in 24 hours. The agent recommends an immediate reroute via Salalah. **87% confidence.**"

*Scroll or wait for the second DecisionCard.*

> "But EVER GIVEN II is carrying industrial machinery with no downstream dependencies. The agent recommends **holding at anchorage** — because rerouting costs $42K for cargo that can wait 48 hours. Same storm, different decision. That's the judgement call."

*Pause for effect.*

---

## T+1:35 — Counterfactual (25 seconds)

*Click "What if we don't act?" on MSC AURORA's decision card.*

> "Judges always ask: what's the cost of inaction? We built that in. If we do nothing — $240,000 in penalties and spoiled cargo. The reroute costs $38,000. The agent surfaced that maths without being asked."

*Red panel slides in.*

---

## T+2:00 — Other scenarios (30 seconds)

*Point to the other three buttons, don't trigger them (time).*

> "We have three more scenarios. Customs hold in Singapore — the agent discovers a $200K/day factory halt and recommends an $8K expedite. Carrier capacity drop — it differentiates between pharmaceutical cargo that needs an immediate vendor switch and bulk chemicals that can wait. And a cascade scenario where a 6-hour delay at Colombo crosses a customs pre-clearance window and becomes a 32-hour delay downstream — the agent finds that."

---

## T+2:30 — Architecture pitch (25 seconds)

> "Under the hood: a single Claude agent on the tool-use API. Four tools — shipment status, port conditions, alternative routes, downstream impact. Every tool call, every reasoning step, every decision streams to this panel as a typed event. The track asks for continuous state evaluation, action triggering, and agentic log trace. That's exactly what you're watching."

---

## T+2:55 — Close (5 seconds)

> "Thank you."

---

## Q&A Prep

**"Is this multi-agent?"**
> "No — it's a single agent with structured tool use. Multi-agent adds latency and failure points. Our bottleneck is reasoning quality, not parallelism. The named stages you see — observation, investigation, decision — show the depth of reasoning, not separate agents."

**"Is the data real?"**
> "Vessel positions and fleet state are simulated — real-world data would come from AIS feeds and TMS APIs. The tool calls and reasoning are live: every tool invocation you saw was a real Claude API call returning structured data."

**"What if the API fails mid-demo?"**
> "30-second timeout with a rule-based fallback. Same event schema, same UI — the log panel shows a FALLBACK badge. We built that in because conference demos are adversarial."

**"How does it scale?"**
> "The WebSocket manager handles multiple concurrent connections. The agent runs per-session in an asyncio task. For production you'd add a task queue — Celery or ARQ — but for the demo scope the async FastAPI loop is sufficient."

**"What's the confidence score based on?"**
> "Claude determines confidence based on what it found during investigation — if it called all four tools and the data was clear, confidence is high. If there were conflicting signals or missing data, it reports lower confidence. We don't post-process it."

---

## Timing reference

| Mark | What's happening |
|------|-----------------|
| 0:00 | Open — point to live map |
| 0:15 | Click Storm · Jebel Ali |
| 0:20 | Map: Jebel Ali turns red |
| 0:35 | First ObservationCards appear |
| 0:50 | Tool calls visible |
| 1:10 | First DecisionCard: MSC AURORA reroute |
| 1:25 | Second DecisionCard: EVER GIVEN II hold |
| 1:35 | Click "What if we don't act?" |
| 1:40 | Counterfactual panel slides in |
| 2:00 | Describe 3 other scenarios |
| 2:30 | Architecture pitch |
| 2:55 | Done |

---

## Pre-demo checklist

- [ ] `curl localhost:8000/health` returns `{"api_key_set": true}`
- [ ] Map shows all 11 vessel dots, they're moving
- [ ] Heartbeat pulse visible in log panel
- [ ] Run storm scenario once in private — verify decisions appear
- [ ] Log panel auto-scrolls correctly
- [ ] Browser zoom at 100% (not zoomed out)
- [ ] Close all other browser tabs
- [ ] Silence phone
- [ ] Know the recovery: if WebSocket drops → Cmd+R → reconnects in 3s
