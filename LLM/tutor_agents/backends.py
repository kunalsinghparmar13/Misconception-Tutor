"""In-process generation backends for the fine-tuned adapters.

Two adapter families are supported, detected from the adapter's ``adapter_config.json``:

* **Qwen3.5-4B** (``LLM/humex``, the Humex tutor, the default when present). Uses the chat template saved
  with the adapter and Qwen's ``enable_thinking`` switch. Thinking is off for serving (``LLM_THINKING=0``)
  because the tutor's replies are short and spoken; any ``<think>`` block is stripped from the reply.
* **Gemma 4 E4B** (``LLM/``, the earlier adapter). Mirrors ``tutor-project.ipynb`` exactly
  (``FastModel.from_pretrained`` + ``get_chat_template('gemma-4')``).

``UnslothBackend`` is tried first; ``PeftBackend`` is a plain transformers + peft fallback.
These classes need a CUDA GPU and are not exercised by the unit tests (the helpers are).
"""

from __future__ import annotations

import json
import os
import re
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

Message = Dict[str, str]

LLM_DIR = Path(__file__).resolve().parents[1]
HUMEX_DIR = LLM_DIR / "humex"
GEMMA_HUB_ID = "kunalsinghparmar/misconception-tutor-gemma4-e4b"


def _truthy(value: Optional[str], default: str = "0") -> bool:
    return str(value if value is not None else default).strip().lower() in {"1", "true", "yes", "on"}


def adapter_location() -> str:
    """Local adapter folder or Hugging Face repo id holding the LoRA weights.

    Order: LLM_ADAPTER_PATH, LLM_ADAPTER_ID, then LLM/humex (Qwen, the Humex tutor), then LLM/ (Gemma)."""
    explicit = os.getenv("LLM_ADAPTER_PATH") or os.getenv("LLM_NOTEBOOK_ADAPTER_PATH")
    if explicit:
        return explicit
    hub_id = os.getenv("LLM_ADAPTER_ID")
    if hub_id:
        return hub_id
    if (HUMEX_DIR / "adapter_config.json").exists():
        return str(HUMEX_DIR)
    if (LLM_DIR / "adapter_config.json").exists():
        return str(LLM_DIR)
    return GEMMA_HUB_ID


def adapter_config(path: Optional[str] = None) -> Dict[str, Any]:
    """The adapter's PEFT config when it is a local folder (empty for a Hub id we have not downloaded)."""
    config = Path(path or adapter_location()) / "adapter_config.json"
    try:
        return json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def base_model_id(path: Optional[str] = None) -> str:
    return str(adapter_config(path).get("base_model_name_or_path") or "")


def model_family(path: Optional[str] = None) -> str:
    """'qwen' or 'gemma'. LLM_MODEL_FAMILY overrides; otherwise read from the adapter's base model."""
    forced = (os.getenv("LLM_MODEL_FAMILY") or "").strip().lower()
    if forced in {"qwen", "gemma"}:
        return forced
    hint = (base_model_id(path) or path or adapter_location()).lower()
    return "qwen" if "qwen" in hint else "gemma"


def default_model_name(path: Optional[str] = None) -> str:
    return "humex-qwen35-4b (fine-tuned)" if model_family(path) == "qwen" else "misconception-tutor-gemma4-e4b (fine-tuned)"


def thinking_enabled() -> bool:
    """Qwen's step-by-step <think> mode. Off by default: it makes spoken replies much slower."""
    return _truthy(os.getenv("LLM_THINKING"), "0")


def template_kwargs(family: str) -> Dict[str, Any]:
    """Extra arguments for apply_chat_template; only Qwen's template understands enable_thinking."""
    return {"enable_thinking": thinking_enabled()} if family == "qwen" else {}


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    """Drop <think>...</think> reasoning so the learner only sees (and hears) the reply."""
    text = _THINK_BLOCK.sub("", text or "")
    if "</think>" in text:            # the template opened <think> in the prompt, so only the close tag is generated
        text = text.split("</think>", 1)[1]
    elif "<think>" in text:           # ran out of tokens while still thinking: there is no reply to show
        text = text.split("<think>", 1)[0]
    return text.strip()


def _has_tokenizer(path: str) -> bool:
    return (Path(path) / "tokenizer_config.json").exists()


class _BaseBackend:
    name = "base"

    def __init__(self) -> None:
        self._lock = threading.Lock()  # one generation at a time on a single GPU
        self.family = "gemma"

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        raise NotImplementedError

    def generate(self, messages: List[Message], max_new_tokens: int = 512, temperature: float = 0.2) -> str:
        with self._lock:
            return strip_thinking(self._generate(messages, max_new_tokens, temperature))

    def _encode(self, messages: List[Message]) -> Dict[str, Any]:
        return self.tokenizer.apply_chat_template(  # type: ignore[attr-defined]
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
            **template_kwargs(self.family),
        )


class UnslothBackend(_BaseBackend):
    name = "unsloth"

    def __init__(self, path: Optional[str] = None, max_seq_length: int = 4096) -> None:
        super().__init__()
        from unsloth import FastModel  # type: ignore

        self.path = path or adapter_location()
        self.family = model_family(self.path)
        # 4-bit keeps the 4B model on a small free GPU; LLM_LOAD_4BIT=0 loads 16-bit (needs ~10 GB, slightly better).
        self.model, tokenizer = FastModel.from_pretrained(
            model_name=self.path,
            max_seq_length=max_seq_length,
            load_in_4bit=_truthy(os.getenv("LLM_LOAD_4BIT"), "1"),
            token=os.getenv("HF_TOKEN") or None,
        )
        FastModel.for_inference(self.model)
        if self.family == "gemma":
            from unsloth.chat_templates import get_chat_template  # type: ignore

            self.tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
        else:
            # Qwen3.5 is a vision-language model: Unsloth may return a processor; the text tokenizer carries the
            # chat template that was saved with the adapter.
            self.tokenizer = getattr(tokenizer, "tokenizer", tokenizer)

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        import torch

        inputs = self._encode(messages)
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
        # Keep special tokens out, but <think> tags are normal text for Qwen and are stripped in generate().
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


class PeftBackend(_BaseBackend):
    name = "peft"

    def __init__(self, path: Optional[str] = None) -> None:
        super().__init__()
        import torch
        from transformers import AutoTokenizer  # type: ignore

        self.path = path or adapter_location()
        self.family = model_family(self.path)
        token = os.getenv("HF_TOKEN") or None
        dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (
            torch.float16 if torch.cuda.is_available() else "auto")
        common = {"token": token, "device_map": os.getenv("LLM_DEVICE_MAP", "auto"), "torch_dtype": dtype,
                  "low_cpu_mem_usage": True}
        if self.family == "qwen":
            from peft import PeftModel  # type: ignore
            from transformers import AutoModelForCausalLM, AutoModelForImageTextToText  # type: ignore

            base_id = base_model_id(self.path) or "unsloth/Qwen3.5-4B"
            try:  # Qwen3.5 checkpoints are vision-language models
                base = AutoModelForImageTextToText.from_pretrained(base_id, **common)
            except (ValueError, KeyError):
                base = AutoModelForCausalLM.from_pretrained(base_id, **common)
            self.model = PeftModel.from_pretrained(base, self.path, token=token)
            tok_source = self.path if _has_tokenizer(self.path) else base_id
        else:
            from peft import AutoPeftModelForCausalLM  # type: ignore

            self.model = AutoPeftModelForCausalLM.from_pretrained(self.path, **common)
            tok_source = self.path
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(tok_source, token=token)

    def _generate(self, messages: List[Message], max_new_tokens: int, temperature: float) -> str:
        import torch

        inputs = self._encode(messages)
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
