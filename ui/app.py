from __future__ import annotations
import streamlit as st

st.set_page_config(page_title="ADAM Console", layout="wide")
st.success("UPDATED UI/APP.PY LOADED")
import pandas as pd
from ui.board_view import render_board_view
from adam_core.simulator import SystemState

from adam_core.config import load_ontology
from adam_core.simulator import forecast
from adam_core.eri import compute_eri
from adam_core.replay import backtest_replay


st.title("ADAM Console — Escalation Forecasting (Synthetic Demo)")

ont = load_ontology("config/ontology.yaml")

st.sidebar.header("Inputs")
import os

uploaded = st.sidebar.file_uploader("Upload a CSV dataset", type=["csv"])
horizon = st.sidebar.slider("Forecast horizon (days)", min_value=7, max_value=60, value=ont.forecast_horizon_days, step=1)

if uploaded is None:
    st.info("No file uploaded, using demo dataset from repo.")
    demo_path = os.path.join("data", "arcadian_cloud_systems_timeseries.csv")
    df = pd.read_csv(demo_path)
else:
    df = pd.read_csv(uploaded)

df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values("timestamp")

st.subheader("Dataset Preview")
st.dataframe(df.tail(10), use_container_width=True)

colA, colB = st.columns([1, 1])

with colA:
    st.subheader("Control Metrics (Last 60 days)")
    recent = df[df["timestamp"] >= df["timestamp"].max() - pd.Timedelta(days=60)]
    st.line_chart(recent.set_index("timestamp")[["vendor_latency_ms", "ops_queue_depth", "override_rate_per_hr", "review_throughput_per_hr", "sla_breach_rate"]])

with colB:
    st.subheader("Run Forecast")
    fr = forecast(df, ont, start_time=None, horizon_days=int(horizon))
    probs = fr.series[0].probabilities if fr.series else {}
    ttf = fr.summary.get("time_to_failure_days")
    eri = compute_eri(probs, ont.impact_weights, ttf)

    st.metric("Escalation Risk Index (ERI)", f"{eri.eri:.3f}")
    st.write("**Top driver:**", eri.top_driver)
    st.write("**Top choke point:**", fr.summary.get("top_choke_point"))
    st.write("**Predicted first SLA degrade/fail:**", fr.summary.get("predicted_first_sla_degrade_or_fail"))

    states_df = pd.DataFrame([{"timestamp": p.timestamp, **p.predicted_states} for p in fr.series]).set_index("timestamp")
    st.line_chart(states_df.applymap(lambda s: {"healthy":0, "constrained":1, "degraded":2, "failed":3}[s]))

st.divider()
st.subheader("Historical Replay (Backtest)")

incident_default = df["timestamp"].max().floor("D")
incident_time = st.text_input("Incident time (ISO8601)", value=str(incident_default.isoformat()))

lookback = st.slider("Lookback window (days)", min_value=7, max_value=120, value=30, step=1)
h2 = st.slider("Replay forecast horizon (days)", min_value=7, max_value=60, value=14, step=1)

try:
    rr = backtest_replay(df, ont, incident_time=incident_time, lookback_days=int(lookback), horizon_days=int(h2))
    st.write(rr.narrative)
    if rr.first_warning_time:
        st.success(f"First ERI warning at {rr.first_warning_time}  — lead time: {rr.lead_time_days:.2f} days")
    else:
        st.warning("No warning threshold crossed in the replay window.")

    eri_df = pd.DataFrame(rr.eri_series)
    eri_df["as_of"] = pd.to_datetime(eri_df["as_of"], utc=True)
    eri_df = eri_df.sort_values("as_of").set_index("as_of")
    st.line_chart(eri_df[["eri"]])
    st.dataframe(eri_df.tail(25), use_container_width=True)
except Exception as e:
    st.error(str(e))



st.divider()
st.header("Board View")

# Vendor health proxy: lower latency means healthier vendor network
latest_vendor_latency = float(df["vendor_latency_ms"].iloc[-1])
vendor_capacity = max(0.0, 1000.0 - latest_vendor_latency)

base_state = SystemState(
    ops_queue_depth=float(df["ops_queue_depth"].iloc[-1]),
    review_throughput_per_hr=float(df["review_throughput_per_hr"].iloc[-1]),
    override_rate_per_hr=float(df["override_rate_per_hr"].iloc[-1]),
    vendor_capacity=vendor_capacity,
    sla_compliance=float(1.0 - df["sla_breach_rate"].iloc[-1]),
)

render_board_view(base_state)
