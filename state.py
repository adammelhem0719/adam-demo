import streamlit as st
import pandas as pd
import numpy as np

def load_data():
    """
    Sidebar CSV uploader. Stores df in st.session_state.data.
    Expects a 'timestamp' column.
    """
    if "data" not in st.session_state:
        st.session_state.data = None

    uploaded = st.sidebar.file_uploader(
        "Upload Company CSV",
        type=["csv"]
    )

    if uploaded is not None:
        df = pd.read_csv(uploaded)

        # Timestamp parsing
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df = df.dropna(subset=["timestamp"])
            df = df.sort_values("timestamp")
        else:
            # If no timestamp, keep as-is but warn later in pages
            pass

        st.session_state.data = df

    return st.session_state.data


def get_numeric_signal_columns(df: pd.DataFrame) -> list[str]:
    """
    Returns numeric columns that can be treated as risk signals.
    Excludes timestamp-like columns.
    """
    if df is None or df.empty:
        return []

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    drop = set([c for c in numeric_cols if c.lower() in {"timestamp", "time", "date"}])
    return [c for c in numeric_cols if c not in drop]


def compute_company_risk_score(df: pd.DataFrame) -> tuple[int, str, float]:
    """
    Overall Company Risk Score: 0-100.
    Uses latest row and averages numeric signals.
    If signals look like 0..1 probabilities, scales to 0..100.
    Returns (score_int, label, raw_mean).
    """
    if df is None or df.empty:
        return 0, "No Data", 0.0

    signals = get_numeric_signal_columns(df)
    if not signals:
        return 0, "No Numeric Signals", 0.0

    latest = df.iloc[-1]
    vals = latest[signals].astype(float).to_numpy()
    vals = vals[~np.isnan(vals)]

    if len(vals) == 0:
        return 0, "No Numeric Signals", 0.0

    raw_mean = float(np.mean(vals))

    # Auto scale
    if 0.0 <= float(np.min(vals)) and float(np.max(vals)) <= 1.0:
        score = int(round(raw_mean * 100))
    else:
        score = int(round(raw_mean))
        score = max(0, min(100, score))

    if score >= 80:
        label = "Critical"
    elif score >= 60:
        label = "High"
    elif score >= 40:
        label = "Moderate"
    else:
        label = "Low"

    return score, label, raw_mean


def categorize_risk_severity(score: int) -> dict:
    """
    Helper for consistent UI messaging.
    """
    if score >= 80:
        return {"status": "Critical", "ui": "error"}
    if score >= 60:
        return {"status": "High", "ui": "warning"}
    if score >= 40:
        return {"status": "Moderate", "ui": "info"}
    return {"status": "Low", "ui": "success"}
