"""Gamification Engine: XP, Levels, Streaks, Daily Challenges, and Explain-It-Back.

Provides the habit-forming layer on top of the tutor:
  - XP earned for every learning action, with combo bonuses
  - Levels from "Curious Beginner" (1) to "Cognitive Master" (50)
  - Calendar-backed streaks with freeze mechanic
  - Daily Challenge: one adaptive problem per day targeting weakest concept
  - Explain-It-Back: learner restates a concept, graded for depth

All data stored locally in SQLite with optional Supabase cloud sync.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, date, timezone, timedelta
from typing import Any, Dict, List, Optional

log = logging.getLogger("misconception_tutor.gamification")

# ==============================================================================
# XP & LEVEL CONFIGURATION
# ==============================================================================

# XP awards per action
XP_AWARDS = {
    "ask_question": 10,
    "practice_correct": 15,
    "practice_incorrect": 5,
    "daily_challenge_complete": 30,
    "streak_day": 5,
    "explain_back_1star": 10,
    "explain_back_2star": 20,
    "explain_back_3star": 35,
    "feedback_given": 5,
}

# Combo bonus: 3+ correct in a row
COMBO_THRESHOLD = 3
COMBO_BONUS_XP = 25

# Level titles and their XP thresholds
LEVEL_TIERS = [
    (1, 0, "Curious Beginner"),
    (5, 200, "Curious Beginner"),
    (10, 600, "Pattern Spotter"),
    (15, 1200, "Pattern Spotter"),
    (20, 2000, "Bug Hunter"),
    (25, 3200, "Bug Hunter"),
    (30, 5000, "Misconception Slayer"),
    (35, 7500, "Misconception Slayer"),
    (40, 11000, "Misconception Slayer"),
    (45, 16000, "Cognitive Master"),
    (50, 22000, "Cognitive Master"),
]


def level_for_xp(total_xp: int) -> Dict[str, Any]:
    """Computes current level, title, and progress to next level from total XP."""
    current_level = 1
    current_title = "Curious Beginner"
    current_threshold = 0
    next_threshold = 200

    for i, (lvl, threshold, title) in enumerate(LEVEL_TIERS):
        if total_xp >= threshold:
            current_level = lvl
            current_title = title
            current_threshold = threshold
            if i + 1 < len(LEVEL_TIERS):
                next_threshold = LEVEL_TIERS[i + 1][1]
            else:
                next_threshold = threshold + 2000
        else:
            break

    # Fine-grained level within tier (interpolate between tier boundaries)
    xp_in_tier = total_xp - current_threshold
    tier_range = next_threshold - current_threshold
    sub_levels = 5  # each tier has 5 sub-levels
    if tier_range > 0:
        sub = min(sub_levels - 1, int(xp_in_tier / (tier_range / sub_levels)))
        fine_level = current_level + sub
    else:
        fine_level = current_level

    progress_pct = int((xp_in_tier / tier_range) * 100) if tier_range > 0 else 100

    return {
        "level": min(50, fine_level),
        "title": current_title,
        "total_xp": total_xp,
        "xp_in_tier": xp_in_tier,
        "xp_to_next_level": max(0, next_threshold - total_xp),
        "next_level_xp": next_threshold,
        "progress_percent": min(100, progress_pct),
    }


# ==============================================================================
# STREAK CONFIGURATION
# ==============================================================================

STREAK_FREEZE_EARN_DAYS = 7  # Earn one freeze every 7 active days
MAX_STREAK_FREEZES = 3


# ==============================================================================
# DATABASE SCHEMA & INIT
# ==============================================================================

def init_gamification_tables(conn: sqlite3.Connection) -> None:
    """Creates gamification tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learner_xp (
            learner_id TEXT PRIMARY KEY,
            total_xp INTEGER NOT NULL DEFAULT 0,
            combo_count INTEGER NOT NULL DEFAULT 0,
            total_actions INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            action TEXT NOT NULL,
            xp_earned INTEGER NOT NULL,
            bonus_xp INTEGER NOT NULL DEFAULT 0,
            detail TEXT,
            ts TEXT NOT NULL
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_xp_log_learner ON xp_log(learner_id, ts DESC);")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS streak_data (
            learner_id TEXT PRIMARY KEY,
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_active_date TEXT,
            freezes_available INTEGER NOT NULL DEFAULT 1,
            freezes_used_total INTEGER NOT NULL DEFAULT 0,
            total_active_days INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS streak_calendar (
            learner_id TEXT NOT NULL,
            active_date TEXT NOT NULL,
            action_count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (learner_id, active_date)
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_challenges (
            learner_id TEXT NOT NULL,
            challenge_date TEXT NOT NULL,
            target_misc TEXT,
            problem_json TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            correct INTEGER,
            xp_earned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            PRIMARY KEY (learner_id, challenge_date)
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS explain_back (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            session_id TEXT,
            misconception TEXT,
            learner_explanation TEXT NOT NULL,
            stars INTEGER NOT NULL DEFAULT 0,
            feedback TEXT,
            xp_earned INTEGER NOT NULL DEFAULT 0,
            ts TEXT NOT NULL
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_explain_learner ON explain_back(learner_id, ts DESC);")


# ==============================================================================
# XP ENGINE
# ==============================================================================

def award_xp(
    conn: sqlite3.Connection,
    learner_id: str,
    action: str,
    is_correct: Optional[bool] = None,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    """Awards XP for a learning action. Returns XP breakdown and level info."""
    now = datetime.now(timezone.utc).isoformat()
    base_xp = XP_AWARDS.get(action, 5)
    bonus_xp = 0

    # Update combo counter
    cur = conn.cursor()
    cur.execute("SELECT total_xp, combo_count FROM learner_xp WHERE learner_id = ?", (learner_id,))
    row = cur.fetchone()

    if row:
        total_xp = row["total_xp"]
        combo = row["combo_count"]
    else:
        total_xp = 0
        combo = 0

    # Combo tracking for practice
    if action.startswith("practice_"):
        if is_correct:
            combo += 1
            if combo >= COMBO_THRESHOLD and combo % COMBO_THRESHOLD == 0:
                bonus_xp = COMBO_BONUS_XP
        else:
            combo = 0
    elif action == "explain_back_3star":
        # Double XP for perfect explain-back
        bonus_xp = base_xp  # effectively 2× (base + bonus = 70)

    earned = base_xp + bonus_xp
    new_total = total_xp + earned

    # Upsert XP record
    cur.execute("""
        INSERT INTO learner_xp (learner_id, total_xp, combo_count, total_actions, updated_at)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(learner_id) DO UPDATE SET
            total_xp = learner_xp.total_xp + ?,
            combo_count = ?,
            total_actions = learner_xp.total_actions + 1,
            updated_at = ?;
    """, (learner_id, earned, combo, now, earned, combo, now))

    # Log it
    cur.execute("""
        INSERT INTO xp_log (learner_id, action, xp_earned, bonus_xp, detail, ts)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (learner_id, action, base_xp, bonus_xp, detail, now))

    level_info = level_for_xp(new_total)

    # Check if leveled up
    old_level = level_for_xp(total_xp)["level"]
    leveled_up = level_info["level"] > old_level

    return {
        "xp_earned": earned,
        "base_xp": base_xp,
        "bonus_xp": bonus_xp,
        "combo_count": combo,
        "combo_bonus": bonus_xp > 0 and action.startswith("practice_"),
        "leveled_up": leveled_up,
        **level_info,
    }


def get_xp_profile(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    """Returns the learner's full XP profile and level info."""
    cur = conn.cursor()
    cur.execute("SELECT total_xp, combo_count, total_actions FROM learner_xp WHERE learner_id = ?", (learner_id,))
    row = cur.fetchone()

    total_xp = row["total_xp"] if row else 0
    combo = row["combo_count"] if row else 0
    total_actions = row["total_actions"] if row else 0

    # Recent XP log
    cur.execute("""
        SELECT action, xp_earned, bonus_xp, detail, ts
        FROM xp_log WHERE learner_id = ?
        ORDER BY ts DESC LIMIT 15
    """, (learner_id,))
    recent = [dict(r) for r in cur.fetchall()]

    return {
        **level_for_xp(total_xp),
        "combo_count": combo,
        "total_actions": total_actions,
        "recent_xp": recent,
    }


# ==============================================================================
# STREAK ENGINE
# ==============================================================================

def record_active_day(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    """Records today as an active study day and updates streak."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    cur = conn.cursor()

    # Mark today in calendar
    cur.execute("""
        INSERT INTO streak_calendar (learner_id, active_date, action_count)
        VALUES (?, ?, 1)
        ON CONFLICT(learner_id, active_date) DO UPDATE SET
            action_count = streak_calendar.action_count + 1;
    """, (learner_id, today))

    # Get current streak data
    cur.execute("SELECT * FROM streak_data WHERE learner_id = ?", (learner_id,))
    row = cur.fetchone()

    if row:
        last_active = row["last_active_date"]
        streak = row["current_streak"]
        longest = row["longest_streak"]
        freezes = row["freezes_available"]
        freezes_used = row["freezes_used_total"]
        total_days = row["total_active_days"]
    else:
        last_active = None
        streak = 0
        longest = 0
        freezes = 1
        freezes_used = 0
        total_days = 0

    # Already counted today
    if last_active == today:
        return _streak_response(streak, longest, freezes, total_days, today, leveled_up_streak=False)

    # Streak logic
    if last_active == yesterday:
        # Consecutive day
        streak += 1
    elif last_active and last_active != today:
        # Missed days — check if we can use a freeze
        missed = (date.today() - date.fromisoformat(last_active)).days - 1
        if missed == 1 and freezes > 0:
            freezes -= 1
            freezes_used += 1
            streak += 1  # freeze saves the streak
        else:
            streak = 1  # reset
    else:
        streak = 1  # first ever day

    total_days += 1
    longest = max(longest, streak)

    # Earn freeze every 7 active days
    if total_days > 0 and total_days % STREAK_FREEZE_EARN_DAYS == 0 and freezes < MAX_STREAK_FREEZES:
        freezes += 1

    # Upsert
    cur.execute("""
        INSERT INTO streak_data (learner_id, current_streak, longest_streak, last_active_date,
                                  freezes_available, freezes_used_total, total_active_days, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(learner_id) DO UPDATE SET
            current_streak = ?, longest_streak = ?, last_active_date = ?,
            freezes_available = ?, freezes_used_total = ?, total_active_days = ?, updated_at = ?;
    """, (
        learner_id, streak, longest, today, freezes, freezes_used, total_days, now,
        streak, longest, today, freezes, freezes_used, total_days, now,
    ))

    return _streak_response(streak, longest, freezes, total_days, today, leveled_up_streak=(streak in (7, 30, 100, 365)))


def get_streak(conn: sqlite3.Connection, learner_id: str) -> Dict[str, Any]:
    """Returns the learner's streak data and 7-day calendar."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM streak_data WHERE learner_id = ?", (learner_id,))
    row = cur.fetchone()

    streak = row["current_streak"] if row else 0
    longest = row["longest_streak"] if row else 0
    freezes = row["freezes_available"] if row else 1
    total_days = row["total_active_days"] if row else 0
    last_active = row["last_active_date"] if row else None

    # Check if streak broke since last visit
    if last_active:
        gap = (date.today() - date.fromisoformat(last_active)).days
        if gap > 1 and not (gap == 2 and freezes > 0):
            streak = 0  # broken

    return _streak_response(streak, longest, freezes, total_days, last_active, leveled_up_streak=False)


def _streak_response(
    streak: int, longest: int, freezes: int, total_days: int,
    last_active: Optional[str], leveled_up_streak: bool,
) -> Dict[str, Any]:
    """Builds streak response with 7-day calendar."""
    today = date.today()
    week_days = []
    day_names = ["M", "T", "W", "T", "F", "S", "S"]
    start_of_week = today - timedelta(days=today.weekday())

    for i in range(7):
        d = start_of_week + timedelta(days=i)
        week_days.append({
            "day": day_names[i],
            "date": d.isoformat(),
            "active": last_active is not None and d <= today and d.isoformat() <= (last_active or ""),
            "today": d == today,
        })

    # Milestone badges
    milestones = []
    for m in (7, 30, 100, 365):
        milestones.append({"days": m, "achieved": streak >= m or longest >= m})

    flame_size = "small" if streak < 7 else ("medium" if streak < 30 else ("large" if streak < 100 else "blazing"))

    return {
        "current_streak": streak,
        "longest_streak": longest,
        "freezes_available": freezes,
        "total_active_days": total_days,
        "last_active_date": last_active,
        "flame_size": flame_size,
        "streak_milestone": leveled_up_streak,
        "week_days": week_days,
        "milestones": milestones,
    }


# ==============================================================================
# DAILY CHALLENGE ENGINE
# ==============================================================================

def get_or_create_daily_challenge(
    conn: sqlite3.Connection,
    learner_id: str,
    generate_problem_fn=None,
    get_masteries_fn=None,
    all_bugs: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Returns today's challenge, creating one if needed."""
    today = date.today().isoformat()
    cur = conn.cursor()

    # Check if already exists
    cur.execute(
        "SELECT * FROM daily_challenges WHERE learner_id = ? AND challenge_date = ?",
        (learner_id, today),
    )
    existing = cur.fetchone()
    if existing:
        problem = json.loads(existing["problem_json"]) if existing["problem_json"] else None
        return {
            "date": today,
            "completed": bool(existing["completed"]),
            "correct": existing["correct"],
            "xp_earned": existing["xp_earned"],
            "target_misc": existing["target_misc"],
            "problem": problem,
        }

    # Create new daily challenge targeting weakest misconception
    target = "M1_add_across"  # fallback
    if all_bugs:
        try:
            cur.execute("SELECT misc_id, p_mastery FROM bkt_states WHERE learner_id = ?", (learner_id,))
            masteries = {r["misc_id"]: float(r["p_mastery"]) for r in cur.fetchall()}
            bugs = list(all_bugs.keys())
            if bugs:
                bugs.sort(key=lambda b: masteries.get(b, 0.5))
                target = bugs[0]
        except Exception:
            if get_masteries_fn:
                try:
                    masteries = get_masteries_fn(learner_id)
                    bugs = list(all_bugs.keys())
                    if bugs:
                        bugs.sort(key=lambda b: masteries.get(b, 0.5))
                        target = bugs[0]
                except Exception:
                    pass

    problem = None
    if generate_problem_fn:
        try:
            problem = generate_problem_fn(target, difficulty=1)
        except Exception:
            pass

    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO daily_challenges (learner_id, challenge_date, target_misc, problem_json, completed, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    """, (learner_id, today, target, json.dumps(problem) if problem else None, now))

    return {
        "date": today,
        "completed": False,
        "correct": None,
        "xp_earned": 0,
        "target_misc": target,
        "problem": problem,
    }


def complete_daily_challenge(
    conn: sqlite3.Connection,
    learner_id: str,
    correct: bool,
) -> Dict[str, Any]:
    """Marks today's challenge as completed and awards XP."""
    today = date.today().isoformat()
    cur = conn.cursor()

    cur.execute(
        "SELECT completed FROM daily_challenges WHERE learner_id = ? AND challenge_date = ?",
        (learner_id, today),
    )
    row = cur.fetchone()
    if not row:
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO daily_challenges (learner_id, challenge_date, target_misc, problem_json, completed, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (learner_id, today, "M1_add_across", None, now))
        row = {"completed": 0}

    if row["completed"]:
        return {"completed": True, "already_completed": True, "xp_earned": 0}

    xp_result = award_xp(conn, learner_id, "daily_challenge_complete", is_correct=correct, detail=f"Daily Challenge {today}")

    cur.execute("""
        UPDATE daily_challenges
        SET completed = 1, correct = ?, xp_earned = ?
        WHERE learner_id = ? AND challenge_date = ?
    """, (int(correct), xp_result["xp_earned"], learner_id, today))

    return {
        "completed": True,
        "correct": correct,
        **xp_result,
    }


def get_challenge_history(conn: sqlite3.Connection, learner_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Returns past daily challenge results."""
    cur = conn.cursor()
    cur.execute("""
        SELECT challenge_date, target_misc, completed, correct, xp_earned
        FROM daily_challenges
        WHERE learner_id = ?
        ORDER BY challenge_date DESC
        LIMIT ?
    """, (learner_id, limit))
    return [dict(r) for r in cur.fetchall()]


# ==============================================================================
# EXPLAIN-IT-BACK ENGINE
# ==============================================================================

def save_explain_back(
    conn: sqlite3.Connection,
    learner_id: str,
    misconception: str,
    learner_explanation: str,
    stars: int,
    feedback: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Records an explain-it-back attempt and awards XP based on star rating."""
    now = datetime.now(timezone.utc).isoformat()
    stars = max(0, min(3, stars))

    # Award XP by star level
    action = f"explain_back_{stars}star"
    xp_result = award_xp(conn, learner_id, action, detail=f"Explain: {misconception[:60]}")

    conn.execute("""
        INSERT INTO explain_back (learner_id, session_id, misconception, learner_explanation, stars, feedback, xp_earned, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (learner_id, session_id, misconception, learner_explanation[:4000], stars, feedback[:2000] if feedback else None, xp_result["xp_earned"], now))

    return {
        "stars": stars,
        "feedback": feedback,
        **xp_result,
    }


def evaluate_explanation(
    misconception: str,
    learner_explanation: str,
    subject: str = "Mathematics",
) -> Dict[str, Any]:
    """Evaluates a learner's explanation of a misconception.

    Scored on a 3-star scale:
      ⭐⭐⭐ (3 stars): Complete, accurate concept coverage, explains *why* the bug occurs and the correct strategy.
      ⭐⭐ (2 stars): Mostly accurate with basic understanding, but missing depth or key nuance.
      ⭐ (1 star): Too brief, vague, or repeats the misconception without clarifying the underlying rule.
    """
    text = (learner_explanation or "").strip()
    words = text.split()
    word_count = len(words)
    text_lower = text.lower()

    if word_count < 6:
        return {
            "stars": 1,
            "completeness": "Needs more detail",
            "accuracy": "Incomplete",
            "clarity": "Too brief",
            "feedback": "Your explanation is a bit too brief! Try expanding on what specifically caused the error and how to handle it properly.",
        }

    # Keyword concept rubrics based on common subject domains
    keywords_math = ["denominator", "common", "lcm", "scale", "factor", "sign", "terms", "multiply", "parts", "derivative", "integral", "fraction", "cross"]
    keywords_code = ["base case", "recursion", "memo", "cache", "return", "boundary", "index", "stack", "time complexity", "loop", "state"]

    relevant_keywords = keywords_code if "python" in subject.lower() or "code" in subject.lower() else keywords_math
    matched_keywords = [kw for kw in relevant_keywords if kw in text_lower]

    # Evaluate depth and clarity
    has_why = any(w in text_lower for w in ["because", "since", "so that", "why", "instead of", "means that", "reason"])
    has_how = any(w in text_lower for w in ["need to", "must", "should", "first", "then", "have to", "rule"])

    if word_count >= 15 and len(matched_keywords) >= 2 and (has_why or has_how):
        stars = 3
        feedback = f"Outstanding explanation! You clearly highlighted the core idea (mentioning {', '.join(matched_keywords[:3])}) and explained both why the slip happens and how to resolve it correctly."
        completeness = "Excellent"
        accuracy = "High"
        clarity = "Very Clear"
    elif word_count >= 10 and (len(matched_keywords) >= 1 or has_why):
        stars = 2
        feedback = "Great effort! You grasped the main concept. To reach 3 stars, try explaining a bit more about the exact mathematical reasoning or step."
        completeness = "Good"
        accuracy = "Solid"
        clarity = "Clear"
    else:
        stars = 1
        feedback = "You're on the right track! Try to be more specific about the rule or principle (e.g. why denominators need to be equal or why a base case is necessary)."
        completeness = "Basic"
        accuracy = "Fair"
        clarity = "Needs expansion"

    return {
        "stars": stars,
        "completeness": completeness,
        "accuracy": accuracy,
        "clarity": clarity,
        "feedback": feedback,
    }


def get_explain_back_history(conn: sqlite3.Connection, learner_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Returns past explain-back attempts."""
    cur = conn.cursor()
    cur.execute("""
        SELECT misconception, stars, feedback, xp_earned, ts
        FROM explain_back
        WHERE learner_id = ?
        ORDER BY ts DESC
        LIMIT ?
    """, (learner_id, limit))
    return [dict(r) for r in cur.fetchall()]
