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
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, g, jsonify, request, send_from_directory, stream_with_context

from backend import auth, backend_code
from backend.llm_engine import llm_engine
from backend.security.guard import prompt_guard
from backend.security.sanitizer import sanitize_input_text, sanitize_math_answer
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

    return jsonify({
        "status": "online",
        "liveAiEnabled": bool(llm_stat["loaded"]),
        "model": llm_stat["model"],
        "llmLoaded": llm_stat["loaded"],
        "llmError": llm_stat["error"],
        "mode": llm_stat.get("mode"),
        "remoteBackend": llm_stat.get("remoteBackend"),
        "agents": llm_stat.get("agents"),
        "modelOnly": llm_stat.get("modelOnly"),
        "trainingMode": "offline_kaggle",
        "trainingSamplesCollected": (
            llm_stat["trainingSamplesCollected"]
        ),
    })


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

    def generate():
        try:
            for event in llm_engine.stream_agents(
                prepared["subject"], prepared["question"], prepared["mode"], prepared["learner_id"],
                practice_count=prepared["practice_count"],
            ):
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

    if not sample_id:
        return jsonify({"error": "Sample ID is required."}), 400

    success = llm_engine.update_sample_feedback(sample_id, feedback, notes)
    return jsonify({"success": success, "sample_id": sample_id})


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
        ],
        "sanitization": {
            "max_prompt_chars": 4000,
            "max_answer_chars": 64,
            "path_traversal_filtering": True,
            "unicode_null_byte_scrubbing": True,
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60,
            "max_requests_per_window": 120,
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
