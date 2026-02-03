from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import math

STATE_ORDER = ["healthy", "constrained", "degraded", "failed"]

@dataclass(frozen=True)
class ControlState:
    state: str
    severity: int  # 0..3
    metric_value: float

def classify_state(direction: str, thresholds: Dict[str, Dict[str, float]], value: float) -> ControlState:
    """Classify a metric value into a discrete control health state.

    - higher_is_worse: uses 'max' thresholds
    - lower_is_worse: uses 'min' thresholds
    """
    if direction not in ("higher_is_worse", "lower_is_worse"):
        raise ValueError(f"Unknown direction: {direction}")

    if direction == "higher_is_worse":
        for i, s in enumerate(STATE_ORDER):
            mx = thresholds[s].get("max", math.inf)
            if value <= mx:
                return ControlState(state=s, severity=i, metric_value=float(value))
        return ControlState(state="failed", severity=3, metric_value=float(value))

    mins = {s: thresholds[s].get("min", -math.inf) for s in STATE_ORDER}
    if value >= mins["healthy"]:
        return ControlState("healthy", 0, float(value))
    if value >= mins["constrained"]:
        return ControlState("constrained", 1, float(value))
    if value >= mins["degraded"]:
        return ControlState("degraded", 2, float(value))
    return ControlState("failed", 3, float(value))

def severity_to_pressure(sev: int) -> float:
    """Convert discrete severity into continuous pressure (0..1)."""
    return {0: 0.0, 1: 0.35, 2: 0.7, 3: 1.0}.get(int(sev), 1.0)

def state_from_pressure(pressure: float) -> Tuple[str, int]:
    """Convert pressure back to a discrete state."""
    if pressure < 0.2:
        return "healthy", 0
    if pressure < 0.5:
        return "constrained", 1
    if pressure < 0.85:
        return "degraded", 2
    return "failed", 3
