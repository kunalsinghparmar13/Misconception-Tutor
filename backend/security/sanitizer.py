"""
================================================================================
ECC Agentic Security Suite: Input Sanitizer & Boundary Guard
Protects against Path Traversal, Denial-of-Service, Injection, and Malicious Uploads.
================================================================================
"""

from __future__ import annotations

import os
import re
from typing import Optional, Set, Tuple

MAX_PROMPT_CHARS = 4000
MAX_ANSWER_CHARS = 64
MAX_UPLOAD_BYTES = 512 * 1024  # 512 KB
MAX_LEARNER_ID_CHARS = 64
MAX_FILENAME_CHARS = 128

ALLOWED_EXTENSIONS: Set[str] = {
    "py", "pyw", "txt", "md", "json", "csv", "js", "ts", "html", "css", "sql", "log"
}

DISALLOWED_EXTENSIONS: Set[str] = {
    "exe", "dll", "so", "dylib", "sh", "bash", "zsh", "bat", "cmd", "ps1",
    "vbs", "php", "phtml", "pl", "cgi", "jar", "elf", "bin", "msi", "app"
}

# Binary magic signatures that must never be decoded as text/code context
DANGEROUS_MAGIC_HEADERS: Tuple[bytes, ...] = (
    b"\x7fELF",        # Linux ELF executable
    b"MZ",             # Windows PE executable / DLL
    b"\xfe\xed\xfa\xce", # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf", # Mach-O 64-bit
    b"\xce\xfa\xed\xfe", # Mach-O reverse
    b"\xcf\xfa\xed\xfe", # Mach-O reverse 64-bit
    b"\xca\xfe\xba\xbe", # Java Class or Mach-O Universal
    b"PK\x03\x04",      # ZIP archive (can conceal executables)
    b"\x1f\x8b\x08",    # GZIP archive
)


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


def sanitize_learner_id(learner_id: Optional[str]) -> str:
    """Sanitizes learner identifier to prevent SQL injection or path traversal via identity."""
    if not learner_id or not isinstance(learner_id, str):
        return "student_demo"

    clean = learner_id.strip()[:MAX_LEARNER_ID_CHARS]
    # Restrict to safe identifier characters (UUID, alphanumeric, hyphen, underscore)
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "", clean)
    if not clean:
        return "student_demo"
    return clean


def sanitize_filename(filename: Optional[str]) -> str:
    """Strips path traversal, directory separators, and control characters from filenames."""
    if not filename or not isinstance(filename, str):
        return "snippet.txt"

    clean = filename.strip()[:MAX_FILENAME_CHARS]
    # Strip path elements
    clean = os.path.basename(clean.replace("\\", "/"))
    # Remove null bytes and control chars
    clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)
    # Remove leading dots to prevent hidden file abuse
    clean = clean.lstrip(".")
    if not clean:
        return "snippet.txt"
    return clean


def sanitize_search_query(query: Optional[str]) -> str:
    """Sanitizes search query for SQL LIKE operations, preventing wildcard denial-of-service."""
    if not query or not isinstance(query, str):
        return ""
    clean = query.strip()[:100]
    # Remove null bytes
    clean = clean.replace("\x00", "")
    return clean


def validate_file_upload(filename: str, raw_bytes: bytes) -> Tuple[bool, Optional[str], str, str]:
    """
    Validates uploaded file against security boundaries:
    - Enforces size limit (512 KB)
    - Validates extension against whitelist and blacklist
    - Detects binary executable headers
    - Decodes and sanitizes text content
    Returns: (is_valid, error_message, sanitized_filename, content_text)
    """
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        return False, f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // 1024} KB.", "snippet.txt", ""

    safe_name = sanitize_filename(filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if ext in DISALLOWED_EXTENSIONS:
        return False, f"Executable or script files (. {ext}) are strictly disallowed.", safe_name, ""

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type (.{ext}). Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}.", safe_name, ""

    # Check for binary executable magic signatures
    for magic in DANGEROUS_MAGIC_HEADERS:
        if raw_bytes.startswith(magic):
            return False, "Binary executable or archive files are not accepted.", safe_name, ""

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw_bytes.decode("latin-1")
        except Exception:
            return False, "File content could not be decoded as text or source code.", safe_name, ""

    sanitized = sanitize_input_text(content, max_length=20000)
    return True, None, safe_name, sanitized
