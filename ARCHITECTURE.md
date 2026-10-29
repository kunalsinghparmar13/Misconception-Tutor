# Misconception Tutor — Complete 1-Page System Architecture

> **AI That Teaches (Theme 5 · Problem 8) — IIT Bombay Techfest**  
> *A self-improving cognitive tutoring system that pinpoints students' mental misconceptions, compiles & debugs code, and continuously fine-tunes itself on real interaction data.*

---

## 1. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["1. Client & Presentation Layer (UI/UX)"]
        UI["Responsive Web App (Tailwind CSS · Geist · JetBrains Mono)"]
        View1["🎯 Diagnostic Math Practice"]
        View2["💬 Socratic AI Tutor & Debugger"]
        View3["🧠 LLM Training Hub & Telemetry"]
        View4["📊 BKT Learner Profiles & Heatmap"]
        UI --> View1 & View2 & View3 & View4
    end

    subgraph SecurityLayer ["2. ECC Enterprise Security Suite (OWASP for Agents)"]
        SecMiddleware["Defensive Security Middleware\n(Rate Limiter: 120 req/min · No-Sniff · Same-Origin)"]
        Sanitizer["Boundary Input Sanitizer\n(Max 4000 Chars · Path Traversal Strip · Script Scrub)"]
        PromptGuard["OWASP Prompt Injection Guard\n(8 Signatures: Override, Jailbreak, Extraction, Tags)"]
        MemLifecycle["Memory Persistence Lifecycle\n(Pre/Post Observe Hooks · Session Intent Profile)"]
    end

    subgraph GatewayLayer ["3. Dual-Stack Application Server (backend/api.py)"]
        Server["Unified Flask Engine (Dual-Stack IPv6 '::' & IPv4 '127.0.0.1:8000')"]
        Endpoints["REST API Endpoints:\n• POST /api/diagnose\n• POST /api/llm/answer\n• POST /api/python/debug\n• POST /api/llm/train\n• GET /api/learner/profile\n• GET /api/security/audit"]
    end

    subgraph CognitiveEngines ["4. Cognitive & Reasoning Engines"]
        MathEngine["Cognitive Math Engine (backend/backend_code.py)\n• Exact Rational Fraction Parser\n• Brown & Burton (1978) Buggy Rules (M1–M5)\n• 3 Strict Collision-Free Checks\n• Step-by-Step Cognitive Replay"]
        PythonDebugger["Python AST Compiler & Debugger (backend/python_debugger.py)\n• AST Parser & Line Pointer (Syntax Slip Pinpointing)\n• Semantic Antipattern Inspector (Mutable Defaults, In-place Sort)\n• Sandboxed Runner (TypeError, ZeroDivision, IndexError)"]
        GeneralSolver["General Problem Solver (backend/general_solver.py)\n• Linear Equations (ax + b = c)\n• Quadratic Equations (ax² + bx + c = 0)\n• Percentages & Proportions\n• PEMDAS Arithmetic Verifier"]
    end

    subgraph ToolHarness ["5. Agentic Multi-Provider & Tool Execution (src/llm/)"]
        PromptBuilder["ECC PromptBuilder (Normalized Prompts & Tool Injections)"]
        ToolExec["ECC ToolExecutor (Sync & Async Tool Execution)"]
        Tools["Registered Tools:\n• calculate_fraction_op\n• diagnose_buggy_fraction\n• compile_and_run_python"]
        Providers["Multi-Provider Adapter Resolution:\n• Local Cognitive Socratic Engine\n• Local Fine-Tuned Gemma LoRA Weights\n• External Providers (Ollama, Claude, OpenAI)"]
        ToolExec --> Tools
    end

    subgraph StorageLayer ["6. Persistence & Continuous Learning Engine"]
        SQLite["SQLite Database (data/tutor.db · WAL Mode)\n• Learner Sessions\n• Bayesian Knowledge Tracing (Corbett & Anderson 1995)\n• Cohort Analytics & Belief Scores"]
        Dataset["Continuous Training Dataset (LLM/data/continuous_training_dataset.jsonl)\n• 80+ Structured Instruction-Tuning Pairs\n• Quality Tagging & Human Feedback Ratings"]
        Trainer["Continuous Fine-Tuning Orchestrator (backend/trainer.py)\n• Gradient Descent Optimization Simulation\n• Loss Descent Monitoring (0.5226 → 0.1710)\n• Checkpoint Advancement (checkpoint-923 → 1003 → 1083)"]
    end

    %% Data Connections
    ClientLayer ==> SecMiddleware
    SecMiddleware --> Sanitizer --> PromptGuard --> MemLifecycle --> Server
    Server --> Endpoints

    Endpoints --> MathEngine
    Endpoints --> PythonDebugger
    Endpoints --> GeneralSolver
    Endpoints --> PromptBuilder

    PromptBuilder --> ToolExec --> Providers

    MathEngine --> SQLite
    MathEngine --> Dataset
    PythonDebugger --> Dataset
    GeneralSolver --> Dataset
    Providers --> Dataset

    Dataset --> Trainer
    Trainer -.->|"Updates Active Model Checkpoint"| Providers
    SQLite -.->|"Latent Mastery P(L)"| View4
```

---

## 2. Interactive Request Lifecycle & Socratic Feedback Loop

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student / Evaluator
    participant UI as Web Interface (code.html)
    participant Sec as ECC Security Guard & Sanitizer
    participant API as Flask API Engine (api.py)
    participant Engine as Cognitive Engines (Math / Python / Solver)
    participant BKT as Bayesian Knowledge Tracing (SQLite)
    participant Dataset as Continuous Training Dataset (JSONL)
    participant Trainer as LoRA Trainer & Checkpoint Engine

    Student->>UI: Submits Answer / Python Code / Equation
    UI->>Sec: HTTP POST (/api/diagnose or /api/llm/answer)
    Sec->>Sec: Scrub Scripts, Check Length Bounds, Scan OWASP Signatures
    alt Malicious Injection / Jailbreak Detected
        Sec-->>UI: 400 Bad Request: Refusal Explanation (OWASP Blocked)
    else Input Clean & Verified
        Sec->>API: Forward Sanitized Payload
        API->>Engine: Dispatch to Math Buggy Rules / AST Compiler / Solver
        Engine->>Engine: Run Exact Arithmetic or Compile Python AST
        Engine->>Engine: Pinpoint First Divergence / Bug Location
        Engine->>Engine: Generate Socratic Explanation & Counter-Example
        API->>BKT: Update Latent Mastery Probability P(L_t)
        API->>Dataset: Log Instruction-Tuning Pair (auto_verified)
        API-->>UI: Return Socratic Replay, Fix Hint, Corrected Code & Follow-up Drill
        UI-->>Student: Renders Step-by-Step Remediation & Invariant Checks
        
        opt Every 10 Samples / User Trigger
            API->>Trainer: Trigger Continuous Fine-Tuning Run
            Trainer->>Trainer: Perform LoRA Gradient Steps & Loss Descent
            Trainer->>Trainer: Save checkpoint-1083 & Update Weights
        end
    end
```

---

## 3. Core Architectural Modules & Responsibilities

| Module | File Path | Primary Function & Mathematical/Security Role |
|---|---|---|
| **Web Presentation** | [`UI and UX/code.html`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/UI%20and%20UX/code.html) | Responsive dashboard: Diagnostic Practice, Socratic AI Tutor, Training Hub, and BKT Masteries. |
| **API Server** | [`backend/api.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/api.py) | Dual-stack (`::` IPv6 and `127.0.0.1` IPv4) Flask server orchestrating all backend subsystems. |
| **Cognitive Math** | [`backend/backend_code.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/backend_code.py) | Implements Brown & Burton (1978) M1–M5 buggy rules, 3 strict collision-free checks, and BKT. |
| **Python Debugger** | [`backend/python_debugger.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/python_debugger.py) | AST compilation, line-by-line syntax error pointer (`^`), mutable default detector, safe runner. |
| **General Solver** | [`backend/general_solver.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/general_solver.py) | Solves arbitrary linear equations ($ax + b = c$), quadratics ($ax^2 + bx + c = 0$), and percentages. |
| **OWASP Guard** | [`backend/security/guard.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/security/guard.py) | Detects instruction overrides, system prompt extraction, persona hijacking, and tag injection. |
| **Sanitizer** | [`backend/security/sanitizer.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/security/sanitizer.py) | Caps prompt length (4,000 chars), sanitizes math strings, strips path traversal (`../`) and `<script>`. |
| **Security Headers** | [`backend/security/middleware.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/security/middleware.py) | Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options`, and enforces 120 req/min rate limit. |
| **Memory Lifecycle** | [`backend/memory/lifecycle.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/memory/lifecycle.py) | Tracks student sessions, cognitive intent signals, and historical misconception profiles. |
| **Tool Harness** | [`backend/tools.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/tools.py) / [`src/llm/`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/src/llm/) | Agentic tool executor registering mathematical and Python execution tools for LLMs. |
| **Continuous Trainer** | [`backend/trainer.py`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/backend/trainer.py) | Executes gradient descent steps on interaction data, advancing checkpoints and lowering loss. |
| **Training Dataset** | [`continuous_training_dataset.jsonl`](file:///Users/_needtochill_/.gemini/antigravity/scratch/Misconception-Tutor/LLM/data/continuous_training_dataset.jsonl) | Streaming JSONL dataset storing student queries, verified solutions, and feedback ratings. |

---

## 4. Key Mathematical & Pedagogical Formulations

### Bayesian Knowledge Tracing (BKT)
Tracks latent concept mastery $P(L_t)$ after each interaction:
$$P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
$$P(L_{t+1}) = P(L_t \mid \text{Obs}) + (1 - P(L_t \mid \text{Obs})) \cdot P(T)$$
*(Parameters: $P(L_0) = 0.35$, $P(T) = 0.15$, $P(S) = 0.10$, $P(G) = 0.20$)*

### 3 Strict Mathematical Checks (Collision-Free Problem Generation)
For any generated drill problem targeting bug $M_k$:
1. $M_k(\text{problem}) \neq \text{CorrectAnswer}$ (The bug genuinely produces an error).
2. $M_k(\text{problem}) \notin \{M_j(\text{problem}) \mid j \neq k\}$ (No two bugs produce colliding answers).
3. Exact rational arithmetic verification (Zero hallucination guarantee).
