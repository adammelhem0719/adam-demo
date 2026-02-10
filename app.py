from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import os

from adam_core.config import load_ontology

st.set_page_config(page_title="ADAM Console", layout="wide")

# Shared state init
if "ont" not in st.session_state:
    st.session_state.ont = load_ontology("config/ontology.yaml")

st.sidebar.title("ADAM Console")
st.sidebar.caption("Enterprise Risk Intelligence")

# Data load (upload or demo)
uploaded = st.sidebar.file_uploader("Upload Company CSV", type=["csv"])

if uploaded is None:
    demo_path = os.path.join("data", "arcadian_cloud_systems_timeseries.csv")
    df = pd.read_csv(demo_path)
else:
    df = pd.read_csv(uploaded)

if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

st.session_state.data = df

horizon = st.sidebar.slider("Forecast horizon (days)", 7, 60, int(st.session_state.ont.forecast_horizon_days), 1)
st.session_state.horizon_days = int(horizon)

st.sidebar.success("Data loaded.")
st.sidebar.caption(f"Rows: {len(df):,}")

risk_vitals = st.Page("ui/pages/1_Risk_Vitals.py", title="Risk Vitals", icon="🛡️")
financial_churn = st.Page("ui/pages/2_Financial_Churn.py", title="Financial Churn", icon="💸")
ai_agents = st.Page("ui/pages/3_AI_Agents.py", title="AI Agents", icon="🤖")

# Order matters: first item becomes the default view on launch
nav = st.navigation([risk_vitals, financial_churn, ai_agents], position="sidebar")
nav.run()

