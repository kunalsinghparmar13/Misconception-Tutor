"""Supabase sign-in for the tutor.

The browser signs in with Supabase Auth (see "UI and UX/auth.js") and sends its access token as
``Authorization: Bearer <token>`` on API calls. The tutor routes listed in PROTECTED_PREFIXES only run
for a signed-in user: the token is checked with Supabase's ``/auth/v1/user`` endpoint and the answer
is cached for a minute, so the model can't be used without an account.

Environment:
SUPABASE_URL              Project URL (defaults to this project's Supabase project).
SUPABASE_PUBLISHABLE_KEY  Public client key. Safe to expose: Row Level Security protects the data.
AUTH_REQUIRED             "0" turns the sign-in check off (tests, offline development). Default "1".
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests

DEFAULT_SUPABASE_URL = "https://elqvhkhtoucovwdnjylp.supabase.co"
DEFAULT_PUBLISHABLE_KEY = "sb_publishable_3Vz1SUNeQ1ddZlEetiCCqA_hf5QpN1_"

# API routes that run the model or record learner work; everything else stays public.
PROTECTED_PREFIXES = (
    "/api/tutor",
    "/api/llm/answer",
    "/api/llm/feedback",
    "/api/practice/",
    "/api/python/debug",
    "/api/diagnose",
)

_CACHE_SECONDS = 60
_cache: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}
_lock = threading.Lock()


def supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL).rstrip("/")


def publishable_key() -> str:
    return os.getenv("SUPABASE_PUBLISHABLE_KEY") or DEFAULT_PUBLISHABLE_KEY


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "1").strip().lower() not in {"0", "false", "no", "off"}


def is_protected(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def bearer_token(header: Optional[str]) -> Optional[str]:
    if header and header.lower().startswith("bearer "):
        token = header[7:].strip()
        return token or None
    return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """The Supabase user for an access token, or None if it is invalid or expired."""
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_SECONDS:
            return hit[1]
    user: Optional[Dict[str, Any]] = None
    try:
        res = requests.get(
            f"{supabase_url()}/auth/v1/user",
            headers={"apikey": publishable_key(), "Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if res.status_code == 200:
            body = res.json()
            if isinstance(body, dict) and body.get("id"):
                user = {"id": body["id"], "email": body.get("email")}
    except (requests.RequestException, ValueError):
        return None  # Supabase unreachable: refuse, but don't cache the failure
    with _lock:
        if len(_cache) > 5000:
            _cache.clear()
        _cache[key] = (now, user)
    return user


def public_config() -> Dict[str, str]:
    """What the browser needs to talk to Supabase (both values are public)."""
    return {"url": supabase_url(), "key": publishable_key()}
