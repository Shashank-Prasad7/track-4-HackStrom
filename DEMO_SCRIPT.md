# Demo Script — 3-Minute Judge Walkthrough

**Practice this 3× minimum before presenting.**

---

## Pre-demo setup (do this 5 minutes before your slot)

```bash
# Terminal 1
cd backend && uvicorn main:app --reload

# Terminal 2
cd frontend && npm run dev
```

1. Open `http://localhost:5173` — fullscreen, browser zoom 100%
2. Verify: 11 vessel dots visible on map, dots moving slowly
3. Verify: log panel shows heartbeat pulse (`◉ 11 vessels · all nominal`)
4. Verify: header shows **"Live"** (green) in top-right
5. **Pre-warm the API** — trigger Storm scenario once privately, wait for decisions, then click the trash icon to clear the log. This keeps the API connection warm and avoids cold-start latency in front of judges.
6. Silence phone. Close all other tabs.

---

## T+0:00 — Open (15 seconds)

*Point to the live map.*

> "This is a real-time supply chain control tower. What you're looking at are 11 live vessels across the Indian Ocean and Arabian Gulf — each one moving, each one carrying cargo, each one with factories and SLAs waiting downstream.
>
> The system is continuously evaluating fleet state. You can see that pulse in the log — the agent checks in every 10 seconds. Nothing is waiting for someone to click a button."

*Let the heartbeat pulse once. Point to the dashed route lines connecting vessels to their next ports.*

---

## T+0:15 — Set the scenario (20 seconds)

*Point to the scenario buttons at the bottom.*

> "We have four real-world disruptions we can trigger. I'm going to show you the most complex one: a sandstorm that closes the Port of Jebel Ali for 48 hours. Three of our vessels are inbound. Watch what happens."

*Click **Storm · Jebel Ali**.*

*The button highlights and shows a spinner. The Jebel Ali port marker turns red on the map — with a pulsing outer ring.*

---

## T+0:35 — Agent reasoning (60 seconds — the hero moment)

*Watch the log panel. Narrate as events appear.*

> "The agent immediately flags all three affected vessels — you can see the observation cards pop in."

*ObservationCards appear. Point to the delay hours in amber.*

> "Now watch the tools. The agent isn't guessing — it's calling our port conditions API to confirm the closure, then checking alternative routes, and then — this is the critical step — it calls `assess_downstream_impact` for each vessel."

*Tool call rows appear. Slow down here.*

> "And look at the timestamps — every event is timestamped. You can see the entire observation-to-decision chain happening in real time, in under 20 seconds."

*Wait for the first DecisionCard to appear.*

> "MSC AURORA is carrying **perishable flowers**. Downstream orders expire in 24 hours. The agent recommends an immediate reroute via Salalah. **87% confidence.** It found the $240K loss risk and surfaced the $38K reroute as the obvious call."

*Scroll or wait for the second DecisionCard.*

> "But EVER GIVEN II is carrying industrial machinery — no downstream dependencies. The agent recommends **holding at anchorage**. Because rerouting costs $42K for cargo that can wait 48 hours. Same storm. Different decision. That's the judgement call."

*Pause.*

---

## T+1:35 — Counterfactual (25 seconds)

*Click "What if we don't act?" on MSC AURORA's decision card.*

> "Judges always ask: what's the cost of inaction? We built that in. If we do nothing — $240,000 in penalties and spoiled cargo. The reroute costs $38K. The agent surfaced that maths without being asked."

*Red "Cost of Inaction" panel appears with the numbers in large type.*

---

## T+2:00 — Other scenarios (30 seconds)

*Point to the other three buttons — don't trigger them.*

> "Three more scenarios. Customs hold in Singapore — the agent finds a $200K/day factory halt and recommends an $8K expedite. Carrier capacity drop — it differentiates between pharmaceutical cargo that needs an immediate vendor switch and bulk chemicals that can wait. And a cascade scenario where a 6-hour delay at Colombo crosses a customs pre-clearance window and becomes a 32-hour delay downstream — the agent finds that."

---

## T+2:30 — Architecture pitch (25 seconds)

> "Under the hood: a single Claude agent on the tool-use API — `claude-sonnet-4-6`. Four tools: shipment status, port conditions, alternative routes, downstream impact. Every tool call, every reasoning step, every decision streams to this panel as a typed event.
>
> We have a 30-second fallback — if the API is unreachable, a rule-based engine fires with the same event schema. You'd see an amber banner across the top and the log would look identical."

*Gesture to the header.*

> "The track asks for continuous state evaluation, action triggering, and agentic log trace. That's exactly what you're watching."

---

## T+2:55 — Close (5 seconds)

> "Thank you."

---

## Q&A Prep

**"Is this multi-agent?"**
> "No — single agent with structured tool use. Multi-agent adds latency and failure surfaces. Our bottleneck is reasoning quality, not parallelism. The named stages in the log — observation, investigation, decision — show the depth of reasoning, not separate agents."

**"Is the data real?"**
> "Vessel positions are simulated — real-world data comes from AIS feeds and TMS APIs. The tool calls and reasoning are live: every tool invocation you saw was a real Claude API call returning structured data."

**"What if the API fails mid-demo?"**
> "30-second timeout, then a rule-based fallback fires with the same event schema. You'd see an amber 'Fallback Mode' banner across the top. Same UI, same decisions — we pre-canned all four scenarios. Conference demos are adversarial, so we built that in."

**"What's the confidence score based on?"**
> "Claude determines confidence based on what it found during investigation. If all four tools returned clear data with no conflicting signals, it reports high confidence. If there were contradictions or missing data, it reports lower. We don't post-process or cap it."

**"How does it scale?"**
> "WebSocket manager handles concurrent connections. Agent runs per-session in an asyncio task. For production you'd add a task queue — Celery or ARQ — but for demo scope the async FastAPI loop is sufficient."

**"Why did you choose Claude over GPT-4?"**
> "Tool-use fidelity. Claude reliably calls the `submit_recommendation` tool to produce structured DecisionEvents rather than hallucinating JSON in free text. That's the architecture hinge — without reliable tool use, the typed event stream breaks."

---

## Timing reference

| Mark | What's happening |
|------|-----------------|
| 0:00 | Open — live map, dashed route lines |
| 0:15 | Click Storm · Jebel Ali |
| 0:18 | Button highlights with spinner |
| 0:20 | Map: Jebel Ali turns red, hot ring pulses |
| 0:35 | ObservationCards appear with delay hours |
| 0:50 | Tool call rows — point to timestamps |
| 1:10 | First DecisionCard: MSC AURORA reroute, 87% |
| 1:25 | Second DecisionCard: EVER GIVEN II hold |
| 1:35 | Click "What if we don't act?" |
| 1:38 | Counterfactual panel: $240K in large type |
| 2:00 | Describe 3 other scenarios |
| 2:30 | Architecture pitch + fallback mention |
| 2:55 | Done |

---

## Pre-demo checklist

- [ ] `curl localhost:8000/health` returns `{"api_key_set": true}`
- [ ] Map shows all 11 vessel dots, they're moving, dashed route lines visible
- [ ] Heartbeat pulse visible in log panel
- [ ] **Run Storm scenario once privately** — verify decisions appear in <20s
- [ ] **Click trash icon** to clear log — map port resets, log is empty
- [ ] Log panel shows "Monitoring 11 vessels · System nominal"
- [ ] Browser zoom at 100%
- [ ] Close all other browser tabs
- [ ] Silence phone
- [ ] Know the recovery: WebSocket drops → Cmd+R → reconnects in 3s, replays last events
- [ ] Know the fallback: if amber banner appears, narrate it as a feature ("we built that in")

---

## Recovery procedures (memorise these)

| Problem | Fix |
|---------|-----|
| WebSocket offline badge | Cmd+R (page reload) — reconnects in <3s |
| Agent running for >30s | Wait — timeout fires and fallback kicks in automatically |
| Map blank | Reload — FitBoundsOnLoad refits on next fleet_snapshot |
| Want to reset between scenarios | Click the trash icon in the log panel header |
| API key missing | Check `backend/.env` has `ANTHROPIC_API_KEY=sk-ant-…` |
