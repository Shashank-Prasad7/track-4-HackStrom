"""
Claude agent with tool-use loop.
H0-H2: Stubs so main.py can import without error.
H4-H6: Full implementation replaces these stubs.
"""
from __future__ import annotations
from typing import Callable, Awaitable


async def run_agent_with_fallback(
    scenario: str,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None = None,
) -> None:
    """Full Claude tool-use agent — implemented in H4-H6 milestone."""
    pass


async def run_counterfactual_analysis(
    shipment_id: str,
    delay_hours: float,
    fleet_state: dict,
    broadcast: Callable[[dict], Awaitable[None]],
    session_id: str | None = None,
) -> None:
    """Counterfactual analysis — implemented in H8-H10 milestone."""
    pass
