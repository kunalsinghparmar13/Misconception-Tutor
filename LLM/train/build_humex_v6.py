"""Build the v6 training mix for Humo (the Humex tutor), trained on top of the v4 adapter.

    python LLM/train/build_humex_v6.py --old-mixes <dir with out/, out_v3/, out_v4/> --out <dir> \
        [--exclude cases.jsonl] [--user-data LLM/data/user_training.jsonl]

Why: a 200-question test of v4 (2026-11-25) found the model never says a maths answer is wrong, rarely offers a
truly different method, and replies in ~12 words. Code now patches those at runtime (tutor_agents/humex_style.py);
this data teaches the model itself to do it, so the patches are needed less and replies read naturally.

Every Humo row is built exactly like the app builds its prompt (coach_system_prompt + "message\\n\\nPrivate facts"),
and every ideal reply is checked with Humo's own leak checks before it is kept. Rows whose learner message appears
in --exclude (the 200 test questions) are dropped so that test stays a fair measure. A replay of the v2-v4 data
keeps the earlier maths, logic, Python and Socratic skills, and --user-data adds real, checked Humo conversations
exported by scripts/export_user_training_data.py.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "LLM"))
sys.path.insert(0, str(ROOT))

from tutor_agents import grounding as gr  # noqa: E402
from tutor_agents import humex_style as style  # noqa: E402
from tutor_agents.humex import (_problem_text, check_reply, clean_history, coach_system_prompt,  # noqa: E402
                                hint_level, is_coding, turn_focus)
from tutor_agents.prompts import HUMEX_REVIEWER  # noqa: E402

rng = random.Random(606)
REVIEWER_LANG = {"en": "Reply in simple English.", "hi": "Reply in simple Hindi written in Devanagari script."}


def fr(x) -> str:
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def pick(options):
    return rng.choice(options)


# ====================================================================================== building one Humo row

class Builder:
    def __init__(self, exclude: set):
        self.rows, self.reviews, self.skipped, self.exclude = [], [], {}, exclude
        self.seen = set()

    def skip(self, why):
        self.skipped[why] = self.skipped.get(why, 0) + 1

    def add(self, category, message, reply, history=None, language="en", subject="", answer=None, expect=None):
        """Add one coach turn, built and checked exactly as the app would see it."""
        history = clean_history(history or [])
        if message in self.exclude:
            return self.skip("in the 200-question test")
        if (message, reply) in self.seen:
            return self.skip("duplicate")
        problem = _problem_text(history, message)
        g = gr.ground(style.spoken_to_math(problem), subject)
        coding = is_coding(g, problem, subject)
        focus = turn_focus(message, history, g)
        if expect and focus != expect:
            return self.skip(f"focus {focus} != {expect}")
        level = min(3, hint_level(history) + 1) if focus == "stuck" else hint_level(history)
        mistake = style.name_mistake(g, language) if focus == "wrong" else None
        method = style.pick_method(style.problem_kind(g, problem, coding), history, message) if focus == "another_way" else None
        checks = check_reply(reply, g, problem, coding)
        if not all(c.ok for c in checks if c.name in ("no_answer_leak", "no_answer_phrase", "no_full_code")):
            return self.skip("reply failed a leak/code check")
        if answer is not None and focus != "right" and _says(reply, answer):
            return self.skip("reply says the answer")
        if "?" not in reply or len(reply.split()) > 85:
            return self.skip("no question / too long")
        facts = g.facts_block().replace("Verified facts", "Private facts") or "Private facts: none for this message."
        system = coach_system_prompt(focus, level, language, coding, mistake=mistake, method=method)
        msgs = [{"role": "system", "content": system}] + history + [
            {"role": "user", "content": f"{message}\n\n{facts}"}, {"role": "assistant", "content": reply}]
        self.seen.add((message, reply))
        self.rows.append({"messages": msgs, "source": f"humo-{category}", "category": category})
        # keep what the reviewer sees for the reviewer rows
        self.reviews.append({"history": history, "message": message, "facts": facts, "good": reply, "answer": answer,
                             "coding": coding, "language": language, "g": g, "problem": problem})


def _says(text, answer) -> bool:
    nums = []
    for m in re.finditer(r"-?\d+(?:\.\d+)?(?:\s*/\s*\d+)?", text.replace(",", "")):
        t = m.group(0).replace(" ", "")
        try:
            nums.append(Fraction(*map(int, t.split("/"))) if "/" in t else Fraction(t))
        except (ValueError, ZeroDivisionError):
            pass
    target = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", str(answer).replace(" ", ""))
    if not target:
        return False
    t = target[-1]
    value = Fraction(*map(int, t.split("/"))) if "/" in t else Fraction(t)
    return value in nums


# ====================================================================================== MATHS

WARM = ["Good question!", "Nice, let's work it out together.", "Great question to ask.", "Let's figure this out together."]
PRAISE = ["Yes, that's right!", "Spot on!", "Exactly right, well done!", "That's correct, nice work!", "Yes! You got it."]
STUCK_OPEN = ["I know it feels tricky, and that's okay.", "No worries, we'll take it one small step at a time.",
              "It's normal to get stuck here, so let's slow down.", "I hear you, this part trips a lot of people up."]
STUCK_WHY = ["I won't hand you the answer, because working it out yourself is what makes it stick.",
             "If I just told you, you'd miss the part that helps next time.",
             "Let's get you there yourself, it'll feel much better."]
MISTAKE_WHY = {
    "M1_add_across": ["Fractions can only be combined when the pieces are the same size, and {b}ths and {d}ths are different sizes.",
                      "Adding the bottoms would change the size of the pieces, which isn't what adding means."],
    "M2_tops_add_bottoms_multiply": ["Multiplying the bottoms can give a shared bottom, but then each top has to grow by the same amount as its bottom.",
                                     "Changing a bottom without changing its top changes how big the fraction is."],
    "M3_no_scaling": ["When you change the bottom of a fraction, the top must change by the same factor, or the fraction changes size.",
                      "A fraction keeps its size only if the top and bottom are multiplied by the same number."],
    "M4_divide_multiply_across": ["Dividing asks how many of the second fraction fit into the first, which is different from multiplying.",
                                  "Multiplying straight across works for multiplication, but division needs one extra move."],
    "M5_flip_wrong_fraction": ["When dividing by a fraction, it's the one you divide by, the second one, that gets flipped.",
                               "Flipping the first fraction changes what you're dividing, not what you're dividing by."],
}


def lcm(a, b):
    return a * b // math.gcd(a, b)


def frac_pair(max_den=12):
    while True:
        b, d = rng.randint(2, max_den), rng.randint(2, max_den)
        a, c = rng.randint(1, b - 1), rng.randint(1, d - 1)
        if b != d:
            return a, b, c, d


def maths(B: Builder):
    fraction_asks = ["What is {a}/{b} + {c}/{d}? I got {w}", "I added {a}/{b} and {c}/{d} and got {w}. Is that right?",
                     "Is {a}/{b} + {c}/{d} = {w}?", "My answer for {a}/{b} + {c}/{d} is {w}", "{a}/{b} + {c}/{d} = {w} right?"]
    division_asks = ["I worked out {a}/{b} ÷ {c}/{d} = {w}. Is that right?", "Is {a}/{b} ÷ {c}/{d} = {w}?",
                     "For {a}/{b} ÷ {c}/{d} I got {w}", "{a}/{b} divided by {c}/{d} = {w} right?"]
    questions_add = ["What number could both {b} and {d} divide into, so the pieces are the same size?",
                     "If you cut both into equal-sized pieces, how many pieces would make a whole?",
                     "What is the smallest number that both {b} and {d} go into evenly?",
                     "Can you rewrite each fraction so they have the same bottom?"]
    questions_div = ["What do you think dividing by {c}/{d} means in words?",
                     "Which fraction should you flip, and what do you multiply it by?",
                     "How many {c}/{d}s would fit into {a}/{b}, roughly more or less than one?"]

    # 1. wrong fractions with a named misconception (~380)
    bugs = {"M1_add_across": lambda a, b, c, d: Fraction(a + c, b + d),
            "M2_tops_add_bottoms_multiply": lambda a, b, c, d: Fraction(a + c, b * d),
            "M3_no_scaling": lambda a, b, c, d: Fraction(a + c, lcm(b, d)),
            "M4_divide_multiply_across": lambda a, b, c, d: Fraction(a * c, b * d),
            "M5_flip_wrong_fraction": lambda a, b, c, d: Fraction(b * c, a * d)}
    for _ in range(420):
        bug = pick(list(bugs))
        a, b, c, d = frac_pair()
        w = bugs[bug](a, b, c, d)
        division = bug in ("M4_divide_multiply_across", "M5_flip_wrong_fraction")
        right = Fraction(a, b) / Fraction(c, d) if division else Fraction(a, b) + Fraction(c, d)
        if w == right:
            continue
        msg = pick(division_asks if division else fraction_asks).format(a=a, b=b, c=c, d=d, w=fr(w))
        g = gr.ground(msg)
        if g.misconception_id != bug:
            continue
        reply = " ".join([style.MISTAKES[bug][0], pick(MISTAKE_WHY[bug]).format(b=b, d=d),
                          pick(questions_div if division else questions_add).format(a=a, b=b, c=c, d=d)])
        B.add("wrong-fraction", msg, reply, answer=fr(right), expect="wrong")

    # 2. wrong equations and arithmetic (~260)
    for _ in range(130):
        x, k, m = rng.randint(2, 15), rng.randint(2, 9), rng.randint(2, 30)
        r = k * x + m
        w = pick([Fraction(r + m, k), Fraction(r, k) - m, x + rng.choice([-2, -1, 1, 2]), r - m])
        if w == x:
            continue
        msg = pick(["Solve {k}x + {m} = {r}. My answer is x = {w}", "I got x = {w} for {k}x + {m} = {r}",
                    "Is x = {w} right for {k}x + {m} = {r}?"]).format(k=k, m=m, r=r, w=fr(w))
        reply = " ".join([f"Not quite. If you put x = {fr(w)} back into the equation, the two sides don't balance.",
                          pick(["Remember, whatever you do to one side, you must do to the other.",
                                "Think about undoing what was done to x, in reverse order."]),
                          pick([f"What could you do to both sides to remove the {m} first?",
                                "Which part of the left side would you undo first, and how?",
                                f"After taking care of the {m}, what is x being multiplied by?"])])
        B.add("wrong-equation", msg, reply, answer=x, expect="wrong")
    for _ in range(130):
        a, b = rng.randint(12, 99), rng.randint(3, 9)
        w = a * b + rng.choice([-10, -1, 1, 10, -20])
        msg = pick(["{a} * {b} = {w} right?", "I worked out {a} × {b} = {w}", "Is {a} times {b} equal to {w}?"]).format(a=a, b=b, w=w)
        tens, ones = a // 10 * 10, a % 10
        reply = " ".join([f"Not quite, {w} isn't right yet.",
                          pick(["Big multiplications are easier in smaller pieces.", "Let's split it into friendlier parts."]),
                          f"What is {tens} times {b}, and what is {ones} times {b}?" if ones else
                          f"What is {a // 10} times {b}, and how does that help with {a}?"])
        B.add("wrong-arithmetic", msg, reply, answer=a * b, expect="wrong")

    # 3. correct answers: praise + why or a harder case (~240)
    for _ in range(240):
        kind = pick(["frac", "eq", "mult"])
        if kind == "frac":
            a, b, c, d = frac_pair(10)
            ans = Fraction(a, b) + Fraction(c, d)
            msg = pick(["I think {a}/{b} + {c}/{d} = {s}", "{a}/{b} + {c}/{d} = {s}, is that right?", "I got {s} for {a}/{b} + {c}/{d}"]).format(
                a=a, b=b, c=c, d=d, s=fr(ans))
            follow = pick(["How did you know the bottoms had to match before adding?",
                           f"Why did {lcm(b, d)} work as the shared bottom?",
                           "Could you explain your steps out loud, as if teaching a friend?",
                           f"Can you try {a}/{b} + {c + 1 if c + 1 < d else c}/{d + 1} the same way?"])
        elif kind == "eq":
            x, k, m = rng.randint(2, 15), rng.randint(2, 9), rng.randint(1, 20)
            msg = pick(["Solve {k}x - {m} = {r}. I got x = {x}", "For {k}x - {m} = {r} I think x = {x}"]).format(k=k, m=m, r=k * x - m, x=x)
            follow = pick([f"Why did you add {m} to both sides before dividing?", "How could you check your answer is right?",
                           "What would change if the equation had a plus instead of a minus?"])
        else:
            a, b = rng.randint(12, 49), rng.randint(3, 9)
            msg = pick(["{a} * {b} = {p} right?", "Is {a} × {b} = {p}?"]).format(a=a, b=b, p=a * b)
            follow = pick(["How did you work it out?", f"Could you check it a different way, like {b} times {a}?",
                           "What trick did you use to multiply so quickly?"])
        B.add("right", msg, f"{pick(PRAISE)} {follow}", expect="right")

    # 4. fresh questions: warm + a first step (~300)
    for _ in range(80):
        a, b, c, d = frac_pair(10)
        op = pick(["+", "-"])
        msg = pick(["How do I work out {a}/{b} {op} {c}/{d}?", "Can you help me with {a}/{b} {op} {c}/{d}?",
                    "I don't get how to do {a}/{b} {op} {c}/{d}"]).format(a=a, b=b, c=c, d=d, op=op)
        reply = f"{pick(WARM)} Before we can {'add' if op == '+' else 'subtract'}, the pieces need to be the same size. " + \
                pick(questions_add).format(b=b, d=d)
        B.add("fresh-fraction", msg, reply, expect="start" if "don't get" not in msg else None)
    for _ in range(70):
        p, n = pick([5, 12, 15, 20, 25, 30, 40, 75]), pick([60, 80, 120, 160, 240, 300, 360])
        msg = pick(["What is {p}% of {n}?", "How do I find {p} percent of {n}?", "Can you help me work out {p}% of {n}?"]).format(p=p, n=n)
        reply = f"{pick(WARM)} Percent means out of a hundred, so {p}% means {p} out of every hundred. " + \
                pick([f"What is 1% of {n}, and how could that help you?", "Could you turn the percent into a fraction first?",
                      f"What is half of {n}, and is {p}% more or less than half?"])
        B.add("fresh-percent", msg, reply, answer=fr(Fraction(p * n, 100)))
    for _ in range(60):
        x, k, m = rng.randint(2, 12), rng.randint(2, 9), rng.randint(1, 25)
        msg = pick(["How do I solve {k}x + {m} = {r}?", "Help me solve {k}x + {m} = {r}"]).format(k=k, m=m, r=k * x + m)
        reply = f"{pick(WARM)} Think of the equation as a balance: both sides weigh the same. " + \
                pick(["What is being done to x on the left side?", f"What could you do to both sides to get rid of the {m}?"])
        B.add("fresh-equation", msg, reply, answer=x)
    words = [
        ("A shop sells {n} pencils in {b} equal boxes. How many pencils are in 3 boxes?", lambda n, b: Fraction(n, b) * 3,
         "What do you need to know first: how many pencils are in one box?"),
        ("A cyclist rides {n} km in {b} hours. How far at the same speed in 7 hours?", lambda n, b: Fraction(n, b) * 7,
         "What is the distance in one hour, and why does that help?"),
        ("Two numbers add up to {n} and one is {b} more than the other. What is the smaller one?", lambda n, b: Fraction(n - b, 2),
         "If you took away the extra {b}, what would the two numbers have in common?"),
        ("A garden is {b} m wide and its perimeter is {n} m. How long is it?", lambda n, b: Fraction(n - 2 * b, 2),
         "What does the perimeter add up, and how many of those sides do you already know?"),
        ("{b} friends share {n} rupees equally. How much does each get?", lambda n, b: Fraction(n, b),
         "Is this a sharing question, and which operation does sharing equally use?"),
    ]
    for _ in range(90):
        text, solve, hint = pick(words)
        b = rng.randint(3, 9)
        n = b * rng.randint(4, 30) + (0 if "share" in text or "pencils" in text or "km" in text else rng.randint(0, 1) * 2)
        if solve(n, b) <= 0 or Fraction(solve(n, b)).denominator != 1:
            continue
        msg = text.format(n=n, b=b)
        B.add("fresh-word", msg, f"{pick(WARM)} Let's find the first useful step. {hint.format(b=b)}", answer=fr(solve(n, b)))

    # 5. another way (~200): a method not yet used, said as a hint
    first_methods = {"fraction": "Let's find a common bottom first. What number could both denominators divide into?",
                     "equation": "Let's undo what was done to x. What would you undo first?",
                     "percent": "Percent means out of a hundred. What is 1% of the number?",
                     "arithmetic": "Let's multiply it the usual way. What do you get for the ones first?"}
    for _ in range(220):
        kind = pick(list(first_methods))
        if kind == "fraction":
            a, b, c, d = frac_pair(8)
            q, ans = f"{a}/{b} + {c}/{d}", fr(Fraction(a, b) + Fraction(c, d))
        elif kind == "equation":
            x, k, m = rng.randint(2, 12), rng.randint(2, 9), rng.randint(1, 20)
            q, ans = f"{k}x + {m} = {k * x + m}", x
        elif kind == "percent":
            p, n = pick([10, 20, 25, 50, 75]), pick([40, 80, 120, 200, 360])
            q, ans = f"{p}% of {n}", fr(Fraction(p * n, 100))
        else:
            a, b = rng.randint(13, 89), rng.randint(3, 9)
            q, ans = f"{a} × {b}", a * b
        history = [{"role": "user", "content": f"How do I do {q}?"}, {"role": "assistant", "content": first_methods[kind]}]
        msg = pick(["Is there another way to do {q}?", "Can you show me another way to do {q}?", "Any other way for {q}?",
                    "I don't like that method, is there a different way to do {q}?"]).format(q=q)
        prob = _problem_text(clean_history(history), msg)
        method = style.pick_method(style.problem_kind(gr.ground(style.spoken_to_math(prob)), prob, False), clean_history(history), msg)
        follow = pick(["Can you try the first step that way?", "What do you get when you try that?",
                       "Which part of that would you do first?"])
        B.add("another-way", msg, f"{pick(['Sure!', 'Of course.', 'Yes, there is.'])} {method} {follow}", history=history,
              answer=ans, expect="another_way")

    # 6. stuck: kind refusal + a smaller step (~160)
    for _ in range(170):
        a, b = rng.randint(13, 47), rng.randint(3, 9)
        kind = pick(["mult", "frac", "eq"])
        if kind == "mult":
            q, ans, step = f"{a} * {b}", a * b, f"What is {a // 10 * 10} times {b}?"
        elif kind == "frac":
            d = pick([3, 4, 5, 6, 8])
            q, ans, step = f"1/{b} + 1/{d}", fr(Fraction(1, b) + Fraction(1, d)), f"What number do both {b} and {d} divide into?"
        else:
            q, ans, step = f"{b}x = {a * b}", a, "What is x being multiplied by, and how could you undo that?"
        msg = pick(["Just tell me the answer to {q}", "I give up, what is {q}?", "Give me the answer for {q}",
                    "I'm stuck on {q}, just tell me", "Please just solve {q} for me"]).format(q=q)
        reply = f"{pick(STUCK_OPEN)} {pick(STUCK_WHY)} Let's do just one small step: {step}"
        B.add("stuck", msg, reply, answer=ans, expect="stuck")

    # 7. working step by step (~150): confirm the step, ask for the next
    for _ in range(150):
        a, b, c, d = frac_pair(8)
        L = lcm(b, d)
        history = [{"role": "user", "content": f"What is {a}/{b} + {c}/{d}?"},
                   {"role": "assistant", "content": f"Before adding, the pieces must be the same size. What number can both {b} and {d} divide into?"}]
        msg = pick(["Okay, so the common denominator is {L}. What now?", "Is it {L}?", "I think {L} works for both"]).format(L=L)
        reply = f"{pick(['Yes, ' + str(L) + ' works!', 'Exactly, ' + str(L) + ' is a good choice.', 'Right, both go into ' + str(L) + '.'])} " + \
                pick([f"Now, how many {L}ths is {a}/{b}?", f"What do you multiply the top of {a}/{b} by to make the bottom {L}?",
                      "What should happen to each top so the fractions stay the same size?"])
        B.add("step", msg, reply, history=history, answer=fr(Fraction(a, b) + Fraction(c, d)))

    # 8. a little Hindi (~120): the same moves in Hindi
    for _ in range(60):
        a, b, c, d = frac_pair(8)
        w = Fraction(a + c, b + d)
        if w == Fraction(a, b) + Fraction(c, d):
            continue
        msg = f"{a}/{b} + {c}/{d} का जवाब {fr(w)} आया"
        reply = f"{style.MISTAKES['M1_add_across'][1]} भिन्न तभी जुड़ती हैं जब टुकड़े बराबर आकार के हों। {b} और {d} दोनों किस संख्या में पूरे-पूरे जाते हैं?"
        B.add("hindi-wrong", msg, reply, language="hi", answer=fr(Fraction(a, b) + Fraction(c, d)))
    for _ in range(60):
        a, b = rng.randint(13, 39), rng.randint(3, 9)
        msg = f"{a} * {b} का जवाब बताओ"
        reply = f"{pick(['कोई बात नहीं, एक-एक छोटा कदम लेते हैं।', 'चिंता मत करो, यह थोड़ा मुश्किल लगता है।'])} जवाब मैं नहीं बताऊँगा, ताकि तुम खुद सीख सको। पहले बताओ, {a // 10 * 10} गुणा {b} कितना होता है?"
        B.add("hindi-stuck", msg, reply, language="hi", answer=a * b)


# ====================================================================================== PYTHON (ideas in words, never code)

BUGS = [  # (code, error, explanation in words, guiding question)
    ("items = ['a', 'b', 'c']\nfor i in range(1, len(items) + 1):\n    print(items[i])", "IndexError: list index out of range",
     "your loop asks for one position past the end. A list of three items has positions 0, 1 and 2.",
     "What is the last position your loop tries to read, and does that position exist?"),
    ("count = 7\nprint('You have ' + count + ' points')", "TypeError: can only concatenate str (not \"int\") to str",
     "you're joining text and a number with plus, and Python won't mix those two types.",
     "How could you turn the number into text before joining them?"),
    ("def double(n):\n    result = n * 2\nprint(double(5))", "it prints None",
     "your function works out the result but never hands it back to the caller.",
     "What keyword sends a value back out of a function?"),
    ("for name in ['Asha', 'Ravi']:\nprint(name)", "IndentationError: expected an indented block",
     "the line inside the loop isn't indented, so Python can't tell it belongs to the loop.",
     "How does Python know which lines are inside a loop?"),
    ("if score = 10:\n    print('ten')", "SyntaxError: invalid syntax",
     "a single equals sign stores a value, but here you want to compare two values.",
     "Which symbol does Python use to check if two things are equal?"),
    ("print(totall)", "NameError: name 'totall' is not defined",
     "Python can't find a variable with exactly that name.",
     "Can you compare the spelling here with where you first created the variable?"),
    ("ages = {'Asha': 12}\nprint(ages['Ravi'])", "KeyError: 'Ravi'",
     "you're asking the dictionary for a key it doesn't have.",
     "How could you check whether a key is in the dictionary before reading it?"),
    ("def add_name(name, names=[]):\n    names.append(name)\n    return names\nprint(add_name('a'))\nprint(add_name('b'))",
     "the second call prints both names", "the default list is created once and then shared by every call.",
     "What would happen if each call started with a fresh, empty list instead?"),
    ("n = 0\nwhile n < 3:\n    print(n)", "it never stops", "nothing inside the loop ever changes n, so the condition stays true forever.",
     "What needs to change on each pass so the loop can finish?"),
    ("marks = []\naverage = sum(marks) / len(marks)", "ZeroDivisionError: division by zero",
     "the list is empty, so its length is zero and you can't divide by zero.",
     "What should the program do when there are no marks yet?"),
    ("name = 'riya'\nname[0] = 'R'", "TypeError: 'str' object does not support item assignment",
     "strings can't be changed in place in Python.", "How could you build a new string with a capital first letter instead?"),
    ("scores = [5, 2, 9]\nordered = scores.sort()\nprint(ordered)", "it prints None",
     "sort changes the list itself and hands back nothing.", "Which list are you printing, and what did sort actually give back?"),
    ("age = input('Age: ')\nprint(age + 1)", "TypeError: can only concatenate str (not \"int\") to str",
     "input always gives you text, even when the user types digits.", "How could you turn that text into a number first?"),
    ("def is_odd(n):\n    if n % 2 == 1:\n        return True\n    return True", "every number counts as odd",
     "both paths in your function give back the same value.", "What should the function say when the remainder isn't 1?"),
    ("total = 0\nfor n in [1, 2, 3]:\n    total = n\nprint(total)", "it prints 3 instead of the sum",
     "each pass replaces the total instead of adding to it.", "What should happen to the old total each time round the loop?"),
    ("word = 'level'\nif word == word.reverse():\n    print('yes')", "AttributeError: 'str' object has no attribute 'reverse'",
     "strings don't have a reverse method the way lists do.", "What other way do you know to get a string backwards?"),
    ("nums = [1, 2, 3]\nfor n in nums:\n    if n == 2:\n        nums.remove(n)\nprint(nums)", "it skips some items",
     "changing a list while you loop over it shifts the items under the loop.", "What if you built a new list instead of removing from the one you're looping over?"),
    ("x = 10\ndef bump():\n    x = x + 1\nbump()", "UnboundLocalError: local variable 'x' referenced before assignment",
     "inside the function Python treats x as a new local name, which has no value yet.", "How could the function receive x and hand back the new value?"),
]
TASKS = [  # (task, approach in words, guiding question)
    ("count how many times a letter appears in a word", "go through the word one character at a time and keep a counter",
     "What should the counter start at, and when should it go up?"),
    ("find the average of a list of marks", "you need two things: the total of all the marks and how many marks there are",
     "Which of those two can you find first?"),
    ("check if a list is sorted", "compare each item with the one right after it",
     "What would tell you the list is not sorted?"),
    ("turn a sentence into a list of words", "think about what separates one word from the next",
     "What character could you split the sentence on?"),
    ("find the longest word in a sentence", "keep track of the longest word you've seen so far while you check each word",
     "What should 'longest so far' be before you look at any words?"),
    ("count the even numbers in a list", "check each number and decide whether it divides evenly by two",
     "What does the remainder tell you when you divide by two?"),
    ("reverse the words in a sentence", "split the sentence into words, change their order, then join them back",
     "Which of those three steps would you try first?"),
    ("find the biggest of three numbers", "compare them two at a time and keep the winner",
     "If you compare the first two, what do you do with the third?"),
    ("check if a number is a perfect square", "think about which whole number, times itself, could give your number",
     "How could you test the numbers up to it one by one?"),
    ("add up the digits of a number", "peel off the last digit, add it, then drop it and repeat",
     "Which arithmetic operation gives you the last digit of a number?"),
    ("print a triangle of stars", "each row has one more star than the row before",
     "How could a loop know how many stars to print on each row?"),
    ("check if two words are anagrams", "two words are anagrams when they use exactly the same letters the same number of times",
     "How could you put both words into a form that's easy to compare?"),
    ("find the first repeated letter in a word", "remember the letters you've already seen as you go",
     "What should you check each time you meet a new letter?"),
    ("convert minutes to hours and minutes", "think about how many whole hours fit into the minutes, and what's left over",
     "Which two operations give you 'how many fit' and 'what's left'?"),
    ("find the smallest even number in a list", "only look at the even numbers, and remember the smallest one so far",
     "What should 'smallest so far' be before you've seen any even numbers?"),
]
PLANS_WRONG = [
    ("find the average of a list", "I'll add the numbers and divide by 2",
     "dividing by 2 only works when there are exactly two numbers. Try it on three numbers like 3, 6 and 9 and see what happens.",
     "What should you divide by so it works for any list?"),
    ("check if a number is prime", "I'll check if it's odd, then it's prime",
     "lots of odd numbers aren't prime. Think about 9 or 15.", "What would you need to check to be sure a number has no other factors?"),
    ("get the last item of a list", "I'll use the position equal to the list's length",
     "positions start at 0, so the length is always one past the last position. Try it on a list of two items.",
     "What position is the last item really at?"),
    ("count the words in a sentence", "I'll count the letters and divide by 5",
     "words have different lengths, so that gives a guess, not a count.", "What separates one word from another in a sentence?"),
    ("find the largest number in a list", "I'll start with biggest set to 0 and compare",
     "starting at 0 breaks when every number is negative, like -3 and -8.", "What could you start 'biggest' at that is always a real number from the list?"),
    ("print the numbers from 1 to 10", "I'll loop over the first ten numbers starting from 0",
     "that gives 0 to 9, one step off at both ends.", "Where should the loop start and stop to include both 1 and 10?"),
    ("join two lists", "I'll append the second list to the first",
     "append adds the whole second list as one single item at the end.", "How could you add the second list's items one by one instead?"),
    ("check if a number is even", "I'll check if the number divided by 2 equals 0",
     "dividing by 2 gives half the number, which is only 0 for zero itself.", "Which operation tells you what's left over after dividing by 2?"),
]
PLANS_RIGHT = [
    ("reverse a string", "I'll take the string backwards with slicing"), ("count each word", "I'll use a dictionary and add one each time I see a word"),
    ("find the largest number", "I'll start with the first item and swap it whenever I find a bigger one"),
    ("check a palindrome", "I'll compare the word with its reverse"), ("sum a list", "I'll keep a running total starting at zero"),
    ("remove duplicates in order", "I'll remember what I've seen in a set and only keep new items"),
    ("check if a list is sorted", "I'll compare each item with the next one"),
    ("count vowels", "I'll check each letter against the five vowels and keep a count"),
]


def python(B: Builder):
    # bugs (~360): what is happening, in words, then a guiding question
    for _ in range(360):
        code, err, why, q = pick(BUGS)
        msg = pick(["My Python code gives an error: {e}\n```python\n{c}\n```\nWhat is wrong?",
                    "Why does this happen? {e}\n```python\n{c}\n```", "Help, my code says {e}:\n```python\n{c}\n```",
                    "I don't understand this bug ({e}):\n```python\n{c}\n```"]).format(e=err, c=code)
        reply = f"{pick(['Good find. ', 'Let’s look at it together. ', 'Nice that you shared the error. ', ''])}It looks like {why} {q}"
        B.add("py-bug", msg, reply.strip(), subject="Python")
    # code demands (~160)
    for _ in range(160):
        code, err, why, q = pick(BUGS)
        msg = pick(["Just give me the fixed code please:\n```python\n{c}\n```", "Fix it for me:\n```python\n{c}\n```",
                    "Can you write the correct code? It says {e}\n```python\n{c}\n```"]).format(c=code, e=err)
        reply = f"{pick(STUCK_OPEN)} I won't write the code for you, but you're close. It looks like {why} {q}"
        B.add("py-stuck", msg, reply, subject="Python", expect="stuck")
    # how do I (~260)
    for _ in range(260):
        task, idea, q = pick(TASKS)
        msg = pick(["How do I {t} in Python?", "Can you help me {t} in Python?", "What's the way to {t} in Python?"]).format(t=task)
        B.add("py-howto", msg, f"{pick(WARM)} Here's the idea in words: {idea}. {q}", subject="Python", expect="start")
    # plans (~260)
    for _ in range(170):
        task, plan, why, q = pick(PLANS_WRONG)
        msg = pick(["I want to {t} in Python. My plan: {p}. Will that work?", "To {t}, {p}. Is that right?",
                    "My approach to {t}: {p}. Good idea?"]).format(t=task, p=plan[0].lower() + plan[1:] if not plan.startswith("I") else plan)
        B.add("py-plan-wrong", msg, f"Not quite: {why} {q}", subject="Python", expect="check_plan")
    for _ in range(90):
        task, plan = pick(PLANS_RIGHT)
        msg = pick(["I want to {t} in Python. My plan: {p}. Will that work?", "To {t}, {p}. Is that a good approach?"]).format(t=task, p=plan)
        B.add("py-plan-right", msg, pick(["Yes, that plan works!", "That's a solid plan.", "Good thinking, that works."]) + " " +
              pick(["What will your very first line need to do?", "What would you check it on first, to be sure?",
                    "Can you walk me through what happens on the first pass?"]), subject="Python", expect="check_plan")
    # another way (~160)
    for _ in range(160):
        task, idea, _q = pick(TASKS)
        history = [{"role": "user", "content": f"How do I {task} in Python?"}, {"role": "assistant", "content": f"Here's the idea in words: {idea}. What would you try first?"}]
        msg = pick(["Is there another way to {t} in Python?", "Any different way to {t}?", "Can you show me a different approach to {t} in Python?"]).format(t=task)
        method = style.pick_method("python", clean_history(history), msg)
        B.add("py-another-way", msg, f"{pick(['Yes, there is.', 'Sure!'])} {method} {pick(['How might that look for your task?', 'What would be the first step that way?'])}",
              history=history, subject="Python", expect="another_way")


# ====================================================================================== reviewer rows

def reviewer_rows(B: Builder, n: int) -> list:
    rows = []
    for item in rng.sample(B.reviews, min(n, len(B.reviews))):
        good = item["good"]
        bad_kind = pick(["pass", "pass", "leak", "code", "echo", "noq"])
        if bad_kind == "leak" and item["answer"] is not None:
            draft, issue = f"The answer is {item['answer']}. {good}", "reveals the final answer"
        elif bad_kind == "code" and item["coding"]:
            draft, issue = f"{good.rstrip('?')}. For example: `result = sum(values)`?", "gives code"
        elif bad_kind == "echo":
            draft, issue = item["message"].split("\n")[0].rstrip("?") + "?", "only repeats the learner's question"
        elif bad_kind == "noq":
            draft, issue = re.sub(r"[^.!?]*\?\s*$", "", good).strip() or good, "does not ask the learner a question"
        else:
            draft, issue = good, None
        if issue and draft == good:
            draft, issue = good, None
        checks = check_reply(draft, item["g"], item["problem"], item["coding"], raw=draft)
        check_lines = "\n".join(f"- {c.name}: {'ok' if c.ok else 'FAILED (' + c.detail + ')'}" for c in checks)
        transcript = "\n".join(f"{'Learner' if t['role'] == 'user' else 'Humo'}: {t['content']}" for t in item["history"][-6:])
        user = (f"Conversation so far:\n{transcript or '(none)'}\nLearner: {item['message']}\n\n{item['facts']}\n\n"
                f"Humo's draft reply:\n{draft}\n\nAutomatic checks:\n{check_lines}")
        answer = ("Verdict: PASS\nIssues: none\nBetter reply: same" if not issue else
                  f"Verdict: FAIL\nIssues: {issue}\nBetter reply: {good}")
        rows.append({"messages": [{"role": "system", "content": HUMEX_REVIEWER.format(language_rule=REVIEWER_LANG[item['language']])},
                                  {"role": "user", "content": user}, {"role": "assistant", "content": answer}],
                     "source": "humo-reviewer", "category": "reviewer-" + ("pass" if not issue else "fail")})
    return rows


# ====================================================================================== replay of v2-v4 + user data

REPLAY = {  # file (in out/, out_v3/, out_v4/) -> rows: keeps earlier maths, logic, Python and Socratic skills
    "out/socrateach.jsonl": 150, "out/socratic_debugging.jsonl": 100, "out/pact_socratic_coding.jsonl": 90,
    "out/socratic_1680.jsonl": 100, "out_v3/socratiq.jsonl": 80, "out_v4/proofwriter_v4.jsonl": 60,
    "out/folio.jsonl": 40, "out_v4/pfolio.jsonl": 60, "out_v4/openthoughts3_math.jsonl": 80,
    "out_v3/opencodereasoning2_v3.jsonl": 50, "out_v3/pyre_v2.jsonl": 60, "out/edumath.jsonl": 40,
}
TESTS = ("out_v4/openr1_math_test.jsonl", "out_v4/proofwriter_test.jsonl", "out_v4/folio_test.jsonl")


def jl(path: Path) -> list:
    return [json.loads(x) for x in path.open(encoding="utf-8") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-mixes", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--exclude", type=Path, help="jsonl of test cases whose 'message' must not be trained on")
    ap.add_argument("--user-data", type=Path, help="real Humo conversations from export_user_training_data.py")
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "LLM" / "humex" / "tokenizer.json")
    ap.add_argument("--max-tokens", type=int, default=1900)
    args = ap.parse_args()

    exclude = {json.loads(x)["message"] for x in args.exclude.open()} if args.exclude else set()
    B = Builder(exclude)
    maths(B)
    python(B)
    reviews = reviewer_rows(B, 420)

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(args.tokenizer))

    def ntok(row):
        if "messages" in row:
            return len(tok.encode(" ".join(m["content"] + m.get("reasoning_content", "") for m in row["messages"])).ids) + 60
        return len(tok.encode(row.get("system", "") + row["question"] + row.get("reasoning", "") + row["answer"]).ids) + 60

    args.out.mkdir(parents=True, exist_ok=True)
    stats = {}

    def write(name, rows):
        rows = [r for r in rows if ntok(r) <= args.max_tokens]
        with (args.out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({k: v for k, v in r.items() if k != "category"}, ensure_ascii=False) + "\n")
        stats[name] = (len(rows), sum(ntok(r) for r in rows))

    write("humo_coach", B.rows)
    write("humo_reviewer", reviews)
    replay = []
    for rel, n in REPLAY.items():
        rows = jl(args.old_mixes / rel)
        rng.shuffle(rows)
        replay += rows[:n]
    write("replay_v2_v4", replay)
    if args.user_data and args.user_data.exists():
        write("humo_user_conversations", jl(args.user_data))
    for rel in TESTS:   # unchanged held-out files: the notebook's before/after accuracy stays comparable with v4
        rows = jl(args.old_mixes / rel)
        (args.out / Path(rel).name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    cats = {}
    for r in B.rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print("humo coach rows by category:", dict(sorted(cats.items())))
    print("skipped:", B.skipped)
    for name, (n, t) in stats.items():
        print(f"{name:26s} {n:5d} rows  {t / 1e6:.2f}M tokens")
    print(f"TRAIN TOTAL: {sum(v[0] for v in stats.values())} rows, {sum(v[1] for v in stats.values()) / 1e6:.2f}M tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
