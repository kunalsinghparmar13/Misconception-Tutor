"""
Process-isolated execution of untrusted student Python snippets.

The snippet runs in a separate interpreter (`python -I`) with:
  * an empty environment (no secrets inherited) and a throwaway working directory
  * CPU, memory, file-size and process-count limits (POSIX `resource` limits)
  * a hard wall-clock timeout enforced by the parent
  * output captured to size-limited temp files, then truncated

The restricted builtins inside the child are a convenience, NOT the security
boundary. The boundary is the process, its limits and the container around it.
Run the app as a non-root user with no outbound network where possible.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import tempfile
from typing import Any, Dict

WALL_TIMEOUT_SECONDS = 3
MAX_OUTPUT_BYTES = 4000

_BOOTSTRAP = r'''
import builtins
import sys

try:
    import resource
    for _name, _soft, _hard in (
        ("RLIMIT_CPU", 2, 3),
        ("RLIMIT_AS", 256 * 1024 * 1024, 256 * 1024 * 1024),
        ("RLIMIT_FSIZE", 1024 * 1024, 1024 * 1024),
        ("RLIMIT_NPROC", 0, 0),
    ):
        try:
            resource.setrlimit(getattr(resource, _name), (_soft, _hard))
        except (ValueError, OSError, AttributeError):
            pass
except ImportError:
    pass

_ALLOWED = {
    "math", "random", "statistics", "itertools", "functools", "collections",
    "string", "re", "json", "datetime", "fractions", "decimal", "typing",
    "dataclasses", "operator",
}
_real_import = builtins.__import__


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level == 0 and name.split(".")[0] in _ALLOWED:
        return _real_import(name, globals, locals, fromlist, level)
    raise ImportError("import of '%s' is not allowed in the sandbox" % name)


_BLOCKED = {
    "eval", "exec", "open", "input", "compile", "breakpoint",
    "quit", "exit", "help", "memoryview",
}
_safe = {k: getattr(builtins, k) for k in dir(builtins) if k not in _BLOCKED}
_safe["__import__"] = _guarded_import

_source = sys.stdin.read()
_code = compile(_source, "<student_code>", "exec")
exec(_code, {"__builtins__": _safe, "__name__": "__main__"})
'''

_LINE_RE = re.compile(r'File "<student_code>", line (\d+)')


def _failure(error_type: str, message: str, stdout: str, line: int = 1) -> Dict[str, Any]:
    return {
        "success": False,
        "error_type": error_type,
        "error_message": message,
        "line": line,
        "stdout": stdout,
    }


def run_student_code(code: str) -> Dict[str, Any]:
    """Run `code` in an isolated child process and return a result dict.

    Success:  {"success": True, "stdout": str, "globals": {}}
    Failure:  {"success": False, "error_type": str, "error_message": str,
               "line": int, "stdout": str}
    """
    env: Dict[str, str] = {}
    if os.name == "nt":  # Python will not start on Windows without this
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    timed_out = False
    with tempfile.TemporaryDirectory() as workdir, \
            tempfile.TemporaryFile() as out_file, \
            tempfile.TemporaryFile() as err_file:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", _BOOTSTRAP],
                input=code.encode("utf-8"),
                stdout=out_file,
                stderr=err_file,
                cwd=workdir,
                env=env,
                timeout=WALL_TIMEOUT_SECONDS,
                check=False,
            )
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = -1

        out_file.seek(0)
        err_file.seek(0)
        stdout = out_file.read(MAX_OUTPUT_BYTES).decode("utf-8", errors="replace")
        stderr = err_file.read(MAX_OUTPUT_BYTES * 4).decode("utf-8", errors="replace")

    timeout_msg = (
        f"Your code ran for more than {WALL_TIMEOUT_SECONDS} seconds. "
        "Look for an infinite loop or a very slow calculation."
    )
    if timed_out:
        return _failure("TimeoutError", timeout_msg, stdout)

    if returncode == 0:
        return {"success": True, "stdout": stdout, "globals": {}}

    if returncode < 0:
        sig = -returncode
        if sig == getattr(signal, "SIGXCPU", -999):
            return _failure("TimeoutError", timeout_msg, stdout)
        if sig == getattr(signal, "SIGXFSZ", -999):
            return _failure("OutputLimitExceeded", "Your code produced too much output.", stdout)
        return _failure("ResourceLimitExceeded", "Your code used more resources than allowed.", stdout)

    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    last = lines[-1] if lines else "RuntimeError: execution failed"
    error_type, _, message = last.partition(": ")
    if error_type == "OSError" and "too large" in message.lower():
        return _failure("OutputLimitExceeded", "Your code produced too much output.", stdout)
    found = _LINE_RE.findall(stderr)
    line = int(found[-1]) if found else 1
    return _failure(error_type.strip(), message.strip(), stdout, line)
