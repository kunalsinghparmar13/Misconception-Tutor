"""Deploy Misconception Tutor with persistent SQLite storage."""

from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parent

APP_NAME = "misconception-tutor"

ADAPTER_ID = "kunalsinghparmar/misconception-tutor-gemma4-e4b"

BASE_MODEL = "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit"

DB_VOLUME_NAME = "misconception-tutor-data"

db_volume = modal.Volume.from_name(
    DB_VOLUME_NAME,
    create_if_missing=True,
)

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "flask",
        "requests",
        "pandas",
        "scikit-learn",
        "torch",
        "transformers>=5.0.0",
        "peft>=0.21.0",
        "huggingface_hub>=0.30.0",
        "bitsandbytes>=0.46.1",
        "accelerate",
    )
    .add_local_dir(
        ROOT,
        "/root/misconception-tutor",
        copy=True,
        ignore=[
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            "*.db",
            "*.db-*",
            "LLM/checkpoint-*",
            "LLM/data/continuous_training_dataset.jsonl",
        ],
    )
)


@app.function(
    image=image,
    gpu="L4",
    timeout=900,
    scaledown_window=300,
    max_containers=1,
    volumes={
        "/mnt/tutor-data": db_volume,
    },
    env={
        "PYTHONPATH": (
            "/root/misconception-tutor/src:"
            "/root/misconception-tutor"
        ),
        "LLM_ADAPTER_ID": ADAPTER_ID,
        "LLM_BASE_MODEL": BASE_MODEL,
        "LLM_ONLY_MODEL": "1",
        "TUTOR_DB_PATH": "/mnt/tutor-data/tutor.db",
        "MODAL_DB_VOLUME": DB_VOLUME_NAME,
        "BACKEND_HOST": "0.0.0.0",
        "PORT": "8000",
    },
    # Add the HF secret here if your base model or adapter
    # requires authenticated access.
    secrets=[
        modal.Secret.from_name("huggingface-secret")
    ],
)
@modal.concurrent(max_inputs=1)
@modal.wsgi_app()
def flask_app():
    import os
    import sys

    os.chdir("/root/misconception-tutor")

    sys.path.insert(0, "/root/misconception-tutor/src")
    sys.path.insert(0, "/root/misconception-tutor")

    from backend.api import app as web_app

    return web_app