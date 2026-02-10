from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from adam_core.simulator import forecast
from adam_core.eri import compute_eri
from adam_core.replay import backtest_replay

from state import compute_company_risk_score, categorize_risk_severity


st.title("Risk Vitals")

df = st.session_state.get("data")
ont = st.session_state.get("ont")
horizon_days = st.session_state.get("horizon_days", 14)

if df is None or ont is None:
    st.warning("Missing data or ontology. Go to the main page and upload data.")
    st.stop()

# Overall Company Risk Score (top, simple)
score, label, _ = compute_company_risk_score(df)
sev = categorize_risk_severity(score)

c1, c2, c3 = st.columns([1.2, 1, 2.8])
with c1:
    st.metric("Overall Company Risk Score", f"{score}/100")
with c2:
    if sev["ui"] == "error":
        st.error(sev["status"])
    elif sev["ui"] == "warning":
        st.warning(sev["status"])
    elif sev["ui"] == "info":
        st.info(sev["status"])
    else:
        st.success(sev["status"])
with c3:
    st.caption("Vitals view. No tables. Key charts only.")

st.divider()

# -------------------------
# GRAPH 1: Control Metrics (Last 60 days)
# -------------------------
st.subheader("Control Metrics (Last 60 days)")

required = ["vendor_latency_ms", "ops_queue_depth", "override_rate_per_hr", "review_throughput_per_hr", "sla_breach_rate"]

if "timestamp" not in df.columns:
    st.info("No 'timestamp' column found, cannot plot time series.")
else:
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        dfx = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        recent = dfx[dfx["timestamp"] >= dfx["timestamp"].max() - pd.Timedelta(days=60)]
        available = [c for c in required if c in recent.columns]

        if not available:
            st.info("None of the expected control metric columns are present.")
        else:
            st.line_chart(recent.set_index("timestamp")[available], use_container_width=True)
    except Exception as e:
        st.warning(f"Could not plot control metrics: {e}")

st.divider()

# -------------------------
# Forecast summary + GRAPH 2: Predicted States
# -------------------------
st.subheader("Escalation Forecast")

try:
    fr = forecast(df, ont, start_time=None, horizon_days=int(horizon_days))
    probs = fr.series[0].probabilities if fr.series else {}
    ttf = fr.summary.get("time_to_failure_days")
    eri = compute_eri(probs, ont.impact_weights, ttf)

    a, b, c = st.columns(3)
    with a:
        st.metric("Escalation Risk Index (ERI)", f"{eri.eri:.3f}")
    with b:
        st.write("**Top driver:**", eri.top_driver)
    with c:
        st.write("**Top choke point:**", fr.summary.get("top_choke_point"))

    st.write("**Predicted first SLA degrade/fail:**", fr.summary.get("predicted_first_sla_degrade_or_fail"))

    # GRAPH 2: Predicted state chart
    st.subheader("Predicted State Trajectory")

    if fr.series:
        states_df = pd.DataFrame(
            [{"timestamp": p.timestamp, **p.predicted_states} for p in fr.series]
        ).set_index("timestamp")

        mapping = {"healthy": 0, "constrained": 1, "degraded": 2, "failed": 3}
        numeric_states = states_df.apply(lambda col: col.map(mapping))

        st.line_chart(numeric_states, use_container_width=True)
        st.caption("State mapping: healthy=0, constrained=1, degraded=2, failed=3")
    else:
        st.info("Forecast returned no series to plot.")

except Exception as e:
    st.error(str(e))

st.divider()

# Optional: keep backtest lightweight, no tables
st.subheader("Historical Replay (Backtest)")

if "timestamp" in df.columns:
    incident_default = df["timestamp"].max().floor("D")
    incident_time = st.text_input("Incident time (ISO8601)", value=str(incident_default.isoformat()))
else:
    incident_time = st.text_input("Incident time (ISO8601)", value="")

lookback = st.slider("Lookback window (days)", min_value=7, max_value=120, value=30, step=1)
h2 = st.slider("Replay forecast horizon (days)", min_value=7, max_value=60, value=14, step=1)

try:
    rr = backtest_replay(df, ont, incident_time=incident_time, lookback_days=int(lookback), horizon_days=int(h2))
    st.write(rr.narrative)

    if rr.first_warning_time:
        st.success(f"First ERI warning at {rr.first_warning_time} | lead time: {rr.lead_time_days:.2f} days")
    else:
        st.warning("No warning threshold crossed in the replay window.")

except Exception as e:
    st.error(str(e))
