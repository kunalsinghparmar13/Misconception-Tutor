"""Serve the approved UI and answer questions with the checked-in PEFT adapter."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "UI and UX"
ADAPTER_DIR = Path(os.getenv("LLM_ADAPTER_PATH", str(ROOT / "LLM"))).expanduser()

app = Flask(__name__)


class LocalTutor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any = None
        self._tokenizer: Any = None
        self.error: str | None = None

    @property
    def base_model(self) -> str:
        return os.getenv("LLM_BASE_MODEL", "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit")

    def status(self) -> dict[str, Any]:
        configured = (ADAPTER_DIR / "adapter_config.json").exists()
        try:
            import peft  # noqa: F401
            import torch  # noqa: F401
            import transformers  # noqa: F401
            dependencies = True
            dependency_error = None
        except ImportError as exc:
            dependencies = False
            dependency_error = f"Install the LLM dependencies: {exc}"
        return {
            "configured": configured,
            "dependenciesInstalled": dependencies,
            "loaded": self._model is not None,
            "available": configured and dependencies,
            "model": self.base_model,
            "error": self.error or dependency_error,
        }

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not (ADAPTER_DIR / "adapter_config.json").exists():
                raise RuntimeError(f"Adapter not found at {ADAPTER_DIR}")
            try:
                from peft import AutoPeftModelForCausalLM
                from transformers import AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(ADAPTER_DIR), trust_remote_code=True
                )
                self._model = AutoPeftModelForCausalLM.from_pretrained(
                    str(ADAPTER_DIR),
                    device_map="auto",
                    torch_dtype="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                )
                self._model.eval()
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
                raise RuntimeError(
                    "Could not load the Gemma adapter. Check the compatible base "
                    f"model and network access: {self.error}"
                ) from exc

    def answer(self, subject: str, question: str, mode: str) -> str:
        self._load()
        tokenizer = self._tokenizer
        model = self._model
        if tokenizer is None or model is None:
            raise RuntimeError("The LLM is not loaded.")

        system = (
            "You are Misconception Tutor, a patient Socratic tutor. "
            "Subject: "
            f"{subject}. Explain the student's reasoning, identify the first "
            "divergence, and teach the correction without simply doing homework "
            "for them. Requested mode: "
            f"{mode}. Use concise Markdown and finish with a Key Takeaway."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
        if hasattr(tokenizer, "apply_chat_template"):
            inputs = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
        else:
            inputs = tokenizer(
                f"System: {system}\nUser: {question}\nAssistant:",
                return_tensors="pt",
            )

        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        import torch

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        prompt_length = inputs["input_ids"].shape[-1]
        return tokenizer.decode(output[0][prompt_length:], skip_special_tokens=True).strip()


tutor = LocalTutor()


@app.get("/")
def index():
    return send_from_directory(UI_DIR, "code.html")


@app.get("/app.js")
def app_script():
    return send_from_directory(UI_DIR, "app.js")


@app.get("/api/health")
def health():
    return jsonify({"status": "online", "llm": tutor.status()})


@app.get("/api/backend-status")
def backend_status():
    state = tutor.status()
    return jsonify(
        {
            "status": "online",
            "liveAiEnabled": state["available"],
            "model": state["model"],
            "llmLoaded": state["loaded"],
            "llmError": state["error"],
        }
    )


@app.post("/api/llm/answer")
def llm_answer():
    body = request.get_json(silent=True) or {}
    question = str(body.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Enter a question before sending it."}), 400
    try:
        answer = tutor.answer(
            str(body.get("subject", "Mathematics")),
            question,
            str(body.get("mode", "diagnostic")),
        )
        return jsonify({"answer": answer, "model": tutor.base_model})
    except RuntimeError as exc:
        return jsonify({"error": str(exc), "llmRequired": True}), 503


if __name__ == "__main__":
    app.run(
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        debug=False,
    )
