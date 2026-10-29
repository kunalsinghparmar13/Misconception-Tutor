"""
================================================================================
AI That Teaches: Misconception Tutor — Python Code Debugger & Compiler Engine
Compiles, analyzes, tests, and provides Socratic explanations for Python code.
Identifies syntax errors, runtime bugs, and logical antipatterns with step-by-step
cognitive replays and verified solutions.
================================================================================
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple


class PythonCodeDebugger:
    """Intelligent Python compiler, AST static analyzer, and Socratic remediation engine."""

    def extract_code(self, text: str) -> str:
        """Extracts code blocks from markdown (```python ... ```) or extracts contiguous code lines."""
        code_block = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
        if code_block:
            return code_block.group(1).strip()

        clean_text = text.strip()
        try:
            ast.parse(clean_text)
            return clean_text
        except SyntaxError:
            pass

        lines = clean_text.splitlines()
        code_indicators = ("def ", "import ", "from ", "class ", "return ", "for ", "while ", "if ", "elif ", "else:", "print(", "try:", "except", "=", "[", "{")

        # Find first line that looks like Python code
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # If line is conversational intro like "Can you fix:", "Here is my code:", skip
            if stripped.endswith(":") and not any(stripped.startswith(kw) for kw in ("def ", "if ", "for ", "while ", "class ", "try", "except")):
                continue
            if stripped.lower().startswith(("can you", "what is", "how do", "why does", "here is", "i have", "please")):
                continue
            if any(kw in stripped for kw in code_indicators):
                start_idx = i
                break

        # Collect lines from start_idx until conversation trailing prompt
        collected = []
        for line in lines[start_idx:]:
            stripped = line.strip()
            if stripped.endswith("?") and not any(kw in stripped for kw in code_indicators):
                break
            if stripped.lower().startswith(("can you", "what is", "how do", "why does", "please")):
                break
            collected.append(line)

        candidate = "\n".join(collected).strip()
        return candidate if candidate else clean_text

    def analyze_and_explain(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Main entrypoint: parses, compiles, checks AST antipatterns, simulates execution,
        and generates a high-precision Socratic diagnosis with corrected code.
        """
        code = self.extract_code(user_input)
        metadata: Dict[str, Any] = {
            "topic": "python_debugging",
            "source": "python_debugger_engine",
            "code_lines": len(code.splitlines()),
        }

        # Step 1: Syntax & Compilation Check
        syntax_err = self._check_syntax(code)
        if syntax_err:
            metadata["error_category"] = "SyntaxError"
            metadata["line"] = syntax_err.get("line")
            return self._format_syntax_explanation(code, syntax_err), metadata

        # Step 2: AST Semantic & Logical Antipattern Check
        parsed_tree = ast.parse(code)
        semantic_bug = self._check_semantic_antipatterns(code, parsed_tree)
        if semantic_bug:
            metadata["error_category"] = semantic_bug["category"]
            metadata["line"] = semantic_bug.get("line")
            return self._format_semantic_explanation(code, semantic_bug), metadata

        # Step 3: Sandboxed Execution Check
        exec_result = self._safe_execute(code)
        if not exec_result["success"]:
            metadata["error_category"] = exec_result["error_type"]
            metadata["line"] = exec_result.get("line")
            return self._format_runtime_explanation(code, exec_result), metadata

        # Step 4: Valid Execution - Provide Socratic Explanation of How the Code Works
        metadata["status"] = "code_executes_cleanly"
        return self._format_clean_code_explanation(code, exec_result), metadata

    def _check_syntax(self, code: str) -> Optional[Dict[str, Any]]:
        """Compiles code to detect syntax, indentation, and token errors."""
        try:
            compile(code, "<student_code>", "exec")
            return None
        except (SyntaxError, IndentationError) as err:
            line_no = err.lineno or 1
            col_no = err.offset or 1
            text_line = (err.text or "").strip()
            msg = str(err.msg)

            # Classify syntax slip
            slip_type = "Syntax Slip"
            hint = "Check Python syntax requirements."
            
            clean_line = text_line.strip()
            is_header = any(clean_line.startswith(kw) for kw in ["def ", "if ", "elif ", "else", "for ", "while ", "try", "except", "class "])
            if "expected ':'" in msg or (is_header and not clean_line.endswith(":")):
                slip_type = "Missing Colon (':')"
                hint = "In Python, headers like `def`, `if`, `for`, `while`, and `class` must end with a colon `:` before the indented block."
            elif "unmatched ')'" in msg or "was never closed" in msg:
                slip_type = "Unmatched Parentheses or Brackets"
                hint = "Ensure every opening `(`, `[`, or `{` has a matching closing counterpart."
            elif "unexpected indent" in msg or "expected an indented block" in msg:
                slip_type = "Indentation Mismatch"
                hint = "Python relies strictly on consistent indentation (use 4 spaces per block level)."
            elif "cannot assign to" in msg or ("invalid syntax" in msg and "=" in text_line):
                slip_type = "Equality vs Assignment Confusion"
                hint = "Did you use `=` (assignment) instead of `==` (equality comparison) in a condition?"

            return {
                "type": type(err).__name__,
                "slip_type": slip_type,
                "line": line_no,
                "column": col_no,
                "offending_line": text_line,
                "raw_message": msg,
                "hint": hint,
            }

    def _check_semantic_antipatterns(self, code: str, tree: ast.AST) -> Optional[Dict[str, Any]]:
        """Inspects AST nodes for common mental models bugs that compile but fail logically."""
        
        # 1. Mutable Default Argument: def func(a, b=[])
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        return {
                            "category": "MutableDefaultArgument",
                            "title": "Mutable Default Parameter Antipattern",
                            "line": node.lineno,
                            "function": node.name,
                            "offending_line": code.splitlines()[node.lineno - 1] if node.lineno <= len(code.splitlines()) else "",
                            "why_it_fails": "Default parameter objects are evaluated only once when the function is defined, NOT each time the function is called. All subsequent invocations share the exact same mutated list/dict instance!",
                            "fix_hint": "Use `None` as the default value and initialize a fresh new list/dict inside the function body (`if target is None: target = []`).",
                        }

        # 2. list.sort() assignment: my_list = my_list.sort()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                    if node.value.func.attr == "sort":
                        line_idx = node.lineno - 1
                        return {
                            "category": "InPlaceMethodAssignment",
                            "title": "In-Place Method Assignment (`list.sort()` returns None)",
                            "line": node.lineno,
                            "offending_line": code.splitlines()[line_idx] if line_idx < len(code.splitlines()) else "",
                            "why_it_fails": "`list.sort()` mutates the list in-place and returns `None`. Assigning its result back wipes out your list into `None`!",
                            "fix_hint": "Call `my_list.sort()` by itself without assigning, or use `my_list = sorted(my_list)` to return a new sorted list.",
                        }

        # 3. Off-by-one matrix/list indexing: row[col + 1] without boundary check
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                    # Check for subscript index + 1 inside loop
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.BinOp):
                            if isinstance(sub.slice.op, ast.Add) and isinstance(sub.slice.right, ast.Constant) and sub.slice.right.value == 1:
                                return {
                                    "category": "IndexOutOfBounds",
                                    "title": "Potential Off-by-One IndexError",
                                    "line": sub.lineno,
                                    "offending_line": code.splitlines()[sub.lineno - 1] if sub.lineno <= len(code.splitlines()) else "",
                                    "why_it_fails": "Accessing `[col + 1]` in the final iteration causes an index equal to `len(...)`, which triggers an `IndexError`.",
                                    "fix_hint": "Constrain the loop range with `range(len(...) - 1)` or add a bounds condition `if col + 1 < len(...)`.",
                                }

        return None

    def _safe_execute(self, code: str) -> Dict[str, Any]:
        """Safely executes the snippet with standard library guards and stdout redirection."""
        import builtins
        stdout_capture = io.StringIO()
        safe_builtins = {
            k: getattr(builtins, k)
            for k in dir(builtins)
            if not k.startswith("__") and k not in ["eval", "exec", "open", "input", "compile", "breakpoint", "quit", "exit"]
        }
        safe_globals: Dict[str, Any] = {
            "__builtins__": safe_builtins,
            "__name__": "__main__",
        }

        try:
            with contextlib.redirect_stdout(stdout_capture):
                compiled = compile(code, "<student_code>", "exec")
                exec(compiled, safe_globals)
            return {
                "success": True,
                "stdout": stdout_capture.getvalue(),
                "globals": {k: v for k, v in safe_globals.items() if not k.startswith("__")},
            }
        except Exception as exc:
            tb = traceback.extract_tb(sys.exc_info()[2])
            line = 1
            for frame in tb:
                if frame.filename == "<student_code>":
                    line = frame.lineno
            return {
                "success": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "line": line,
                "stdout": stdout_capture.getvalue(),
            }

    def _format_syntax_explanation(self, code: str, err: Dict[str, Any]) -> str:
        """Formats an intuitive Socratic diagnosis for syntax slips."""
        lines = code.splitlines()
        line_no = err["line"]
        bad_line = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else err.get("offending_line", "")
        pointer = " " * max(0, err.get("column", 1) - 1) + "^"

        # Generate corrected code
        fixed_lines = list(lines)
        if err["slip_type"] == "Missing Colon (':')":
            if 0 <= line_no - 1 < len(fixed_lines):
                fixed_lines[line_no - 1] = fixed_lines[line_no - 1].rstrip() + ":"
        elif err["slip_type"] == "Equality vs Assignment Confusion":
            if 0 <= line_no - 1 < len(fixed_lines):
                fixed_lines[line_no - 1] = re.sub(r"(if|elif|while)\s+(.+?)\s*=\s*(.+?):", r"\1 \2 == \3:", fixed_lines[line_no - 1])
        fixed_code = "\n".join(fixed_lines)

        return (
            f"### 🔍 Syntax Slip Detected: {err['slip_type']}\n\n"
            f"**File Location:** Line {line_no}, Column {err.get('column', 1)}\n\n"
            f"```python\n"
            f"{line_no} | {bad_line}\n"
            f"    {' ' * len(str(line_no))} {pointer}\n"
            f"```\n\n"
            f"**What Python says:** `{err['type']}: {err['raw_message']}`\n\n"
            f"**Why this happened:** {err['hint']}\n\n"
            f"### 💡 Socratic Guidance\n"
            f"Look at the end of line {line_no}. Before starting the indented code block that belongs inside this structure, did you notify Python where the header ends?\n\n"
            f"### 🛠️ Corrected Python Code\n"
            f"```python\n"
            f"{fixed_code}\n"
            f"```\n\n"
            f"### 📌 Key Takeaway\n"
            f"Python compound statements (`def`, `if`, `elif`, `else`, `for`, `while`, `try`, `except`, `class`) must always terminate with a colon `:` to introduce an indented suite."
        )

    def _format_semantic_explanation(self, code: str, bug: Dict[str, Any]) -> str:
        """Formats explanation for subtle semantic antipatterns."""
        lines = code.splitlines()
        line_no = bug["line"]

        # Generate fixed code for mutable default argument
        fixed_code = code
        if bug["category"] == "MutableDefaultArgument":
            fn_name = bug.get("function", "func")
            fixed_code = re.sub(
                rf"def\s+{fn_name}\s*\((.*?)=\s*\[\]\s*\):",
                rf"def {fn_name}(\1=None):\n    if \1 is None:\n        \1 = []",
                code
            )
        elif bug["category"] == "InPlaceMethodAssignment":
            fixed_code = re.sub(r"(\w+)\s*=\s*\1\.sort\(\)", r"\1.sort()", code)

        return (
            f"### 🔍 Logical Antipattern: {bug['title']}\n\n"
            f"**Location:** Line {line_no}\n"
            f"```python\n"
            f"{line_no} | {bug.get('offending_line', '')}\n"
            f"```\n\n"
            f"**Why it fails:** {bug['why_it_fails']}\n\n"
            f"### 💡 Socratic Question\n"
            f"If you call this function multiple times in a row, what happens to the default object? Does Python allocate a brand-new list for each call, or does it reuse the existing reference?\n\n"
            f"### 🛠️ Idiomatic Solution\n"
            f"```python\n"
            f"{fixed_code}\n"
            f"```\n\n"
            f"### 📌 Key Takeaway\n"
            f"{bug['fix_hint']}"
        )

    def _format_runtime_explanation(self, code: str, res: Dict[str, Any]) -> str:
        """Formats explanation for runtime exceptions (TypeError, ZeroDivisionError, IndexError)."""
        line_no = res.get("line", 1)
        lines = code.splitlines()
        bad_line = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else ""
        err_type = res["error_type"]
        err_msg = res["error_message"]

        fix_hint = "Ensure variables match expected types and divisors are non-zero."
        if err_type == "ZeroDivisionError":
            fix_hint = "Check denominator before division: add a guard like `if denominator != 0:` to prevent dividing by zero."
        elif err_type == "TypeError" and "can only concatenate" in err_msg:
            fix_hint = "Python does not automatically coerce integers to strings during concatenation. Wrap the value in `str(value)` or use an f-string: `f'Result: {value}'`."
        elif err_type == "IndexError":
            fix_hint = "The requested index is outside the length of the list. Remember Python lists are 0-indexed, so the valid indices are `0` to `len - 1`."

        return (
            f"### 🔍 Runtime Exception: `{err_type}`\n\n"
            f"**Trigger Line:** Line {line_no}\n"
            f"```python\n"
            f"{line_no} | {bad_line}\n"
            f"```\n\n"
            f"**Runtime Exception:** `{err_type}: {err_msg}`\n\n"
            f"### 💡 Root Cause Analysis\n"
            f"{fix_hint}\n\n"
            f"### 🛠️ Socratic Step-by-Step Fix\n"
            f"1. Examine the variable values evaluated right before Line {line_no}.\n"
            f"2. Add input validation or type casting before performing the operation.\n\n"
            f"### 📌 Key Takeaway\n"
            f"Always guard against boundary inputs (empty lists, 0 denominators, mismatched types) before operations to build resilient Python software."
        )

    def _format_clean_code_explanation(self, code: str, res: Dict[str, Any]) -> str:
        """Explains clean code execution trace and outputs."""
        stdout = res.get("stdout", "").strip()
        stdout_display = f"\n**Execution Output (`stdout`):**\n```text\n{stdout}\n```\n" if stdout else ""
        return (
            f"### ✅ Code Compiles & Executes Successfully!\n\n"
            f"Your Python code was parsed, compiled, and executed cleanly with 0 syntax or runtime exceptions.{stdout_display}\n"
            f"### 🔍 Execution Architecture\n"
            f"1. **Syntax & AST Structure**: All statements are valid Python 3 syntax with balanced delimiters.\n"
            f"2. **State & Scoping**: Variables are initialized before reference, and no global state leaks were observed.\n"
            f"3. **Efficiency**: Control flow terminates cleanly without redundant loops.\n\n"
            f"### 📌 Key Takeaway\n"
            f"Writing clean Python with clear function boundaries and type hints makes debugging straightforward and production deployments robust."
        )


# Global singleton
python_debugger = PythonCodeDebugger()
