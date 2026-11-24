"""The link from the Humex backend to the Humex LLM.

Humo can use its own model server (``HUMEX_MODEL_URL``, e.g. the Qwen ``LLM/humex`` adapter served by
``LLM/serve/model_server.py`` on a Kaggle GPU) or share the model the rest of the app uses
(``LLM_BACKEND_URL``). Both speak the same OpenAI-style ``/v1/chat/completions`` API.
"""

from __future__ import annotations

import threading
from typing import Optional

from backend.humex.config import HumexSettings, load_settings


def _dedicated_client_class():
    from tutor_agents.model_client import ModelClient

    class HumexModelClient(ModelClient):
        """ModelClient pointed at Humo's own server instead of the app-wide LLM_BACKEND_URL."""

        def __init__(self, settings: HumexSettings) -> None:
            super().__init__(model_name=settings.model_name)
            self._settings = settings

        @property
        def url(self) -> Optional[str]:
            return self._settings.model_url

        @property
        def token(self) -> Optional[str]:
            return self._settings.model_token

        @property
        def local_enabled(self) -> bool:  # a dedicated server is always remote
            return False

    return HumexModelClient


_lock = threading.Lock()
_cached: dict = {}


def get_client():
    """Humo's model client: the dedicated one when HUMEX_MODEL_URL is set, else the app's shared client."""
    settings = load_settings()
    if not settings.dedicated_model:
        from tutor_agents.pipeline import get_pipeline

        return get_pipeline().client
    with _lock:  # one client per URL, so its health cache is reused between requests
        key = (settings.model_url, settings.model_token, settings.model_name)
        if key not in _cached:
            _cached.clear()
            _cached[key] = _dedicated_client_class()(settings)
        return _cached[key]
