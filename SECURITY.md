# Security Policy — Misconception Tutor

## Enterprise Security Architecture (OWASP for LLM Applications)

This project integrates the enterprise-grade **ECC Agentic Security Suite** to ensure robust defense across all untrusted user interactions, cognitive diagnosis requests, and fine-tuning pipelines.

---

### 1. OWASP Top 10 for LLM Applications & Agents Compliance

| Vulnerability Category | Mitigation in Misconception Tutor | Implementation |
|---|---|---|
| **LLM01: Prompt Injection** | Multi-layer pattern matching and canary tokens | `backend/security/guard.py` (`PromptGuard`) |
| **LLM02: Sensitive Information Disclosure** | Secret, system prompt, and API key leak filters | `PromptGuard` (`SECRET_EXFILTRATION` signature) |
| **LLM04: Model Denial of Service** | Bounded length enforcement (`MAX_PROMPT_CHARS = 4000`, `MAX_ANSWER_CHARS = 64`) & rate limiting | `backend/security/sanitizer.py`, `backend/security/middleware.py` |
| **LLM06: Excessive Agency / Unbounded Tools** | Strictly typed tool registry with explicit JSON schema and input validation | `backend/tools.py`, `src/llm/tools/executor.py` |
| **LLM07: System Instruction Override** | Instruction override filters blocking `[INST]`, `<system>`, and DAN overrides | `PromptGuard` (`INSTRUCTION_OVERRIDE`, `DAN_OVERRIDE`) |
| **LLM08: Data & Output Sanitization** | HTML/script tag stripping, path traversal stripping (`../`), null-byte scrubbing | `backend/security/sanitizer.py` |

---

### 2. Security Middleware & Defense-in-Depth

All HTTP endpoints are protected by standard defensive headers registered on Flask startup:
- `X-Content-Type-Options: nosniff` (Prevents MIME-type sniffing attacks)
- `X-Frame-Options: SAMEORIGIN` (Mitigates clickjacking)
- `X-XSS-Protection: 1; mode=block` (Enforces browser XSS filtering)
- `IP-based Rate Limiter`: Default 120 requests / 60 seconds per IP to mitigate denial-of-service attempts.

---

### 3. Continuous Learning Dataset Integrity

All user queries and responses logged to `LLM/data/continuous_training_dataset.jsonl` are:
- Pre-scanned for prompt injection payloads (flagged payloads are blocked and never reach the training corpus).
- Memory-tracked through `backend/memory/lifecycle.py` for auditability.
- Validated with arithmetic verification tools before labeling as auto-verified.

---

### 4. Security Audit & Monitoring APIs

Maintainers and evaluators can verify real-time security status via:
- `GET /api/security/audit`: Active OWASP guard signatures, sanitization limits, and rate-limiting configuration.
- `GET /api/memory/sessions`: Active learner sessions, memory bounds, and observed cognitive bug profiles.

---

### 5. Reporting Security Vulnerabilities

If you identify a security issue or unexpected behavior:
1. Do **not** post security bugs in public issues.
2. Open a confidential report via GitHub Private Vulnerability Reporting or contact the project maintainers.
