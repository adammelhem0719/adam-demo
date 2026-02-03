import streamlit as st

from adam_core.simulator import SystemState, WhatIfControls, apply_controls, compute_eri
from adam_core.finance import FinanceInputs, estimate_impact


def render_board_view(base_state: SystemState):
    st.title("Board View")

    st.subheader("What-If Controls")
    c1, c2, c3 = st.columns(3)
    with c1:
        vendor_mult = st.slider("Vendor Capacity", 0.5, 2.0, 1.0, 0.05)
    with c2:
        thr_mult = st.slider("Review Throughput", 0.5, 2.0, 1.0, 0.05)
    with c3:
        ov_mult = st.slider("Manual Overrides", 0.0, 2.0, 1.0, 0.05)

    ctl = WhatIfControls(
        vendor_capacity_multiplier=vendor_mult,
        throughput_multiplier=thr_mult,
        overrides_multiplier=ov_mult,
    )
    new_state = apply_controls(base_state, ctl)
    eri = compute_eri(new_state)

    st.subheader("90-Day Outlook")
    m1, m2, m3 = st.columns(3)
    m1.metric("Escalation Risk Index", f"{eri:.3f}")
    m2.metric("Top Choke Point", "Manual Overrides" if ov_mult >= 1.0 else "Queue Load")
    m3.metric("Predicted First SLA Degrade", "Demo (wire model later)")

    st.subheader("Financial Impact (Demo Assumptions)")
    breached_accounts = st.number_input("Breached Accounts (est.)", min_value=0, value=120, step=10)
    avg_contract_value = st.number_input("Avg Contract Value ($/yr)", min_value=0.0, value=250000.0, step=10000.0)
    sla_penalty = st.number_input("SLA Penalty ($/acct)", min_value=0.0, value=15000.0, step=1000.0)
    churn_prob = st.slider("Churn Probability", 0.0, 1.0, 0.12, 0.01)
    overtime_hours = st.number_input("Overtime Hours", min_value=0.0, value=400.0, step=10.0)
    overtime_rate = st.number_input("Overtime Rate ($/hr)", min_value=0.0, value=120.0, step=5.0)

    out = estimate_impact(FinanceInputs(
        breached_accounts=int(breached_accounts),
        avg_contract_value=float(avg_contract_value),
        sla_penalty_per_account=float(sla_penalty),
        churn_probability=float(churn_prob),
        overtime_hours=float(overtime_hours),
        overtime_rate=float(overtime_rate),
    ))

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Penalty Cost", f"${out.penalty_cost:,.0f}")
    a2.metric("Churn Cost", f"${out.churn_cost:,.0f}")
    a3.metric("Overtime Cost", f"${out.overtime_cost:,.0f}")
    a4.metric("Total Impact", f"${out.total_impact:,.0f}")

    st.divider()

    if st.button("Simulate Intervention"):
        auto_ctl = WhatIfControls(
            vendor_capacity_multiplier=1.15,
            throughput_multiplier=1.10,
            overrides_multiplier=0.70,
        )
        improved = apply_controls(base_state, auto_ctl)
        new_eri = compute_eri(improved)
        st.success(f"Intervention applied. New ERI: {new_eri:.3f}")
