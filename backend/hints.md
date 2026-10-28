# AI That Teaches: Member B Backend Hints & Purpose Guide
**File:** `backend/backend_code.py`  
**Role:** Member B (Math Engine, Targeted Generator, Database Tracking & Learner Model)  
**Hackathon:** IIT Bombay Techfest (Theme 5 · Problem 8)

---

## 🧭 What Code is Used for What Purpose?

Every section in `backend/backend_code.py` serves a specific purpose in the tutoring loop:

| Section & Functions | Purpose in the AI Tutor | Technical Hint & Design Rationale |
| :--- | :--- | :--- |
| **Section 1: Exact Rational Arithmetic**<br>`parse_fraction(s)`<br>`format_fraction(f)`<br>`check_answer(...)` | Converts messy student inputs into exact mathematical fractions. | **Hint:** Students type inputs like `"1 1/2"`, `"0.5"`, or `"  5 / 12  "`. Pre-compiled regex and `@lru_cache(2048)` parse them in microseconds. `check_answer` checks mathematical equivalence so unreduced fractions (`10/24`) are accepted as correct! |
| **Section 2: Cognitive Buggy Rules**<br>`BUGS_ADD`<br>`BUGS_DIV`<br>`correct_add`<br>`correct_div` | Formally defines the 5 student misconceptions as mathematical rules. | **Hint:** Based on Brown & Burton's (1978) cognitive model (*BUGGY*). $M_1$ adds across, $M_2$ multiplies bottoms, $M_3$ skips numerator scaling, $M_4$ multiplies across without flipping, $M_5$ flips the wrong fraction. |
| **Section 3: 30 Base Problems**<br>`BASE_PROBLEMS`<br>`build_base_problems()` | Hand-verified benchmark problems with pre-calculated bug answers. | **Hint:** Meets the Week 1 deliverable of 20 addition and 10 division benchmark problems. |
| **Section 4: Explanations & Replays**<br>`EXPLANATIONS`<br>`generate_replay(misc_id, ...)` | Explains why the student is stuck and reconstructs their exact mental trace. | **Hint:** Generates the "Why we think this" dynamic replay (e.g., *"1+1=2 on top, 4+6=10 on bottom -> 2/10 -> 1/5. That is your answer!"*). |
| **Section 5: Targeted Problem Generator**<br>`make_add_problem(...)`<br>`make_div_problem(...)`<br>`generate_targeted_problem(...)`<br>`generate_candidate_batch(...)` | Generates a new problem specifically designed as a "trap" for the student's bug. | **Hint:** Enforces the **3 Strict Checks**: (1) Exact arithmetic, (2) `target_bug != correct`, (3) `target_bug != any other bug` (zero collision). |
| **Section 6: O(1) Problem Cache**<br>`build_problem_bank()`<br>`get_fast_problem(...)`<br>`generate_problem(...)` | Pre-indexes certified collision-free problems into memory. | **Hint:** Eliminates runtime rejection-sampling loops. Serves problems to the UI in **$O(1)$ instantaneous time**. |
| **Section 7: SQLite Tracking & BKT**<br>`get_connection()`<br>`init_db()`<br>`log_attempt(...)`<br>`_update_bkt_incremental(...)`<br>`get_learner_mastery(...)`<br>`compute_bug_rates(...)`<br>`get_teacher_heatmap_data(...)`<br>`export_attempts_to_csv(...)` | Gives the tutor long-term memory across sessions and models student mastery. | **Hint:** Enabled Write-Ahead Logging (`WAL` mode) and compound indexes (`idx_attempts_learner`, `idx_attempts_target`) for non-blocking multi-session access. Implements **Corbett & Anderson (1995) Bayesian Knowledge Tracing** to track latent concept mastery. |
| **Section 8: Simulation & Benchmarking**<br>`simulate_learning_cohort(...)` | Generates virtual cohorts of learners to validate the system before real trials. | **Hint:** Simulates learning curves where error rates decay as targeted problems are answered. |
| **Section 9: Standalone Verification**<br>`if __name__ == "__main__":` | Self-testing test suite. | **Hint:** Running `python backend/backend_code.py` tests arithmetic, problem invariants, SQLite logging, and BKT mastery progression in 1 second. |

---

## 🔒 The 3 Strict Checks (Core Math Generator Invariants)
Whenever a problem is generated, it mathematically validates:
1. $\text{target\_bug\_answer} \neq \text{correct}$ (Bug actually causes an error).
2. $\text{target\_bug\_answer} \notin \text{other\_bugs}$ (No two bugs produce the same answer).
3. Exact fraction arithmetic verification (Zero LLM math hallucination).

---

## 🧠 Bayesian Knowledge Tracing (BKT) Update Math
* **When Correct:**
  $$P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
* **When Incorrect:**
  $$P(L_t \mid \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
* **Learning Transition:**
  $$P(L_{t+1}) = P(L_t \mid \text{obs}) + (1 - P(L_t \mid \text{obs})) \cdot P(T)$$
