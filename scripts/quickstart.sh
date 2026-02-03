#!/usr/bin/env bash
set -euo pipefail
python scripts/generate_synthetic_data.py --out data --days 180 --seed 7
uvicorn api.main:app --reload --port 8000
