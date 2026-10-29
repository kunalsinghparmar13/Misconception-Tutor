"""
================================================================================
ECC Agentic Security Suite: Prompt Injection & Jailbreak Guard
Implements OWASP Top 10 for Agents defenses as detailed in ECC's Security Guide:
- Prompt injection detection (direct & indirect)
- System instruction override protection
- Canary & secret leak prevention
================================================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SecurityScanResult:
    is_safe: bool
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    flagged_pattern: str | None = None
    sanitized_text: str = ""


# Canonical prompt injection signatures (ECC Security Guide)
INJECTION_SIGNATURES = [
    (r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbreak)\b", "JAILBREAK_ATTEMPT"),
    (r"(?i)\breveal\s+(your\s+)?(system\s+prompt|instructions|secret|api\s*key)\b", "SECRET_EXFILTRATION"),
    (r"(?i)\bprint\s+(your\s+)?(initial\s+prompt|hidden\s+text)\b", "PROMPT_EXTRACTION"),
    (r"(?i)\bact\s+as\s+(an\s+unrestricted|a\s+malicious|an\s+evil)\b", "PERSONA_HIJACK"),
    (r"(?i)\bdo\s+anything\s+now\b", "DAN_OVERRIDE"),
    (r"(?i)<\s*system\s*>.*<\s*/\s*system\s*>", "XML_SYSTEM_TAG_INJECTION"),
    (r"(?i)\[\s*INST\s*\].*\[\s*/\s*INST\s*\]", "LLAMA_TAG_INJECTION"),
]


class PromptGuard:
    """Enterprise security filter for agentic inputs."""

    def __init__(self, strict_mode: bool = False) -> None:
        self.strict_mode = strict_mode

    def scan(self, text: str) -> SecurityScanResult:
        if not text or not isinstance(text, str):
            return SecurityScanResult(is_safe=True, risk_level="LOW", sanitized_text="")

        # Normalize unicode and whitespace
        normalized = text.strip()

        # Check for injection signatures
        for pattern, tag in INJECTION_SIGNATURES:
            match = re.search(pattern, normalized)
            if match:
                return SecurityScanResult(
                    is_safe=False,
                    risk_level="HIGH",
                    flagged_pattern=tag,
                    sanitized_text=self._sanitize(normalized),
                )

        return SecurityScanResult(
            is_safe=True,
            risk_level="LOW",
            sanitized_text=normalized,
        )

    def _sanitize(self, text: str) -> str:
        """Strips malicious override prefixes while preserving benign math/code."""
        sanitized = text
        for pattern, _ in INJECTION_SIGNATURES:
            sanitized = re.sub(pattern, "[FILTERED_SECURITY_OVERRIDE]", sanitized)
        return sanitized


# Global singleton instance
prompt_guard = PromptGuard()
