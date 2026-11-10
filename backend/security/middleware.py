"""
================================================================================
ECC Agentic Security Suite: HTTP Security Middleware, Rate Limiter & Boundary Guard
Enforces enterprise defensive headers, adaptive sliding-window rate limiting,
OWASP Content-Security-Policy (CSP), and admin protection.
================================================================================
"""

from __future__ import annotations

import hmac
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Set

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

logger = logging.getLogger("misconception_tutor.security")

# Routes that expose other learners' data or internal state.
ADMIN_PATHS = frozenset({
    "/api/memory/sessions",
    "/api/security/audit",
    "/api/llm/dataset",
    "/api/llm/dataset/export",
})

# Resource-intensive endpoints requiring stricter rate limit bounds
HEAVY_COMPUTE_PATHS = frozenset({
    "/api/tutor/stream",
    "/api/tutor",
    "/api/llm/answer",
    "/api/context/upload",
    "/api/practice/verify",
})

_MAX_TRACKED_IPS = 10_000


class IPRateLimiter:
    """Thread-safe sliding-window rate limiter with per-endpoint tiering."""

    def __init__(self, default_max: int = 120, heavy_max: int = 40, window_seconds: int = 60) -> None:
        self.default_max = default_max
        self.heavy_max = heavy_max
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._history: Dict[str, List[float]] = {}
        self._heavy_history: Dict[str, List[float]] = {}

    def is_allowed(self, ip: str, path: str = "") -> bool:
        now = time.time()
        is_heavy = path in HEAVY_COMPUTE_PATHS
        max_allowed = self.heavy_max if is_heavy else self.default_max

        with self._lock:
            cutoff = now - self.window_seconds
            store = self._heavy_history if is_heavy else self._history

            if len(store) > _MAX_TRACKED_IPS:
                store = {
                    k: stamps for k, stamps in store.items()
                    if stamps and stamps[-1] > cutoff
                }
                if is_heavy:
                    self._heavy_history = store
                else:
                    self._history = store

            timestamps = [ts for ts in store.get(ip, []) if ts > cutoff]

            if len(timestamps) >= max_allowed:
                store[ip] = timestamps
                return False

            timestamps.append(now)
            store[ip] = timestamps
            return True


rate_limiter = IPRateLimiter(default_max=120, heavy_max=40, window_seconds=60)


def apply_security_headers(response: Response) -> Response:
    """Injects enterprise defensive headers as defined in ECC security guidelines."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Modern OWASP & Browser Defense Headers
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    
    # Content-Security-Policy (CSP) allowing local assets, Google Fonts, and Supabase JS CDN
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "connect-src 'self' https: wss:",
        "frame-ancestors 'self'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    return response


def _proxy_hops() -> int:
    try:
        return max(0, int(os.getenv("TRUST_PROXY_HOPS", "1")))
    except ValueError:
        return 1


def _admin_access_allowed() -> bool:
    token = os.getenv("ADMIN_TOKEN", "").strip()
    if token:
        supplied = request.headers.get("X-Admin-Token", "")
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        return hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8"))
    return os.getenv("APP_ENV", "development").strip().lower() != "production"


def register_security_middleware(app: Flask) -> None:
    """Hooks proxy handling, headers, rate limiting, admin guard and error handlers."""
    hops = _proxy_hops()
    if hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)  # type: ignore[method-assign]

    @app.after_request
    def add_headers(response: Response) -> Response:
        return apply_security_headers(response)

    @app.before_request
    def guard_requests():
        path = request.path

        if path in ADMIN_PATHS and not _admin_access_allowed():
            return jsonify({"error": "Admin access required."}), 403

        # Only rate limit API calls, allow static files
        if path.startswith("/api/"):
            client_ip = request.remote_addr or "unknown"
            if not rate_limiter.is_allowed(client_ip, path):
                return jsonify({"error": "Rate limit exceeded. Please wait a moment before sending more requests."}), 429
        return None

    @app.errorhandler(ValueError)
    def handle_bad_value(exc: ValueError):
        logger.warning("Bad parameter on %s %s: %s", request.method, request.path, exc)
        return jsonify({"error": "Invalid request parameter."}), 400

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        if isinstance(exc, HTTPException):
            return exc
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "Internal server error."}), 500
