"""
Shipment simulator.
H0-H2: Static fleet seed data + get_fleet_state().
H2-H4: Add background asyncio loop that moves vessels and broadcasts position updates.
"""
from __future__ import annotations
import asyncio
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Callable, Awaitable

# ── Fleet seed data ───────────────────────────────────────────────────────────
# 11 vessels with deliberate asymmetries for scenario variety.
# Positions are real sea-lane coordinates (Indian Ocean / Gulf region).

_BASE_FLEET: dict[str, dict] = {
    "SHP001": {
        "shipment_id": "SHP001",
        "vessel_name": "MSC AURORA",
        "position": {"lat": 24.8, "lng": 56.5},   # inbound Jebel Ali
        "next_port": "AEJEA",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=18)).isoformat(),
        "cargo_type": "perishable",
        "cargo_value_usd": 2_800_000,
        "perishable": True,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-7741", "ORD-7742"],
    },
    "SHP002": {
        "shipment_id": "SHP002",
        "vessel_name": "EVER GIVEN II",
        "position": {"lat": 25.1, "lng": 55.8},   # inbound Jebel Ali
        "next_port": "AEJEA",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "cargo_type": "industrial_machinery",
        "cargo_value_usd": 8_500_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": [],
    },
    "SHP003": {
        "shipment_id": "SHP003",
        "vessel_name": "MAERSK SENTOSA",
        "position": {"lat": 23.9, "lng": 57.2},   # inbound Jebel Ali
        "next_port": "AEJEA",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=36)).isoformat(),
        "cargo_type": "consumer_electronics",
        "cargo_value_usd": 14_200_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-8801"],
    },
    "SHP004": {
        "shipment_id": "SHP004",
        "vessel_name": "OOCL SINGAPORE",
        "position": {"lat": 1.25, "lng": 103.8},  # at Singapore
        "next_port": "SGSIN",
        "current_port": "SGSIN",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "cargo_type": "automotive_parts",
        "cargo_value_usd": 5_600_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-9910", "ORD-9911"],  # factory assembly line
    },
    "SHP005": {
        "shipment_id": "SHP005",
        "vessel_name": "CMA CGM MARCO POLO",
        "position": {"lat": 6.9, "lng": 79.8},    # near Colombo
        "next_port": "LKCMB",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "cargo_type": "bulk_grain",
        "cargo_value_usd": 1_200_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-5520"],
    },
    "SHP006": {
        "shipment_id": "SHP006",
        "vessel_name": "HAPAG BERLIN",
        "position": {"lat": 12.5, "lng": 44.0},   # Red Sea / Gulf of Aden
        "next_port": "AEJEA",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=52)).isoformat(),
        "cargo_type": "pharmaceuticals",
        "cargo_value_usd": 22_000_000,
        "perishable": True,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-6601", "ORD-6602", "ORD-6603"],
    },
    "SHP007": {
        "shipment_id": "SHP007",
        "vessel_name": "COSCO HARMONY",
        "position": {"lat": 15.3, "lng": 51.2},   # Arabian Sea
        "next_port": "OMSLL",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=28)).isoformat(),
        "cargo_type": "consumer_electronics",
        "cargo_value_usd": 9_700_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": [],
    },
    "SHP008": {
        "shipment_id": "SHP008",
        "vessel_name": "PIL MERIDIAN",
        "position": {"lat": 4.2, "lng": 73.5},    # Indian Ocean
        "next_port": "SGSIN",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=44)).isoformat(),
        "cargo_type": "industrial_machinery",
        "cargo_value_usd": 6_300_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": [],
    },
    "SHP009": {
        "shipment_id": "SHP009",
        "vessel_name": "EVERGREEN JADE",
        "position": {"lat": 8.5, "lng": 77.1},    # near Sri Lanka
        "next_port": "LKCMB",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat(),
        "cargo_type": "textiles",
        "cargo_value_usd": 3_100_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": ["ORD-4412"],
    },
    "SHP010": {
        "shipment_id": "SHP010",
        "vessel_name": "ZIM EXCELLENCE",
        "position": {"lat": 18.2, "lng": 63.4},   # Arabian Sea
        "next_port": "AEJEA",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=60)).isoformat(),
        "cargo_type": "bulk_chemicals",
        "cargo_value_usd": 4_800_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": [],
    },
    "SHP011": {
        "shipment_id": "SHP011",
        "vessel_name": "YANG MING ROSE",
        "position": {"lat": 10.8, "lng": 93.2},   # Bay of Bengal
        "next_port": "SGSIN",
        "eta_original": (datetime.now(timezone.utc) + timedelta(hours=32)).isoformat(),
        "cargo_type": "consumer_goods",
        "cargo_value_usd": 7_400_000,
        "perishable": False,
        "risk_level": "nominal",
        "downstream_orders": [],
    },
}

# Runtime mutable state
_fleet: dict[str, dict] = {k: dict(v) for k, v in _BASE_FLEET.items()}


def get_fleet_state() -> dict[str, dict]:
    return {k: dict(v) for k, v in _fleet.items()}


def get_vessel(shipment_id: str) -> dict | None:
    v = _fleet.get(shipment_id)
    return dict(v) if v else None


def set_risk_level(shipment_id: str, level: str) -> None:
    if shipment_id in _fleet:
        _fleet[shipment_id]["risk_level"] = level


# ── Background simulator (H2-H4) ─────────────────────────────────────────────
# Moves each vessel slightly toward its next port every 3 seconds.

_PORT_COORDS: dict[str, tuple[float, float]] = {
    "AEJEA": (25.01, 55.06),   # Jebel Ali
    "SGSIN": (1.27, 103.82),   # Singapore
    "LKCMB": (6.93, 79.84),    # Colombo
    "OMSLL": (17.02, 54.09),   # Salalah
}


def _step_toward(lat: float, lng: float, target_lat: float, target_lng: float, step: float = 0.05) -> tuple[float, float]:
    dlat = target_lat - lat
    dlng = target_lng - lng
    dist = math.sqrt(dlat ** 2 + dlng ** 2)
    if dist < step:
        return target_lat, target_lng
    ratio = step / dist
    jitter = random.uniform(-0.005, 0.005)
    return lat + dlat * ratio + jitter, lng + dlng * ratio + jitter


async def run_simulator(broadcast: Callable[[dict], Awaitable[None]]) -> None:
    """Moves vessels every 3s and broadcasts position-update heartbeats."""
    while True:
        await asyncio.sleep(3)
        for vessel in _fleet.values():
            port = vessel.get("next_port", "")
            if port in _PORT_COORDS:
                tlat, tlng = _PORT_COORDS[port]
                pos = vessel["position"]
                new_lat, new_lng = _step_toward(pos["lat"], pos["lng"], tlat, tlng)
                vessel["position"] = {"lat": round(new_lat, 5), "lng": round(new_lng, 5)}
