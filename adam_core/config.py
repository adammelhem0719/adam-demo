from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any
import yaml

@dataclass(frozen=True)
class ControlStateThresholds:
    direction: str  # "higher_is_worse" or "lower_is_worse"
    states: Dict[str, Dict[str, float]]  # each state: {max: x} or {min: x}

@dataclass(frozen=True)
class Control:
    id: str
    name: str
    metric: str
    thresholds: ControlStateThresholds

@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    delay_days: int
    amplification: float

@dataclass(frozen=True)
class Ontology:
    version: str
    controls: Dict[str, Control]
    edges: List[Edge]
    impact_weights: Dict[str, float]
    forecast_horizon_days: int
    step_hours: int
    eri_warning: float
    company_profile: Dict[str, Any]

def load_ontology(path: str) -> Ontology:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    controls: Dict[str, Control] = {}
    for c in raw["controls"]:
        thresholds = ControlStateThresholds(direction=c["direction"], states=c["states"])
        controls[c["id"]] = Control(id=c["id"], name=c["name"], metric=c["metric"], thresholds=thresholds)

    edges = [Edge(**e) for e in raw.get("propagation_graph", [])]
    forecast = raw.get("forecast", {})
    warn = forecast.get("warning_thresholds", {}).get("eri", 0.65)

    return Ontology(
        version=str(raw.get("version", "0.1")),
        controls=controls,
        edges=edges,
        impact_weights=raw.get("impact_weights", {}),
        forecast_horizon_days=int(forecast.get("horizon_days", 14)),
        step_hours=int(forecast.get("step_hours", 6)),
        eri_warning=float(warn),
        company_profile=raw.get("company_profile", {}),
    )
