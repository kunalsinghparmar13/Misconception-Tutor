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
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from backend import backend_code
from backend.llm_engine import llm_engine
from backend.trainer import continuous_trainer
from backend.security.guard import prompt_guard
from backend.security.sanitizer import sanitize_input_text, sanitize_math_answer
from backend.security.middleware import register_security_middleware
from backend.memory.lifecycle import memory_lifecycle

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "UI and UX"
DATA_DIR = ROOT / "data"

app = Flask(__name__)

# Register ECC Enterprise Security Suite (Security Headers & Rate Limiting)
register_security_middleware(app)

# Initialize database tables on startup
backend_code.init_db()


# ==============================================================================
# SECTION 1: STATIC & ASSET ROUTES (Serving the approved UI/UX)
# ==============================================================================

@app.get("/")
def index():
    """Serves the approved responsive interface."""
    return send_from_directory(UI_DIR, "code.html")


@app.get("/app.js")
def app_script():
    """Serves the frontend application controller."""
    return send_from_directory(UI_DIR, "app.js")


@app.get("/screen.png")
def screen_image():
    """Serves the visual UI preview snapshot."""
    return send_from_directory(UI_DIR, "screen.png")


# ==============================================================================
# SECTION 2: HEALTH & SYSTEM READINESS API
# ==============================================================================

@app.get("/api/health")
def health():
    """Returns service health, database status, and LLM availability."""
    return jsonify({
        "status": "online",
        "database": "sqlite_wal_active",
        "llm": llm_engine.status(),
        "trainer": continuous_trainer.get_status(),
    })


@app.get("/api/backend-status")
def backend_status():
    """Returns runtime state for UI status badges."""
    llm_stat = llm_engine.status()
    trainer_stat = continuous_trainer.get_status()
    return jsonify({
        "status": "online",
        "liveAiEnabled": True,
        "model": llm_stat["model"],
        "activeCheckpoint": trainer_stat["activeCheckpoint"],
        "trainingSamplesCollected": llm_stat["trainingSamplesCollected"],
        "llmLoaded": llm_stat["loaded"],
        "llmError": llm_stat["error"],
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

@app.post("/api/llm/answer")
def llm_answer():
    """Handles freeform Socratic questions with OWASP prompt injection defense and logs training samples."""
    body = request.get_json(silent=True) or {}
    raw_question = str(body.get("question", "")).strip()
    if not raw_question:
        return jsonify({"error": "Enter a question before sending it."}), 400

    # ECC Input Sanitization & OWASP Prompt Injection Detection
    question = sanitize_input_text(raw_question)
    scan_result = prompt_guard.scan(question)
    if not scan_result.is_safe:
        return jsonify({
            "answer": "I am a dedicated Socratic Math Tutor designed to guide you through mathematical problem solving. I cannot process instruction override requests, system prompt inspections, or roleplay escapes. Let's focus on solving fractions and algebra!",
            "model": "ECC-Security-Guard (OWASP-Blocked)",
            "status": "refused_injection",
            "risk_level": scan_result.risk_level,
            "flagged_pattern": scan_result.flagged_pattern,
        }), 400

    subject = sanitize_input_text(str(body.get("subject", "Mathematics")), max_length=64)
    mode = sanitize_input_text(str(body.get("mode", "diagnostic")), max_length=64)
    learner_id = sanitize_input_text(str(body.get("learner_id", "student_demo")), max_length=64) or "student_demo"

    # ECC Memory Lifecycle: pre-observe intent
    memory_lifecycle.pre_observe(learner_id, question)

    try:
        result = llm_engine.answer_socratic(
            subject=subject,
            question=question,
            mode=mode,
            learner_id=learner_id,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


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
    """Triggers continuous fine-tuning run on the collected interaction dataset."""
    result = continuous_trainer.start_training_run()
    return jsonify(result)


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
    """Returns real-time fine-tuning progress, loss curves, and active checkpoint."""
    return jsonify(continuous_trainer.get_status())


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
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))
    print(f"Starting Misconception Tutor Server on http://{host}:{port} ...")
    app.run(host=host, port=port, debug=False)
