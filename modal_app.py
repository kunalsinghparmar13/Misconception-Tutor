"""Deploy Misconception Tutor and the Gemma adapter on Modal.

Deploy from the repository root:

    modal deploy modal_app.py

The public URL printed by Modal serves the existing Flask UI and API.
"""

from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
APP_NAME = "misconception-tutor"
ADAPTER_ID = "kunalsinghparmar/misconception-tutor-gemma4-e4b"
BASE_MODEL = "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit"

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
    env={
        "PYTHONPATH": "/root/misconception-tutor/src:/root/misconception-tutor",
        "LLM_ADAPTER_ID": ADAPTER_ID,
        "LLM_BASE_MODEL": BASE_MODEL,
        "LLM_ONLY_MODEL": "1",
        "BACKEND_HOST": "0.0.0.0",
        "PORT": "8000",
    },
)
@modal.concurrent(max_inputs=8)
@modal.wsgi_app()
def flask_app():
    import os
    import sys

    os.chdir("/root/misconception-tutor")
    sys.path.insert(0, "/root/misconception-tutor/src")
    sys.path.insert(0, "/root/misconception-tutor")

    from backend.api import app as web_app

    return web_app
