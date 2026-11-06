"""
ECC Agentic Security Suite: HTTP Security Middleware & Rate Limiter
Enforces security headers, IP rate limiting, admin-route protection and safe
error responses to maintain server integrity.

Environment variables
---------------------
TRUST_PROXY_HOPS  Number of reverse proxies in front of the app that append to
                  X-Forwarded-For (default 1: Render, Hugging Face Spaces,
                  Modal and Cloudflare Tunnel all count as one). Set 0 when the
                  app is exposed directly. Client-supplied forwarding headers
                  beyond that many hops are ignored, so they cannot be spoofed
                  to dodge the rate limit.
ADMIN_TOKEN       Secret for the admin/data routes in ADMIN_PATHS. Send it as
                  `Authorization: Bearer <token>` or `X-Admin-Token: <token>`.
APP_ENV           When "production" and ADMIN_TOKEN is unset, admin routes are
                  closed (403). In any other environment they stay open so local
                  development and the demo UI keep working.
"""

from __future__ import annotations

import hmac
import logging
import os
import threading
import time
from typing import Dict, List

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

_MAX_TRACKED_IPS = 10_000


class IPRateLimiter:
    """Thread-safe sliding-window rate limiter for public endpoints."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            cutoff = now - self.window_seconds
            if len(self._history) > _MAX_TRACKED_IPS:
                # Bound memory: drop keys whose newest request is outside the window.
                self._history = {
                    key: stamps for key, stamps in self._history.items()
                    if stamps and stamps[-1] > cutoff
                }

            timestamps = [ts for ts in self._history.get(ip, []) if ts > cutoff]

            if len(timestamps) >= self.max_requests:
                self._history[ip] = timestamps
                return False

            timestamps.append(now)
            self._history[ip] = timestamps
            return True


rate_limiter = IPRateLimiter(max_requests=120, window_seconds=60)


def apply_security_headers(response: Response) -> Response:
    """Injects enterprise defensive headers as defined in ECC security guidelines."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
            # remote_addr is already the real client IP when ProxyFix applies.
            client_ip = request.remote_addr or "unknown"
            if not rate_limiter.is_allowed(client_ip):
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
