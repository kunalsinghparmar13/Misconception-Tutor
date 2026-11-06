"""Tolerant parsers for model output (a 4B model does not follow formats perfectly)."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Sequence, Tuple

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.DOTALL)


def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """All fenced blocks as ``(language, code)``; an unterminated final fence is accepted."""
    blocks = [(m.group(1).lower(), m.group(2).strip("\n")) for m in _FENCE.finditer(text)]
    if not blocks:
        tail = re.search(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*)$", text, re.DOTALL)
        if tail:
            blocks.append((tail.group(1).lower(), tail.group(2).strip("\n")))
    return blocks


def first_python_block(text: str) -> Optional[str]:
    blocks = extract_code_blocks(text)
    for lang, code in blocks:
        if lang in {"python", "py", "python3"} and code.strip():
            return code
    for lang, code in blocks:
        if not lang and code.strip():
            return code
    return None


def strip_code_blocks(text: str) -> str:
    return _FENCE.sub("", text).strip()


def _heading_regex(aliases: Sequence[str]) -> str:
    return "|".join(re.escape(a) for a in aliases)


def split_sections(text: str, headings: Dict[str, Sequence[str]]) -> Dict[str, str]:
    """Split ``text`` on heading lines such as ``What went wrong:`` / ``### Why this happens``.

    ``headings`` maps a canonical key to accepted spellings. Text before the first heading is
    stored under ``"_preamble"``. Content inside code fences is never treated as a heading.
    """
    patterns = {
        key: re.compile(
            r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:\d+[.)]\s*)?(?:" + _heading_regex(aliases) + r")\s*(?:\*\*|__)?\s*[:\-–—]?\s*(?:\*\*|__)?\s*(.*)$",
            re.IGNORECASE,
        )
        for key, aliases in headings.items()
    }
    sections: Dict[str, List[str]] = {"_preamble": []}
    current = "_preamble"
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            sections.setdefault(current, []).append(line)
            continue
        matched = None
        if not in_fence:
            for key, pattern in patterns.items():
                m = pattern.match(line)
                if m:
                    matched = (key, m.group(1))
                    break
        if matched:
            current = matched[0]
            sections.setdefault(current, [])
            if matched[1].strip():
                sections[current].append(matched[1].strip())
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def find_field(text: str, labels: Sequence[str]) -> Optional[str]:
    """Value on the first line that starts with one of ``labels`` (``Final answer: 5/12``)."""
    pattern = re.compile(
        r"^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:" + _heading_regex(labels) + r")\s*(?:\*\*|__)?\s*[:=\-–—]\s*(?:\*\*|__)?\s*(.+?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return None
    value = m.group(1).strip().strip("*_`").strip()
    return value or None


def parse_json_loose(text: str) -> Optional[object]:
    """Parse JSON that may be wrapped in prose or a code fence."""
    candidates = [text]
    for _, code in extract_code_blocks(text):
        candidates.append(code)
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if m:
        candidates.append(m.group(1))
    for cand in candidates:
        try:
            return json.loads(cand)
        except (ValueError, TypeError):
            continue
    return None


_PROBLEM_SPLIT = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:problem|question|exercise|practice)\s*#?\s*(\d+)\s*(?:\*\*|__)?\s*[:.)\-–—]?\s*(?:\*\*|__)?\s*$|"
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:problem|exercise|practice)\s*#?\s*(\d+)\s*(?:\*\*|__)?\s*[:.)\-–—]\s*(?:\*\*|__)?\s*(\S.*)$",
    re.IGNORECASE,
)
_FIELD = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*|__)?\s*(question|task|prompt|answer|final answer|solution|why|explanation|hint|"
    r"buggy code|starter code|broken code|code|correct code|fixed code|corrected code|expected output)"
    r"\s*(?:\*\*|__)?\s*[:\-–—]\s*(?:\*\*|__)?\s*(.*)$",
    re.IGNORECASE,
)
_FIELD_KEYS = {
    "question": "question", "task": "question", "prompt": "question",
    "answer": "answer", "final answer": "answer", "solution": "answer",
    "why": "why", "explanation": "why", "hint": "hint",
    "buggy code": "code", "starter code": "code", "broken code": "code", "code": "code",
    "correct code": "correct_code", "fixed code": "correct_code", "corrected code": "correct_code",
    "expected output": "expected_output",
}


def parse_practice(text: str) -> List[Dict[str, str]]:
    """Parse ``Problem N`` blocks into dicts with question/answer/code/correct_code/why/hint."""
    blocks: List[List[str]] = []
    current: Optional[List[str]] = None
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence:
            m = _PROBLEM_SPLIT.match(line)
            if m:
                current = []
                blocks.append(current)
                inline = m.group(3)
                if inline:
                    current.append(f"Question: {inline}")
                continue
        if current is not None:
            current.append(line)

    items: List[Dict[str, str]] = []
    for lines in blocks:
        item: Dict[str, str] = {}
        field: Optional[str] = None
        buf: List[str] = []
        in_fence = False
        fence_buf: List[str] = []

        def flush() -> None:
            nonlocal buf, field
            if field and buf:
                value = "\n".join(buf).strip()
                if value and field not in item:
                    item[field] = value
            buf = []

        pending_code_label: Optional[str] = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_fence:
                    in_fence = True
                    fence_buf = []
                    continue
                in_fence = False
                code = "\n".join(fence_buf).strip("\n")
                key = pending_code_label or ("code" if "code" not in item else "correct_code")
                if code.strip() and key not in item:
                    item[key] = code
                pending_code_label = None
                continue
            if in_fence:
                fence_buf.append(line)
                continue
            m = _FIELD.match(line)
            if m:
                flush()
                key = _FIELD_KEYS[m.group(1).lower()]
                rest = m.group(2).strip()
                if key in {"code", "correct_code"}:
                    pending_code_label = key
                    field = None
                    if rest:
                        item.setdefault(key, rest)
                else:
                    field = key
                    buf = [rest] if rest else []
            elif field:
                buf.append(line)
        flush()
        if in_fence and fence_buf:  # unterminated fence at the end of the block
            key = pending_code_label or ("code" if "code" not in item else "correct_code")
            item.setdefault(key, "\n".join(fence_buf).strip("\n"))
        if item.get("question") or item.get("code"):
            items.append(item)
    return items
