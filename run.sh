#!/bin/bash
# Startup script for Misconception Tutor Web Application

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Repair partially-created environments as well as newly-created ones.
if ! .venv/bin/python -c "import flask" >/dev/null 2>&1; then
    echo "Installing Python dependencies..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi

echo "=================================================="
echo " Starting Misconception Tutor Web Application..."
echo " http://localhost:8000"
echo "=================================================="

PYTHONPATH=src:. .venv/bin/python -m backend.api
