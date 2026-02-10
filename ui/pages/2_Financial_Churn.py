from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import numpy as np
import pandas as pd

from adam_core.simulator import forecast
from adam_core.eri import compute_eri
from board_view import render_board_view

st.title("Financial Churn")

df = st.session_state.get("data")
ont = st.session_state.get("ont")
horizon_days = st.session_state.get("horizon_days", 14)

if df is None or df.empty or ont is None:
    st.warning("Missing data or ontology. Upload data in the sidebar.")
    st.stop()

latest = df.iloc[-1]

def num(col: str, default: float) -> float:
    if col in df.columns:
        try:
            return float(latest[col])
        except Exception:
            return default
    return default

# -------------------------
# Operational signals (best effort)
# -------------------------
queue = num("ops_queue_depth", 0.0)
sla_breach = float(np.clip(num("sla_breach_rate", 0.0), 0.0, 1.0))
throughput = num("review_throughput_per_hr", 0.0)
overrides = num("override_rate_per_hr", 0.0)
latency = num("vendor_latency_ms", np.nan)

# -------------------------
# Forecast from actual uploaded data
# -------------------------
fr = forecast(df, ont, start_time=None, horizon_days=int(horizon_days))
probs = fr.series[0].probabilities if fr.series else {}
ttf = float(fr.summary.get("time_to_failure_days") or horizon_days)

eri_obj = compute_eri(probs, ont.impact_weights, ttf)
eri_val = float(eri_obj.eri)
failure_prob = float(probs.get("failed", 0.0))

# -------------------------
# Baseline churn derived from data + forecast (grounded but simple)
# -------------------------
base_churn = float(np.clip(
    0.10
    + 0.35 * failure_prob
    + 0.25 * sla_breach
    + 0.10 * (overrides / max(1.0, throughput + 1.0)),
    0.0,
    1.0
))

# Baseline exposure derived from data
breached_accounts_base = max(50.0, queue * 2.0)

# Financial defaults (can later be replaced with real columns if you have them)
avg_contract_value = 250000.0
sla_penalty_per_acct = 15000.0

# Overtime defaults derived from stress
overtime_hours = float(max(50.0, queue * 0.10))
overtime_rate = 120.0

# Vendor capacity proxy baseline (for scenario interpretation)
if not np.isnan(latency):
    vendor_capacity_base = max(0.0, 1000.0 - float(latency))
else:
    vendor_capacity_base = 500.0

defaults = {
    "vendor_capacity_base": vendor_capacity_base,
    "review_throughput_base": float(throughput),
    "manual_overrides_base": float(overrides),
    "churn_base": base_churn,
    "breached_accounts_base": breached_accounts_base,
    "avg_contract_value": avg_contract_value,
    "sla_penalty_per_acct": sla_penalty_per_acct,
    "overtime_hours": overtime_hours,
    "overtime_rate": overtime_rate,
}

outlook = {
    "eri": eri_val,
    "top_choke_point": fr.summary.get("top_choke_point", ""),
    "predicted_first_sla_degrade_or_fail": fr.summary.get("predicted_first_sla_degrade_or_fail", ""),
    "ttf_days": ttf,
    "failure_prob": failure_prob,
}

# -------------------------
# Top banner (simple)
# -------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Baseline Churn", f"{base_churn:.2f}")
with c2:
    st.metric("Failure Prob", f"{failure_prob:.0%}")
with c3:
    st.metric("Time To Failure", f"{ttf:.1f} days")
with c4:
    st.metric("Baseline Accounts At Risk", f"{int(breached_accounts_base):,}")

st.divider()

# -------------------------
# Main: Board View scenario controls
# -------------------------
scenario = render_board_view(defaults=defaults, outlook=outlook)

st.divider()

# -------------------------
# Graph: Projected Loss Over Time (returns to Financial Churn)
# -------------------------
st.subheader("Projected Loss Curve If No Intervention")

# We want the curve to steepen as:
# - ERI increases
# - time to failure is shorter
# - failure_prob is higher
total_impact = float(scenario["total_impact"])

days = np.arange(1, int(horizon_days) + 1)

# Shape parameters
risk_accel = float(np.clip(eri_val, 0.10, 3.00))
ttf_eff = float(max(1.0, ttf))
prob_eff = float(np.clip(failure_prob, 0.01, 0.99))

# Exponential ramp, normalized to end near total_impact
ramp = np.exp((days / ttf_eff) * risk_accel * prob_eff)
ramp = ramp / ramp.max()

loss_curve = total_impact * ramp

loss_df = pd.DataFrame({"Expected Loss": loss_curve}, index=days)
loss_df.index.name = "Day"

st.line_chart(loss_df, use_container_width=True)

st.caption("Curve updates with your scenario controls. It is anchored to forecast risk (ERI, time to failure, failure probability) and scaled to the scenario Total Impact.")

st.divider()

# -------------------------
# Scenario delta summary
# -------------------------
st.subheader("Scenario Delta")

delta_churn = float(scenario["churn_probability"] - scenario["churn_base"])
delta_breached = float(scenario["breached_accounts"] - scenario["breached_base"])

d1, d2, d3 = st.columns(3)
with d1:
    st.metric("Churn Change", f"{delta_churn:+.2f}")
with d2:
    st.metric("Breached Accounts Change", f"{delta_breached:+.0f}")
with d3:
    st.metric("Total Impact", f"${scenario['total_impact']:,.0f}")

st.caption("Baseline is derived from uploaded dataset plus forecast. Scenario is your slider-adjusted what-if.")
