"""Run the Humex backend on its own (API only), e.g. to host Humo separately from the main app.

    HUMEX_MODEL_URL=https://<your-model-server> HUMEX_MODEL_TOKEN=<token> \\
        PYTHONPATH=src:. .venv/bin/python -m backend.humex.server        # serves on :8002

Normally you do not need this: the main app (``python -m backend.api``) already includes these routes.
"""

from __future__ import annotations

import os

from flask import Flask, g, jsonify, request

from backend import auth
from backend.humex import register
from backend.security.middleware import register_security_middleware


def create_app() -> Flask:
    app = Flask(__name__)
    register_security_middleware(app)   # security headers + rate limits, same as the main app

    @app.before_request
    def require_sign_in():
        """Same rule as the main app: /api/humex/chat needs a signed-in Supabase user (AUTH_REQUIRED=0 turns it off)."""
        g.user = None
        if request.method == "OPTIONS" or not auth.is_protected(request.path) or not auth.auth_required():
            return None
        token = auth.bearer_token(request.headers.get("Authorization"))
        g.user = auth.verify_token(token) if token else None
        if not g.user:
            return jsonify({"error": "Please sign in to talk to Humo.", "status": "unauthenticated"}), 401
        return None

    register(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8002")), debug=False)
