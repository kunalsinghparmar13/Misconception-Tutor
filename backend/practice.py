"""Targeted practice generation for math and Python misconceptions."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from backend import backend_code


CODE_PRACTICE: Dict[str, List[Dict[str, str]]] = {
    "SyntaxError": [
        {"prompt": "Add the missing colon so this function runs.", "code": "def greet(name)\n    return f'Hello {name}'"},
        {"prompt": "Fix the missing colon in the conditional.", "code": "score = 72\nif score >= 60\n    print('pass')"},
        {"prompt": "Repair the loop syntax.", "code": "for value in [1, 2, 3]\n    print(value)"},
        {"prompt": "Make this class definition valid Python.", "code": "class Student\n    pass"},
        {"prompt": "Fix the syntax before the indented block.", "code": "try\n    result = 10 / 2\nexcept ZeroDivisionError:\n    result = 0"},
        {"prompt": "Correct the function header.", "code": "def square(number)\n    return number * number"},
    ],
    "IndentationError": [
        {"prompt": "Use consistent indentation for the function body.", "code": "def total(values):\nreturn sum(values)"},
        {"prompt": "Indent the statement inside the conditional.", "code": "if ready:\nprint('start')"},
        {"prompt": "Align both statements inside the loop.", "code": "for item in items:\n    print(item)\n  count += 1"},
        {"prompt": "Indent the exception handler body.", "code": "try:\n    value = int(text)\nexcept ValueError:\nvalue = 0"},
        {"prompt": "Fix the nested block indentation.", "code": "def classify(x):\n    if x > 0:\n    return 'positive'\n    return 'other'"},
        {"prompt": "Make this conditional block consistently indented.", "code": "if active:\n    print('on')\n      print('still on')"},
    ],
    "Equality vs Assignment Confusion": [
        {"prompt": "Use comparison rather than assignment in the condition.", "code": "age = 18\nif age = 18:\n    print('adult')"},
        {"prompt": "Fix the condition so it checks the flag.", "code": "enabled = True\nif enabled = True:\n    print('enabled')"},
        {"prompt": "Correct the loop comparison.", "code": "count = 0\nwhile count = 3:\n    count += 1"},
        {"prompt": "Check whether the value is zero.", "code": "value = 0\nif value = 0:\n    print('zero')"},
        {"prompt": "Use the equality operator in this branch.", "code": "command = 'go'\nif command = 'go':\n    print('run')"},
        {"prompt": "Compare the result instead of assigning it.", "code": "result = 10\nif result = 10:\n    print('correct')"},
    ],
    "MutableDefaultArgument": [
        {"prompt": "Prevent calls from sharing the same list.", "code": "def add_item(item, items=[]):\n    items.append(item)\n    return items"},
        {"prompt": "Fix the shared dictionary default.", "code": "def count(name, counts={}):\n    counts[name] = counts.get(name, 0) + 1\n    return counts"},
        {"prompt": "Make a fresh accumulator for each call.", "code": "def collect(value, bucket=[]):\n    bucket.append(value)\n    return bucket"},
        {"prompt": "Remove the mutable default state.", "code": "def tags(name, values=[]):\n    values.append(name)\n    return values"},
        {"prompt": "Fix this function so history is not shared.", "code": "def remember(event, history=[]):\n    history.append(event)\n    return history"},
        {"prompt": "Use a safe default for options.", "code": "def configure(options={}):\n    options['ready'] = True\n    return options"},
    ],
    "InPlaceMethodAssignment": [
        {"prompt": "Keep the sorted list instead of assigning None.", "code": "items = [3, 1, 2]\nitems = items.sort()\nprint(items)"},
        {"prompt": "Fix the in-place reverse call.", "code": "values = [1, 2, 3]\nvalues = values.reverse()\nprint(values)"},
        {"prompt": "Use the return value of sorted correctly.", "code": "names = ['b', 'a']\nnames = names.sort()\nprint(names)"},
        {"prompt": "Sort this list without losing the reference.", "code": "scores = [4, 2, 3]\nresult = scores.sort()\nprint(result)"},
        {"prompt": "Choose either sorted() or sort(), not assignment from sort().", "code": "data = [5, 1]\ndata = data.sort()"},
        {"prompt": "Repair this list ordering code.", "code": "queue = ['c', 'a', 'b']\nordered = queue.sort()\nprint(ordered)"},
    ],
    "IndexOutOfBounds": [
        {"prompt": "Prevent the final iteration from reading past the list.", "code": "values = [10, 20, 30]\nfor i in range(len(values)):\n    print(values[i + 1])"},
        {"prompt": "Fix the neighbor lookup at the right boundary.", "code": "for col in range(len(row)):\n    right = row[col + 1]"},
        {"prompt": "Keep the index inside the list bounds.", "code": "items = ['a', 'b']\nfor i in range(len(items)):\n    print(items[i + 1])"},
        {"prompt": "Guard the next-column access.", "code": "for col in range(len(grid[0])):\n    if grid[0][col + 1] == 1:\n        print(col)"},
        {"prompt": "Fix this off-by-one slice access.", "code": "numbers = [1, 2, 3]\nfor index in range(len(numbers)):\n    next_value = numbers[index + 1]"},
        {"prompt": "Make the loop stop before the invalid index.", "code": "letters = ['x', 'y', 'z']\nfor index in range(len(letters)):\n    print(letters[index + 1])"},
    ],
    "RuntimeError": [
        {"prompt": "Prevent division by zero.", "code": "denominator = 0\nresult = 12 / denominator"},
        {"prompt": "Convert the number safely before concatenating.", "code": "count = 5\nmessage = 'Items: ' + count"},
        {"prompt": "Handle an empty list before reading its first item.", "code": "items = []\nfirst = items[0]"},
        {"prompt": "Validate the input before converting it.", "code": "text = 'abc'\nnumber = int(text)"},
        {"prompt": "Guard the divisor before calculating the average.", "code": "total = 10\ncount = 0\naverage = total / count"},
        {"prompt": "Make the operation use compatible types.", "code": "price = '10'\ntax = 2\ntotal = price + tax"},
    ],
}


def _code_solution(code: str, misconception: str) -> tuple[str, str]:
    """Return a corrected answer and a short explanation for a code drill."""
    if misconception == "SyntaxError":
        fixed = re.sub(
            r"(?m)^(\s*(?:def|if|for|while|class|try|except|else|elif|finally)\b[^\n:]*)(?=\n|$)",
            r"\1:",
            code,
        )
        return fixed, "Python block headers must end with a colon before their indented body."
    if misconception == "IndentationError":
        lines = code.splitlines()
        fixed = []
        block_indent = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed.append("")
                continue
            if stripped.startswith(("return ", "print(", "value =", "count +=", "result =")):
                block_indent = max(block_indent, 4)
                fixed.append(" " * block_indent + stripped)
            elif stripped.startswith(("except ", "else:", "elif ")):
                block_indent = 0
                fixed.append(stripped)
            else:
                fixed.append(line.rstrip())
        return "\n".join(fixed), "Statements inside a function, loop, or conditional must use the same indentation level."
    if misconception == "Equality vs Assignment Confusion":
        return re.sub(r"(?m)^(\s*if .*?) = ", r"\1 == ", code), "Use == to compare values; a single = assigns a value and is not valid in a condition."
    if misconception == "MutableDefaultArgument":
        fixed = re.sub(r"\b(items|counts|bucket|values|history|options)=({}|\[\])", r"\1=None", code)
        parameter = re.search(r"\b(items|counts|bucket|values|history|options)=None", fixed)
        if parameter:
            name = parameter.group(1)
            lines = fixed.splitlines()
            insert_at = 1
            fixed = "\n".join(lines[:insert_at] + [f"    {name} = {name} or " + ("{}" if name in {"counts", "options"} else "[]")] + lines[insert_at:])
        return fixed, "Mutable default objects are shared by every call; use None and create a fresh list or dictionary inside the function."
    if misconception == "InPlaceMethodAssignment":
        fixed = re.sub(r"(\b\w+)\s*=\s*\1\.(sort|reverse)\(\)", r"\1.\2()", code)
        fixed = re.sub(r"(\b\w+)\s*=\s*(\w+)\.sort\(\)", r"\2.sort()", fixed)
        return fixed, "sort() and reverse() modify a list in place and return None; call them without assigning their return value."
    if misconception == "IndexOutOfBounds":
        fixed = re.sub(r"range\(len\(([^)]+)\)\)", r"range(len(\1) - 1)", code)
        return fixed, "An index plus one is valid only before the final element, so stop the loop one position earlier."
    fixed = code.replace("denominator = 0", "denominator = 1")
    fixed = fixed.replace("count = 0", "count = 1")
    fixed = re.sub(r"'Items: '\s*\+\s*count", "f'Items: {count}'", fixed)
    fixed = fixed.replace("items = []\nfirst = items[0]", "items = []\nfirst = items[0] if items else None")
    fixed = fixed.replace("text = 'abc'\nnumber = int(text)", "text = 'abc'\nnumber = int(text) if text.isdigit() else 0")
    fixed = re.sub(r"price = '10'\ntax = 2\ntotal = price \+ tax", "price = 10\ntax = 2\ntotal = price + tax", fixed)
    return fixed, "Validate values and convert compatible types before performing an operation that can raise a runtime error."


def classify_misconception(subject: str, question: str, metadata: Dict[str, Any] | None = None) -> str:
    """Return a stable misconception label for practice generation."""
    metadata = metadata or {}
    label = metadata.get("misconception") or metadata.get("error_category") or metadata.get("slip_type")
    if label:
        if label in CODE_PRACTICE:
            return label
        if label in ("TypeError", "ZeroDivisionError", "IndexError", "NameError", "ValueError"):
            return "RuntimeError" if label != "IndexError" else "IndexOutOfBounds"
        return str(label)

    text = question.lower()
    if subject.lower() in {"python", "coding", "programming", "computer science", "cs"}:
        if "recursion" in text or "indexerror" in text or "out of range" in text:
            return "IndexOutOfBounds"
        if "def " in text or "```" in text or "python" in text:
            return "SyntaxError"
        return "RuntimeError"
    if re.search(r"\d+\s*/\s*\d+\s*[+÷/]\s*\d+\s*/\s*\d+", text):
        return "M1_add_across"
    return "general_math"


def generate_practice_set(subject: str, misconception: str, count: int = 6) -> Dict[str, Any]:
    """Generate six same-domain questions targeted at the detected error."""
    count = max(5, min(6, int(count)))
    is_code = subject.lower() in {"python", "coding", "programming", "computer science", "cs"}
    if is_code:
        pool = CODE_PRACTICE.get(misconception, CODE_PRACTICE["RuntimeError"])
        questions = [
            {
                "id": f"code_{misconception}_{idx + 1}",
                "subject": "Python",
                "type": "code",
                "prompt": item["prompt"],
                "code": item["code"],
                "target_misconception": misconception,
                "correct_code": _code_solution(item["code"], misconception)[0],
                "explanation": _code_solution(item["code"], misconception)[1],
            }
            for idx, item in enumerate(pool[:count])
        ]
    else:
        target = misconception if misconception in backend_code.ALL_BUGS else "M1_add_across"
        questions = []
        for idx in range(count):
            problem = backend_code.generate_targeted_problem(target, difficulty=1 + (idx // 3))
            questions.append(
                {
                    "id": f"math_{target}_{idx + 1}",
                    "subject": "Mathematics",
                    "type": "math",
                    "prompt": problem["text"],
                    "target_misconception": target,
                    "operation": problem["operation"],
                    "a": problem["a"],
                    "b": problem["b"],
                    "c": problem["c"],
                    "d": problem["d"],
                    "correct_answer": problem["correct_answer"],
                }
            )
    return {
        "subject": "Python" if is_code else "Mathematics",
        "misconception": misconception,
        "count": len(questions),
        "questions": questions,
    }
