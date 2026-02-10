import streamlit as st
import numpy as np

def _clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def _money(x: float) -> str:
    return f"${x:,.0f}"

def render_board_view(
    *,
    defaults: dict,
    outlook: dict,
) -> dict:
    """
    Renders the Board View and returns the chosen scenario inputs plus computed impact.

    defaults keys (expected):
      vendor_capacity_base (float)
      review_throughput_base (float)
      manual_overrides_base (float)
      churn_base (float 0..1)
      breached_accounts_base (float)
      avg_contract_value (float)
      sla_penalty_per_acct (float)
      overtime_hours (float)
      overtime_rate (float)

    outlook keys (expected):
      eri (float)
      top_choke_point (str)
      predicted_first_sla_degrade_or_fail (str)
      ttf_days (float)
      failure_prob (float 0..1)
    """

    st.header("Board View")

    st.subheader("What-If Controls")

    # Multipliers relative to baseline (keeps UI consistent across datasets)
    c1, c2, c3 = st.columns(3)

    with c1:
        vendor_mult = st.slider(
            "Vendor Capacity",
            min_value=0.50,
            max_value=2.00,
            value=1.00,
            step=0.05,
        )

    with c2:
        throughput_mult = st.slider(
            "Review Throughput",
            min_value=0.50,
            max_value=2.00,
            value=1.00,
            step=0.05,
        )

    with c3:
        overrides_mult = st.slider(
            "Manual Overrides",
            min_value=0.00,
            max_value=2.00,
            value=1.00,
            step=0.05,
        )

    st.divider()
    st.subheader("90-Day Outlook")

    o1, o2, o3 = st.columns([1, 1, 1])
    with o1:
        st.metric("Escalation Risk Index", f"{outlook.get('eri', 0.0):.3f}")
        st.caption(f"Failure Prob (horizon): {outlook.get('failure_prob', 0.0):.0%}")
        st.caption(f"Time To Failure: {outlook.get('ttf_days', 0.0):.1f} days")
    with o2:
        st.metric("Top Choke Point", outlook.get("top_choke_point", ""))
    with o3:
        st.metric("Predicted First SLA Degrade", outlook.get("predicted_first_sla_degrade_or_fail", ""))

    st.divider()
    st.subheader("Financial Impact")

    # Baselines from data
    churn_base = float(defaults.get("churn_base", 0.10))
    breached_base = float(defaults.get("breached_accounts_base", 50))
    acv = float(defaults.get("avg_contract_value", 250000))
    sla_penalty = float(defaults.get("sla_penalty_per_acct", 15000))
    ot_hours = float(defaults.get("overtime_hours", 100))
    ot_rate = float(defaults.get("overtime_rate", 120))

    # Scenario churn model: shifts from baseline using the multipliers
    # Higher overrides increases churn, higher capacity and throughput reduce churn.
    churn_shift = (
        + 0.25 * (overrides_mult - 1.0)
        - 0.20 * (throughput_mult - 1.0)
        - 0.15 * (vendor_mult - 1.0)
    )
    churn_scenario = _clip01(churn_base + churn_shift)

    # Breached accounts scale with "stress": more overrides and lower throughput/capacity increases breaches
    stress = (
        1.0
        + 0.35 * max(0.0, overrides_mult - 1.0)
        + 0.25 * max(0.0, 1.0 - throughput_mult)
        + 0.20 * max(0.0, 1.0 - vendor_mult)
    )
    breached_scenario = max(0.0, breached_base * stress)

    # Inputs (user can still change financial assumptions)
    breached_accounts = st.number_input("Breached Accounts (est.)", min_value=0.0, value=float(breached_scenario), step=10.0)
    avg_contract_value = st.number_input("Avg Contract Value ($/yr)", min_value=0.0, value=float(acv), step=5000.0)
    sla_penalty_per_acct = st.number_input("SLA Penalty ($/acct)", min_value=0.0, value=float(sla_penalty), step=500.0)
    churn_probability = st.slider("Churn Probability", 0.0, 1.0, float(churn_scenario), 0.01)
    overtime_hours = st.number_input("Overtime Hours", min_value=0.0, value=float(ot_hours), step=10.0)
    overtime_rate = st.number_input("Overtime Rate ($/hr)", min_value=0.0, value=float(ot_rate), step=5.0)

    # Costs
    penalty_cost = breached_accounts * sla_penalty_per_acct
    churn_cost = breached_accounts * avg_contract_value * churn_probability
    overtime_cost = overtime_hours * overtime_rate
    total_impact = penalty_cost + churn_cost + overtime_cost

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Penalty Cost", _money(penalty_cost))
    with k2:
        st.metric("Churn Cost", _money(churn_cost))
    with k3:
        st.metric("Overtime Cost", _money(overtime_cost))
    with k4:
        st.metric("Total Impact", _money(total_impact))

    return {
        "vendor_mult": float(vendor_mult),
        "throughput_mult": float(throughput_mult),
        "overrides_mult": float(overrides_mult),
        "churn_probability": float(churn_probability),
        "breached_accounts": float(breached_accounts),
        "avg_contract_value": float(avg_contract_value),
        "sla_penalty_per_acct": float(sla_penalty_per_acct),
        "overtime_hours": float(overtime_hours),
        "overtime_rate": float(overtime_rate),
        "penalty_cost": float(penalty_cost),
        "churn_cost": float(churn_cost),
        "overtime_cost": float(overtime_cost),
        "total_impact": float(total_impact),
        "churn_base": float(churn_base),
        "breached_base": float(breached_base),
    }
