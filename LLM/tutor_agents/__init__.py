"""Four-agent tutoring pipeline powered by the user's fine-tuned Gemma adapter.

Agents
------
1. ExplainerAgent  - why the learner's answer/code is wrong and why the mistake happens
2. SolverAgent     - the correct answer (maths) or correct code (programming)
3. PracticeAgent   - new practice problems aimed at the same misconception
4. ReviewerAgent   - checks everything (exact arithmetic, real code execution, model critique)

Every piece of text a learner reads is written by the fine-tuned model. Deterministic
tools are used only to *ground* the prompts and to *verify* the output.

Import as ``tutor_agents`` (the ``LLM`` directory is put on ``sys.path`` by the backend);
the package is deliberately not named ``llm`` so it can never clash with ``src/llm``
on case-insensitive filesystems.
"""

from .model_client import ChatResult, ModelClient, ModelUnavailable
from .pipeline import TutorPipeline, get_pipeline, set_pipeline

__all__ = [
    "ChatResult",
    "ModelClient",
    "ModelUnavailable",
    "TutorPipeline",
    "get_pipeline",
    "set_pipeline",
]
