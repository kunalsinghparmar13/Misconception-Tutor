"""Humex backend: the server side of Humo, the 3D voice tutor.

The app (``UI and UX/code.html``) sends what the learner said or typed to ``POST /api/humex/chat``.
This package checks it, asks the Humex LLM for a hint-only reply, has the reviewer check that reply,
and returns it for the 3D avatar to speak. See README.md in this folder.
"""

import sys
from pathlib import Path

_LLM_DIR = Path(__file__).resolve().parents[2] / "LLM"   # the agents (coach + reviewer) live in LLM/tutor_agents
if str(_LLM_DIR) not in sys.path:
    sys.path.insert(0, str(_LLM_DIR))

from backend.humex.routes import humex_bp  # noqa: E402


def register(app) -> None:
    """Add the Humex routes to a Flask app."""
    app.register_blueprint(humex_bp)


__all__ = ["humex_bp", "register"]
