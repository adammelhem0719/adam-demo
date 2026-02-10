import streamlit as st
import pandas as pd
from datetime import datetime, timezone

st.title("AI Agents")

def log_event(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    st.session_state.agent_audit.append(f"[{ts}] {msg}")

# Initialize state
if "agent_registry" not in st.session_state:
    st.session_state.agent_registry = []

if "agent_audit" not in st.session_state:
    st.session_state.agent_audit = []

# Seed demo agents one time
if "demo_agents_seeded" not in st.session_state:
    st.session_state.demo_agents_seeded = True

    demo_agents = [
        {
            "name": "triage_router",
            "owner": "risk_ops",
            "scopes": "Read Risk, Write Risk",
            "status": "active",
            "purpose": "Auto routes incidents to the right queue and owner based on severity and control mapping.",
        },
        {
            "name": "evidence_collector",
            "owner": "grc",
            "scopes": "Read Risk",
            "status": "active",
            "purpose": "Pulls audit evidence from logs, tickets, and runbooks to reduce manual compliance packaging.",
        },
        {
            "name": "sla_guardian",
            "owner": "ops",
            "scopes": "Read Risk, Deploy",
            "status": "active",
            "purpose": "Monitors SLA signals and triggers mitigation playbooks when degradation risk crosses threshold.",
        },
        {
            "name": "vendor_anomaly_monitor",
            "owner": "platform",
            "scopes": "Read Risk",
            "status": "active",
            "purpose": "Detects vendor latency anomalies and correlates with queue depth and override spikes.",
        },
        {
            "name": "churn_intervention_planner",
            "owner": "finance_ops",
            "scopes": "Read Finance, Write Finance",
            "status": "active",
            "purpose": "Recommends retention interventions and calculates expected churn savings and penalty avoidance.",
        },
    ]

    # Only seed if registry is empty
    if len(st.session_state.agent_registry) == 0:
        st.session_state.agent_registry = demo_agents
        log_event("Seeded demo enterprise agents.")

st.subheader("Agent Registry")

if len(st.session_state.agent_registry) == 0:
    st.info("No agents registered yet.")
else:
    reg_df = pd.DataFrame(st.session_state.agent_registry)
    st.dataframe(reg_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Register Agent")

with st.container(border=True):
    name = st.text_input("Agent Name", placeholder="invoice_reconciler")
    owner = st.text_input("Owner", placeholder="finance_ops")
    scopes = st.multiselect(
        "Allowed Scopes",
        ["Read Risk", "Write Risk", "Read Finance", "Write Finance", "Deploy", "Admin"],
        default=["Read Risk"]
    )
    purpose = st.text_area("Purpose", placeholder="What does this agent do and what manual work does it reduce?")

    c1, c2 = st.columns([1, 2])
    with c1:
        register = st.button("Register", type="primary")
    with c2:
        reset_demo = st.button("Reset Demo Agents")

    if register:
        if not name.strip():
            st.error("Agent Name is required.")
        else:
            st.session_state.agent_registry.append({
                "name": name.strip(),
                "owner": owner.strip() or "unknown",
                "scopes": ", ".join(scopes),
                "status": "active",
                "purpose": purpose.strip() or "Not specified",
            })
            log_event(f"Registered agent '{name.strip()}' (owner={owner.strip() or 'unknown'})")
            st.success("Agent registered.")

    if reset_demo:
        st.session_state.agent_registry = []
        st.session_state.demo_agents_seeded = False
        st.success("Demo agents cleared. Reloading will seed again.")
        st.rerun()

st.divider()

st.subheader("Manage Agents")

if len(st.session_state.agent_registry) > 0:
    names = [a["name"] for a in st.session_state.agent_registry]
    selected = st.selectbox("Select agent", names)
    idx = names.index(selected)
    agent = st.session_state.agent_registry[idx]

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        new_status = st.selectbox("Status", ["active", "inactive"], index=0 if agent["status"] == "active" else 1)
    with c2:
        delete = st.button("Delete Agent")
    with c3:
        st.caption("Status changes apply immediately.")

    if new_status != agent["status"]:
        agent["status"] = new_status
        log_event(f"Updated status for '{agent['name']}' -> {new_status}")
        st.success("Status updated.")

    if delete:
        log_event(f"Deleted agent '{agent['name']}'")
        st.session_state.agent_registry.pop(idx)
        st.success("Deleted.")
        st.rerun()

st.divider()

st.subheader("Audit Log")

if len(st.session_state.agent_audit) == 0:
    st.info("No audit events yet.")
else:
    for line in reversed(st.session_state.agent_audit[-50:]):
        st.write(line)
