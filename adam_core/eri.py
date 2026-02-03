from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import math

@dataclass(frozen=True)
class ERIResult:
    eri: float
    components: Dict[str, float]
    top_driver: str
    time_to_failure_days: float | None

def compute_eri(probabilities: Dict[str, float], impact_weights: Dict[str, float], time_to_failure_days: float | None) -> ERIResult:
    components = {}
    total = 0.0
    for ctrl, p in probabilities.items():
        w = float(impact_weights.get(ctrl, 1.0))
        comp = float(p) * w
        components[ctrl] = comp
        total += comp

    eri = 1.0 - math.exp(-total)

    if time_to_failure_days is not None:
        t = max(0.0, float(time_to_failure_days))
        time_boost = 1.0 / (1.0 + (t / 14.0))
        eri = min(1.0, eri * (0.8 + 0.4 * time_boost))

    top = max(components.items(), key=lambda kv: kv[1])[0] if components else "unknown"
    return ERIResult(eri=float(eri), components=components, top_driver=top, time_to_failure_days=time_to_failure_days)
