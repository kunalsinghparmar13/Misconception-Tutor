"""
================================================================================
AI That Teaches: Misconception Tutor — LLM Engine & Socratic Generator
Integrates the fine-tuned PEFT adapter with a resilient Cognitive Socratic fallback,
and orchestrates continuous training data logging.
================================================================================
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm.core.types import Message, Role  # noqa: E402
from llm.prompt.builder import PromptBuilder, PromptConfig  # noqa: E402
from backend.tools import math_tool_executor, tool_registry  # noqa: E402

LLM_DIR = ROOT / "LLM"
DATA_DIR = ROOT / "data"
TRAINING_DATA_DIR = LLM_DIR / "data"

TRAINING_DATASET_PATH = TRAINING_DATA_DIR / "continuous_training_dataset.jsonl"


class LLMEngine:
    """Manages LLM inference, Socratic prompt formatting, and continuous training data capture."""

    def __init__(self, adapter_dir: Optional[Path] = None) -> None:
        self.adapter_dir = adapter_dir or LLM_DIR
        self._lock = threading.Lock()
        self._model: Any = None
        self._tokenizer: Any = None
        self.error: Optional[str] = None
        self._init_storage()

    @property
    def active_checkpoint(self) -> str:
        try:
            from backend.trainer import continuous_trainer
            return continuous_trainer.get_status().get("activeCheckpoint", "checkpoint-1003")
        except Exception:
            return "checkpoint-1003"

    @property
    def base_model(self) -> str:
        default_model = "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit"
        return os.getenv("LLM_BASE_MODEL", default_model)

    @property
    def adapter_source(self) -> str:
        # Use a local adapter only when explicitly configured.
        local_adapter = os.getenv("LLM_NOTEBOOK_ADAPTER_PATH")
        if local_adapter and Path(local_adapter).is_dir():
            if (Path(local_adapter) / "adapter_config.json").exists():
                return local_adapter

        return os.getenv(
            "LLM_ADAPTER_ID",
            "kunalsinghparmar/misconception-tutor-gemma4-e4b",
        )

    @property
    def remote_backend_url(self) -> Optional[str]:
        """Returns the base URL of a separate remote LLM service (Modal, HF Space, or GPU host)."""
        url = (
            os.getenv("LLM_BACKEND_URL")
            or os.getenv("REMOTE_LLM_URL")
            or os.getenv("LLM_API_URL")
            or os.getenv("MODAL_APP_URL")
            or os.getenv("HF_SPACE_URL")
        )
        if url:
            return url.strip().rstrip("/")
        return None

    def _check_remote_backend_status(self) -> Dict[str, Any]:
        """Probes the configured remote LLM backend for readiness and model information."""
        url = self.remote_backend_url
        if not url:
            return {"configured": False, "reachable": False}
        import requests

        headers = {}
        token = (
            os.getenv("LLM_BACKEND_TOKEN")
            or os.getenv("HF_TOKEN")
            or os.getenv("ADMIN_TOKEN")
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Admin-Token"] = token

        for ep in ("/api/ready", "/api/health", "/api/backend-status"):
            try:
                res = requests.get(f"{url}{ep}", headers=headers, timeout=4.0)
                if res.status_code == 200:
                    data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    return {
                        "configured": True,
                        "reachable": True,
                        "url": url,
                        "endpoint": ep,
                        "model": data.get("model") or self.adapter_source,
                        "status": "online",
                    }
            except Exception:
                continue

        return {"configured": True, "reachable": False, "url": url}

    def _init_storage(self) -> None:
        """Ensures the training data directories and files are initialized."""
        TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not TRAINING_DATASET_PATH.exists():
            self._seed_initial_training_samples()

    def status(self) -> Dict[str, Any]:
        """Returns the readiness status of the LLM system."""
        configured = (self.adapter_dir / "adapter_config.json").exists() or bool(
            self.adapter_source
        ) or bool(self.remote_backend_url)
        dependencies_installed = False
        dep_error = None
        try:
            import peft  # noqa: F401
            import torch  # noqa: F401
            import transformers  # noqa: F401

            dependencies_installed = True
        except ImportError as exc:
            dep_error = f"PyTorch/PEFT not installed: {exc}"

        dataset_size = self.get_training_sample_count()
        ecc_provider = os.getenv("LLM_PROVIDER")

        remote_status = self._check_remote_backend_status() if self.remote_backend_url else None
        is_remote_ready = bool(remote_status and remote_status.get("reachable", False))
        is_loaded = (self._model is not None) or is_remote_ready

        active_mode = "Cognitive Socratic Engine (Fine-tuned Gemma format)"
        if self.remote_backend_url and is_remote_ready:
            active_mode = f"Remote GPU LLM Backend ({self.remote_backend_url})"
        elif ecc_provider:
            active_mode = f"ECC Enterprise Provider ({ecc_provider})"
        elif self._model:
            active_mode = "PEFT Adapter (Gemma-4B)"

        model_name = remote_status.get("model") if is_remote_ready else self.adapter_source

        return {
            "configured": configured,
            "dependenciesInstalled": dependencies_installed,
            "loaded": is_loaded,
            "available": is_loaded,
            "liveAiEnabled": is_loaded,
            "model": model_name,
            "baseModel": self.base_model,
            "activeCheckpoint": self.active_checkpoint,
            "trainingSamplesCollected": dataset_size,
            "mode": active_mode,
            "tools": [t.name for t in tool_registry.list_tools()],
            "ecc_provider": ecc_provider,
            "remoteBackend": {
                "url": self.remote_backend_url,
                "reachable": is_remote_ready,
            } if self.remote_backend_url else None,
            "error": self.error or dep_error,
            "modelOnly": os.getenv("LLM_ONLY_MODEL", "").lower() in {"1", "true", "yes"},
        }

    def _try_load_peft(self) -> bool:
        """Load the published Hugging Face PEFT adapter once."""
        if self._model is not None:
            return True

        with self._lock:
            if self._model is not None:
                return True

            adapter_source = os.getenv("LLM_ADAPTER_PATH") or self.adapter_source
            hf_token = os.getenv("HF_TOKEN")

            try:
                import torch  # noqa: F401
                from peft import AutoPeftModelForCausalLM, PeftConfig
                from transformers import AutoTokenizer

                # Read adapter metadata first.
                peft_config = PeftConfig.from_pretrained(
                    adapter_source,
                    token=hf_token,
                )

                base_model_id = (
                    peft_config.base_model_name_or_path
                    or self.base_model
                )

                # Load tokenizer from the base model, not necessarily the adapter.
                self._tokenizer = AutoTokenizer.from_pretrained(
                    base_model_id,
                    token=hf_token,
                    trust_remote_code=True,
                )

                # Load base model + adapter.
                self._model = AutoPeftModelForCausalLM.from_pretrained(
                    adapter_source,
                    token=hf_token,
                    device_map=os.getenv("LLM_DEVICE_MAP", "auto"),
                    torch_dtype="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                )

                self._model.eval()
                self.error = None
                return True

            except Exception as exc:
                self._model = None
                self._tokenizer = None
                self.error = (
                    f"Could not load adapter '{adapter_source}': "
                    f"{type(exc).__name__}: {exc}"
                )
                return False

    def _call_remote_backend(
        self,
        subject: str,
        question: str,
        mode: str,
        learner_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Forwards generation request to teammate's separate LLM backend (Modal, Hugging Face Spaces, or GPU host).
        Ensures 100% interoperability with the separate LLM microservice.
        """
        url = self.remote_backend_url
        if not url:
            return None

        import requests

        headers = {"Content-Type": "application/json"}
        token = (
            os.getenv("LLM_BACKEND_TOKEN")
            or os.getenv("HF_TOKEN")
            or os.getenv("ADMIN_TOKEN")
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Admin-Token"] = token

        timeout = float(os.getenv("LLM_BACKEND_TIMEOUT", "35.0"))
        payload = {
            "question": question,
            "subject": subject,
            "mode": mode,
            "learner_id": learner_id,
        }

        try:
            resp = requests.post(
                f"{url}/api/llm/answer",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("answer"):
                    sample_id = self.log_training_sample(
                        subject=subject,
                        instruction=f"Diagnose the {subject} query using remote LLM backend in {mode} mode.",
                        user_input=question,
                        model_output=data["answer"],
                        learner_id=learner_id,
                        metadata={
                            "source": "remote_llm_backend",
                            "remote_url": url,
                            "remote_model": data.get("model", self.adapter_source),
                            **(data.get("metadata") or {}),
                        },
                    )
                    data["sample_id"] = sample_id
                    data["status"] = "success"
                    return data
            elif resp.status_code == 503 and os.getenv("LLM_ONLY_MODEL", "").lower() in {"1", "true", "yes"}:
                return resp.json()
            else:
                self.error = f"Remote LLM at {url} returned HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            self.error = f"Remote LLM connection to {url} failed: {exc}"
            if os.getenv("LLM_ONLY_MODEL", "").lower() in {"1", "true", "yes"}:
                return {
                    "answer": (
                        "### Remote LLM Backend Unavailable\n\n"
                        f"Could not connect to the remote LLM backend at `{url}`.\n"
                        f"Runtime reason: {type(exc).__name__}: {exc}\n\n"
                        "Check that your Modal / Hugging Face Spaces LLM backend is active and reachable."
                    ),
                    "model": f"Remote LLM ({url})",
                    "sample_id": "",
                    "metadata": {
                        "source": "model_unavailable",
                        "remote_url": url,
                        "error": str(exc),
                    },
                    "status": "model_unavailable",
                }
        return None

    def answer_socratic(
        self,
        subject: str,
        question: str,
        mode: str = "diagnostic",
        learner_id: str = "student_demo",
    ) -> Dict[str, Any]:
        """
        Generates Socratic tutoring response adhering to Bloom 2-Sigma principles.
        Utilizes remote LLM backend (Modal / HF Spaces), ECC multi-provider harness,
        local PEFT Gemma adapter, or Cognitive Socratic Engine.
        """
        # 1. Try remote separate LLM backend if configured (e.g. Modal app, HF Space GPU, remote server)
        if self.remote_backend_url:
            remote_res = self._call_remote_backend(subject, question, mode, learner_id)
            if remote_res is not None:
                return remote_res

        system_prompt = (
            "You are Misconception Tutor, a patient Socratic math tutor. "
            f"Subject: {subject}. Mode: {mode}. Explain the student's reasoning, identify the first "
            "divergence, and teach the correction without doing homework for them. "
            "Use concise Markdown and finish with a Key Takeaway."
        )
        builder = PromptBuilder(PromptConfig(system_template=system_prompt, include_tools_in_system=True))
        normalized_messages = builder.build(
            messages=[Message(role=Role.USER, content=question)],
            tools=tool_registry.list_tools(),
        )

        # 2. Try ECC multi-provider if configured
        provider_name = os.getenv("LLM_PROVIDER")
        if provider_name:
            try:
                from llm.providers.resolver import get_provider
                provider = get_provider(provider_name)
                llm_out = provider.generate(normalized_messages, tools=tool_registry.list_tools())
                
                # Execute any tool calls if returned
                if llm_out.tool_calls:
                    results = math_tool_executor.execute_all(llm_out.tool_calls)
                    tool_content = "\n".join(r.content for r in results)
                    ans_text = f"{llm_out.content}\n\n[Verified Arithmetic via ECC Math Tool]:\n{tool_content}" if llm_out.content else tool_content
                else:
                    ans_text = llm_out.content

                sample_id = self.log_training_sample(
                    subject=subject,
                    instruction=f"Diagnose the {subject} query using ECC {provider_name} provider in {mode} mode.",
                    user_input=question,
                    model_output=ans_text,
                    learner_id=learner_id,
                    metadata={"source": f"ecc_{provider_name}", "mode": mode},
                )
                return {
                    "answer": ans_text,
                    "model": f"ECC {provider_name.capitalize()} Tutor ({self.active_checkpoint})",
                    "sample_id": sample_id,
                    "status": "success",
                }
            except Exception as e:
                self.error = f"ECC provider '{provider_name}' error: {e}. Falling back to local engine."

        # 3. Try local PEFT adapter if weights are smudged/loaded
        if self._try_load_peft() and self._model and self._tokenizer:
            try:
                ans_text = self._generate_peft(subject, question, mode)
                sample_id = self.log_training_sample(
                    subject=subject,
                    instruction=f"Diagnose the {subject} query and provide Socratic remediation in {mode} mode.",
                    user_input=question,
                    model_output=ans_text,
                    learner_id=learner_id,
                    metadata={"source": "peft_adapter", "mode": mode},
                )
                return {
                    "answer": ans_text,
                    "model": f"Fine-tuned Gemma ({self.active_checkpoint})",
                    "sample_id": sample_id,
                    "status": "success",
                }
            except Exception as e:
                self.error = f"PEFT generation error: {e}. Falling back to Cognitive Socratic Engine."

        # 4. Do not present deterministic output as the user's model when
        # model-only mode is requested.
        if os.getenv("LLM_ONLY_MODEL", "").lower() in {"1", "true", "yes"}:
            reason = self.error or "The configured adapter could not be loaded."
            return {
                "answer": (
                    "### Model unavailable\n\n"
                    "Your Gemma adapter was not used for this answer. "
                    f"Runtime reason: {reason}\n\n"
                    "Run this app on a CUDA machine with the notebook-compatible "
                    "Unsloth/PEFT stack, or set LLM_BACKEND_URL to your separate Modal/HF GPU backend."
                ),
                "model": self.adapter_source,
                "sample_id": "",
                "metadata": {
                    "source": "model_unavailable",
                    "adapter": self.adapter_source,
                    "error": reason,
                },
                "status": "model_unavailable",
            }

        # 5. High-precision cognitive Socratic generator
        ans_text, metadata = self._generate_cognitive_socratic(subject, question, mode)
        sample_id = self.log_training_sample(
            subject=subject,
            instruction=f"Diagnose the {subject} query, pinpoint first divergence, and provide Socratic guidance.",
            user_input=question,
            model_output=ans_text,
            learner_id=learner_id,
            metadata=metadata,
        )
        return {
            "answer": ans_text,
            "model": f"Deterministic Cognitive Socratic Engine ({self.active_checkpoint})",
            "sample_id": sample_id,
            "metadata": metadata,
            "status": "success",
        }

    def _generate_peft(self, subject: str, question: str, mode: str) -> str:
        """Inference with PEFT adapter grounded with exact mathematical & AST execution facts."""
        tokenizer = self._tokenizer
        model = self._model

        # Tool Grounding: Pre-compute exact facts to prevent mental math / hallucinated execution slips
        grounding_facts: List[str] = []
        is_code = subject.lower() in ["python", "coding", "programming", "computer science", "cs"] or (
            any(k in question for k in ["def ", "import ", "print(", "```", "SyntaxError", "ZeroDivisionError"])
        )
        if is_code:
            try:
                from backend.sandbox import run_student_code
                from backend.python_debugger import python_debugger
                code, _, _ = python_debugger.split_input(question)
                if code:
                    exec_res = run_student_code(code)
                    if not exec_res["success"]:
                        grounding_facts.append(
                            f"Execution error: {exec_res.get('error_type')} at line {exec_res.get('line')}: {exec_res.get('error_message')}"
                        )
                    else:
                        stdout = exec_res.get("stdout", "").strip()
                        grounding_facts.append(f"Execution output: clean execution with stdout '{stdout}'")
            except Exception:
                pass
        else:
            match = re.search(r"(\d+)\s*/\s*(\d+)\s*([\+\-\*\/÷])\s*(\d+)\s*/\s*(\d+)", question)
            if match:
                try:
                    from backend import backend_code
                    a, b, op, c, d = int(match.group(1)), int(match.group(2)), match.group(3), int(match.group(4)), int(match.group(5))
                    is_div = op in ["/", "÷"]
                    correct = backend_code.correct_div(a, b, c, d) if is_div else backend_code.correct_add(a, b, c, d)
                    grounding_facts.append(
                        f"Exact mathematical ground truth: {a}/{b} {op} {c}/{d} = {backend_code.format_fraction(correct)}"
                    )
                except Exception:
                    pass

        facts_block = ""
        if grounding_facts:
            facts_block = "\nVerified calculation/execution facts:\n- " + "\n- ".join(grounding_facts) + "\n"

        system = (
            "You are Misconception Tutor, a patient Socratic tutor for mathematics and coding. "
            f"Subject: {subject}. Mode: {mode}.\n"
            "Pedagogical Principles:\n"
            "1. Do not simply do homework for the student; teach the conceptual foundation.\n"
            "2. Identify the first divergence or buggy mental rule.\n"
            "3. Provide a clear real-world intuition or counter-example.\n"
            "4. Show the step-by-step correction in bite-sized stages.\n"
            "5. Conclude with one short practice challenge and a Key Takeaway.\n"
            "Structure your response with clear markdown headings."
        )
        user_content = question + facts_block
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        if hasattr(tokenizer, "apply_chat_template"):
            inputs = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
        else:
            inputs = tokenizer(
                f"System: {system}\nUser: {user_content}\nAssistant:",
                return_tensors="pt",
            )
        import torch

        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        prompt_length = inputs["input_ids"].shape[-1]
        return tokenizer.decode(output[0][prompt_length:], skip_special_tokens=True).strip()

    def _generate_cognitive_socratic(
        self, subject: str, question: str, mode: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Specialized domain-aware cognitive engine that generates precise Socratic responses
        matching the fine-tuned Gemma checkpoint format.
        Supports Python code debugging, compiler execution, algebraic equations, and fraction diagnosis.
        """
        q_lower = question.lower()
        metadata: Dict[str, Any] = {"topic": "general", "source": "cognitive_socratic_engine"}

        # Case 1: Fraction addition / division misconceptions
        fraction_pattern = re.search(r"(\d+)\s*/\s*(\d+)\s*([\+\-\*\/÷])\s*(\d+)\s*/\s*(\d+)", question)
        if fraction_pattern or "fraction" in q_lower or any(k in q_lower for k in ["add across", "common denominator", "flip"]):
            return self._socratic_math_fraction(question)

        # Case 2: Quadratic factorization & AC Method concept
        if any(k in q_lower for k in ["factor", "2x²", "2x^2", "middle term", "roots", "ac method", "signs feel wrong"]):
            metadata["topic"] = "quadratic_factorization"
            metadata["misconception"] = "quadratic_ac_method"
            response = (
                "### 🔍 First Divergence: Middle Term Coefficient\n\n"
                "In factoring a quadratic $ax^2 + bx + c$, the two split terms must multiply to $a \\cdot c$ and sum to $b$.\n\n"
                "Let's trace your attempt:\n"
                "- Given: $2x^2 + 5x - 12 = 0$\n"
                "- Product requirement: $a \\cdot c = 2 \\times (-12) = -24$\n"
                "- Sum requirement: $b = +5$\n\n"
                "If you test $(2x - 3)(x + 4)$, notice the expansion:\n"
                "$$2x(x + 4) - 3(x + 4) = 2x^2 + 8x - 3x - 12 = 2x^2 + 5x - 12$$\n\n"
                "Your factorization **actually factors the expression correctly!** Where the doubt often creeps in is checking the roots vs. the expansion:\n"
                "- Set factor 1 to zero: $2x - 3 = 0 \\implies x = 3/2$\n"
                "- Set factor 2 to zero: $x + 4 = 0 \\implies x = -4$\n\n"
                "### 💡 Socratic Check\n"
                "When you substituted back, did you check $x = 3/2$ into $2(3/2)^2 + 5(3/2) - 12$? Notice: $2(9/4) + 15/2 - 12 = 9/2 + 15/2 - 12 = 24/2 - 12 = 0$. The check holds!\n\n"
                "### 📌 Key Takeaway\n"
                "Always verify factoring with the **'AC Method'**: Find factors of $a \\cdot c$ that add to $b$. To check signs safely, expand $(A + B)(C + D)$ with FOIL before solving for roots."
            )
            return response, metadata

        # Case 3: Python Code Compilation & AST Debugging Check (Dynamic Code First)
        has_code_syntax = (
            "```" in question
            or "def " in question
            or "import " in question
            or ("for " in question and ":" in question)
            or ("while " in question and ":" in question)
            or "print(" in question
            or "SyntaxError" in question
            or "IndentationError" in question
            or "TypeError" in question
            or "ZeroDivisionError" in question
            or "IndexError" in question
        )
        is_python_subject = subject.lower() in ["python", "coding", "programming", "computer science", "cs"]
        # If actual code syntax is provided, always debug the user's specific code dynamically
        if has_code_syntax or (is_python_subject and any(c in question for c in ["=", "(", ")", ":", "[", "]"])):
            from backend.python_debugger import python_debugger
            return python_debugger.analyze_and_explain(question)

        # Case 4: Recursive Fibonacci / Stack Overflow Conceptual Problem
        if any(k in q_lower for k in ["fib", "fibonacci", "memoization", "recursionerror"]):
            metadata["topic"] = "recursion_optimization"
            response = (
                "### 🔍 First Divergence: Exponential Call Tree Overlap\n\n"
                "In naive recursive Fibonacci `fib(n) = fib(n-1) + fib(n-2)`:\n"
                "- To compute `fib(5)`, it computes `fib(4)` and `fib(3)`.\n"
                "- But `fib(4)` ALSO computes `fib(3)` and `fib(2)` independently.\n\n"
                "The branching creates an $O(2^n)$ call tree where the same subproblems are solved billions of redundant times! When $n \\ge 1000$, Python hits `sys.getrecursionlimit()` (default 1000 frames), raising `RecursionError`.\n\n"
                "### 💡 Socratic Fix: Preserve Signature via Memoization\n\n"
                "Instead of redesigning the function signature, cache prior results:\n\n"
                "```python\n"
                "from functools import lru_cache\n\n"
                "@lru_cache(maxsize=None)\n"
                "def fib(n: int) -> int:\n"
                "    if n <= 1:\n"
                "        return n\n"
                "    return fib(n - 1) + fib(n - 2)\n"
                "```\n\n"
                "By memoizing, the call graph collapses from an exponential tree of $O(2^n)$ to a linear chain of $O(n)$ time complexity and $O(n)$ recursion depth.\n\n"
                "### 📌 Key Takeaway\n"
                "When a recursive function branches into overlapping subproblems, add `@lru_cache` or an iterative bottom-up array to convert exponential time into linear time without breaking callers."
            )
            return response, metadata

        # Case 5: Integration by Parts Sign Flip
        if any(k in q_lower for k in ["integration by parts", "integral", "∫", "dx", "e^(-2x)"]):
            metadata["topic"] = "calculus_integration_by_parts"
            response = (
                "### 🔍 First Divergence: The Differential of $v$\n\n"
                "Recall the Integration by Parts formula:\n"
                "$$\\int u \\, dv = u v - \\int v \\, du$$\n\n"
                "Let's trace your choices for $\\int x e^{-2x} \\, dx$:\n"
                "1. Choose $u = x \\implies du = dx$\n"
                "2. Choose $dv = e^{-2x} dx \\implies v = -\\frac{1}{2} e^{-2x}$\n\n"
                "Now assemble $u v - \\int v \\, du$:\n"
                "$$= x \\left(-\\frac{1}{2} e^{-2x}\\right) - \\int \\left(-\\frac{1}{2} e^{-2x}\\right) dx$$\n\n"
                "Notice the **double negative** in $-\\int (-\\dots)$! It becomes positive:\n"
                "$$= -\\frac{1}{2} x e^{-2x} + \\frac{1}{2} \\int e^{-2x} dx$$\n\n"
                "Now integrate the remaining term: $\\int e^{-2x} dx = -\\frac{1}{2} e^{-2x}$.\n"
                "$$= -\\frac{1}{2} x e^{-2x} + \\frac{1}{2}\\left(-\\frac{1}{2} e^{-2x}\\right) = -\\frac{1}{2} x e^{-2x} - \\frac{1}{4} e^{-2x} + C$$\n\n"
                "### 💡 Where the Slip Happened\n"
                "The extra minus sign emerged because the second integration introduces another factor of $(-1/2)$ that flips the $+1/2$ back to $-1/4$.\n\n"
                "### 📌 Key Takeaway\n"
                "Write down the three signs explicitly: (1) the negative in $uv - \\int v du$, (2) the negative inside $v$, and (3) the negative from the chain rule antiderivative of $e^{-kx}$."
            )
            return response, metadata

        # Case 6: Nested 2D Grid / Matrix Loop Boundary Check (Canonical Problem)
        if ("grid" in q_lower and ("col" in q_lower or "boundary" in q_lower or "horizon" in q_lower)) or "grid[row][col+1]" in question.replace(" ", ""):
            metadata["topic"] = "matrix_boundary_guard"
            response = (
                "### 🔍 First Divergence: Off-by-One Horizon\n\n"
                "In the line:\n"
                "```python\n"
                "for col in range(len(grid[0])):\n"
                "    if grid[row][col + 1] == 1: ...\n"
                "```\n"
                "When `col == len(grid[0]) - 1` (the last column), evaluating `col + 1` queries an index equal to `len(grid[0])`, which exceeds the bounds of a 0-indexed list.\n\n"
                "### 💡 Idiomatic Guard Solutions\n\n"
                "**Option A: Constrain the loop range:**\n"
                "```python\n"
                "# Only iterate up to the penultimate column\n"
                "for col in range(len(grid[0]) - 1):\n"
                "    if grid[row][col + 1] == 1:\n"
                "        count += 1\n"
                "```\n\n"
                "**Option B: Explicit condition guard:**\n"
                "```python\n"
                "for col in range(len(grid[0])):\n"
                "    if col + 1 < len(grid[0]) and grid[row][col + 1] == 1:\n"
                "        count += 1\n"
                "```\n\n"
                "### 📌 Key Takeaway\n"
                "Whenever accessing `index + k`, either restrict `range(..., len - k)` or use Python short-circuit evaluation (`index + k < len and ...`) to prevent `IndexError`."
            )
            return response, metadata

        # Case 7: General Mathematical Equations, Arithmetic & Percentage Problem Solving
        from backend.general_solver import general_solver
        if general_solver.can_solve(question):
            return general_solver.solve_and_explain(question)

        # Default Socratic Guidance for custom queries
        metadata["topic"] = "general_socratic"
        response = (
            f"### 🔍 Socratic Analysis: {subject}\n\n"
            f"Let's look at the problem you're tackling:\n> *{question[:160]}...*\n\n"
            "To pinpoint the divergence without giving the answer away, let's step through the reasoning:\n"
            "1. **Identify the Given State**: What are your known inputs, constraints, and assumptions?\n"
            "2. **The Divergence Point**: At what specific step or operation did the result diverge from expectations?\n"
            "3. **Invariant Check**: Does the intermediate result preserve scale, signs, and dimensions?\n\n"
            "### 💡 Guiding Question\n"
            "Can you write down your step immediately preceding the error? Look closely at whether any sign, scaling factor, or boundary condition was modified implicitly.\n\n"
            "### 📌 Key Takeaway\n"
            "In both mathematical proofs and algorithmic routines, systematic verification of invariants at each step prevents small mental slips from compounding."
        )
        return response, metadata

    def _socratic_math_fraction(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """Handles fraction misconception diagnosis within Socratic flow using exact buggy rules."""
        from backend import backend_code

        metadata = {"topic": "fraction_arithmetic", "source": "cognitive_math_engine"}

        # Look for fraction problem like 1/4 + 1/6 or 1/2 ÷ 1/4
        match = re.search(r"(\d+)\s*/\s*(\d+)\s*([\+\-\*\/÷])\s*(\d+)\s*/\s*(\d+)", question)
        if match:
            a, b, op, c, d = int(match.group(1)), int(match.group(2)), match.group(3), int(match.group(4)), int(match.group(5))
            is_div = op in ["/", "÷"]
            correct = backend_code.correct_div(a, b, c, d) if is_div else backend_code.correct_add(a, b, c, d)
            corr_str = backend_code.format_fraction(correct)

            # Look for student's attempted answer in the prompt (e.g. "got 1/5", "= 1/5", "gives 1/5")
            attempt_matches = re.findall(r"(\d+)\s*/\s*(\d+)", question)
            student_frac = None
            if len(attempt_matches) > 2:
                last_m = attempt_matches[-1]
                student_frac = backend_code.Fraction(int(last_m[0]), int(last_m[1]))

            # Check buggy rules
            detected_bug = None
            bug_rules = backend_code.BUGS_DIV if is_div else backend_code.BUGS_ADD
            if student_frac:
                for bug_id, bug_fn in bug_rules.items():
                    try:
                        top, bot = bug_fn(a, b, c, d)
                        if bot != 0 and backend_code.Fraction(top, bot) == student_frac:
                            detected_bug = bug_id
                            break
                    except Exception:
                        pass

            if detected_bug:
                metadata["misconception"] = detected_bug
                expl = backend_code.EXPLANATIONS.get(detected_bug, {})
                replay = backend_code.generate_replay(detected_bug, a, b, c, d)
                follow_up = backend_code.generate_targeted_problem(detected_bug, difficulty=1)

                response = (
                    f"### 🔍 First Divergence: {expl.get('title', detected_bug)}\n\n"
                    f"**Cognitive Replay:** {replay}\n\n"
                    f"**Why it fails:** {expl.get('why_it_fails', '')}\n\n"
                    f"**Counter-example:** {expl.get('simple_example', '')}\n\n"
                    f"### 💡 Socratic Correction\n"
                    f"{expl.get('fix_hint', '')}\n\n"
                    f"- The exact verified result for ${a}/{b} {'÷' if is_div else '+'} {c}/{d}$ is **${corr_str}$**.\n\n"
                    f"### 🎯 Targeted Practice Drill\n"
                    f"Try solving this isomorphic follow-up drill: **{follow_up['text']}**\n\n"
                    f"### 📌 Key Takeaway\n"
                    f"Always preserve equal piece sizes when adding fractions by finding a common denominator first, and use 'Keep, Change, Flip' when dividing."
                )
                return response, metadata
            else:
                metadata["misconception"] = "M4_div_mult_across" if is_div else "M1_add_across"
                response = (
                    f"### 🔍 Socratic Fraction Analysis\n\n"
                    f"For the problem **${a}/{b} {'÷' if is_div else '+'} {c}/{d}$**:\n\n"
                    f"1. **Identify the Operation**: {'Division represents finding how many portions of the divisor fit into the dividend.' if is_div else 'Addition represents accumulating counts of equal-sized pieces.'}\n"
                    f"2. **Common Denominator / Inversion Rule**: {'Keep the first fraction, change ÷ to ×, and invert the second fraction.' if is_div else f'Find the least common multiple of denominators {b} and {d}: lcm({b}, {d}) = {backend_code.lcm(b, d)}.'}\n"
                    f"3. **Exact Evaluation**: The mathematically verified result is **${corr_str}$**.\n\n"
                    f"### 💡 Guiding Question\n"
                    f"Check whether your intermediate step modified slice sizes or inverted the wrong fraction.\n\n"
                    f"### 📌 Key Takeaway\n"
                    f"Never add denominators directly. Denominators dictate slice size, not piece count."
                )
                return response, metadata

        # Default fraction overview
        metadata["misconception"] = "M1_add_across"
        response = (
            "### 🔍 Socratic Fraction Diagnosis\n\n"
            "When combining fractions, the denominator represents **the size of each equal piece**, while the numerator counts **how many pieces you have**.\n\n"
            "- **For Addition:** You cannot add numerators across different slice sizes. You must convert both fractions to an equivalent common denominator first.\n"
            "- **For Division:** Dividing by a fraction asks *'how many portions of this size fit inside the total?'*, which requires multiplying by the reciprocal (Keep, Change, Flip).\n\n"
            "### 💡 Socratic Tip\n"
            "Paste any specific problem and your attempted step into the composer below (e.g. `1/4 + 1/6 = 1/5`) to trace the exact mental rule that produced it!"
        )
        return response, metadata

    def log_training_sample(
        self,
        subject: str,
        instruction: str,
        user_input: str,
        model_output: str,
        learner_id: str = "anon",
        misconception: Optional[str] = None,
        feedback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Stores an interaction pair in JSONL format for continuous fine-tuning.
        Returns unique sample ID.
        """
        sample_id = f"samp_{int(datetime.utcnow().timestamp() * 1000)}"
        sample_record = {
            "id": sample_id,
            "timestamp": datetime.utcnow().isoformat(),
            "learner_id": learner_id,
            "subject": subject,
            "instruction": instruction,
            "input": user_input,
            "output": model_output,
            "misconception": misconception or metadata.get("misconception") if metadata else None,
            "feedback": feedback or "unrated",
            "metadata": metadata or {},
        }

        # Thread-safe append to JSONL file
        with self._lock:
            with open(TRAINING_DATASET_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample_record, ensure_ascii=False) + "\n")

        # Automatic self-training trigger every 10 collected interactions
        if os.getenv("AUTO_TRAIN_ENABLED", "1") == "1":
            total = self.get_training_sample_count()
            if total > 0 and total % 10 == 0:
                try:
                    from backend.trainer import continuous_trainer
                    if not continuous_trainer.is_training:
                        continuous_trainer.start_training_run()
                except Exception as exc:
                    print(f"Auto-train notice: {exc}")

        return sample_id

    def update_sample_feedback(self, sample_id: str, feedback: str, notes: Optional[str] = None) -> bool:
        """Updates feedback rating (helpful/unhelpful) on a logged sample."""
        if not TRAINING_DATASET_PATH.exists():
            return False

        with self._lock:
            lines = []
            updated = False
            with open(TRAINING_DATASET_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("id") == sample_id:
                        rec["feedback"] = feedback
                        if notes:
                            rec["feedback_notes"] = notes
                        updated = True
                    lines.append(rec)

            if updated:
                with open(TRAINING_DATASET_PATH, "w", encoding="utf-8") as f:
                    for rec in lines:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return updated

    def get_training_sample_count(self) -> int:
        """Returns the number of logged training samples."""
        if not TRAINING_DATASET_PATH.exists():
            return 0
        try:
            with open(TRAINING_DATASET_PATH, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def get_recent_samples(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent training samples for the UI inspector."""
        if not TRAINING_DATASET_PATH.exists():
            return []
        samples = []
        try:
            with open(TRAINING_DATASET_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        samples.append(json.loads(line))
            return samples[-limit:][::-1]
        except Exception:
            return []

    def _seed_initial_training_samples(self) -> None:
        """Seeds initial diverse training pairs for the hackathon demonstration."""
        seeds = [
            {
                "id": "samp_seed_01",
                "timestamp": datetime.utcnow().isoformat(),
                "learner_id": "seed_student",
                "subject": "Mathematics",
                "instruction": "Diagnose the fraction addition mistake and explain the buggy rule.",
                "input": "Problem: 1/4 + 1/6. Student answer: 1/5.",
                "output": "### 🔍 Misconception: Add Across (M1)\nYou added the numerators (1+1=2) and denominators (4+6=10) directly, giving 2/10 = 1/5.\n### 💡 Socratic Hint\nDenominators represent slice sizes. Find a common denominator (12) first so the pieces match before adding.",
                "misconception": "M1_add_across",
                "feedback": "helpful",
                "metadata": {"seeded": True},
            },
            {
                "id": "samp_seed_02",
                "timestamp": datetime.utcnow().isoformat(),
                "learner_id": "seed_student",
                "subject": "Mathematics",
                "instruction": "Diagnose fraction addition where tops are added and bottoms multiplied.",
                "input": "Problem: 1/4 + 1/6. Student answer: 1/12.",
                "output": "### 🔍 Misconception: Add Tops, Multiply Bottoms (M2)\nYou added the tops (1+1=2) and multiplied bottoms (4×6=24), resulting in 2/24 = 1/12.\n### 💡 Socratic Hint\nMultiplying denominators shrinks the value. Convert each fraction to common denominator 12 instead.",
                "misconception": "M2_tops_add_bottoms_multiply",
                "feedback": "helpful",
                "metadata": {"seeded": True},
            },
            {
                "id": "samp_seed_03",
                "timestamp": datetime.utcnow().isoformat(),
                "learner_id": "seed_student",
                "subject": "Mathematics",
                "instruction": "Diagnose fraction division where student multiplied straight across.",
                "input": "Problem: 1/2 ÷ 1/4. Student answer: 1/8.",
                "output": "### 🔍 Misconception: Multiply Straight Across on Division (M4)\nYou multiplied straight across: (1×1)/(2×4) = 1/8.\n### 💡 Socratic Hint\nDividing by 1/4 asks how many quarters fit inside a half. Use 'Keep, Change, Flip' to multiply by 4/1.",
                "misconception": "M4_divide_multiply_across",
                "feedback": "helpful",
                "metadata": {"seeded": True},
            },
            {
                "id": "samp_seed_04",
                "timestamp": datetime.utcnow().isoformat(),
                "learner_id": "seed_student",
                "subject": "Mathematics",
                "instruction": "Diagnose division where first fraction was inverted instead of second.",
                "input": "Problem: 1/2 ÷ 1/4. Student answer: 1/2.",
                "output": "### 🔍 Misconception: Invert Dividend Instead of Divisor (M5)\nYou inverted the first fraction (2/1 × 1/4 = 2/4 = 1/2). Invert only the divisor (the second fraction).",
                "misconception": "M5_flip_wrong_fraction",
                "feedback": "helpful",
                "metadata": {"seeded": True},
            },
        ]
        with open(TRAINING_DATASET_PATH, "w", encoding="utf-8") as f:
            for s in seeds:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")


# Global singleton instance
llm_engine = LLMEngine()
