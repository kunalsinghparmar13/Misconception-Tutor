"""HTTP routes of the Humex backend.

    POST /api/humex/chat     the app sends what the learner said or typed; returns Humo's reviewed hint
    GET  /api/humex/health   is Humo's model connected? (used by the page to show its status)
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, current_app, g, jsonify, request

from backend import training_store
from backend.humex.config import load_settings
from backend.humex.model import get_client
from backend.security.guard import prompt_guard
from backend.security.sanitizer import sanitize_input_text

humex_bp = Blueprint("humex", __name__, url_prefix="/api/humex")

REFUSAL = {
    "en": "I can't follow instructions like that, but I'd love to think through a maths, logic or coding question with you. What are you working on?",
    "hi": "मैं ऐसे निर्देश नहीं मान सकता, पर गणित, तर्क या कोडिंग के किसी सवाल पर साथ सोचना अच्छा लगेगा। तुम किस पर काम कर रहे हो?",
}

_slots = threading.BoundedSemaphore(load_settings().max_concurrent)


def parse_request(body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    """Validate and clean what the app sent: {message, history: [{role, content}], language, subject}."""
    settings = load_settings()
    message = sanitize_input_text(str(body.get("message", "")).strip(), max_length=settings.max_message_chars)
    if not message:
        return None, (jsonify({"error": "Say or type a message first."}), 400)
    language = sanitize_input_text(str(body.get("language", "en")), max_length=8).lower().split("-")[0] or "en"
    history: List[Dict[str, str]] = []
    raw_history = body.get("history") if isinstance(body.get("history"), list) else []
    for turn in raw_history[-settings.max_history_turns:]:
        if isinstance(turn, dict):
            history.append({"role": str(turn.get("role", "")),
                            "content": sanitize_input_text(str(turn.get("content", "")),
                                                           max_length=settings.max_message_chars)})
    return {
        "message": message,
        "history": history,
        "language": language,
        "subject": sanitize_input_text(str(body.get("subject", "")), max_length=64),
    }, None


def is_injection(message: str, history: List[Dict[str, str]]) -> bool:
    """The whole learner side is scanned, because the browser sends the history back to us."""
    return any(not prompt_guard.scan(text).is_safe
               for text in [message] + [t["content"] for t in history if t["role"] == "user"])


@humex_bp.post("/chat")
def chat():
    """App -> Humex backend -> Humex LLM (coach, then reviewer) -> back to the app for the 3D avatar to speak."""
    from tutor_agents.humex import get_coach
    from tutor_agents.model_client import ModelUnavailable

    data, error = parse_request(request.get_json(silent=True) or {})
    if error:
        return error
    if is_injection(data["message"], data["history"]):
        return jsonify({"reply": REFUSAL.get(data["language"], REFUSAL["en"]), "status": "refused_injection",
                        "review": {"verdict": "REFUSED", "issues": [], "checks": [], "revised": True}})

    if not _slots.acquire(blocking=False):
        return jsonify({"error": "Humo is busy with other learners. Please retry in a few seconds."}), 429
    try:
        result = get_coach(get_client()).respond(data["message"], data["history"],
                                                 language=data["language"], subject=data["subject"])
        reply = {**result.to_dict(), "status": "ok"}
        reply["example_id"] = _remember_for_training(data, reply)
        return jsonify(reply)
    except ModelUnavailable as exc:
        return jsonify({"error": exc.public_message, "status": "model_unavailable"}), 503
    except Exception:
        current_app.logger.exception("humex chat failed")
        return jsonify({"error": "Humo hit an unexpected error."}), 500
    finally:
        _slots.release()


def _remember_for_training(data: Dict[str, Any], reply: Dict[str, Any]) -> Optional[str]:
    """Save a signed-in learner's turn so Humo can learn from real conversations in the next training round.
    The id is made here and the save runs in the background, so the spoken reply is never delayed by it."""
    user = getattr(g, "user", None) or {}
    if not user.get("id") or not training_store.enabled() or not training_store.humex_turn_is_learnable(reply):
        return None
    example_id = str(uuid.uuid4())
    threading.Thread(target=training_store.save_humex_turn, daemon=True,
                     args=(user["id"], data["message"], data["history"], reply, data["language"],
                           bool(reply.get("coding")), example_id)).start()
    return example_id


@humex_bp.post("/feedback")
def feedback():
    """The learner's thumbs up/down on one of Humo's replies; 'unhelpful' keeps that turn out of training."""
    body = request.get_json(silent=True) or {}
    example_id = sanitize_input_text(str(body.get("example_id", "")), max_length=64)
    rating = str(body.get("rating", "")).strip().lower()
    if rating not in ("helpful", "unhelpful") or not example_id:
        return jsonify({"error": "Send example_id and rating ('helpful' or 'unhelpful')."}), 400
    user = getattr(g, "user", None) or {}
    return jsonify({"saved": training_store.rate_example(user.get("id"), example_id, rating)})


@humex_bp.get("/health")
def health():
    """Whether Humo's model is configured and reachable. Never exposes the model server's address."""
    settings = load_settings()
    try:
        status = get_client().health()
    except Exception as exc:  # noqa: BLE001 - health must always answer
        status = {"configured": False, "reachable": False, "error": type(exc).__name__}
    return jsonify({
        "service": "humex",
        "ready": bool(status.get("configured") and status.get("reachable")),
        "configured": bool(status.get("configured")),
        "reachable": bool(status.get("reachable")),
        "model": status.get("model"),
        "dedicated_model": settings.dedicated_model,
    })
