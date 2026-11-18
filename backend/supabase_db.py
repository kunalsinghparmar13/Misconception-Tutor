"""Supabase cloud data persistence and synchronization for Sikora AI Tutor.

Provides cloud-native storage for learner study sessions, practice attempts,
Bayesian Knowledge Tracing (BKT) mastery states, and notifications via PostgREST.
Respects Row-Level Security (RLS) by passing the learner's JWT Bearer token when available,
or using the server's service role key for system operations.
Gracefully falls back to local SQLite if Supabase is unreachable or unconfigured.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import requests

from backend import auth

log = logging.getLogger("misconception_tutor.supabase_db")
_TIMEOUT = 5.0


def is_configured() -> bool:
    """True if Supabase URL and at least one API key are configured."""
    return bool(auth.supabase_url() and (auth.publishable_key() or os.getenv("SUPABASE_SECRET_KEY")))


def _build_headers(auth_token: Optional[str] = None, prefer_merge: bool = False) -> Dict[str, str]:
    """Builds PostgREST request headers with appropriate auth and preferences."""
    pub_key = auth.publishable_key()
    sec_key = os.getenv("SUPABASE_SECRET_KEY")

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    prefer_values = ["return=representation"]
    if prefer_merge:
        prefer_values.append("resolution=merge-duplicates")
    headers["Prefer"] = ", ".join(prefer_values)

    if auth_token:
        headers["apikey"] = pub_key
        headers["Authorization"] = f"Bearer {auth_token}"
    elif sec_key:
        headers["apikey"] = sec_key
        headers["Authorization"] = f"Bearer {sec_key}"
    else:
        headers["apikey"] = pub_key

    return headers


# ==============================================================================
# 1. TUTOR SESSIONS
# ==============================================================================

def sync_tutor_session(
    session_data: Dict[str, Any],
    auth_token: Optional[str] = None,
) -> Optional[str]:
    """Persists a tutor session into Supabase tutor_sessions table."""
    if not is_configured():
        return None

    sid = session_data.get("id")
    learner_id = session_data.get("learner_id")
    question = session_data.get("question") or ""
    subject = session_data.get("subject") or "Mathematics"
    misconception = session_data.get("misconception")
    result = session_data.get("result")
    sample_id = session_data.get("sample_id")

    payload: Dict[str, Any] = {
        "question": question[:4000],
        "subject": subject[:100],
        "misconception": misconception,
        "result": result if isinstance(result, (dict, list)) else {"text": str(result)},
    }
    if sid:
        payload["id"] = sid
    if learner_id:
        payload["learner_id"] = str(learner_id)
    if sample_id:
        payload["sample_id"] = str(sample_id)

    try:
        url = f"{auth.supabase_url()}/rest/v1/tutor_sessions"
        headers = _build_headers(auth_token, prefer_merge=True)
        res = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        if res.status_code in (200, 201):
            body = res.json()
            row = body[0] if isinstance(body, list) and body else body
            return str(row.get("id")) if isinstance(row, dict) and row.get("id") else sid
        log.warning("Supabase sync_tutor_session HTTP %s: %s", res.status_code, res.text[:200])
    except Exception as exc:
        log.debug("Supabase sync_tutor_session error (falling back to local): %s", exc)
    return None


def fetch_tutor_sessions(
    learner_id: str,
    limit: int = 50,
    subject: Optional[str] = None,
    search: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetches sessions for learner from Supabase. Returns None on network/config failure."""
    if not is_configured():
        return None

    try:
        url = f"{auth.supabase_url()}/rest/v1/tutor_sessions"
        params: Dict[str, str] = {
            "select": "id,learner_id,question,subject,misconception,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        if learner_id and learner_id != "student_demo":
            params["learner_id"] = f"eq.{learner_id}"
        if subject and subject.lower() != "all":
            params["subject"] = f"ilike.{subject}"
        if search and search.strip():
            params["or"] = f"(question.ilike.%{search.strip()}%,misconception.ilike.%{search.strip()}%)"

        headers = _build_headers(auth_token)
        res = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        if res.status_code == 200:
            return res.json()
        log.warning("Supabase fetch_tutor_sessions HTTP %s: %s", res.status_code, res.text[:200])
    except Exception as exc:
        log.debug("Supabase fetch_tutor_sessions error (falling back): %s", exc)
    return None


def fetch_tutor_session_by_id(
    session_id: str,
    auth_token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a single session by ID from Supabase."""
    if not is_configured():
        return None

    try:
        url = f"{auth.supabase_url()}/rest/v1/tutor_sessions"
        params = {"id": f"eq.{session_id}", "select": "*"}
        headers = _build_headers(auth_token)
        res = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        if res.status_code == 200:
            rows = res.json()
            if rows and isinstance(rows, list):
                row = rows[0]
                return {
                    "id": row.get("id"),
                    "learner_id": row.get("learner_id"),
                    "question": row.get("question"),
                    "subject": row.get("subject"),
                    "misconception": row.get("misconception"),
                    "result": row.get("result") or {},
                    "created_at": row.get("created_at"),
                }
    except Exception as exc:
        log.debug("Supabase fetch_tutor_session_by_id error: %s", exc)
    return None


def delete_tutor_session(
    session_id: str,
    learner_id: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> bool:
    """Deletes a session from Supabase tutor_sessions."""
    if not is_configured():
        return False

    try:
        url = f"{auth.supabase_url()}/rest/v1/tutor_sessions"
        params = {"id": f"eq.{session_id}"}
        if learner_id and learner_id != "student_demo":
            params["learner_id"] = f"eq.{learner_id}"
        headers = _build_headers(auth_token)
        res = requests.delete(url, params=params, headers=headers, timeout=_TIMEOUT)
        return res.status_code in (200, 204)
    except Exception as exc:
        log.debug("Supabase delete_tutor_session error: %s", exc)
        return False


# ==============================================================================
# 2. BAYESIAN KNOWLEDGE TRACING (BKT) STATES
# ==============================================================================

def sync_bkt_state(
    learner_id: str,
    misc_id: str,
    p_mastery: float,
    last_updated: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> bool:
    """Upserts incremental BKT knowledge state into Supabase bkt_states."""
    if not is_configured() or not learner_id or not misc_id:
        return False

    payload = {
        "learner_id": str(learner_id),
        "misc_id": str(misc_id),
        "p_mastery": float(p_mastery),
    }
    if last_updated:
        payload["last_updated"] = last_updated

    try:
        url = f"{auth.supabase_url()}/rest/v1/bkt_states"
        headers = _build_headers(auth_token, prefer_merge=True)
        res = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        return res.status_code in (200, 201)
    except Exception as exc:
        log.debug("Supabase sync_bkt_state error: %s", exc)
        return False


def fetch_bkt_masteries(
    learner_id: str,
    auth_token: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """Fetches latent BKT concept masteries for learner from Supabase."""
    if not is_configured() or not learner_id:
        return None

    try:
        url = f"{auth.supabase_url()}/rest/v1/bkt_states"
        params = {"learner_id": f"eq.{learner_id}", "select": "misc_id,p_mastery"}
        headers = _build_headers(auth_token)
        res = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        if res.status_code == 200:
            rows = res.json()
            if isinstance(rows, list):
                return {r["misc_id"]: float(r["p_mastery"]) for r in rows if "misc_id" in r and "p_mastery" in r}
    except Exception as exc:
        log.debug("Supabase fetch_bkt_masteries error: %s", exc)
    return None


# ==============================================================================
# 3. PRACTICE ATTEMPTS
# ==============================================================================

def sync_practice_attempt(
    attempt_data: Dict[str, Any],
    auth_token: Optional[str] = None,
) -> bool:
    """Logs practice attempt in Supabase practice_attempts."""
    if not is_configured():
        return False

    payload = {
        "learner_id": str(attempt_data.get("learner_id", "student_demo")),
        "practice_id": str(attempt_data.get("practice_id", "prac_01")),
        "subject": str(attempt_data.get("subject", "Mathematics")),
        "misconception": attempt_data.get("misconception"),
        "correct": bool(attempt_data.get("correct")),
        "answer": str(attempt_data.get("answer", ""))[:4000],
    }
    if attempt_data.get("session_id"):
        payload["session_id"] = attempt_data["session_id"]

    try:
        url = f"{auth.supabase_url()}/rest/v1/practice_attempts"
        headers = _build_headers(auth_token)
        res = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        return res.status_code in (200, 201)
    except Exception as exc:
        log.debug("Supabase sync_practice_attempt error: %s", exc)
        return False


def fetch_practice_progress(
    learner_id: str,
    auth_token: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetches raw practice attempts for aggregation from Supabase."""
    if not is_configured():
        return None

    try:
        url = f"{auth.supabase_url()}/rest/v1/practice_attempts"
        params = {
            "select": "subject,misconception,correct",
            "learner_id": f"eq.{learner_id}",
        }
        headers = _build_headers(auth_token)
        res = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        if res.status_code == 200:
            return res.json()
    except Exception as exc:
        log.debug("Supabase fetch_practice_progress error: %s", exc)
    return None


# ==============================================================================
# 4. LEARNER NOTIFICATIONS
# ==============================================================================

def fetch_learner_notifications(
    learner_id: str,
    auth_token: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetches learner notifications from Supabase."""
    if not is_configured():
        return None

    try:
        url = f"{auth.supabase_url()}/rest/v1/learner_notifications"
        params = {
            "learner_id": f"eq.{learner_id}",
            "order": "created_at.desc",
            "select": "id,title,message,icon,category,read_status,created_at",
        }
        headers = _build_headers(auth_token)
        res = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
        if res.status_code == 200:
            rows = res.json()
            if isinstance(rows, list):
                return [
                    {
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "message": r.get("message"),
                        "icon": r.get("icon") or "sparkles",
                        "category": r.get("category") or "general",
                        "read": bool(r.get("read_status")),
                        "created_at": r.get("created_at"),
                    }
                    for r in rows
                ]
    except Exception as exc:
        log.debug("Supabase fetch_learner_notifications error: %s", exc)
    return None


def mark_notification_read(
    notif_id: str,
    learner_id: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> bool:
    """Marks one or all notifications as read in Supabase."""
    if not is_configured():
        return False

    try:
        url = f"{auth.supabase_url()}/rest/v1/learner_notifications"
        params: Dict[str, str] = {}
        if notif_id and notif_id != "all":
            params["id"] = f"eq.{notif_id}"
        if learner_id and learner_id != "student_demo":
            params["learner_id"] = f"eq.{learner_id}"

        headers = _build_headers(auth_token)
        res = requests.patch(url, json={"read_status": True}, params=params, headers=headers, timeout=_TIMEOUT)
        return res.status_code in (200, 204)
    except Exception as exc:
        log.debug("Supabase mark_notification_read error: %s", exc)
        return False
