"""Settings for the Humex backend, read from environment variables (see README.md in this folder)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


@dataclass(frozen=True)
class HumexSettings:
    model_url: Optional[str]      # HUMEX_MODEL_URL: Humo's own model server; unset = share the app's model
    model_token: Optional[str]    # HUMEX_MODEL_TOKEN: bearer token for that server
    model_name: Optional[str]     # HUMEX_MODEL_NAME: label sent to the server (OpenAI 'model' field)
    max_concurrent: int           # HUMEX_MAX_CONCURRENT: replies generated at the same time (one GPU: keep small)
    max_message_chars: int = 1600
    max_history_turns: int = 10

    @property
    def dedicated_model(self) -> bool:
        return self.model_url is not None


def load_settings() -> HumexSettings:
    try:
        concurrent = max(1, int(os.getenv("HUMEX_MAX_CONCURRENT", "2")))
    except ValueError:
        concurrent = 2
    return HumexSettings(
        model_url=(_env("HUMEX_MODEL_URL") or "").rstrip("/") or None,
        model_token=_env("HUMEX_MODEL_TOKEN"),
        model_name=_env("HUMEX_MODEL_NAME"),
        max_concurrent=concurrent,
    )
