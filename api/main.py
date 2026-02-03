from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd

from adam_core.config import load_ontology, Ontology
from adam_core.simulator import forecast
from adam_core.eri import compute_eri
from adam_core.replay import backtest_replay

APP_ONT_PATH = "config/ontology.yaml"
API_KEY = "adam-demo-key"  # replace with env/secret manager in production

app = FastAPI(
    title="ADAM API",
    version="0.1",
    description="Enterprise integration surface for Adam: control-health forecasting and historical replay.",
)

def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def get_ontology() -> Ontology:
    return load_ontology(APP_ONT_PATH)

class ForecastRequest(BaseModel):
    csv_path: str = Field(..., description="Path to CSV with columns: timestamp + required metrics.")
    start_time: Optional[str] = Field(None, description="ISO8601 time to forecast from; defaults to last row timestamp.")
    horizon_days: Optional[int] = Field(None, description="Forecast horizon; defaults to ontology.")

class ReplayRequest(BaseModel):
    csv_path: str
    incident_time: str = Field(..., description="ISO8601 incident time (ground truth).")
    lookback_days: int = Field(30, ge=7, le=120)
    horizon_days: int = Field(14, ge=7, le=60)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ontology", dependencies=[Depends(require_api_key)])
def ontology():
    ont = get_ontology()
    return {
        "version": ont.version,
        "company_profile": ont.company_profile,
        "controls": {cid: {"name": c.name, "metric": c.metric, "direction": c.thresholds.direction, "states": c.thresholds.states} for cid, c in ont.controls.items()},
        "propagation_graph": [{"src": e.src, "dst": e.dst, "delay_days": e.delay_days, "amplification": e.amplification} for e in ont.edges],
        "impact_weights": ont.impact_weights,
        "forecast": {"horizon_days": ont.forecast_horizon_days, "step_hours": ont.step_hours, "eri_warning": ont.eri_warning},
    }

@app.post("/forecast", dependencies=[Depends(require_api_key)])
def run_forecast(req: ForecastRequest):
    ont = get_ontology()
    df = pd.read_csv(req.csv_path)
    fr = forecast(df, ont, start_time=req.start_time, horizon_days=req.horizon_days)

    probs = fr.series[0].probabilities if fr.series else {}
    ttf = fr.summary.get("time_to_failure_days")
    eri = compute_eri(probs, ont.impact_weights, ttf)

    return {
        "eri": eri.eri,
        "top_driver": eri.top_driver,
        "time_to_failure_days": eri.time_to_failure_days,
        "summary": fr.summary,
        "series": [
            {
                "timestamp": str(p.timestamp.isoformat()),
                "pressures": p.pressures,
                "predicted_states": p.predicted_states,
                "probabilities": p.probabilities,
            }
            for p in fr.series
        ],
    }

@app.post("/replay", dependencies=[Depends(require_api_key)])
def run_replay(req: ReplayRequest):
    ont = get_ontology()
    df = pd.read_csv(req.csv_path)
    rr = backtest_replay(df, ont, incident_time=req.incident_time, lookback_days=req.lookback_days, horizon_days=req.horizon_days)
    return rr.__dict__
