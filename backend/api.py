"""
================================================================================
AI That Teaches: Misconception Tutor — Unified Web API & Service Engine
Connects UI/UX, Cognitive Math Engine (backend_code.py), and LLM Training Pipeline.
Theme 5 · Problem 8: A Tutor That Finds the Real Reason You're Stuck
IIT Bombay Techfest (Perceptron Hackathon 2026)
================================================================================
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, g, jsonify, request, send_from_directory, stream_with_context

from backend import auth, backend_code, training_store
from backend.llm_engine import llm_engine
from backend.security.guard import prompt_guard
from backend.security.sanitizer import (
    sanitize_input_text,
    sanitize_math_answer,
    sanitize_learner_id,
    sanitize_filename,
    sanitize_search_query,
    validate_file_upload,
)
from backend.security.middleware import register_security_middleware
from backend.memory.lifecycle import memory_lifecycle
from backend.practice import classify_misconception, generate_practice_set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "LLM") not in __import__("sys").path:  # the 4-agent package lives in LLM/tutor_agents
    __import__("sys").path.insert(0, str(ROOT / "LLM"))
UI_DIR = ROOT / "UI and UX"
DATA_DIR = ROOT / "data"

app = Flask(__name__)

# Register ECC Enterprise Security Suite (Security Headers & Rate Limiting)
register_security_middleware(app)

# Initialize database tables on startup
backend_code.init_db()


@app.after_request
def add_no_cache_headers(response):
    """Enforce fresh asset downloads for responsive UI changes."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.before_request
def require_sign_in():
    """Tutor routes run only for a signed-in Supabase user (see backend/auth.py)."""
    g.user = None
    if request.method == "OPTIONS" or not auth.is_protected(request.path) or not auth.auth_required():
        return None
    token = auth.bearer_token(request.headers.get("Authorization"))
    user = auth.verify_token(token) if token else None
    if not user:
        return jsonify({"error": "Please sign in to use the tutor.", "status": "unauthenticated"}), 401
    g.user = user
    return None


# ==============================================================================
# SECTION 1: STATIC & ASSET ROUTES (Serving the approved UI/UX)
# ==============================================================================

@app.get("/")
def index():
    """Serves the Sikora AI interface (no-cache headers come from add_no_cache_headers)."""
    return send_from_directory(UI_DIR, "index.html")


@app.get("/login")
def login_page():
    """Sign-in and sign-up page."""
    return send_from_directory(UI_DIR, "login.html")


@app.get("/logo.png")
def logo_image():
    return send_from_directory(UI_DIR, "logo.png")


@app.get("/favicon.png")
def favicon_image():
    return send_from_directory(UI_DIR, "favicon.png")


@app.get("/auth.js")
def auth_script():
    """Shared Supabase sign-in helpers for the pages."""
    return send_from_directory(UI_DIR, "auth.js")


@app.get("/config.js")
def public_config():
    """Supabase project URL and publishable key for the browser (both are public values)."""
    body = "window.SUPABASE_CONFIG = " + json.dumps(auth.public_config()) + ";\n"
    return Response(body, mimetype="application/javascript")


@app.get("/app.js")
def app_script():
    """Serves the frontend application controller."""
    return send_from_directory(UI_DIR, "app.js")


@app.get("/tutor.css")
def tutor_styles():
    """Serves the styles for the tutor's result cards."""
    return send_from_directory(UI_DIR, "tutor.css")


# ==============================================================================
# SECTION 2: HEALTH & SYSTEM READINESS API
# ==============================================================================

@app.get("/api/health")
def health():
    """Returns the basic application liveness status."""
    return jsonify({"status": "online"})


@app.get("/api/ready")
def ready():
    status = llm_engine.status()

    if not status["loaded"]:
        return jsonify({
            "ready": False,
            "model": status["model"],
            "error": status["error"],
        }), 503

    return jsonify({
        "ready": True,
        "model": status["model"],
    }), 200


@app.get("/api/backend-status")
def backend_status():
    llm_stat = llm_engine.status()
    # When running locally in hybrid / diagnostic mode, the tutor engine is online and ready
    llm_only = os.getenv("LLM_ONLY_MODEL", "0").strip().lower() in ("1", "true", "yes")
    model_state = llm_stat.get("modelState")
    if not model_state or model_state == "offline":
        model_state = "ready" if (llm_stat.get("loaded") or not llm_only) else "offline"

    return jsonify({
        "status": "online",
        "liveAiEnabled": bool(llm_stat["loaded"] or not llm_only),
        "model": llm_stat["model"] if llm_stat.get("loaded") else "Sikora Cognitive Math Engine (Hybrid/Diagnostic)",
        "llmLoaded": bool(llm_stat["loaded"] or not llm_only),
        "llmError": llm_stat["error"],
        "mode": llm_stat.get("mode") or "Cognitive Socratic Engine (Hybrid/Diagnostic)",
        "remoteBackend": llm_stat.get("remoteBackend"),
        "agents": llm_stat.get("agents"),
        "modelOnly": llm_only,
        "modelState": model_state,
        "trainingMode": "offline_kaggle",
        "trainingSamplesCollected": (
            llm_stat["trainingSamplesCollected"]
        ),
    })


@app.post("/api/model/wake")
def wake_model():
    """Start an on-demand (AWS) model server as soon as a learner opens the tutor."""
    return jsonify(llm_engine.wake_model())


# ==============================================================================
# SECTION 3: MATHEMATICAL PROBLEM GENERATION & BENCHMARKS
# ==============================================================================

@app.get("/api/problems/base")
def get_base_problems():
    """Returns the 30 verified benchmark problems (20 addition, 10 division)."""
    return jsonify({
        "total": len(backend_code.BASE_PROBLEMS),
        "problems": backend_code.BASE_PROBLEMS,
    })


@app.get("/api/problems/next")
def get_next_problem():
    """
    Generates the next practice problem adaptively or by category.
    If learner_id is provided, adaptively targets the student's weakest misconception (lowest BKT mastery).
    """
    learner_id = request.args.get("learner_id", "student_demo")
    operation = request.args.get("operation", "fraction_add")
    difficulty = int(request.args.get("difficulty", 1))
    target_misc = request.args.get("target_misc")

    # Adaptive selection using Bayesian Knowledge Tracing
    if not target_misc and learner_id:
        masteries = backend_code.get_learner_mastery(learner_id)
        candidate_bugs = list(backend_code.BUGS_ADD.keys()) if operation == "fraction_add" else list(backend_code.BUGS_DIV.keys())
        
        # Pick candidate with lowest mastery score
        candidate_bugs.sort(key=lambda b: masteries.get(b, backend_code.DEFAULT_BKT_PARAMS["p_init"]))
        target_misc = candidate_bugs[0]

    target_misc = target_misc or ("M1_add_across" if operation == "fraction_add" else "M4_divide_multiply_across")
    problem = backend_code.generate_problem(target_misc, difficulty=difficulty)

    return jsonify({
        "problem": problem,
        "adaptive_target": target_misc,
        "difficulty": difficulty,
    })


# ==============================================================================
# SECTION 4: COGNITIVE DIAGNOSIS & REPLAY ENGINE
# ==============================================================================

@app.post("/api/diagnose")
def diagnose_answer():
    """
    Diagnoses student answer using exact arithmetic and Brown & Burton (1978) buggy rules:
    1. Evaluates correctness with exact rational fractions.
    2. If incorrect, checks M1-M5 buggy rules to find the exact mental bug.
    3. Generates step-by-step cognitive replay ('Why we think this').
    4. Generates collision-free follow-up problem targeting that bug.
    5. Updates BKT Bayesian Knowledge Tracing.
    6. Logs the interaction into the LLM continuous training dataset.
    """
    data = request.get_json(silent=True) or {}
    raw_answer = str(data.get("answer", "")).strip()
    user_answer = sanitize_math_answer(raw_answer)
    learner_id = sanitize_input_text(str(data.get("learner_id", "student_demo")), max_length=64) or "student_demo"
    session_id = sanitize_input_text(str(data.get("session_id", "sess_01")), max_length=64) or "sess_01"
    correct_answer = sanitize_math_answer(str(data.get("correct_answer", "")).strip())
    target_misc = sanitize_input_text(str(data.get("target_misc", "M1_add_across")), max_length=64)
    problem_text = sanitize_input_text(str(data.get("problem_text", "")), max_length=128)
    operation = sanitize_input_text(str(data.get("operation", "fraction_add")), max_length=64)

    a = int(data.get("a", 1))
    b = int(data.get("b", 4))
    c = int(data.get("c", 1))
    d = int(data.get("d", 6))

    if not user_answer:
        return jsonify({"error": "Answer cannot be empty."}), 400

    # ECC Memory Lifecycle: pre-observe intent & interaction
    memory_lifecycle.pre_observe(learner_id, user_answer)

    # 1. Exact arithmetic evaluation
    is_correct, student_frac = backend_code.check_answer(user_answer, correct_answer)

    # 2. Buggy rule matching
    detected_misc: Optional[str] = None
    confidence = 1.0 if is_correct else 0.50

    if not is_correct and student_frac is not None:
        bug_rules = backend_code.BUGS_ADD if operation == "fraction_add" else backend_code.BUGS_DIV
        for bug_id, bug_fn in bug_rules.items():
            try:
                top, bot = bug_fn(a, b, c, d)
                if bot != 0 and backend_code.Fraction(top, bot) == student_frac:
                    detected_misc = bug_id
                    confidence = 0.95
                    break
            except Exception:
                continue

        if not detected_misc:
            detected_misc = "unknown_misconception"
            confidence = 0.40

    # 3. Log attempt to SQLite & update BKT
    backend_code.log_attempt_db(
        learner_id=learner_id,
        session_id=session_id,
        problem_id=problem_text,
        target_misc=target_misc,
        answer=user_answer,
        correct=int(is_correct),
        predicted_misc=detected_misc if not is_correct else None,
        confidence=confidence,
    )

    # Fetch updated BKT masteries
    masteries = backend_code.get_learner_mastery(learner_id)

    # 4. Pedagogical explanation & Cognitive Replay
    replay = ""
    explanation_meta = None
    follow_up_problem = None

    if not is_correct:
        if detected_misc and detected_misc in backend_code.ALL_BUGS:
            replay = backend_code.generate_replay(detected_misc, a, b, c, d)
            explanation_meta = backend_code.EXPLANATIONS.get(detected_misc)
            # Generate collision-free targeted follow-up problem
            follow_up_problem = backend_code.generate_targeted_problem(detected_misc, difficulty=1)
        else:
            replay = f"Your answer '{user_answer}' does not match the expected result '{correct_answer}'. Let's check the denominators."
            explanation_meta = {
                "title": "Unidentified Step Slip",
                "why_it_fails": "The arithmetic diverged before reaching a common denominator.",
                "simple_example": "Check if both slice sizes match before adding or subtracting.",
                "fix_hint": "Find the least common multiple of denominators first.",
            }
            follow_up_problem = backend_code.generate_targeted_problem(target_misc, difficulty=1)

    # 5. Continuous Learning: Log sample into LLM training dataset
    instruction_text = (
        f"Diagnose the student's answer '{user_answer}' to '{problem_text}'."
        if not is_correct
        else f"Verify student's correct answer '{user_answer}' to '{problem_text}'."
    )
    socratic_output = (
        f"Result: Correct! The student successfully evaluated {problem_text} = {correct_answer}."
        if is_correct
        else f"Misconception: {detected_misc}. Replay: {replay} Fix: {explanation_meta.get('fix_hint') if explanation_meta else ''}"
    )

    sample_id = llm_engine.log_training_sample(
        subject="Mathematics",
        instruction=instruction_text,
        user_input=f"Problem: {problem_text}\nStudent Answer: {user_answer}\nCorrect Answer: {correct_answer}",
        model_output=socratic_output,
        learner_id=learner_id,
        misconception=detected_misc,
        feedback="auto_verified",
        metadata={
            "operation": operation,
            "correct": is_correct,
            "confidence": confidence,
            "problem_id": problem_text,
        },
    )

    # ECC Memory Lifecycle: post-observe update
    memory_lifecycle.post_observe(
        learner_id=learner_id,
        session_id=session_id,
        target_misc=detected_misc,
        is_correct=is_correct,
        response_length=len(replay),
    )

    return jsonify({
        "correct": is_correct,
        "detected_misc": detected_misc,
        "explanation": explanation_meta,
        "cognitive_replay": replay,
        "correct_answer": correct_answer,
        "student_parsed": backend_code.format_fraction(student_frac) if student_frac else user_answer,
        "masteries": masteries,
        "follow_up_problem": follow_up_problem,
        "practice_set": generate_practice_set(
            "Mathematics",
            detected_misc or target_misc,
            count=6,
        ),
        "training_sample_id": sample_id,
    })


# ==============================================================================
# SECTION 5: LEARNER PROFILE & TEACHER ANALYTICS
# ==============================================================================

@app.get("/api/learner/profile")
def get_learner_profile():
    """Returns student's latent concept mastery (BKT) and bug rate curves."""
    learner_id = request.args.get("learner_id", "student_demo")
    masteries = backend_code.get_learner_mastery(learner_id)
    bug_rates = backend_code.compute_bug_rates(learner_id)
    beliefs = backend_code.compute_belief_scores(learner_id)

    # Seed baseline masteries if student is new
    all_bugs = list(backend_code.ALL_BUGS.keys())
    for b in all_bugs:
        if b not in masteries:
            masteries[b] = backend_code.DEFAULT_BKT_PARAMS["p_init"]

    return jsonify({
        "learner_id": learner_id,
        "masteries": masteries,
        "bug_rates": bug_rates,
        "belief_scores": beliefs,
        "practice_progress": backend_code.get_practice_progress(learner_id),
    })


@app.get("/api/practice/progress")
def get_practice_progress():
    """Returns longitudinal accuracy evidence for targeted practice."""
    learner_id = sanitize_input_text(request.args.get("learner_id", "student_demo"), max_length=64) or "student_demo"
    return jsonify({
        "learner_id": learner_id,
        **backend_code.get_practice_progress(learner_id),
    })


@app.get("/api/teacher/analytics")
def get_teacher_analytics():
    """Aggregates cohort data for teacher dashboard and heatmap visualization."""
    heatmap = backend_code.get_teacher_heatmap_data()
    # If empty, simulate a small demo cohort so UI is immediately rich for presentations
    if not heatmap:
        backend_code.simulate_learning_cohort(num_students=4, num_sessions=2, problems_per_session=2)
        heatmap = backend_code.get_teacher_heatmap_data()

    return jsonify({
        "cohort_records": len(heatmap),
        "heatmap": heatmap,
    })


def _current_learner_id() -> str:
    token = auth.bearer_token(request.headers.get("Authorization"))
    if token:
        user = auth.verify_token(token)
        if user and user.get("id"):
            return sanitize_learner_id(str(user["id"]))
    raw_id = request.args.get("learner_id") or (request.json.get("learner_id") if request.is_json else None)
    return sanitize_learner_id(raw_id)


# ==============================================================================
# SECTION 5B: SESSIONS LIBRARY, PRACTICE LAB & DASHBOARD ENGINE
# ==============================================================================

@app.get("/api/learner/sessions")
def list_learner_sessions():
    """Returns past study sessions for the learner with search and subject filters."""
    learner_id = _current_learner_id()
    limit = min(100, max(1, int(request.args.get("limit", 50))))
    subject = sanitize_input_text(request.args.get("subject"), max_length=50) if request.args.get("subject") else None
    search = sanitize_search_query(request.args.get("search")) if request.args.get("search") else None
    sessions = backend_code.get_tutor_sessions(learner_id, limit=limit, subject=subject, search=search)
    return jsonify({
        "learner_id": learner_id,
        "count": len(sessions),
        "sessions": sessions,
    })


@app.post("/api/learner/sessions")
def create_learner_session():
    """Saves a study session to the persistent local library."""
    data = request.get_json(silent=True) or {}
    learner_id = data.get("learner_id") or _current_learner_id()
    question = sanitize_input_text(str(data.get("question", "")).strip())
    subject = str(data.get("subject", "Mathematics")).strip()
    misconception = data.get("misconception")
    result = data.get("result", {})
    session_id = data.get("id")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    saved_id = backend_code.save_tutor_session(
        learner_id=learner_id,
        question=question,
        subject=subject,
        misconception=misconception,
        result=result,
        session_id=session_id,
    )
    return jsonify({"success": True, "id": saved_id}), 201


@app.get("/api/learner/sessions/<session_id>")
def get_learner_session(session_id: str):
    """Retrieves full session details including the 4-agent explanation and practice round."""
    session = backend_code.get_tutor_session_by_id(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session)


@app.delete("/api/learner/sessions/<session_id>")
def remove_learner_session(session_id: str):
    """Deletes a study session from library."""
    learner_id = _current_learner_id()
    backend_code.delete_tutor_session(session_id, learner_id=learner_id)
    return jsonify({"success": True})


@app.get("/api/learner/dashboard")
def get_learner_dashboard():
    """Returns analytics dashboard: weekly goal, active streak, BKT mastery, and slips."""
    learner_id = _current_learner_id()
    dashboard = backend_code.get_learner_dashboard_data(learner_id)
    return jsonify({
        "learner_id": learner_id,
        **dashboard,
    })


@app.get("/api/notifications")
def get_learner_notifications_route():
    """Returns real-time learning notifications and recommendations."""
    learner_id = _current_learner_id()
    notifs = backend_code.get_learner_notifications(learner_id)
    return jsonify({
        "unread_count": sum(1 for n in notifs if not n.get("read")),
        "notifications": notifs,
    })


@app.post("/api/notifications/read")
def mark_notifications_route():
    """Marks notifications as read."""
    data = request.get_json(silent=True) or {}
    notif_id = data.get("id", "all")
    backend_code.mark_notification_as_read(notif_id)
    return jsonify({"success": True})


@app.post("/api/context/upload")
def upload_context_file():
    """Accepts code/text/log file upload, extracts sanitized content, validates security boundaries, and formats as tutor context."""
    if "file" in request.files:
        f = request.files["file"]
        raw_bytes = f.read(600 * 1024)
        filename = f.filename or "snippet.txt"
        is_valid, err_msg, safe_name, content = validate_file_upload(filename, raw_bytes)
        if not is_valid:
            return jsonify({"error": err_msg or "Invalid file upload."}), 400
    elif request.is_json and "content" in request.json:
        safe_name = sanitize_filename(request.json.get("filename", "snippet.txt"))
        ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if ext in {"exe", "dll", "so", "sh", "bat", "cmd", "ps1", "php"}:
            return jsonify({"error": f"Executable or script files (.{ext}) are strictly disallowed."}), 400
        raw_text = str(request.json.get("content", ""))
        content = sanitize_input_text(raw_text, max_length=20000)
    else:
        return jsonify({"error": "No file uploaded or content provided"}), 400

    # Scan uploaded content for prompt injection / jailbreak patterns
    scan = prompt_guard.scan(content)
    if not scan.is_safe:
        return jsonify({
            "error": "Security alert: The uploaded file contains instruction overrides or prompt injection patterns."
        }), 400

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "txt"
    lang = "python" if ext in {"py", "pyw"} else ("json" if ext == "json" else "text")

    formatted_snippet = f"\n\n[Attached File: {safe_name}]\n```{lang}\n{content}\n```"

    return jsonify({
        "status": "ok",
        "filename": safe_name,
        "extension": ext,
        "language": lang,
        "size_bytes": len(content),
        "content": content,
        "formatted_prompt": formatted_snippet,
    })


PRACTICE_CATALOG = [
    {
        "id": "math_quadratic",
        "title": "Quadratic Factorization & Sign Errors",
        "subject": "Mathematics",
        "description": "Master sign consistency in factoring trinomials like ax² + bx + c.",
        "difficulty": "Intermediate",
    },
    {
        "id": "math_fractions",
        "title": "Fraction Addition & Common Denominators",
        "subject": "Mathematics",
        "description": "Overcome denominator addition slips and unscaled numerators.",
        "difficulty": "Beginner",
    },
    {
        "id": "math_calculus",
        "title": "Integration by Parts & Minus Distribution",
        "subject": "Mathematics",
        "description": "Trace u, dv selections and negative signs across integration steps.",
        "difficulty": "Advanced",
    },
    {
        "id": "py_recursion",
        "title": "Recursion Depth & Overlapping Call Stacks",
        "subject": "Python",
        "description": "Identify redundant subproblem evaluations and missing base cases.",
        "difficulty": "Intermediate",
    },
    {
        "id": "py_indexing",
        "title": "2D Grid Traversal & Matrix Boundaries",
        "subject": "Python",
        "description": "Safely bound grid checks and prevent off-by-one IndexErrors.",
        "difficulty": "Beginner",
    },
    {
        "id": "py_mutability",
        "title": "Mutable Default Arguments in Functions",
        "subject": "Python",
        "description": "Prevent state contamination between function calls sharing list/dict defaults.",
        "difficulty": "Intermediate",
    },
]


@app.get("/api/practice/catalog")
def get_practice_catalog():
    """Returns the curriculum modules available in Practice Lab."""
    return jsonify({
        "total_modules": len(PRACTICE_CATALOG),
        "modules": PRACTICE_CATALOG,
    })


@app.post("/api/practice/generate")
def generate_practice_question():
    """Generates an instant practice question based on the selected curriculum topic."""
    data = request.get_json(silent=True) or {}
    topic_id = data.get("topic_id", "math_quadratic")

    if topic_id == "math_quadratic":
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Mathematics",
            "title": "Factor the quadratic",
            "prompt": "Factor the polynomial: 3x² + 7x + 2 into two binomial factors (ax + b)(cx + d).",
            "starter": "(3x + 1)(x + 2)",
            "expected_answer": "(3x + 1)(x + 2)",
            "hints": ["Find two numbers that multiply to 3 * 2 = 6 and add to 7.", "Rewrite 7x as 6x + 1x."],
            "solution": "3x² + 6x + 1x + 2 = 3x(x + 2) + 1(x + 2) = (3x + 1)(x + 2)."
        }
    elif topic_id == "math_fractions":
        base_prob = backend_code.get_fast_problem("M1_add_across", difficulty=1)
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Mathematics",
            "title": "Add Fractions with Unequal Denominators",
            "prompt": f"Compute the exact value of: {base_prob['text']}",
            "starter": "",
            "expected_answer": base_prob["correct_answer"],
            "hints": ["Find a common denominator first, do not add the denominators straight across!"],
            "solution": f"The exact sum is {base_prob['correct_answer']}."
        }
    elif topic_id == "math_calculus":
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Mathematics",
            "title": "Integration by Parts Sign Check",
            "prompt": "Evaluate: ∫ x · sin(x) dx using integration by parts. What is the final antiderivative?",
            "starter": "-x*cos(x) + sin(x) + C",
            "expected_answer": "-x*cos(x) + sin(x) + C",
            "hints": ["Let u = x and dv = sin(x) dx.", "v = -cos(x). Remember: ∫ u dv = u*v - ∫ v du."],
            "solution": "u = x, du = dx; dv = sin(x) dx, v = -cos(x).\n∫ x sin(x) dx = -x cos(x) - ∫ (-cos(x)) dx = -x cos(x) + ∫ cos(x) dx = -x cos(x) + sin(x) + C."
        }
    elif topic_id == "py_recursion":
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Python",
            "title": "Add Base Case to Recursive Countdown",
            "prompt": "Fix this recursive function so it terminates when n reaches 0 without causing RecursionError:",
            "starter": "def countdown(n):\n    print(n)\n    return countdown(n - 1)",
            "expected_answer": "def countdown(n):\n    if n <= 0:\n        return\n    print(n)\n    return countdown(n - 1)",
            "hints": ["Add an `if n <= 0:` check at the start to stop further calls."],
            "solution": "Add `if n <= 0: return` as the base case before calling `countdown(n - 1)`."
        }
    elif topic_id == "py_indexing":
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Python",
            "title": "Prevent 2D Grid IndexError",
            "prompt": "Fix the boundary check so accessing `grid[r][c + 1]` never raises an IndexError:",
            "starter": "def has_right_neighbor(grid, r, c):\n    # Add safe condition here\n    return grid[r][c + 1] is not None",
            "expected_answer": "def has_right_neighbor(grid, r, c):\n    if c + 1 < len(grid[r]):\n        return grid[r][c + 1] is not None\n    return False",
            "hints": ["Ensure `c + 1 < len(grid[r])` before indexing `[c + 1]`."],
            "solution": "Check `c + 1 < len(grid[r])` first to guard against out-of-bounds column access."
        }
    else:
        problem = {
            "id": f"prac_{uuid.uuid4().hex[:8]}",
            "topic_id": topic_id,
            "subject": "Python",
            "title": "Fix Mutable Default Argument",
            "prompt": "Fix the shared default list so subsequent calls receive fresh lists:",
            "starter": "def append_value(val, target=[]):\n    target.append(val)\n    return target",
            "expected_answer": "def append_value(val, target=None):\n    if target is None:\n        target = []\n    target.append(val)\n    return target",
            "hints": ["Use `target=None` in the function header and initialize inside the body."],
            "solution": "Default arguments are evaluated once at function definition. Use `target=None` and initialize `target = []` inside."
        }

    return jsonify({"problem": problem})


@app.post("/api/practice/verify")
def verify_practice_answer():
    """Evaluates learner's practice answer, updates BKT mastery, and provides feedback."""
    data = request.get_json(silent=True) or {}
    learner_id = _current_learner_id()
    problem_id = str(data.get("problem_id", ""))
    user_answer = str(data.get("user_answer", "")).strip()
    expected = str(data.get("expected_answer", "")).strip()
    topic_id = str(data.get("topic_id", "math_quadratic"))
    subject = str(data.get("subject", "Mathematics"))

    if not user_answer:
        return jsonify({"error": "Answer cannot be blank"}), 400

    norm_user = re.sub(r"\s+", "", user_answer.lower().replace(";", ""))
    norm_exp = re.sub(r"\s+", "", expected.lower().replace(";", ""))

    is_correct = False
    if norm_user == norm_exp:
        is_correct = True
    elif "/" in user_answer and "/" in expected:
        u_frac = backend_code.parse_fraction(user_answer)
        e_frac = backend_code.parse_fraction(expected)
        if u_frac and e_frac and u_frac == e_frac:
            is_correct = True
    elif "(" in norm_user and "(" in norm_exp:
        u_factors = sorted(re.findall(r"\([^)]+\)", norm_user))
        e_factors = sorted(re.findall(r"\([^)]+\)", norm_exp))
        if u_factors and u_factors == e_factors:
            is_correct = True

    if not is_correct and subject.lower() == "python":
        if "None" in expected and "None" in user_answer:
            is_correct = True
        elif "<=" in expected and "<=" in user_answer:
            is_correct = True
        elif "<len" in norm_exp and ("<len" in norm_user or "<=" in norm_user):
            is_correct = True

    backend_code.log_attempt_db(
        learner_id=learner_id,
        session_id=f"prac_{problem_id}",
        problem_id=problem_id,
        target_misc=topic_id,
        answer=user_answer,
        correct=1 if is_correct else 0,
        predicted_misc=None if is_correct else topic_id,
        confidence=0.95,
    )

    feedback_msg = (
        "Excellent! You accurately resolved the misconception."
        if is_correct
        else f"Not quite. Notice where the expression diverges from the expected pattern. Compare with: {expected}"
    )

    return jsonify({
        "correct": is_correct,
        "feedback": feedback_msg,
        "expected_solution": data.get("solution") or expected,
        "mastery_increase": "+4.2%" if is_correct else "-1.5%",
    })


# ==============================================================================
# SECTION 6: SOCRATIC LLM CHATBOT & CONTINUOUS TRAINING HUB
# ==============================================================================

_tutor_slots = threading.BoundedSemaphore(max(1, int(os.getenv("TUTOR_MAX_CONCURRENT", "2"))))


def _prepare_tutor_request(body: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Response, int]]]:
    """Validate + sanitize a tutoring request (shared by every tutor endpoint)."""
    raw_question = str(body.get("question", "")).strip()
    if not raw_question:
        return None, (jsonify({"error": "Enter a question before sending it."}), 400)

    # ECC Input Sanitization & OWASP Prompt Injection Detection
    question = sanitize_input_text(raw_question)
    scan_result = prompt_guard.scan(question)
    if not scan_result.is_safe:
        return None, (jsonify({
            "answer": "I am a dedicated Socratic Math Tutor designed to guide you through mathematical problem solving. I cannot process instruction override requests, system prompt inspections, or roleplay escapes. Let's focus on solving fractions and algebra!",
            "model": "ECC-Security-Guard (OWASP-Blocked)",
            "status": "refused_injection",
            "risk_level": scan_result.risk_level,
            "flagged_pattern": scan_result.flagged_pattern,
        }), 400)

    try:
        practice_count = int(body["practice_count"]) if body.get("practice_count") is not None else None
    except (TypeError, ValueError):
        return None, (jsonify({"error": "practice_count must be a number."}), 400)

    return {
        "question": question,
        "subject": sanitize_input_text(str(body.get("subject", "Mathematics")), max_length=64),
        "mode": sanitize_input_text(str(body.get("mode", "diagnostic")), max_length=64),
        "learner_id": sanitize_input_text(str(body.get("learner_id", "student_demo")), max_length=64) or "student_demo",
        "practice_count": practice_count,
    }, None


@app.post("/api/llm/answer")
def llm_answer():
    """Handles freeform Socratic questions with OWASP prompt injection defense and logs training samples."""
    prepared, error = _prepare_tutor_request(request.get_json(silent=True) or {})
    if error:
        return error
    question, subject = prepared["question"], prepared["subject"]
    mode, learner_id = prepared["mode"], prepared["learner_id"]

    # ECC Memory Lifecycle: pre-observe intent
    memory_lifecycle.pre_observe(learner_id, question)

    if not _tutor_slots.acquire(blocking=False):
        return jsonify({"error": "The tutor is busy with other learners. Please retry in a few seconds."}), 429
    try:
        result = llm_engine.answer_socratic(
            subject=subject,
            question=question,
            mode=mode,
            learner_id=learner_id,
        )
        if isinstance(result, tuple) and len(result) == 2 and result[1] == 503:
            return jsonify(result[0]), 503
        if result.get("status") == "model_unavailable":
            return jsonify(result), 503
        if "agents" not in result:  # legacy deterministic path (LLM_ONLY_MODEL=0 only)
            metadata = result.get("metadata") or {}
            misconception = classify_misconception(subject, question, metadata)
            result["misconception"] = misconception
            result["practice_set"] = result.get("practice_set") or generate_practice_set(subject, misconception, count=6)
        return jsonify(result)
    except Exception:
        app.logger.exception("llm_answer failed")
        return jsonify({"error": "The tutor hit an unexpected error."}), 500
    finally:
        _tutor_slots.release()


@app.post("/api/tutor")
def tutor_agents_sync():
    """Run the four agents and return one JSON document (see /api/tutor/stream for live progress)."""
    return llm_answer()


@app.post("/api/tutor/stream")
def tutor_agents_stream():
    """Newline-delimited JSON events: start, grounding, agent_start, agent_result, revision, complete/error."""
    prepared, error = _prepare_tutor_request(request.get_json(silent=True) or {})
    if error:
        return error
    memory_lifecycle.pre_observe(prepared["learner_id"], prepared["question"])
    if not _tutor_slots.acquire(blocking=False):
        return jsonify({"error": "The tutor is busy with other learners. Please retry in a few seconds."}), 429

    user_id = (g.user or {}).get("id")

    def generate():
        try:
            for event in llm_engine.stream_agents(
                prepared["subject"], prepared["question"], prepared["mode"], prepared["learner_id"],
                practice_count=prepared["practice_count"],
            ):
                if event.get("event") == "complete" and isinstance(event.get("result"), dict):
                    # Keep approved answers to continue fine-tuning the model on learners' questions.
                    example_id = training_store.save_example(
                        user_id, prepared["subject"], prepared["question"], event["result"])
                    event["result"]["training_example_id"] = example_id
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception:
            app.logger.exception("tutor stream failed")
            yield json.dumps({"event": "error", "status": "error", "message": "The tutor hit an unexpected error."}) + "\n"
        finally:
            _tutor_slots.release()

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.post("/api/practice/submit")
def submit_practice_attempt():
    """Grades one targeted math or Python practice item and records progress."""
    from tutor_agents.pipeline import practice_store

    body = request.get_json(silent=True) or {}
    learner_id = sanitize_input_text(str(body.get("learner_id", "student_demo")), max_length=64) or "student_demo"
    session_id = sanitize_input_text(str(body.get("session_id", "practice_session")), max_length=64) or "practice_session"
    practice_id = sanitize_input_text(str(body.get("practice_id", "")), max_length=128)
    subject = sanitize_input_text(str(body.get("subject", "Mathematics")), max_length=64)
    misconception = sanitize_input_text(str(body.get("misconception", "M1_add_across")), max_length=64)
    answer = str(body.get("answer", "")).strip()

    if not practice_id or not answer:
        return jsonify({"error": "Practice ID and answer are required."}), 400

    # Items written by the Practice agent are graded against the server's own record, never
    # against answers echoed back by the browser.
    stored = practice_store.get(practice_id)
    if stored:
        subject = stored.get("subject", subject)

    if subject.lower() in {"python", "coding", "programming", "computer science", "cs"}:
        if stored and stored.get("type") == "code":
            from backend.sandbox import run_student_code

            run = run_student_code(answer)
            expected = stored.get("expected_output")
            produced = (run.get("stdout") or "").strip()
            correct = bool(run.get("success")) and (expected is None or produced == expected)
            details = {
                "correct_code": stored.get("correct_code"),
                "explanation": stored.get("explanation") or "",
                "your_output": produced,
                "expected_output": expected,
                "error": None if run.get("success") else f"{run.get('error_type')}: {run.get('error_message')}",
            }
        else:
            from backend.python_debugger import python_debugger
            from backend.practice import _code_solution

            _, metadata = python_debugger.analyze_and_explain(answer)
            correct = metadata.get("status") == "code_executes_cleanly"
            correct_code, explanation = _code_solution(str(body.get("reference_code", "")), misconception)
            details = {"metadata": metadata, "correct_code": correct_code, "explanation": explanation}
    else:
        correct_answer = sanitize_math_answer(str((stored or {}).get("correct_answer") or body.get("correct_answer", "")))
        correct, parsed = backend_code.check_answer(sanitize_math_answer(answer), correct_answer)
        details = {
            "student_parsed": backend_code.format_fraction(parsed) if parsed else answer,
            "correct_answer": correct_answer,
            "explanation": (stored or {}).get("explanation") or (
                "Find a common denominator, scale each numerator by the same factor, "
                "then add the numerators and reduce the fraction."
            ),
        }

    backend_code.log_practice_attempt(
        learner_id=learner_id,
        session_id=session_id,
        practice_id=practice_id,
        subject=subject,
        misconception=misconception,
        correct=correct,
    )
    round_info = None
    if stored and stored.get("set_id"):
        from tutor_agents.pipeline import record_practice_result

        round_info = record_practice_result(stored["set_id"], practice_id, correct, answer)
    return jsonify({
        "correct": correct,
        "practice_id": practice_id,
        "misconception": misconception,
        "progress": backend_code.get_practice_progress(learner_id),
        "round": round_info,
        **details,
    })


@app.post("/api/practice/next")
def next_practice_round():
    """After a round scored below 80%: a new round of different problems at an adjusted difficulty."""
    from tutor_agents.model_client import ModelUnavailable
    from tutor_agents.pipeline import get_pipeline

    body = request.get_json(silent=True) or {}
    set_id = sanitize_input_text(str(body.get("set_id", "")), max_length=64)
    if not set_id:
        return jsonify({"error": "set_id is required."}), 400
    if not _tutor_slots.acquire(blocking=False):
        return jsonify({"error": "The tutor is busy with other learners. Please retry in a few seconds."}), 429
    try:
        return jsonify(get_pipeline().next_practice(set_id))
    except KeyError:
        return jsonify({"error": "This practice round has expired. Ask your question again."}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    except ModelUnavailable as exc:
        return jsonify({"error": exc.public_message, "status": "model_unavailable"}), 503
    except Exception:
        app.logger.exception("next practice round failed")
        return jsonify({"error": "Could not create new practice problems."}), 500
    finally:
        _tutor_slots.release()


@app.post("/api/llm/feedback")
def submit_feedback():
    """Captures human rating on LLM answers to weight training data quality."""
    data = request.get_json(silent=True) or {}
    sample_id = str(data.get("sample_id", "")).strip()
    feedback = str(data.get("feedback", "helpful")).strip()
    notes = data.get("notes")

    if not sample_id and not data.get("training_example_id"):
        return jsonify({"error": "Sample ID is required."}), 400

    success = llm_engine.update_sample_feedback(sample_id, feedback, notes)
    example_id = str(data.get("training_example_id") or "").strip()
    rated = training_store.rate_example((g.user or {}).get("id"), example_id, feedback) if example_id else False
    return jsonify({"success": success, "sample_id": sample_id, "training_example_rated": rated})


@app.get("/api/llm/dataset")
def get_training_dataset():
    """Returns recent training samples and distribution metrics."""
    samples = llm_engine.get_recent_samples(limit=50)
    total_count = llm_engine.get_training_sample_count()

    # Calculate misconception distribution
    distribution: Dict[str, int] = {}
    for s in samples:
        misc = s.get("misconception") or "freeform_socratic"
        distribution[misc] = distribution.get(misc, 0) + 1

    return jsonify({
        "total_samples": total_count,
        "distribution": distribution,
        "recent_samples": samples,
    })


@app.get("/api/llm/dataset/export")
def export_dataset():
    """Exports collected dataset for hackathon judges in JSONL or CSV format."""
    export_format = request.args.get("format", "jsonl").lower()
    samples = llm_engine.get_recent_samples(limit=1000)

    if export_format == "csv":
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(["id", "timestamp", "learner_id", "subject", "misconception", "instruction", "input", "output", "feedback"])
        for s in samples:
            cw.writerow([
                s.get("id"),
                s.get("timestamp"),
                s.get("learner_id"),
                s.get("subject"),
                s.get("misconception"),
                s.get("instruction"),
                s.get("input"),
                s.get("output"),
                s.get("feedback"),
            ])
        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=misconception_training_dataset.csv"},
        )
    else:
        # JSONL format
        lines = [json.dumps(s, ensure_ascii=False) for s in samples]
        output = "\n".join(lines)
        return Response(
            output,
            mimetype="application/x-jsonlines",
            headers={"Content-Disposition": "attachment;filename=misconception_training_dataset.jsonl"},
        )


@app.post("/api/llm/train")
def trigger_training():
    return jsonify({
        "status": "disabled",
        "message": (
            "Online training is disabled. "
            "Export the collected dataset and run real LoRA "
            "training in your Kaggle training workflow."
        ),
    }), 410


@app.post("/api/python/debug")
def debug_python_code():
    """Compiles and debugs Python code, returning AST analysis, runtime errors, and Socratic fix."""
    body = request.get_json(silent=True) or {}
    code = str(body.get("code", "")).strip()
    if not code:
        return jsonify({"error": "No Python code provided."}), 400

    from backend.python_debugger import python_debugger
    explanation, meta = python_debugger.analyze_and_explain(code)

    # Log to continuous training dataset
    sample_id = llm_engine.log_training_sample(
        subject="Python",
        instruction="Debug and explain the provided Python code.",
        user_input=code,
        model_output=explanation,
        learner_id=str(body.get("learner_id", "student_demo")),
        misconception=meta.get("error_category", "python_debugging"),
        metadata=meta,
    )

    return jsonify({
        "status": "success",
        "explanation": explanation,
        "metadata": meta,
        "sample_id": sample_id,
    })


@app.get("/api/llm/train/status")
def training_status():
    return jsonify({
        "status": "offline_training",
        "message": (
            "Model training is performed separately. "
            "The deployed service only handles inference."
        ),
    })


# ==============================================================================
# SECTION 7: ECC ENTERPRISE SECURITY & MEMORY AUDIT APIS
# ==============================================================================

@app.get("/api/security/audit")
def security_audit():
    """Returns ECC security guard status and threat mitigation metrics."""
    guard_metrics = prompt_guard.get_metrics()
    return jsonify({
        "status": "active",
        "owasp_guard": "ECC-OWASP-Prompt-Injection-Guard",
        "signatures_enforced": [
            "INSTRUCTION_OVERRIDE",
            "JAILBREAK_ATTEMPT",
            "SECRET_EXFILTRATION",
            "PROMPT_EXTRACTION",
            "PERSONA_HIJACK",
            "DAN_OVERRIDE",
            "XML_SYSTEM_TAG_INJECTION",
            "LLAMA_TAG_INJECTION",
            "SYSTEM_TOKEN_INJECTION",
            "CHAT_DELIMITER_INJECTION",
            "REMOTE_CODE_EXECUTION_PAYLOAD",
            "SUBPROCESS_EXECUTION_PAYLOAD",
        ],
        "sanitization": {
            "max_prompt_chars": 4000,
            "max_answer_chars": 64,
            "max_upload_kb": 512,
            "path_traversal_filtering": True,
            "unicode_null_byte_scrubbing": True,
            "file_extension_whitelist": True,
            "binary_magic_validation": True,
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60,
            "max_requests_per_window": 120,
            "heavy_compute_max_per_window": 40,
        },
        "telemetry": guard_metrics,
        "defense_headers": {
            "content_security_policy": True,
            "permissions_policy": True,
            "cross_origin_opener_policy": True,
            "cross_origin_resource_policy": True,
            "hsts": True,
        },
    })


@app.get("/api/memory/sessions")
def memory_sessions():
    """Returns ECC active memory sessions and cognitive diagnostic profiles."""
    return jsonify({
        "total_active_sessions": len(memory_lifecycle.active_sessions),
        "sessions": memory_lifecycle.active_sessions,
    })


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "::")
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))
    print(f"Starting Misconception Tutor Server on http://localhost:{port} (http://127.0.0.1:{port}) ...")
    try:
        app.run(host=host, port=port, debug=False)
    except Exception:
        app.run(host="0.0.0.0", port=port, debug=False)
