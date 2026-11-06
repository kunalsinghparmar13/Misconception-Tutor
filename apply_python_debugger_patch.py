"""
One-shot patch: make PythonCodeDebugger._safe_execute use the isolated sandbox.

Run from the repository root:   python apply_python_debugger_patch.py
It is idempotent and refuses to write a file that no longer parses.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TARGET = Path("backend/python_debugger.py")
NEW_METHOD = '''    def _safe_execute(self, code: str) -> Dict[str, Any]:
        """Runs the snippet in an isolated, resource-limited child process."""
        return run_student_code(code)

'''


def main() -> int:
    if not TARGET.exists():
        print(f"{TARGET} not found - run this from the repository root.")
        return 1
    src = TARGET.read_text(encoding="utf-8")
    if "run_student_code" in src:
        print("Already patched.")
        return 0

    pattern = re.compile(
        r"    def _safe_execute\(self, code: str\).*?(?=    def _format_syntax_explanation)",
        re.DOTALL,
    )
    if not pattern.search(src):
        print("Could not find _safe_execute; patch manually (see backend/sandbox.py).")
        return 1
    src = pattern.sub(lambda _m: NEW_METHOD, src, count=1)

    # Drop imports that only the old in-process executor used.
    for mod in ("contextlib", "io", "sys", "traceback"):
        body = re.sub(rf"^import {mod}\n", "", src, flags=re.MULTILINE)
        if not re.search(rf"\b{mod}\.", body):
            src = body

    src = re.sub(
        r"^(from typing import [^\n]+\n)",
        r"\1\nfrom backend.sandbox import run_student_code\n",
        src,
        count=1,
        flags=re.MULTILINE,
    )

    ast.parse(src)  # refuse to write broken code
    TARGET.write_text(src, encoding="utf-8")
    print("Patched backend/python_debugger.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
