# Architecture (Enterprise)
## Components
1. **Ingestion**: control-health metrics from observability/GRC/Ops tools.
2. **Normalizer**: converts metrics -> discrete states + continuous pressure.
3. **Propagation Simulator**: graph-based simulation with delays & amplification.
4. **ERI + Explanation**: probability-weighted index + choke points.
5. **API + UI**: FastAPI integration surface; Streamlit analyst console.

## Minimal CSV Contract
Required columns:
- timestamp
- vendor_latency_ms
- ops_queue_depth
- override_rate_per_hr
- review_throughput_per_hr
- sla_breach_rate
