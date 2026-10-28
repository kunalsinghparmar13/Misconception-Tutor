#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi

"$ROOT_DIR/.venv/bin/python" -m pip install -q -r "$ROOT_DIR/requirements.txt"
exec "$ROOT_DIR/.venv/bin/python" -m backend.api
