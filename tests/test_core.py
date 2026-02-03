import pandas as pd
from adam_core.config import load_ontology
from adam_core.simulator import forecast
from adam_core.replay import backtest_replay

def test_forecast_runs():
    ont = load_ontology("config/ontology.yaml")
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=10, freq="6H", tz="UTC").astype(str),
        "vendor_latency_ms": [180]*10,
        "ops_queue_depth": [200]*10,
        "override_rate_per_hr": [2]*10,
        "review_throughput_per_hr": [130]*10,
        "sla_breach_rate": [0.001]*10,
        "error_rate_pct": [0.2]*10,
        "cpu_util_pct": [40]*10,
        "incident_flag": [0]*10,
    })
    fr = forecast(df, ont, horizon_days=7)
    assert fr.series
    assert "top_choke_point" in fr.summary

def test_replay_runs():
    ont = load_ontology("config/ontology.yaml")
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=80, freq="6H", tz="UTC").astype(str),
        "vendor_latency_ms": [180]*80,
        "ops_queue_depth": [200]*80,
        "override_rate_per_hr": [2]*80,
        "review_throughput_per_hr": [130]*80,
        "sla_breach_rate": [0.001]*79 + [0.03],
        "error_rate_pct": [0.2]*80,
        "cpu_util_pct": [40]*80,
        "incident_flag": [0]*79 + [1],
    })
    incident_time = pd.to_datetime(df["timestamp"].iloc[-1], utc=True).isoformat()
    rr = backtest_replay(df, ont, incident_time=incident_time, lookback_days=10, horizon_days=7)
    assert rr.eri_series
