from __future__ import annotations
import asyncio
import json
import uuid
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from events import HeartbeatEvent, SystemEvent, BrewingRisk
from simulator import get_fleet_state, run_simulator

load_dotenv()


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        # Ring buffer: replay last 200 events to reconnecting clients
        self._buffer: list[dict] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        for event in self._buffer[-50:]:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                pass

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast(self, event: dict) -> None:
        self._buffer.append(event)
        if len(self._buffer) > 200:
            self._buffer = self._buffer[-200:]

        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        async with self._lock:
            for ws in dead:
                if ws in self._connections:
                    self._connections.remove(ws)


manager = ConnectionManager()


# ── Lifespan: start background tasks ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(heartbeat_loop()),
        asyncio.create_task(run_simulator(manager.broadcast)),
    ]
    yield
    for t in tasks:
        t.cancel()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Supply Chain Control Tower", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "connections": len(manager._connections),
        "api_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; client can send pings
    except WebSocketDisconnect:
        await manager.disconnect(ws)


@app.post("/events/trigger")
async def trigger_scenario(body: dict) -> dict:
    scenario = body.get("scenario", "")
    session_id = str(uuid.uuid4())

    await manager.broadcast(
        SystemEvent(
            session_id=session_id,
            status="agent_start",
            message=f"Agent triggered: {scenario}",
        ).model_dump()
    )

    asyncio.create_task(_run_scenario(scenario, session_id))
    return {"status": "triggered", "scenario": scenario, "session_id": session_id}


@app.post("/events/counterfactual")
async def counterfactual(body: dict) -> dict:
    shipment_id = body.get("shipment_id", "")
    delay_hours = float(body.get("delay_hours", 24))
    session_id = str(uuid.uuid4())
    asyncio.create_task(_run_counterfactual(shipment_id, delay_hours, session_id))
    return {"status": "triggered", "session_id": session_id}


# ── Background helpers ────────────────────────────────────────────────────────

async def heartbeat_loop() -> None:
    from simulator import get_fleet_state
    while True:
        await asyncio.sleep(10)
        fleet = get_fleet_state()
        at_risk = [
            v for v in fleet.values()
            if v.get("risk_level") in ("warning", "critical")
        ]
        event = HeartbeatEvent(
            active_shipments=len(fleet),
            at_risk_count=len(at_risk),
            nominal_count=len(fleet) - len(at_risk),
            system_status="nominal",
            brewing_risks=[
                BrewingRisk(
                    shipment_id=v["shipment_id"],
                    vessel_name=v["vessel_name"],
                    risk_type=v.get("risk_level", "unknown"),
                    eta_hours=2.0,
                )
                for v in at_risk[:3]
            ],
        )
        await manager.broadcast(event.model_dump())


async def _run_scenario(scenario: str, session_id: str) -> None:
    from agent import run_agent_with_fallback
    fleet = get_fleet_state()
    try:
        await asyncio.wait_for(
            run_agent_with_fallback(scenario, fleet, manager.broadcast, session_id),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        await manager.broadcast(
            SystemEvent(
                session_id=session_id,
                status="fallback_activated",
                message="Agent timed out (30s). Activating rule-based fallback.",
            ).model_dump()
        )
    finally:
        await manager.broadcast(
            SystemEvent(
                session_id=session_id,
                status="agent_end",
                message=f"Session complete: {scenario}",
            ).model_dump()
        )


async def _run_counterfactual(shipment_id: str, delay_hours: float, session_id: str) -> None:
    from agent import run_counterfactual_analysis
    fleet = get_fleet_state()
    await run_counterfactual_analysis(shipment_id, delay_hours, fleet, manager.broadcast, session_id)
