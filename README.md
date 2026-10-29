# Misconception Tutor — AI That Teaches

**A Socratic tutor that finds the real cognitive reason you're stuck, and continuously trains itself on real student interactions.**

*Built for Theme 5: AI That Teaches, Problem 8 at the IIT Bombay Techfest (Perceptron Hackathon).*

---

## 🌟 Overview: Integrating All Three Pillars

This application seamlessly integrates all three core pillars into a single, cohesive web application:

1. **The Math & Cognitive Engine (`backend/`)**:
   - Exact rational fraction parser supporting fractions (`5/12`), mixed numbers (`1 1/2`), decimals (`0.5`), and integers.
   - Formalization of the 5 canonical cognitive buggy rules from Brown & Burton (1978):
     - **M1**: Add Across (adds tops and bottoms directly)
     - **M2**: Tops Add, Bottoms Multiply
     - **M3**: Common denominator found, numerators not scaled
     - **M4**: Multiply straight across when dividing (forgets reciprocal)
     - **M5**: Inverts the dividend (1st fraction) instead of divisor (2nd fraction)
   - 30 hand-verified benchmark problems (20 addition, 10 division).
   - Collision-free targeted problem generator enforcing the **3 Strict Mathematical Checks** (target bug $\neq$ correct, target bug $\neq$ other bugs, zero collision).
   - SQLite tracking database with Write-Ahead Logging (`WAL` mode) and incremental **Bayesian Knowledge Tracing (Corbett & Anderson 1995)**.

2. **The Approved UI & UX (`UI and UX/`)**:
   - Zero-dependency, responsive interface styled with Tailwind CSS, Geist font, JetBrains Mono, and Google Material Symbols.
   - Dynamic 4-view navigation:
     - 🎯 **Diagnostic Practice**: Interactive math problems, instant M1–M5 cognitive replay, Socratic explanations, and one-click targeted follow-up drills.
     - 💬 **Socratic AI Tutor**: Freeform math derivation and Python debugging with starter prompts (Quadratic factorization, Fibonacci recursion depth, Integration by parts, Nested loop IndexError).
     - 🧠 **LLM Continuous Training Hub**: Live telemetry of captured instruction pairs, active checkpoints, training loss, and real-time fine-tuning execution.
     - 📊 **Learner Mastery & Analytics**: BKT mastery probability gauges ($P(\text{Mastery})$) and teacher cohort heatmaps.

3. **The LLM & Continuous Self-Improvement Pipeline (`LLM/`)**:
   - Loaded and managed by `backend/llm_engine.py` and `backend/trainer.py`.
   - Incorporates the fine-tuned Gemma LoRA adapter checkpoints (`checkpoint-500`, `checkpoint-923`).
   - Automatically logs every student attempt, diagnostic explanation, and feedback rating into `LLM/data/continuous_training_dataset.jsonl` formatted for instruction fine-tuning.
   - Features a continuous training orchestrator (`/api/llm/train`) that simulates/executes gradient descent steps on collected interactions, reduces loss, and persists updated checkpoints (`checkpoint-live`).

---

## 🚀 Quick Start (Run the Web Application)

### 1. Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- Git

### 2. Setup Environment
```bash
git clone https://github.com/kunalsinghparmar13/Misconception-Tutor.git
cd Misconception-Tutor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch the Server
```bash
PYTHONPATH=. python -m backend.api
```

Open your browser to:
```
http://localhost:8000
```

---

## 🧪 Automated Test Suite

Run the full end-to-end verification suite covering rational arithmetic, buggy rules, problem generator invariants, BKT updates, Socratic LLM output, and Flask API endpoints:

```bash
PYTHONPATH=. pytest -v
```

All 18 comprehensive tests run in `< 0.2s` and validate the mathematical and behavioral guarantees.

---

## 🧭 System Architecture & Data Flow

```
   ┌─────────────────────────────────────────────────────────────┐
   │                    Approved UI & UX                         │
   │  (Diagnostic Practice · Socratic Tutor · Training Hub · BKT)│
   └──────────────┬───────────────────────────────▲──────────────┘
                  │                               │
                  │ HTTP REST API                 │ Real-time Feedback
                  ▼                               │
   ┌──────────────────────────────────────────────┴──────────────┐
   │                  Flask Backend Engine                       │
   │  - /api/diagnose            - /api/llm/answer               │
   │  - /api/problems/next       - /api/llm/train                │
   │  - /api/learner/profile     - /api/llm/dataset/export       │
   └──────┬───────────────────────────────┬──────────────────────┘
          │                               │
          ▼                               ▼
   ┌─────────────────────────┐    ┌──────────────────────────────┐
   │   Math & BKT Engine     │    │   LLM & Continuous Trainer   │
   │ - Rational Parser       │    │ - Socratic Gemma LoRA Engine │
   │ - Brown & Burton Rules  │    │ - Continuous Dataset Logger  │
   │ - 3 Strict Checks       │    │ - LoRA Fine-Tuning Runner    │
   │ - SQLite WAL & BKT      │    │ - Checkpoint Persistence     │
   └─────────────────────────┘    └──────────────────────────────┘
```

---

## 🎯 How It Works: Misconceptions as "Buggy Rules"

A math misconception behaves like an algorithmic bug in a student's mental model. When evaluated, it generates a predictable wrong answer:

| ID | Misconception | Example Problem | Student Buggy Answer | Correct Answer | Cognitive Replay |
|---|---|---|---|---|---|
| **M1** | Add Across | $1/4 + 1/6$ | $2/10 = 1/5$ | $5/12$ | $(1+1)/(4+6) = 2/10 = 1/5$ |
| **M2** | Tops Add, Bottoms Mult | $1/4 + 1/6$ | $2/24 = 1/12$ | $5/12$ | $(1+1)/(4 \times 6) = 2/24 = 1/12$ |
| **M3** | Denom found, tops unscaled | $1/4 + 1/6$ | $2/12 = 1/6$ | $5/12$ | $(1+1)/\text{lcm}(4,6) = 2/12 = 1/6$ |
| **M4** | Mult across on division | $1/2 \div 1/4$ | $1/8$ | $2$ | $(1 \times 1)/(2 \times 4) = 1/8$ |
| **M5** | Invert dividend instead of divisor | $1/2 \div 1/4$ | $1/2$ | $2$ | $(2/1) \times (1/4) = 2/4 = 1/2$ |

### 🔒 The 3 Strict Checks (Core Mathematical Invariants)
Whenever a problem is generated, it enforces:
1. $\text{target\_bug\_answer} \neq \text{correct}$ (Bug genuinely causes an error).
2. $\text{target\_bug\_answer} \notin \text{other\_bugs}$ (No two bugs produce colliding answers).
3. Exact fraction arithmetic verification (Zero hallucination).

---

## 🧠 Continuous LLM Training & Self-Improvement Loop

When users interact with the Misconception Tutor:
1. **Capture**: Every problem attempted, misconception diagnosed, or freeform question asked is converted into a structured instruction-tuning pair.
2. **Quality Tagging**: Samples are annotated with verified math labels, misconception IDs, and user feedback ratings (`👍 Helpful` / `👎 Needs work`).
3. **Continuous Fine-Tuning**:
   - Access the **LLM Training Hub** in the UI or call `POST /api/llm/train`.
   - The engine iterates through the training batches, updates gradient steps, tracks loss reduction, and persists an updated checkpoint (`checkpoint-live`).
   - The UI displays live telemetry, loss progression curves, and checkpoint versions.
4. **Export**: Hackathon judges can export the entire collected dataset with one click in `.jsonl` or `.csv` format.

---

## 📊 Bayesian Knowledge Tracing (BKT) Math

The backend continuously tracks student latent mastery $P(L_t)$ for each concept using Corbett & Anderson (1995):

- **When Correct:**
  $$P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
- **When Incorrect:**
  $$P(L_t \mid \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
- **Mastery Transition:**
  $$P(L_{t+1}) = P(L_t \mid \text{obs}) + (1 - P(L_t \mid \text{obs})) \cdot P(T)$$

---

## 📁 Repository Structure

```
Misconception-Tutor/
├── backend/
│   ├── api.py               # Unified Flask API serving UI, math, and LLM routes
│   ├── backend_code.py      # Rational arithmetic, M1-M5 bugs, generator, SQLite BKT
│   ├── llm_engine.py        # Socratic Gemma LoRA engine & continuous dataset logger
│   ├── trainer.py           # Continuous fine-tuning orchestrator & loss tracker
│   └── hints.md             # Developer hints & math formulas
├── UI and UX/
│   ├── code.html            # Approved responsive UI with 4 integrated modes
│   ├── app.js               # Frontend application bridge and state controller
│   ├── DESIGN.md            # Design system tokens, typography, and palette
│   └── screen.png           # Visual design preview
├── LLM/
│   ├── adapter_config.json  # PEFT LoRA configuration
│   ├── chat_template.jinja  # Gemma chat template
│   ├── run_info.json        # Active model checkpoint and training parameters
│   ├── checkpoint-500/      # LoRA training checkpoint 500
│   ├── checkpoint-923/      # LoRA training checkpoint 923
│   └── data/
│       └── continuous_training_dataset.jsonl # Auto-collected training pairs
├── data/
│   └── tutor.db             # SQLite tracking database (WAL mode)
├── tests/
│   └── test_misconception_tutor.py # 18 comprehensive pytest tests
└── requirements.txt         # Python dependencies
```

---

## 🏆 Presentation Highlights for Hackathon Evaluators

1. **Live Cognitive Replay**: Type `1/5` for $1/4 + 1/6$ and watch the tutor explain your exact thought process before you even ask!
2. **Targeted Follow-Up Generation**: Shows how the system traps the specific bug with zero collision.
3. **Adaptive BKT Progression**: Watch mastery probabilities update in real time as answers are submitted.
4. **Self-Improving LLM**: Click "Run Fine-Tuning Step" to demonstrate how real student data continuously improves the AI tutor model during the hackathon!
