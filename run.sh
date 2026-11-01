#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then echo 'Python 3.11–3.13 is required.'; exit 1; fi
if ! command -v npm >/dev/null; then echo 'Node.js 20.19+ or 22.12+ is required.'; exit 1; fi
if [ ! -x backend/.venv/bin/python ]; then python3 -m venv backend/.venv; fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
(cd backend && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m app.cli prepare)
(cd frontend && npm ci)
pids=()
cleanup() { trap - EXIT INT TERM; for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd backend && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000) & pids+=("$!")
(cd frontend && npm run dev) & pids+=("$!")
printf '\nHelioGrid: http://localhost:5173\nAPI docs: http://localhost:8000/api/docs\nPress Ctrl+C to stop both processes.\n\n'
wait -n
