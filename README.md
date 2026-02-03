# ADAM (Enterprise-Ready Reference Implementation)
**Adam** is a control-health, propagation-simulation, and escalation-forecasting system.
This repository is a **production-style reference implementation** using **realistic synthetic data** for a fake company.

> Adam watches control health (not customer data), normalizes metrics into control states, simulates propagation,
> and outputs an **Escalation Risk Index (ERI)** plus **actionable choke-point explanations**.

## Contents
- `data/` synthetic company datasets (CSV) + scenario config
- `config/ontology.yaml` control ontology + thresholds
- `adam_core/` core engine (states, graph, simulator, ERI)
- `api/` FastAPI service (enterprise integration surface)
- `ui/` Streamlit UI (demo & analyst console)
- `tests/` unit tests
- `docker/` Dockerfiles + `docker-compose.yml`

## Quickstart (Local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/generate_synthetic_data.py --out data --days 180 --seed 7

uvicorn api.main:app --reload --port 8000
# optional UI
streamlit run ui/app.py
```

Open:
- API docs: http://localhost:8000/docs
- UI: http://localhost:8501

## Demo Narrative (what to show)
1. Load the synthetic company dataset.
2. Run **Forecast** for next 14 days: show ERI, predicted failure time, and choke points.
3. Run **Replay** for a known historical incident window: show Adam would have warned days earlier.

## License
MIT (reference implementation).
