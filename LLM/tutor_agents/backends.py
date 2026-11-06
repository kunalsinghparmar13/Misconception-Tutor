"""In-process generation backends for the fine-tuned Gemma adapter.

``UnslothBackend`` mirrors the loading and generation code in ``tutor-project.ipynb``
exactly (``FastModel.from_pretrained`` + ``get_chat_template('gemma-4')``), because that is
the stack the adapter was trained and verified with. ``PeftBackend`` is a plain
transformers + peft fallback.

These classes need a CUDA GPU and are not exercised by the unit tests.
"""

from __future__ import annotations

import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

Message = Dict[str, str]

LLM_DIR = Path(__file__).resolve().parents[1]


def adapter_location() -> str:
    """Local adapter folder or Hugging Face repo id holding the LoRA weights."""
    explicit = os.getenv("LLM_ADAPTER_PATH") or os.getenv("LLM_NOTEBOOK_ADAPTER_PATH")
    if explicit:
        return explicit
    hub_id = os.getenv("LLM_ADAPTER_ID")
    if hub_id:
        return hub_id
    if (LLM_DIR / "adapter_config.json").exists():
        return str(LLM_DIR)
    return "kunalsinghparmar/misconception-tutor-gemma4-e4b"


class _BaseBackend:
    name = "base"

    def __init__(self) -> None:
        self._lock = threading.Lock()  # one generation at a time on a single GPU

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        raise NotImplementedError

    def generate(self, messages: List[Message], max_new_tokens: int = 512, temperature: float = 0.2) -> str:
        with self._lock:
            return self._generate(messages, max_new_tokens, temperature)


class UnslothBackend(_BaseBackend):
    name = "unsloth"

    def __init__(self, path: Optional[str] = None, max_seq_length: int = 4096) -> None:
        super().__init__()
        from unsloth import FastModel  # type: ignore
        from unsloth.chat_templates import get_chat_template  # type: ignore

        self.path = path or adapter_location()
        self.model, tokenizer = FastModel.from_pretrained(
            model_name=self.path,
            max_seq_length=max_seq_length,
            load_in_4bit=True,
            token=os.getenv("HF_TOKEN") or None,
        )
        FastModel.for_inference(self.model)
        self.tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        import torch

        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        inputs = {k: v.to(self.model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
        kwargs = {"max_new_tokens": int(max_new_tokens), "use_cache": True}
        # Hard stop so one slow call can never hold the GPU for minutes and queue everything behind it.
        kwargs["max_time"] = float(os.getenv("LLM_MAX_GEN_SECONDS", "90"))
        if temperature and temperature > 0:
            kwargs.update(do_sample=True, temperature=float(temperature), top_p=0.95)
        else:
            kwargs["do_sample"] = False
        started = time.time()
        with torch.inference_mode():
            output = self.model.generate(**inputs, **kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        secs = max(time.time() - started, 1e-6)
        self.last_stats = {"prompt_tokens": int(inputs["input_ids"].shape[1]), "new_tokens": int(len(new_tokens)), "seconds": round(secs, 2),
                           "tokens_per_second": round(len(new_tokens) / secs, 2)}
        print(f"[gen] {self.last_stats}", flush=True)
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


class PeftBackend(_BaseBackend):
    name = "peft"

    def __init__(self, path: Optional[str] = None) -> None:
        super().__init__()
        import torch
        from peft import AutoPeftModelForCausalLM  # type: ignore
        from transformers import AutoTokenizer  # type: ignore

        self.path = path or adapter_location()
        token = os.getenv("HF_TOKEN") or None
        self.model = AutoPeftModelForCausalLM.from_pretrained(
            self.path,
            token=token,
            device_map=os.getenv("LLM_DEVICE_MAP", "auto"),
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else "auto",
            low_cpu_mem_usage=True,
        )
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, token=token)

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        import torch

        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        kwargs = {"max_new_tokens": int(max_new_tokens)}
        if temperature and temperature > 0:
            kwargs.update(do_sample=True, temperature=float(temperature), top_p=0.95)
        else:
            kwargs["do_sample"] = False
        with torch.inference_mode():
            output = self.model.generate(**inputs, **kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def load_backend(kind: Optional[str] = None) -> _BaseBackend:
    """Load the adapter. ``LLM_GEN_BACKEND`` = ``unsloth`` (default, tries it first) or ``peft``."""
    kind = (kind or os.getenv("LLM_GEN_BACKEND") or "auto").lower()
    errors: List[str] = []
    if kind in {"auto", "unsloth"}:
        try:
            return UnslothBackend()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unsloth: {type(exc).__name__}: {exc}")
            if kind == "unsloth":
                raise
    if kind in {"auto", "peft"}:
        try:
            return PeftBackend()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"peft: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors) or f"Unknown LLM_GEN_BACKEND '{kind}'")
