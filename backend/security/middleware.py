"""
================================================================================
ECC Agentic Security Suite: HTTP Security Middleware & Rate Limiter
Enforces security headers and IP rate limiting to maintain server integrity.
================================================================================
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Tuple
from flask import Flask, Request, Response, jsonify, request


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
            timestamps = self._history.get(ip, [])
            # Prune timestamps older than window
            cutoff = now - self.window_seconds
            timestamps = [ts for ts in timestamps if ts > cutoff]

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


def register_security_middleware(app: Flask) -> None:
    """Hooks security headers and rate-limiting into Flask lifecycle."""
    @app.after_request
    def add_headers(response: Response) -> Response:
        return apply_security_headers(response)

    @app.before_request
    def check_rate_limit():
        # Only rate limit API calls, allow static files
        if request.path.startswith("/api/"):
            client_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown"
            # In X-Forwarded-For, take the first client IP
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()

            if not rate_limiter.is_allowed(client_ip):
                return jsonify({"error": "Rate limit exceeded. Please wait a moment before sending more requests."}), 429
