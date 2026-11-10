"""
================================================================================
ECC Agentic Security Suite: Prompt Injection & Jailbreak Guard
Implements OWASP Top 10 for Agents defenses as detailed in ECC's Security Guide:
- Prompt injection detection (direct & indirect)
- System instruction override protection
- Canary & secret leak prevention
- Token & control sequence neutralization
- Threat metrics & real-time telemetry
================================================================================
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class SecurityScanResult:
    is_safe: bool
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    flagged_pattern: str | None = None
    sanitized_text: str = ""


# Canonical prompt injection signatures (ECC Security Guide + OWASP Top 10 for LLMs)
INJECTION_SIGNATURES: List[Tuple[str, str]] = [
    # 1. Instruction overrides
    (r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+instructions\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\bforget\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)\b", "INSTRUCTION_OVERRIDE"),
    # 2. Jailbreaks & personas
    (r"(?i)\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbreak)\b", "JAILBREAK_ATTEMPT"),
    (r"(?i)\bact\s+as\s+(an\s+unrestricted|a\s+malicious|an\s+evil|chaosgpt|aim|godmode)\b", "PERSONA_HIJACK"),
    (r"(?i)\bdo\s+anything\s+now\b", "DAN_OVERRIDE"),
    # 3. Secret & prompt extraction
    (r"(?i)\breveal\s+(your\s+)?(system\s+prompt|instructions|secret|api\s*key)\b", "SECRET_EXFILTRATION"),
    (r"(?i)\bprint\s+(your\s+)?(initial\s+prompt|hidden\s+text)\b", "PROMPT_EXTRACTION"),
    (r"(?i)\bdump\s+(the\s+)?(environment|env|secrets|api\s*keys|config)\b", "SECRET_EXFILTRATION"),
    # 4. Token & prompt template delimiters
    (r"(?i)<\s*system\s*>.*<\s*/\s*system\s*>", "XML_SYSTEM_TAG_INJECTION"),
    (r"(?i)\[\s*INST\s*\].*\[\s*/\s*INST\s*\]", "LLAMA_TAG_INJECTION"),
    (r"(?i)<\s*<\s*SYS\s*>\s*>.*<\s*<\s*/\s*SYS\s*>\s*>", "SYSTEM_TOKEN_INJECTION"),
    (r"<\|im_start\|>|<\|im_end\|>|<turn_start>|<turn_end>", "CHAT_DELIMITER_INJECTION"),
    # 5. Remote code & OS command escape payloads
    (r"(?i)__import__\s*\(\s*['\"]os['\"]\s*\)", "REMOTE_CODE_EXECUTION_PAYLOAD"),
    (r"(?i)subprocess\.(?:Popen|run|check_output|call)", "SUBPROCESS_EXECUTION_PAYLOAD"),
]


class PromptGuard:
    """Enterprise security filter for agentic inputs with thread-safe audit telemetry."""

    def __init__(self, strict_mode: bool = False) -> None:
        self.strict_mode = strict_mode
        self._lock = threading.Lock()
        self._total_scanned: int = 0
        self._total_flagged: int = 0
        self._flags_by_type: Dict[str, int] = {}

    def scan(self, text: str) -> SecurityScanResult:
        if not text or not isinstance(text, str):
            return SecurityScanResult(is_safe=True, risk_level="LOW", sanitized_text="")

        normalized = text.strip()
        with self._lock:
            self._total_scanned += 1

        for pattern, tag in INJECTION_SIGNATURES:
            match = re.search(pattern, normalized)
            if match:
                with self._lock:
                    self._total_flagged += 1
                    self._flags_by_type[tag] = self._flags_by_type.get(tag, 0) + 1

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

    def get_metrics(self) -> Dict[str, Any]:
        """Returns real-time threat telemetry for security audits."""
        with self._lock:
            return {
                "total_scanned": self._total_scanned,
                "total_flagged": self._total_flagged,
                "block_rate_percent": round((self._total_flagged / self._total_scanned * 100), 2) if self._total_scanned > 0 else 0.0,
                "flags_by_type": dict(self._flags_by_type),
            }


# Global singleton instance
prompt_guard = PromptGuard()
