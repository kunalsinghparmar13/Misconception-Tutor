"""OpenAI-compatible HTTP server for the fine-tuned Gemma adapter.

Run this wherever a GPU is available (a free Kaggle/Colab notebook, Modal, your own machine):

    python LLM/serve/model_server.py            # loads the adapter, serves on :8001

then point the web app at it:

    LLM_BACKEND_URL=https://<your-tunnel-or-host>      LLM_BACKEND_TOKEN=<MODEL_SERVER_TOKEN>

Endpoints
    GET  /health                 liveness + whether the model is loaded
    GET  /v1/models              model list (OpenAI style)
    POST /v1/chat/completions    chat completion (non-streaming)

Environment
    MODEL_SERVER_TOKEN   if set, /v1/* require ``Authorization: Bearer <token>``
    LLM_ADAPTER_PATH     adapter folder or Hugging Face repo id (default: ``LLM/`` in this repo)
    LLM_GEN_BACKEND      ``unsloth`` (default, same stack as tutor-project.ipynb) or ``peft``
    MODEL_BACKEND=stub   skip loading; answer with a fixed string (to test networking only)
    PORT                 default 8001
"""

from __future__ import annotations

import hmac
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, request

LLM_DIR = Path(__file__).resolve().parents[1]
if str(LLM_DIR) not in sys.path:
    sys.path.insert(0, str(LLM_DIR))

MAX_TOKENS_CAP = 1024
KEEPALIVE_SECONDS = 15
MAX_PROMPT_CHARS = 24_000
ALLOWED_ROLES = {"system", "user", "assistant"}

app = Flask(__name__)
_state: Dict[str, Any] = {"backend": None, "error": None, "loading": False}
_state_lock = threading.Lock()
_queue_lock = threading.Lock()
_waiting = 0  # requests running or queued for the single GPU
MAX_WAITING = int(os.getenv("MODEL_MAX_QUEUE", "3"))


def model_name() -> str:
    return os.getenv("LLM_MODEL_NAME", "misconception-tutor-gemma4-e4b")


class _StubBackend:
    name = "stub"

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 64, temperature: float = 0.0) -> str:
        return "stub reply: the model server is reachable, but no model is loaded (MODEL_BACKEND=stub)."


def load_model() -> None:
    """Load the adapter once (blocking). Safe to call several times."""
    with _state_lock:
        if _state["backend"] is not None:
            return
        _state["loading"] = True
    try:
        if os.getenv("MODEL_BACKEND", "").lower() == "stub":
            backend: Any = _StubBackend()
        else:
            from tutor_agents.backends import load_backend

            backend = load_backend()
        with _state_lock:
            _state.update(backend=backend, error=None)
    except Exception as exc:  # noqa: BLE001 - surface the reason via /health
        with _state_lock:
            _state["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        with _state_lock:
            _state["loading"] = False


def _authorized() -> bool:
    token = os.getenv("MODEL_SERVER_TOKEN", "").strip()
    if not token:
        return True
    header = request.headers.get("Authorization", "")
    supplied = header[7:].strip() if header.lower().startswith("bearer ") else request.headers.get("X-Admin-Token", "")
    return hmac.compare_digest(supplied.encode(), token.encode())


def _validate(payload: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(payload, dict):
        return None, "JSON body required."
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return None, "'messages' must be a non-empty list."
    clean: List[Dict[str, str]] = []
    total = 0
    for m in messages:
        if not isinstance(m, dict) or m.get("role") not in ALLOWED_ROLES or not isinstance(m.get("content"), str):
            return None, "Each message needs a role (system/user/assistant) and string content."
        total += len(m["content"])
        clean.append({"role": m["role"], "content": m["content"]})
    if total > MAX_PROMPT_CHARS:
        return None, f"Prompt too long ({total} > {MAX_PROMPT_CHARS} characters)."
    try:
        max_tokens = max(1, min(int(payload.get("max_tokens") or 512), MAX_TOKENS_CAP))
        temperature = max(0.0, min(float(payload.get("temperature", 0.2)), 1.5))
    except (TypeError, ValueError):
        return None, "max_tokens must be an integer and temperature a number."
    return {"messages": clean, "max_tokens": max_tokens, "temperature": temperature}, None


@app.get("/health")
@app.get("/api/health")
def health():
    with _state_lock:
        backend, error, loading = _state["backend"], _state["error"], _state["loading"]
    return jsonify({
        "status": "ok" if backend is not None else ("loading" if loading else "no_model"),
        "model_loaded": backend is not None,
        "model": model_name(),
        "backend": getattr(backend, "name", None),
        "error": error,
    })


@app.get("/v1/models")
def models():
    if not _authorized():
        return jsonify({"error": "Unauthorized."}), 401
    return jsonify({"object": "list", "data": [{"id": model_name(), "object": "model"}]})


@app.post("/v1/chat/completions")
def chat_completions():
    if not _authorized():
        return jsonify({"error": "Unauthorized."}), 401
    params, problem = _validate(request.get_json(silent=True))
    if problem:
        return jsonify({"error": problem}), 400
    with _state_lock:
        backend = _state["backend"]
    if backend is None:
        return jsonify({"error": _state["error"] or "Model is not loaded yet."}), 503
    started = time.time()
    global _waiting
    with _queue_lock:
        if _waiting >= MAX_WAITING:
            return jsonify({"error": "Model is busy; try again in a moment."}), 503
        _waiting += 1

    def completion(text: str) -> Dict[str, Any]:
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(started),
            "model": model_name(),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"latency_seconds": round(time.time() - started, 2)},
        }

    def run() -> Dict[str, Any]:
        global _waiting
        try:
            text = backend.generate(params["messages"], max_new_tokens=params["max_tokens"], temperature=params["temperature"])
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Generation failed: {type(exc).__name__}: {exc}"}
        finally:
            with _queue_lock:
                _waiting -= 1
        return completion(text)

    if request.headers.get("X-Keepalive") != "1":
        body = run()
        return jsonify(body), (500 if "error" in body else 200)

    # Keep-alive mode: free tunnels (Cloudflare quick tunnels) drop requests that send no bytes for
    # ~100 s (HTTP 524). Write a space every few seconds while generating, then the JSON body;
    # leading whitespace is valid JSON. Errors arrive as {"error": ...} with status 200.
    result: Dict[str, Any] = {}
    worker = threading.Thread(target=lambda: result.update(run()), daemon=True)
    worker.start()

    def stream():
        yield " "
        while worker.is_alive():
            worker.join(timeout=KEEPALIVE_SECONDS)
            if worker.is_alive():
                yield " "
        yield json.dumps(result)

    return Response(stream(), mimetype="application/json", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


def main() -> None:
    port = int(os.getenv("PORT", "8001"))
    print("Loading the fine-tuned model (this can take a few minutes)...", flush=True)
    load_model()
    print(f"Model ready. Serving on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
