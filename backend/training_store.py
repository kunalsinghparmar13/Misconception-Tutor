"""Collect learner questions + reviewer-approved answers in Supabase, to keep fine-tuning the model on them.

Only the server writes here, with the Supabase secret key (bypasses Row Level Security); the
`training_examples` table has no browser access, so learners cannot plant fake "verified" examples.
Nothing personal goes into training: the export (scripts/export_user_training_data.py) drops user ids.

Environment:
SUPABASE_SECRET_KEY   Server-only key (Supabase dashboard > Settings > API Keys > Secret keys).
                      Without it, examples are still logged locally but not collected in Supabase.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

import requests

from backend import auth

log = logging.getLogger("misconception_tutor.training_store")
TABLE = "training_examples"
_TIMEOUT = 8

# Phrases that mean the tutor told the learner they were wrong. Used to keep out answers that contradict
# an exact check which proved the learner right.
_MISTAKE_CLAIM = re.compile(r"\b(what went wrong|misconception\s*:|is (not|in)correct|isn'?t correct|is wrong|made a mistake)\b", re.I)


def secret_key() -> Optional[str]:
    key = (os.getenv("SUPABASE_SECRET_KEY") or "").strip()
    return key or None


def enabled() -> bool:
    return secret_key() is not None


def _headers() -> Dict[str, str]:
    # New-style secret keys go in the apikey header only (they are not JWTs).
    return {"apikey": secret_key() or "", "Content-Type": "application/json", "Prefer": "return=representation"}


def assistant_text(result: Dict[str, Any]) -> str:
    """The tutor reply to learn from: the explanation and the correct answer/code (not the review notes)."""
    agents = result.get("agents") or {}
    parts = [(agents.get("explanation") or {}).get("text", ""), (agents.get("solution") or {}).get("text", "")]
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def contradicts_check(result: Dict[str, Any]) -> bool:
    """True when the exact check proved the learner right but the reply still claims a mistake."""
    grounding = (result.get("agents") or {}).get("grounding") or {}
    if grounding.get("student_correct") is not True:
        return False
    text = ((result.get("agents") or {}).get("explanation") or {}).get("text", "")
    return bool(_MISTAKE_CLAIM.search(text))


def save_example(user_id: Optional[str], subject: str, question: str, result: Dict[str, Any]) -> Optional[str]:
    """Store one reviewer-approved answer. Returns the example id, or None if not stored."""
    if not enabled():
        return None
    agents = result.get("agents") or {}
    review = agents.get("review") or {}
    if not review.get("approved"):
        return None  # never learn from answers the reviewer rejected
    answer = assistant_text(result)
    if not answer:
        return None
    grounding = agents.get("grounding") or {}
    row = {
        "user_id": user_id,
        "subject": (subject or "Mathematics")[:64],
        "question": question[:4000],
        "answer": answer[:20000],
        "misconception": (result.get("misconception") or None),
        "grounding_kind": grounding.get("kind"),
        "student_correct": grounding.get("student_correct"),
        "approved": True,
        "verified": bool(review.get("verified")) and not contradicts_check(result),
        "model": (str(result.get("model") or "")[:200] or None),
    }
    try:
        res = requests.post(f"{auth.supabase_url()}/rest/v1/{TABLE}", json=row, headers=_headers(), timeout=_TIMEOUT)
        if res.status_code in (200, 201):
            body = res.json()
            return (body[0] if isinstance(body, list) and body else body).get("id")
        log.warning("training example not saved: HTTP %s %s", res.status_code, res.text[:200])
    except (requests.RequestException, ValueError) as exc:
        log.warning("training example not saved: %s", exc)
    return None


def rate_example(user_id: Optional[str], example_id: str, rating: str) -> bool:
    """Attach a learner's thumbs up/down to their own example."""
    if not enabled() or not user_id or rating not in {"helpful", "unhelpful"}:
        return False
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", example_id or ""):
        return False
    try:
        res = requests.patch(
            f"{auth.supabase_url()}/rest/v1/{TABLE}",
            params={"id": f"eq.{example_id}", "user_id": f"eq.{user_id}"},
            json={"rating": rating},
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        return res.status_code in (200, 204) and (res.status_code == 204 or bool(res.json()))
    except (requests.RequestException, ValueError) as exc:
        log.warning("rating not saved: %s", exc)
        return False
