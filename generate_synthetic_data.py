from __future__ import annotations
import argparse
import os
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))

def generate(days: int = 180, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2025, 7, 1, tzinfo=timezone.utc)
    timestamps = [start + timedelta(hours=6*i) for i in range(int(days * 24 / 6))]
    n = len(timestamps)

    # --- Exogenous driver: upstream/vendor degradation (slow burn) ---
    day_index = np.array([(ts - start).total_seconds() / (3600*24) for ts in timestamps])
    ramp_center = 120.0                      # incident forms late in the window
    ramp = _sigmoid((day_index - ramp_center) / 5.0)  # 0 -> 1 smoothly

    vendor_latency = np.clip(rng.normal(180, 18, size=n), 110, 260)
    vendor_latency += 520 * ramp
    vendor_latency += rng.normal(0, 18, size=n)
    vendor_latency = np.clip(vendor_latency, 90, 2000)

    # --- Endogenous controls: designed to be stable pre-ramp ---
    ops_queue = np.zeros(n)
    overrides = np.zeros(n)
    throughput = np.zeros(n)
    sla_breach = np.zeros(n)

    # Baselines (healthy)
    ops_queue[0] = 180
    overrides[0] = 1.2
    throughput[0] = 130
    sla_breach[0] = 0.0009

    for i in range(1, n):
        # Convert vendor latency into a bounded stress signal (0..1)
        v_stress = np.clip((vendor_latency[i] - 250) / 700, 0.0, 1.2)

        # Ops queue rises modestly with stress; otherwise mean-reverts
        ops_queue[i] = 0.985 * ops_queue[i-1] + 10 + 160 * v_stress + rng.normal(0, 10)
        ops_queue[i] = np.clip(ops_queue[i], 60, 5000)

        # Overrides rise when queue is high and stress is present; otherwise stable
        overrides_target = 1.2 + 0.004 * max(0, ops_queue[i] - 250) + 3.5 * v_stress
        overrides[i] = 0.92 * overrides[i-1] + 0.08 * overrides_target + rng.normal(0, 0.15)
        overrides[i] = np.clip(overrides[i], 0.2, 60)

        # Throughput declines with overrides + stress; otherwise mean-reverts to ~130
        throughput_target = 132 - 1.6 * overrides[i] - 10 * v_stress
        throughput[i] = 0.90 * throughput[i-1] + 0.10 * throughput_target + rng.normal(0, 2.0)
        throughput[i] = np.clip(throughput[i], 25, 160)

        # SLA breach stays low unless queue + low throughput persist
        breach_pressure = 0.0000035 * max(0, ops_queue[i] - 300) + 0.00014 * max(0, 95 - throughput[i]) + 0.0095 * v_stress
        sla_breach[i] = 0.93 * sla_breach[i-1] + 0.07 * (0.0008 + breach_pressure) + rng.normal(0, 0.00025)
        sla_breach[i] = float(np.clip(sla_breach[i], 0.0, 0.12))

    # Extra observability metrics (nice for demos)
    error_rate = np.clip(0.15 + 3.2 * np.clip((vendor_latency - 200) / 900, 0, 2) + rng.normal(0, 0.12, n), 0.0, 12.0)
    cpu_util = np.clip(32 + 22 * ramp + rng.normal(0, 3.5, n), 8, 98)

    incident_flag = (sla_breach >= 0.02).astype(int)

    df = pd.DataFrame({
        "timestamp": [t.isoformat() for t in timestamps],
        "vendor_latency_ms": np.round(vendor_latency, 2),
        "ops_queue_depth": np.round(ops_queue, 0).astype(int),
        "override_rate_per_hr": np.round(overrides, 2),
        "review_throughput_per_hr": np.round(throughput, 1),
        "sla_breach_rate": np.round(sla_breach, 6),
        "error_rate_pct": np.round(error_rate, 3),
        "cpu_util_pct": np.round(cpu_util, 2),
        "incident_flag": incident_flag,
    })
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df = generate(days=args.days, seed=args.seed)

    out_csv = os.path.join(args.out, "arcadian_cloud_systems_timeseries.csv")
    df.to_csv(out_csv, index=False)

    df_ts = df.copy()
    df_ts["timestamp"] = pd.to_datetime(df_ts["timestamp"], utc=True)
    inc = df_ts[df_ts["sla_breach_rate"] >= 0.02]
    incident_time = inc["timestamp"].iloc[0].isoformat() if not inc.empty else df_ts["timestamp"].iloc[-1].isoformat()

    meta = {
        "company": "Arcadian Cloud Systems",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": args.days,
        "seed": args.seed,
        "suggested_incident_time": incident_time,
        "notes": "incident_flag is 1 when sla_breach_rate >= 0.02; suggested_incident_time is first crossing.",
    }
    with open(os.path.join(args.out, "dataset_meta.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(meta, f, indent=2)

    print("Wrote:", out_csv)
    print("Suggested incident_time:", incident_time)

if __name__ == "__main__":
    main()
