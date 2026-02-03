from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

from .config import Ontology
from .states import classify_state, severity_to_pressure, state_from_pressure
from .graph import build_graph

@dataclass(frozen=True)
class ForecastPoint:
    timestamp: pd.Timestamp
    pressures: Dict[str, float]
    predicted_states: Dict[str, str]
    probabilities: Dict[str, float]

@dataclass(frozen=True)
class ForecastResult:
    start: str
    end: str
    horizon_days: int
    series: List[ForecastPoint]
    summary: Dict[str, Any]

def _estimate_probability(pressure_series: List[float]) -> float:
    if not pressure_series:
        return 0.0
    cur = float(pressure_series[-1])
    if len(pressure_series) < 3:
        return float(min(1.0, max(0.0, cur)))
    prev_mean = float(np.mean(pressure_series[:-1]))
    trend = cur - prev_mean
    p = 0.65 * cur + 0.35 * max(0.0, trend) * 1.2
    return float(min(1.0, max(0.0, p)))

def forecast(df: pd.DataFrame, ontology: Ontology, start_time: str | None = None, horizon_days: int | None = None) -> ForecastResult:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")

    if start_time:
        t0 = pd.to_datetime(start_time, utc=True)
        df_hist = df[df["timestamp"] <= t0].copy()
        if df_hist.empty:
            raise ValueError("start_time is earlier than any available data.")
    else:
        df_hist = df.copy()
        t0 = df_hist["timestamp"].iloc[-1]

    horizon = int(horizon_days or ontology.forecast_horizon_days)
    step_hours = int(ontology.step_hours)
    steps = int((horizon * 24) / step_hours)

    pg = build_graph(ontology.edges)

    last = df_hist[df_hist["timestamp"] == t0].iloc[-1]
    pressures: Dict[str, float] = {}
    for cid, ctrl in ontology.controls.items():
        val = float(last[ctrl.metric])
        cs = classify_state(ctrl.thresholds.direction, ctrl.thresholds.states, val)
        pressures[cid] = severity_to_pressure(cs.severity)

    pressure_hist: Dict[str, List[float]] = {cid: [pressures[cid]] for cid in ontology.controls.keys()}

    series: List[ForecastPoint] = []
    current_time = t0

    decay_per_step = 0.03
    noise_scale = 0.01
    rng = np.random.default_rng(42)

    edge_buffers: Dict[Tuple[str, str], List[float]] = {}
    for u, v, d in pg.graph.edges(data=True):
        delay_steps = int((int(d["delay_days"]) * 24) / step_hours)
        edge_buffers[(u, v)] = [0.0 for _ in range(max(1, delay_steps))]

    for _ in range(steps):
        incoming = {cid: 0.0 for cid in ontology.controls.keys()}
        for u, v, d in pg.graph.edges(data=True):
            amp = float(d["amplification"])
            buf = edge_buffers[(u, v)]
            buf.append(pressures[u] * amp)
            arriving = buf.pop(0)
            incoming[v] += arriving

        for cid in pressures.keys():
            new_p = pressures[cid] * (1.0 - decay_per_step) + incoming[cid] * 0.25
            new_p = new_p + float(rng.normal(0.0, noise_scale))
            pressures[cid] = float(min(1.0, max(0.0, new_p)))
            pressure_hist[cid].append(pressures[cid])

        predicted_states: Dict[str, str] = {}
        probabilities: Dict[str, float] = {}
        for cid, pseries in pressure_hist.items():
            st, _ = state_from_pressure(pseries[-1])
            predicted_states[cid] = st
            probabilities[cid] = _estimate_probability(pseries[-12:])

        current_time = current_time + pd.Timedelta(hours=step_hours)
        series.append(ForecastPoint(timestamp=current_time, pressures=dict(pressures), predicted_states=predicted_states, probabilities=probabilities))

    first_fail = None
    for pt in series:
        if pt.predicted_states.get("sla_compliance") in ("degraded", "failed"):
            first_fail = pt.timestamp
            break

    time_to_failure_days = None
    if first_fail is not None:
        time_to_failure_days = (first_fail - t0).total_seconds() / (3600 * 24)

    avg_pressure = {cid: float(np.mean([pt.pressures[cid] for pt in series])) for cid in ontology.controls.keys()}
    choke = max(avg_pressure.items(), key=lambda kv: kv[1])[0]

    summary = {
        "start_time": str(t0.isoformat()),
        "predicted_first_sla_degrade_or_fail": str(first_fail.isoformat()) if first_fail is not None else None,
        "time_to_failure_days": time_to_failure_days,
        "avg_pressure": avg_pressure,
        "top_choke_point": choke,
        "propagation_edges": [{"src": u, "dst": v, **d} for u, v, d in pg.graph.edges(data=True)],
    }

    return ForecastResult(
        start=str(t0.isoformat()),
        end=str(series[-1].timestamp.isoformat()) if series else str(t0.isoformat()),
        horizon_days=horizon,
        series=series,
        summary=summary,
    )





from dataclasses import dataclass

@dataclass
class SystemState:
    ops_queue_depth: float
    review_throughput_per_hr: float
    override_rate_per_hr: float
    vendor_capacity: float
    sla_compliance: float

@dataclass
class WhatIfControls:
    vendor_capacity_multiplier: float
    throughput_multiplier: float
    overrides_multiplier: float

def apply_controls(state: SystemState, ctl: WhatIfControls) -> SystemState:
    return SystemState(
        ops_queue_depth=state.ops_queue_depth,
        review_throughput_per_hr=state.review_throughput_per_hr * ctl.throughput_multiplier,
        override_rate_per_hr=state.override_rate_per_hr * ctl.overrides_multiplier,
        vendor_capacity=state.vendor_capacity * ctl.vendor_capacity_multiplier,
        sla_compliance=state.sla_compliance,
    )

def compute_eri(state: SystemState) -> float:
    risk = 0.0
    risk += min(1.0, state.ops_queue_depth / 5000.0) * 0.45
    risk += min(1.0, state.override_rate_per_hr / 200.0) * 0.30
    risk += (1.0 - min(1.0, state.review_throughput_per_hr / 300.0)) * 0.15
    risk += (1.0 - min(1.0, state.vendor_capacity / 1000.0)) * 0.10
    return max(0.0, min(1.0, risk))


