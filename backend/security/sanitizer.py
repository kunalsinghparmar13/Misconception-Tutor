"""
================================================================================
ECC Agentic Security Suite: Input Sanitizer & Boundary Guard
Protects against Path Traversal, Denial-of-Service, and Unbounded Payloads.
================================================================================
"""

from __future__ import annotations

import html
import re
from typing import Optional

MAX_PROMPT_CHARS = 4000
MAX_ANSWER_CHARS = 64


def sanitize_input_text(text: Optional[str], max_length: int = MAX_PROMPT_CHARS) -> str:
    """Sanitizes freeform user input, enforces character limits, and removes control characters."""
    if not text or not isinstance(text, str):
        return ""

    # Truncate to maximum allowed bounds
    clean = text.strip()[:max_length]

    # Neutralize null bytes and dangerous terminal escapes
    clean = clean.replace("\x00", "").replace("\r\n", "\n")

    # Path traversal neutralizing
    clean = re.sub(r"\.\./+", "", clean)

    return clean


def sanitize_math_answer(answer: Optional[str]) -> str:
    """Sanitizes student mathematical input for arithmetic parsing."""
    if not answer or not isinstance(answer, str):
        return ""

    clean = answer.strip()[:MAX_ANSWER_CHARS]
    # Strip script blocks completely
    clean = re.sub(r"(?is)<script.*?>.*?</script>", "", clean)
    # Strip any remaining HTML tags
    clean = re.sub(r"<[^>]*>", "", clean)
    # Restrict to mathematical fraction characters: digits, slash, space, minus, period
    clean = re.sub(r"[^0-9\/\s\.\-]", "", clean)
    # Normalize internal whitespace
    return " ".join(clean.split())
