"""Model access for the agents.

Two ways to reach the user's fine-tuned model, chosen by environment variables:

* **Remote** (``LLM_BACKEND_URL``): any OpenAI-compatible ``/v1/chat/completions`` server.
  ``LLM/serve/model_server.py`` is one (runs the adapter on a free GPU notebook, Modal, a
  local GPU box ...); llama.cpp's ``llama-server``, vLLM and Ollama speak the same protocol.
* **Local** (``LLM_LOCAL_MODEL=1``): load the adapter inside this process (needs a GPU and
  ``unsloth`` or ``transformers`` + ``peft``).

If neither is configured, or the model cannot be reached, ``ModelUnavailable`` is raised.
Nothing is ever substituted for the model's output.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("misconception_tutor.model")

Message = Dict[str, str]
Transport = Callable[[List[Message], int, float], str]

_URL_ENV_NAMES = (
    "LLM_BACKEND_URL",
    "REMOTE_LLM_URL",
    "LLM_API_URL",
    "MODAL_APP_URL",
    "HF_SPACE_URL",
)
_RETRY_STATUS = {502, 503, 504}


class ModelUnavailable(RuntimeError):
    """The fine-tuned model could not be reached or failed to answer.

    ``str(exc)`` is the technical detail (for logs); ``public_message`` is safe to show to
    learners - it never contains the model server's address or raw exception text.
    """

    public_message = "The tutor model is not reachable right now. Please try again in a minute."


@dataclass
class ChatResult:
    text: str
    model: str
    seconds: float
    backend: str


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class ModelClient:
    """Thin, thread-safe chat client around the user's model."""

    def __init__(self, transport: Optional[Transport] = None, model_name: Optional[str] = None) -> None:
        # ``transport`` lets tests (or embedders) inject a callable instead of HTTP.
        self._transport = transport
        self._model_name = model_name
        self._local_backend: Any = None
        self._local_lock = threading.Lock()
        self._local_error: Optional[str] = None
        self._health_cache: Dict[str, Any] = {"at": 0.0, "value": None}

    # ------------------------------------------------------------------ config
    @property
    def url(self) -> Optional[str]:
        for name in _URL_ENV_NAMES:
            value = os.getenv(name)
            if value and value.strip():
                return value.strip().rstrip("/")
        return None

    @property
    def token(self) -> Optional[str]:
        return os.getenv("LLM_BACKEND_TOKEN") or os.getenv("HF_TOKEN") or None

    @property
    def timeout(self) -> float:
        try:
            return float(os.getenv("LLM_BACKEND_TIMEOUT", "180"))
        except ValueError:
            return 180.0

    @property
    def local_enabled(self) -> bool:
        return _truthy(os.getenv("LLM_LOCAL_MODEL"))

    @property
    def mode(self) -> str:
        if self._transport is not None:
            return "injected"
        if self.url:
            return "remote"
        if self.local_enabled:
            return "local"
        return "none"

    @property
    def configured(self) -> bool:
        return self.mode != "none"

    @property
    def model_name(self) -> str:
        return (
            self._model_name
            or os.getenv("LLM_MODEL_NAME")
            or "misconception-tutor-gemma4-e4b (fine-tuned)"
        )

    # ------------------------------------------------------------------ health
    def health(self, max_age: float = 5.0) -> Dict[str, Any]:
        """Cheap readiness probe (cached for a few seconds)."""
        now = time.time()
        cached = self._health_cache
        if cached["value"] is not None and now - cached["at"] < max_age:
            return cached["value"]
        value = self._probe()
        self._health_cache = {"at": now, "value": value}
        return value

    def _probe(self) -> Dict[str, Any]:
        mode = self.mode
        if mode == "none":
            return {
                "configured": False,
                "reachable": False,
                "mode": mode,
                "error": "No model configured. Set LLM_BACKEND_URL (remote model server) "
                         "or LLM_LOCAL_MODEL=1 (load the adapter in this process).",
            }
        if mode == "injected":
            return {"configured": True, "reachable": True, "mode": mode, "model": self.model_name}
        if mode == "local":
            return {
                "configured": True,
                "reachable": self._local_backend is not None or self._local_error is None,
                "mode": mode,
                "model": self.model_name,
                "loaded": self._local_backend is not None,
                "error": self._local_error,
            }
        import requests

        headers = self._headers()
        for path in ("/health", "/api/health", "/api/ready", "/v1/models"):
            try:
                res = requests.get(f"{self.url}{path}", headers=headers, timeout=3)
            except Exception as exc:  # noqa: BLE001 - report any network failure
                last = "no response"
                log.warning("model health probe %s failed: %s", path, exc)
                continue
            if res.status_code == 200:
                info: Dict[str, Any] = {}
                try:
                    info = res.json()
                except ValueError:
                    pass
                return {
                    "configured": True,
                    "reachable": True,
                    "mode": mode,
                    "model": info.get("model") or self.model_name,
                    "modelLoaded": info.get("model_loaded", True),
                }
            last = f"HTTP {res.status_code} from {path}"
        return {
            "configured": True,
            "reachable": False,
            "mode": mode,
            "error": f"Model server not reachable ({last}).",
        }

    # ------------------------------------------------------------------- chat
    def chat(
        self,
        messages: List[Message],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> ChatResult:
        started = time.time()
        mode = self.mode
        if mode == "none":
            raise ModelUnavailable(self._probe()["error"])
        if mode == "injected":
            try:
                text = self._transport(messages, max_tokens, temperature)  # type: ignore[misc]
            except ModelUnavailable:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ModelUnavailable(f"Injected model failed: {exc}") from exc
        elif mode == "local":
            text = self._chat_local(messages, max_tokens, temperature)
        else:
            text = self._chat_remote(messages, max_tokens, temperature)
        text = (text or "").strip()
        if not text:
            raise ModelUnavailable("The model returned an empty response.")
        return ChatResult(text=text, model=self.model_name, seconds=time.time() - started, backend=mode)

    def _headers(self) -> Dict[str, str]:
        # X-Keepalive: our model server then trickles spaces while generating, so free tunnels
        # (Cloudflare's ~100 s idle limit) don't cut long generations off. Other servers ignore it.
        headers = {"Content-Type": "application/json", "Accept": "application/json", "X-Keepalive": "1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _chat_remote(self, messages: List[Message], max_tokens: int, temperature: float) -> str:
        import requests

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "stream": False,
        }
        last_error = "unknown error"
        for attempt in range(2):  # one retry: free tunnels and cold starts are flaky
            try:
                res = requests.post(
                    f"{self.url}/v1/chat/completions",
                    json=payload,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(1.5)
                continue
            if res.status_code == 200:
                try:
                    body = res.json()
                except ValueError as exc:
                    raise ModelUnavailable(f"Unexpected response from model server: {exc}") from exc
                if isinstance(body, dict) and body.get("error"):  # keep-alive mode reports errors in the body
                    last_error = str(body["error"])[:200]
                    break
                try:
                    return body["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise ModelUnavailable(f"Unexpected response from model server: {exc}") from exc
            last_error = f"HTTP {res.status_code}: {res.text[:200]}"
            if res.status_code in _RETRY_STATUS and attempt == 0:
                time.sleep(2.0)
                continue
            break
        log.warning("model server %s failed: %s", self.url, last_error)
        raise ModelUnavailable(f"Model server failed ({last_error}).")

    def _chat_local(self, messages: List[Message], max_tokens: int, temperature: float) -> str:
        backend = self._ensure_local()
        try:
            return backend.generate(messages, max_new_tokens=max_tokens, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailable(f"Local generation failed: {type(exc).__name__}: {exc}") from exc

    def _ensure_local(self) -> Any:
        if self._local_backend is not None:
            return self._local_backend
        with self._local_lock:
            if self._local_backend is not None:
                return self._local_backend
            try:
                from .backends import load_backend

                self._local_backend = load_backend()
                self._local_error = None
            except Exception as exc:  # noqa: BLE001
                self._local_error = f"{type(exc).__name__}: {exc}"
                raise ModelUnavailable(f"Could not load the adapter locally: {self._local_error}") from exc
        return self._local_backend
