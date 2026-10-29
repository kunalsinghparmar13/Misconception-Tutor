#!/bin/bash
# Startup script for Misconception Tutor Web Application

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "=================================================="
echo " Starting Misconception Tutor Web Application..."
echo " http://localhost:8000"
echo "=================================================="

PYTHONPATH=. .venv/bin/python backend/api.py
