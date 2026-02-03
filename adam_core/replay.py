from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd

from .config import Ontology
from .simulator import forecast
from .eri import compute_eri

@dataclass(frozen=True)
class ReplayResult:
    window_start: str
    window_end: str
    incident_time: str
    first_warning_time: str | None
    lead_time_days: float | None
    eri_series: List[Dict[str, Any]]
    narrative: Dict[str, Any]

def backtest_replay(df: pd.DataFrame, ontology: Ontology, incident_time: str, lookback_days: int = 30, horizon_days: int = 14) -> ReplayResult:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")
    incident_ts = pd.to_datetime(incident_time, utc=True)

    start_ts = incident_ts - pd.Timedelta(days=lookback_days)
    window = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= incident_ts)].copy()
    if window.empty:
        raise ValueError("No data in the requested replay window.")

    days = pd.date_range(window["timestamp"].iloc[0].floor("D"), incident_ts.floor("D"), freq="1D", tz="UTC")

    eri_series: List[Dict[str, Any]] = []
    first_warning = None

    for day in days:
        sub = window[window["timestamp"] <= day].copy()
        if sub.empty:
            continue
        t0 = sub["timestamp"].iloc[-1].isoformat()
        fr = forecast(sub, ontology, start_time=t0, horizon_days=horizon_days)

        probs = fr.series[0].probabilities if fr.series else {}
        ttf = fr.summary.get("time_to_failure_days")
        eri = compute_eri(probs, ontology.impact_weights, ttf)

        eri_point = {
            "as_of": t0,
            "eri": eri.eri,
            "top_driver": eri.top_driver,
            "time_to_failure_days": eri.time_to_failure_days,
            "predicted_first_sla_degrade_or_fail": fr.summary.get("predicted_first_sla_degrade_or_fail"),
            "top_choke_point": fr.summary.get("top_choke_point"),
        }
        eri_series.append(eri_point)

        if first_warning is None and eri.eri >= ontology.eri_warning:
            first_warning = pd.to_datetime(t0, utc=True)

    lead_time = None
    if first_warning is not None:
        lead_time = (incident_ts - first_warning).total_seconds() / (3600 * 24)

    narrative = {
        "what_this_proves": "Adam can raise an escalation warning before a known incident using only control-health vitals.",
        "eri_warning_threshold": ontology.eri_warning,
        "lead_time_days": lead_time,
    }

    return ReplayResult(
        window_start=str(window["timestamp"].iloc[0].isoformat()),
        window_end=str(window["timestamp"].iloc[-1].isoformat()),
        incident_time=str(incident_ts.isoformat()),
        first_warning_time=str(first_warning.isoformat()) if first_warning is not None else None,
        lead_time_days=lead_time,
        eri_series=eri_series,
        narrative=narrative,
    )
