"""Serve the fine-tuned adapter as an OpenAI-compatible API on Modal (GPU, scales to zero).

This is the *model* only. The light web app (Flask + UI) runs on any free CPU host and talks to
this endpoint through LLM_BACKEND_URL / LLM_BACKEND_TOKEN.

    pip install modal && modal setup
    modal secret create tutor-model-secrets MODEL_SERVER_TOKEN=<long-random-string>
    modal deploy modal_app.py
    curl https://<your-workspace>--misconception-tutor-model-serve.modal.run/health

Run ``git lfs pull`` first so LLM/adapter_model.safetensors is the real 139 MB file, not a pointer.
Modal bills per second of GPU time from your monthly credits; check modal.com/pricing for the
current free allowance.
"""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent

app = modal.App("misconception-tutor-model")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("flask", "unsloth", "huggingface_hub")
    .add_local_dir(
        ROOT / "LLM",
        "/root/LLM",
        copy=True,
        ignore=["checkpoint-*", "data", "*.ipynb", "*.md"],
    )
)


@app.function(
    image=image,
    gpu="L4",
    timeout=900,
    scaledown_window=300,  # keep the GPU warm for 5 minutes after the last request
    max_containers=1,
    secrets=[modal.Secret.from_name("tutor-model-secrets")],
    env={"LLM_ADAPTER_PATH": "/root/LLM", "LLM_GEN_BACKEND": "unsloth"},
)
@modal.concurrent(max_inputs=4)
@modal.wsgi_app()
def serve():
    import sys

    sys.path.insert(0, "/root/LLM")
    from serve import model_server

    model_server.load_model()  # blocks until the adapter is on the GPU
    return model_server.app
