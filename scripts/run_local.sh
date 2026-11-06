#!/usr/bin/env bash
# Run Misconception Tutor on your own computer (http://localhost:8000). Nothing is deployed.
#
#   export LLM_BACKEND_URL=https://xxxx.trycloudflare.com   # your model server (Kaggle notebook / Modal / your GPU PC)
#   export LLM_BACKEND_TOKEN=...                             # the token it printed
#   ./scripts/run_local.sh
#
# Or save those two lines (LLM_BACKEND_URL=... and LLM_BACKEND_TOKEN=...) in .env.kaggle and just run the script.
set -euo pipefail
cd "$(dirname "$0")/.."

# Optional: put LLM_BACKEND_URL / LLM_BACKEND_TOKEN in .env.kaggle (git-ignored) instead of exporting them.
if [ -z "${LLM_BACKEND_URL:-}" ] && [ -f .env.kaggle ]; then
  set -a; . ./.env.kaggle; set +a
fi

if [ -z "${LLM_BACKEND_URL:-}" ]; then
  echo "Set LLM_BACKEND_URL (and LLM_BACKEND_TOKEN) to your model server first. See docs/DEPLOY_FREE.md." >&2
  exit 1
fi

if [ ! -d .venv ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q -r requirements.txt

export LLM_ONLY_MODEL="${LLM_ONLY_MODEL:-1}"
export APP_ENV="${APP_ENV:-development}"
export BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"
export PYTHONPATH="src:.:LLM"

echo "Open http://localhost:${PORT}  (Ctrl+C to stop)"
exec python -m backend.api
