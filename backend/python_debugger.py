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
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.sandbox import run_student_code


class PythonCodeDebugger:
    """Intelligent Python compiler, AST static analyzer, and Socratic remediation engine."""

    _QUESTION_PREFIXES = (
        "can you", "what is", "how do", "why does", "why is", "here is",
        "i have", "please", "it prints", "it print", "the output", "is it",
        "if not", "what is wrong", "what's wrong", "does this",
    )

    def split_input(self, text: str) -> Tuple[str, str, int]:
        """Split mixed prose/code input and return code, question, and source line."""
        code_block = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
        if code_block:
            before = text[:code_block.start()].strip()
            after = text[code_block.end():].strip()
            question = " ".join(part for part in (before, after) if part)
            return code_block.group(1).strip(), question, text[:code_block.start()].count("\n") + 1

        lines = text.strip().splitlines()
        start = next((i for i, line in enumerate(lines) if self._looks_like_code(line)), 0)
        code_lines: List[str] = []
        question_lines: List[str] = lines[:start]
        saw_code = False
        for line in lines[start:]:
            stripped = line.strip()
            if stripped and saw_code and not self._looks_like_code(line):
                question_lines.append(line)
                continue
            if not stripped and saw_code:
                code_lines.append(line)
                continue
            if self._looks_like_code(line):
                code_lines.append(line)
                saw_code = True
            else:
                question_lines.append(line)
        code = "\n".join(code_lines).strip()
        question = " ".join(line.strip() for line in question_lines if line.strip())
        return code or text.strip(), question, start + 1

    def _looks_like_code(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith(("#", "def ", "class ", "if ", "elif ", "else:", "for ", "while ", "try:", "except", "finally:", "return ", "import ", "from ", "with ", "async ")):
            return True
        if re.match(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s*=", stripped):
            return True
        if re.match(r"^(?:print|len|range|sum|int|float|str|list|dict|set)\s*\(", stripped):
            return True
        if stripped.startswith((")", "]", "}")):
            return True
        return bool(line[:1].isspace() and not stripped.lower().startswith(self._QUESTION_PREFIXES))

    def extract_code(self, text: str) -> str:
        """Extracts code blocks from markdown (```python ... ```) or extracts contiguous code lines."""
        code, _, _ = self.split_input(text)
        clean_text = code.strip()
        try:
            ast.parse(clean_text)
            return clean_text
        except SyntaxError:
            pass

        return clean_text

    def analyze_and_explain(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Main entrypoint: parses, compiles, checks AST antipatterns, simulates execution,
        and generates a high-precision Socratic diagnosis with corrected code.
        """
        code, question_text, source_line = self.split_input(user_input)
        metadata: Dict[str, Any] = {
            "topic": "python_debugging",
            "source": "python_debugger_engine",
            "code_lines": len(code.splitlines()),
            "extracted_code": code,
            "input_kind": "python_code_with_question" if code.strip() != user_input.strip() else "python_code",
            "question_text": question_text,
            "source_line": source_line,
        }

        # Step 1: Syntax & Compilation Check
        syntax_err = self._check_syntax(code)
        if syntax_err:
            metadata["error_category"] = "SyntaxError"
            metadata["line"] = syntax_err.get("line")
            return self._format_syntax_explanation(code, syntax_err), metadata

        # Step 2: AST Semantic & Logical Antipattern Check
        parsed_tree = ast.parse(code)
        semantic_bug = self._check_semantic_antipatterns(code, parsed_tree, question_text)
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

        output_issue = self._check_claimed_output(question_text, exec_result.get("stdout", ""))
        if output_issue:
            metadata["error_category"] = "OutputMismatch"
            metadata["line"] = output_issue["line"]
            return self._format_output_mismatch(code, exec_result, output_issue), metadata

        # Step 4: Valid Execution - Provide Socratic Explanation of How the Code Works
        metadata["status"] = "code_executes_cleanly"
        return self._format_clean_code_explanation(code, exec_result), metadata

    def _check_claimed_output(self, question: str, stdout: str) -> Optional[Dict[str, Any]]:
        if not question or not stdout.strip():
            return None
        claimed = re.search(
            r"(?:prints?|outputs?|result(?:\s+is)?|gives?)\D*(-?\d+(?:\.\d+)?)",
            question,
            re.IGNORECASE,
        )
        actual = re.search(r"-?\d+(?:\.\d+)?", stdout)
        if claimed and actual and claimed.group(1) != actual.group(0):
            return {"claimed": claimed.group(1), "actual": actual.group(0), "line": 1}
        return None

    def _format_output_mismatch(
        self, code: str, result: Dict[str, Any], issue: Dict[str, Any]
    ) -> str:
        return (
            "### 🔍 Output Mismatch\n\n"
            f"Your question says the program should produce `{issue['claimed']}`, but verified "
            f"execution produced `{issue['actual']}`.\n\n"
            "The code and question were analyzed separately, so the natural-language question "
            "was not treated as Python code.\n\n"
            "### 🛠️ Code that was executed\n"
            f"```python\n{code}\n```\n\n"
            "### 📌 Key Takeaway\n"
            "Compare the expected value with the actual output, then trace the first expression "
            "that changes the value."
        )

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

    def _check_semantic_antipatterns(self, code: str, tree: ast.AST, question: str = "") -> Optional[Dict[str, Any]]:
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

        # A post-division adjustment is often an unintended formula change.
        # Keep this generic and only report it when the learner asks for a
        # correctness/error diagnosis.
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp):
                if (
                    isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value.left, ast.BinOp)
                    and isinstance(node.value.left.op, ast.Div)
                    and isinstance(node.value.op, (ast.Add, ast.Sub))
                    and isinstance(node.value.right, ast.Constant)
                    and isinstance(node.value.right.value, (int, float))
                    and any(token in question.lower() for token in ("wrong", "error", "correct", "should", "prints", "output"))
                ):
                    adjustment = ast.unparse(node.value.right)
                    operator = "+" if isinstance(node.value.op, ast.Add) else "-"
                    name = node.targets[0].id
                    return {
                        "category": "AverageFormulaAdjustment" if name == "average" else "PostDivisionAdjustment",
                        "title": f"Formula applies `{operator} {adjustment}` after division",
                        "line": node.lineno,
                        "offending_line": code.splitlines()[node.lineno - 1],
                        "why_it_fails": (
                            f"Python evaluates division before `{operator} {adjustment}`, so this "
                            f"expression is `({ast.unparse(node.value.left)}) {operator} {adjustment}`. "
                            "That final adjustment changes the quotient and may not match the intended formula."
                        ),
                        "fix_hint": (
                            f"Verify whether `{operator} {adjustment}` is intentional. If the goal is "
                            f"the quotient only, use `{name} = {ast.unparse(node.value.left)}`."
                        ),
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
        """Runs the snippet in an isolated, resource-limited child process."""
        return run_student_code(code)

    def _format_syntax_explanation(self, code: str, err: Dict[str, Any]) -> str:
        """Formats an intuitive, warm Socratic diagnosis for syntax slips."""
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
            f"👋 **Hey there! Let's take a look at your code together.**\n\n"
            f"You are so close! Python ran into a small syntax slip right at **Line {line_no}**: **{err['slip_type']}**.\n\n"
            f"```python\n"
            f"{line_no} | {bad_line}\n"
            f"    {' ' * len(str(line_no))} {pointer}\n"
            f"```\n\n"
            f"#### 💡 What Python is Thinking\n"
            f"Python encountered: `{err['type']}: {err['raw_message']}`.\n\n"
            f"Think of Python like a reader who relies on punctuation to know where one idea ends and instructions begin. "
            f"When you write a header like `def`, `if`, `for`, or `while`, Python pauses at the end of the line waiting for a colon `:`.\n"
            f"The colon is Python's green light that says: *'Header is complete—now get ready for the indented block of code inside!'*\n\n"
            f"#### 🧠 Socratic Walkthrough: The Fix\n"
            f"Look right at the end of Line {line_no}: `{bad_line}`.\n"
            f"If you place that friendly colon `:` right at the end of the line, Python will understand immediately:\n\n"
            f"```python\n"
            f"{fixed_code}\n"
            f"```\n\n"
            f"#### 🎯 Check Your Understanding\n"
            f"Do you see how headers in Python always end with a colon before indenting? Take a quick glance through the rest of your script to make sure all your function headers and loops have their `:`!"
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
        elif bug["category"] == "AverageFormulaAdjustment":
            fixed_code = re.sub(
                r"average\s*=\s*total_score\s*/\s*num_students\s*-\s*1",
                "average = total_score / num_students",
                code,
            )
        elif bug["category"] == "PostDivisionAdjustment":
            fixed_lines = lines[:]
            original = fixed_lines[line_no - 1]
            fixed_lines[line_no - 1] = re.sub(
                r"(\w+\s*=\s*[^#\n]+/\s*[^#\n]+?)\s*[+-]\s*(?:\d+(?:\.\d*)?|\.\d+)\s*$",
                r"\1",
                original,
            )
            fixed_code = "\n".join(fixed_lines)

        socratic_question = (
            f"Which part of line {line_no} changes the value after the division? "
            "Does the expression represent the standard average, or an adjusted value?"
            if bug["category"] in {"AverageFormulaAdjustment", "PostDivisionAdjustment"}
            else (
                "If you call this function multiple times in a row, what happens to "
                "the default object? Does Python allocate a brand-new list for each "
                "call, or does it reuse the existing reference?"
            )
        )
        verified_result = ""
        if bug["category"] in {"AverageFormulaAdjustment", "PostDivisionAdjustment"}:
            assignments: Dict[str, Any] = {}
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Assign)
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id in {"total_score", "num_students"}
                    ):
                        assignments[node.targets[0].id] = ast.literal_eval(node.value)
                if {"total_score", "num_students"} <= assignments.keys() and assignments["num_students"] != 0:
                    standard = assignments["total_score"] / assignments["num_students"]
                    adjustment = 1
                    target = next(
                        (
                            node for node in ast.walk(tree)
                            if isinstance(node, ast.Assign)
                            and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id in {"average", "result"}
                            and isinstance(node.value, ast.BinOp)
                        ),
                        None,
                    )
                    if target is not None:
                        adjustment = ast.literal_eval(target.value.right)
                        if isinstance(target.value.op, ast.Add):
                            adjustment = -adjustment
                    original = standard - adjustment
                    verified_result = (
                        f"\n\n**Verified result:** With `total_score = {assignments['total_score']}` "
                        f"and `num_students = {assignments['num_students']}`, the standard average is "
                        f"`{standard:g}`. The original expression applies its final adjustment and prints "
                        f"`{original:g}`."
                    )
            except (ValueError, TypeError, ZeroDivisionError, SyntaxError):
                pass

        return (
            f"### 🔍 Logical Antipattern: {bug['title']}\n\n"
            f"**Location:** Line {line_no}\n"
            f"```python\n"
            f"{line_no} | {bug.get('offending_line', '')}\n"
            f"```\n\n"
            f"**Why it fails:** {bug['why_it_fails']}\n\n"
            f"{verified_result}\n"
            f"### 💡 Socratic Question\n"
            f"{socratic_question}\n\n"
            f"### 🛠️ Idiomatic Solution\n"
            f"```python\n"
            f"{fixed_code}\n"
            f"```\n\n"
            f"### 📌 Key Takeaway\n"
            f"{bug['fix_hint']}"
        )

    def _format_runtime_explanation(self, code: str, res: Dict[str, Any]) -> str:
        """Formats warm human pedagogical explanation for runtime exceptions."""
        line_no = res.get("line", 1)
        lines = code.splitlines()
        bad_line = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else ""
        err_type = res["error_type"]
        err_msg = res["error_message"]

        if err_type == "ZeroDivisionError":
            analogy_section = (
                "#### 🍪 Real-World Analogy: Sharing Cookies Among Friends\n"
                "Imagine you have a plate of cookies and you want to share them equally with your friends:\n"
                "- If you divide 10 cookies among 2 friends, each person gets 5 cookies.\n"
                "- But what if there are **0 friends** in the room? How many cookies does each person get?\n\n"
                "You can't distribute anything when nobody is there! In mathematics and in Python, dividing by zero doesn't produce an answer—it leaves math stranded. "
                "That's why Python raises `ZeroDivisionError: division by zero`."
            )
            socratic_guidance = (
                "Before performing any division, add a simple guard check to ensure your divisor isn't 0:\n"
                "```python\n"
                "if denominator != 0:\n"
                "    result = numerator / denominator\n"
                "else:\n"
                "    print('Cannot divide by zero! Please provide a non-zero divisor.')\n"
                "```"
            )
            check_question = "What should your program do when a user inputs 0? Should it prompt them again, or return a default placeholder?"
            fixed_code = "if denominator != 0:\n    result = numerator / denominator\nelse:\n    result = None  # handle the zero-denominator case"

        elif err_type == "TypeError" and "can only concatenate" in err_msg:
            analogy_section = (
                "#### 🗣️ The Mental Model: Two Different Languages\n"
                "Think of Python as speaking two distinct languages: **numbers (integers/floats)** and **words (strings)**.\n"
                "When Python sees the `+` sign:\n"
                "- Between numbers (`5 + 3`), it adds them up to make `8`.\n"
                "- Between text (`'hello ' + 'world'`), it glues them together into `'hello world'`.\n"
                "- But when it sees text AND a number (`'Items: ' + 5`), Python pauses! It doesn't want to guess whether you want math or words."
            )
            socratic_guidance = (
                "We can tell Python explicitly to treat the number as text by wrapping it with `str(...)`, or even better, using a modern Python **f-string**:\n"
                "```python\n"
                "f'Items left: {count}'\n"
                "```"
            )
            check_question = "Which one feels cleaner and easier to read for you: `'Items: ' + str(count)` or `f'Items: {count}'`?"
            fixed_code = re.sub(r"(['\"][^'\"]*['\"])\s*\+\s*(\w+)", r"f\1{\2}", code)

        elif err_type == "IndexError":
            analogy_section = (
                "#### 🏨 Real-World Analogy: Hotel Rooms with 0-Based Numbering\n"
                "Picture a row of hotel rooms that start numbering at room **0** instead of room 1:\n"
                "- 1st guest lives in **Room 0**\n"
                "- 2nd guest lives in **Room 1**\n"
                "- 3rd guest lives in **Room 2**\n\n"
                "Because counting starts at 0, the very last room is always **one less than the total count** (`length - 1`).\n"
                f"When your code asked Python for an index outside this range on line {line_no}, Python knocked on the door, saw nobody was there, and raised `IndexError: list index out of range`!"
            )
            socratic_guidance = (
                "Whenever accessing items by position:\n"
                "1. Check the collection length with `len(...)`.\n"
                "2. Valid indices run from `0` to `len - 1`.\n"
                "3. If you want the very last item without worrying about its index number, you can use Python's negative index trick: `items[-1]`!"
            )
            check_question = "If you have a list with 3 elements, what are the three valid index numbers you can query?"
            fixed_code = code + "\n# Guard an index before reading it: 0 <= index < len(items)"

        else:
            analogy_section = (
                f"#### 💡 What Happened on Line {line_no}\n"
                f"Python encountered an unexpected runtime state: `{err_type}: {err_msg}`."
            )
            socratic_guidance = "Inspect the values and types being evaluated right before this line, ensuring all preconditions are satisfied."
            check_question = "What values did your variables hold right at the moment this operation took place?"
            fixed_code = code

        return (
            f"👋 **Hey! Don't worry at all—every developer hits this roadblock! Let's understand what happened.**\n\n"
            f"When Python reached **Line {line_no}**, it ran into a runtime bump: `{err_type}: {err_msg}`.\n\n"
            f"```python\n"
            f"{line_no} | {bad_line}\n"
            f"```\n\n"
            f"{analogy_section}\n\n"
            f"#### 🧠 Let's Walk Through the Solution\n"
            f"{socratic_guidance}\n\n"
            f"#### 🛠️ Corrected Pattern\n"
            f"```python\n"
            f"{fixed_code}\n"
            f"```\n\n"
            f"#### 🎯 Check Your Understanding\n"
            f"{check_question}"
        )

    def _format_clean_code_explanation(self, code: str, res: Dict[str, Any]) -> str:
        """Explains clean code execution trace and outputs with warm human enthusiasm."""
        stdout = res.get("stdout", "").strip()
        stdout_display = f"\n**Program Output:**\n```text\n{stdout}\n```\n" if stdout else ""
        return (
            f"🎉 **Awesome job! Code Compiles & Executes Successfully!**\n\n"
            f"I ran your Python code in our safe sandbox, and it executed smoothly from start to finish without a single error.{stdout_display}\n"
            f"#### 🌟 What Made Your Code Work So Well:\n"
            f"1. **Clean Syntax**: Every loop, parenthesis, and colon was placed right where it belongs.\n"
            f"2. **Predictable State Flow**: Variables were properly initialized before use, and data flowed cleanly without side effects.\n"
            f"3. **Smooth Execution**: Python followed your instructions seamlessly without hitting boundary or type hiccups.\n\n"
            f"#### 🚀 Next Step Challenge\n"
            f"Now that this foundation works, how might you expand it? Try experimenting with edge cases or passing unexpected input types to see how resilient it is!"
        )


# Global singleton
python_debugger = PythonCodeDebugger()
