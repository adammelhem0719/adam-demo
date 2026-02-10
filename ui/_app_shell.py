from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



import streamlit as st
import pandas as pd
import os

from state import load_data
from adam_core.config import load_ontology

st.set_page_config(page_title="ADAM Console", layout="wide")

# Load ontology once
if "ont" not in st.session_state:
    st.session_state.ont = load_ontology("config/ontology.yaml")

st.sidebar.title("ADAM Console")
st.sidebar.caption("Enterprise Risk Intelligence")

# Data loading (sidebar uploader handled inside load_data)
df = load_data()

# If user did not upload, fall back to demo dataset once
if df is None:
    demo_path = os.path.join("data", "arcadian_cloud_systems_timeseries.csv")
    try:
        df = pd.read_csv(demo_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        st.session_state.data = df
        st.sidebar.info("Using demo dataset from repo.")
    except Exception as e:
        st.sidebar.error(f"Demo dataset load failed: {e}")

# Shared controls
st.sidebar.divider()
horizon = st.sidebar.slider(
    "Forecast horizon (days)",
    min_value=7,
    max_value=60,
    value=int(st.session_state.ont.forecast_horizon_days),
    step=1,
)
st.session_state.horizon_days = int(horizon)

st.sidebar.divider()
if st.session_state.get("data") is None:
    st.sidebar.warning("No data loaded yet.")
else:
    st.sidebar.success("Data loaded.")
    st.sidebar.caption(f"Rows: {len(st.session_state.data):,}")

# Landing page
st.title("ADAM Console")
st.caption("Use the left navigation to open Risk Vitals, Financial Churn, or AI Agents.")
