"""Humo, the Humex 3D voice tutor: a hint-only Socratic coach plus a reviewer.

Flow for every learner turn (spoken or typed):

    learner message ──► CoachAgent (hint or guiding question, never the answer)
                    ──► HumexReviewer
                          1. exact checks: does the draft leak the verified answer or the fixed code?
                             does it end with a question? is it short enough to speak?
                          2. model review: is the hint correct and helpful? if not, it writes a better reply
                    ──► final safety net: if the reply still leaks the answer, use a safe generic hint
                    ──► reply that the 3D avatar speaks

The exact answer is computed by ``grounding`` so the reviewer can catch leaks without trusting the model.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from . import grounding as gr
from .backends import trim_run_on
from .model_client import ModelClient
from .prompts import HUMEX_COACH, HUMEX_FOCUS, HUMEX_HINT_LEVELS, HUMEX_REVIEWER

Message = Dict[str, str]

MAX_TURNS = 10            # conversation turns sent to the model
MAX_SPOKEN_WORDS = 90     # longer replies are too long to listen to
LANGUAGES = {
    "hi": "Reply in simple Hindi written in Devanagari script.",
    "en": "Reply in simple English.",
}

# Phrases that hand over a result: "final answer / the answer is / answer = / the solution is / it equals" followed by an
# actual value (a number, x = ..., code). "Your answer is correct", "what is your final answer?" or "the answer is to find
# a common denominator" pass.
_ANSWER_PHRASES = re.compile(
    r"\b(final answer( is)?|the (correct |right )?answer is|answer\s*[=:]|the solution is|so it equals|the result is|"
    r"it equals)\s*:?\s*(-?\d|[a-z]\s*=|`|\$)",
    re.IGNORECASE,
)
_CODE_BLOCK = re.compile(r"```(?:\w+)?\n?(.*?)```", re.DOTALL)
# A line of Python: a statement keyword, a call like print(...), or an assignment such as total = 0.
_CODE_LINE = re.compile(
    r"^\s*(def |class |import |from \S+ import |for \w+ in |while .+:|if .+:\s*$|elif |else:|return\b|try:|except\b|"
    r"print\(|\w+(\.\w+)*\(.*\)\s*$|[A-Za-z_]\w*\s*(\[.*\])?\s*[-+*/]?=\s*[^=])",
    re.MULTILINE,
)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_CALL = re.compile(r"\b[a-z_][a-z0-9_]*(\.[a-z_]\w*)*\((?!s\))[^()\n]{0,40}\)")   # print(total), nums.sort(), len(x); not item(s)
_CODING_WORDS = re.compile(r"\b(python|code|coding|program|function|loop|list|dict|string|variable|error|bug|"
                           r"print|def|syntax|indent|traceback)\b", re.IGNORECASE)
_ANOTHER_WAY = re.compile(r"\b(another|other|different|new|alternative)\s+(way|method|approach)|\bany other way\b|"
                          r"दूसरा तरीका|और तरीका|अलग तरीका", re.IGNORECASE)
_GIVE_UP = re.compile(r"\b(just tell me|(give|show|send|tell) me the ((fixed|correct|right|working|full|complete|whole|"
                      r"final) )?(answer|code|solution|version|program)|tell me the answer|what'?s the answer|"
                      r"write (the|my|this) (code|program|function)|write it for me|solve it for me|"
                      r"(fix|solve|do|correct) (it|this|that|my code|the code) for me|just (fix|solve|do) (it|this)|"
                      r"i give up|i'?m stuck|i don'?t know)\b|उत्तर बताओ|जवाब बताओ|कोड दो", re.I)
# The learner describes how they intend to solve it and asks whether that works.
_PLAN = re.compile(r"\b(my plan|my approach|my idea|my method|i'?ll |i will |i'?m going to|i am going to|i plan to|"
                   r"i want to use|i'?d use|will (that|this|it) work|would (that|this|it) work|"
                   r"is (that|this) (right|a good|correct|ok|okay|the right))", re.I)


@dataclass
class HumexCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class HumexReply:
    reply: str
    verdict: str                      # PASS, REVISED or FALLBACK
    issues: List[str] = field(default_factory=list)
    checks: List[HumexCheck] = field(default_factory=list)
    hint_level: int = 1
    focus: str = "start"
    kind: str = "general"
    seconds: float = 0.0
    model: str = ""

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["review"] = {
            "verdict": self.verdict,
            "issues": self.issues,
            "checks": [asdict(c) for c in self.checks],
            "revised": self.verdict != "PASS",
        }
        return data


def clean_history(history: List[Dict[str, str]]) -> List[Message]:
    """Keep only well-formed user/assistant turns, newest last."""
    out: List[Message] = []
    for turn in history or []:
        role = str(turn.get("role", "")).strip().lower()
        text = str(turn.get("content", "")).strip()
        if role in ("user", "assistant") and text:
            out.append({"role": role, "content": text[:1600]})
    return out[-MAX_TURNS:]


def hint_level(history: List[Message]) -> int:
    """Hints get stronger the longer the learner has worked on the same problem (counted by tutor turns)."""
    tutor_turns = sum(1 for t in history if t["role"] == "assistant")
    return 1 if tutor_turns < 2 else 2 if tutor_turns < 4 else 3


def _problem_text(history: List[Message], message: str) -> str:
    """The learner's recent words, so a short follow-up like 'is it 7?' is grounded with its problem."""
    learner = [t["content"] for t in history if t["role"] == "user"][-3:]
    return "\n".join(learner + [message])


def _reveals_value(text: str, value: Optional[str]) -> bool:
    target = gr.parse_number(value or "")
    if target is None:
        return False
    return any(n == target for n in gr.numbers_in(text))


def is_coding(g: gr.Grounding, learner_text: str, subject: str = "") -> bool:
    """A programming conversation: grounding found code, the subject is Python, or the learner talks about code."""
    return g.is_code or subject.strip().lower() in {"python", "programming", "coding"} or bool(_CODING_WORDS.search(learner_text))


def _norm_code(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _code_in(raw: str, coding: bool, learner_text: str = "") -> str:
    """Describe any code in the reply ('' if none). In a coding chat even one line or `snippet` counts.
    Code the learner wrote themselves may be quoted back ("what does word.count('aeiou') count?"): that hands
    nothing over, so it is ignored."""
    theirs = _norm_code(learner_text)

    def new_code(snippet: str) -> bool:
        code = _norm_code(snippet)
        return bool(code) and code not in theirs

    blocks = [b for b in _CODE_BLOCK.findall(raw) if b.strip() and new_code(b)]
    if blocks and (coding or any(len([ln for ln in b.splitlines() if ln.strip()]) >= 3 for b in blocks)):
        return "contains a code block"
    if coding:
        prose = _CODE_BLOCK.sub("", raw)
        snippet = next((s for s in _INLINE_CODE.findall(prose) if re.search(r"[=(\[:]", s) and new_code(s)), None)
        if snippet:
            return f"contains code `{snippet}`"
        for pattern in (_CODE_LINE, _CALL):
            for m in pattern.finditer(prose):
                if new_code(m.group(0)):
                    return f"contains code '{m.group(0).strip()[:40]}'"
    return ""


def check_reply(reply: str, g: gr.Grounding, learner_text: str, coding: bool = False,
                raw: Optional[str] = None) -> List[HumexCheck]:
    """Exact checks that do not trust the model. ``raw`` is the model's text before markdown was stripped."""
    checks: List[HumexCheck] = []
    learner_has_it = g.student_correct is True or _reveals_value(learner_text, g.verified_answer)

    leak = bool(g.verified_answer) and not learner_has_it and _reveals_value(reply, g.verified_answer)
    checks.append(HumexCheck("no_answer_leak", not leak,
                             f"says the answer {g.verified_answer}" if leak else ""))

    # Once the learner has said the answer, confirming it ("yes, your answer is 5/12") reveals nothing.
    phrase = None if learner_has_it else _ANSWER_PHRASES.search(reply)
    checks.append(HumexCheck("no_answer_phrase", phrase is None, f"uses '{phrase.group(0).strip()}'" if phrase else ""))

    code = _code_in(raw if raw is not None else reply, coding, learner_text)
    checks.append(HumexCheck("no_full_code", not code, code))

    asks = "?" in reply or "？" in reply
    checks.append(HumexCheck("asks_question", asks, "" if asks else "does not ask the learner a question"))

    words = len(reply.split())
    checks.append(HumexCheck("short_for_voice", words <= MAX_SPOKEN_WORDS, f"{words} words" if words > MAX_SPOKEN_WORDS else ""))
    return checks


def turn_focus(message: str, history: List[Message], g: gr.Grounding) -> str:
    """What this reply must do: help pick an approach, correct a wrong one, confirm, offer another way, or unstick."""
    if _ANOTHER_WAY.search(message):
        return "another_way"
    if _GIVE_UP.search(message):
        return "stuck"
    if g.student_correct is False:
        return "wrong"
    if g.student_correct is True:
        return "right"
    if _PLAN.search(message):
        return "check_plan"
    return "continue" if any(t["role"] == "assistant" for t in history) else "start"


def _blocking(checks: List[HumexCheck]) -> List[HumexCheck]:
    """Leaks are never allowed through; the other checks are style and can be fixed by the reviewer."""
    return [c for c in checks if not c.ok and c.name in {"no_answer_leak", "no_answer_phrase", "no_full_code"}]


def fallback_hint(g: gr.Grounding, language: str, coding: bool = False) -> str:
    """A safe hint that cannot leak anything, used only when every model reply leaked the answer."""
    hi = language == "hi"
    if coding and g.kind != "python":
        return ("कोड लिखने से पहले, शब्दों में बताओ: प्रोग्राम को क्या लेना है, क्या करना है, और क्या दिखाना है?" if hi else
                "Before any code, say it in words: what does the program take in, what must it do, and what should it show?")
    if g.kind == "fraction":
        return ("चलो धीरे चलते हैं। भिन्नों को जोड़ने से पहले हरों के बारे में क्या सच होना चाहिए?" if hi else
                "Let's slow down. Before you combine the fractions, what has to be true about their denominators?")
    if g.kind == "equation":
        return ("x को अकेला करने के लिए, पहले कौन सा संख्या हटाओगे, और कैसे?" if hi else
                "To get x on its own, which number would you move first, and how would you undo it?")
    if g.kind == "python":
        return ("एरर मैसेज ध्यान से पढ़ो। किस लाइन पर रुकता है, और वहाँ कौन सा नाम या मान गायब है?" if hi else
                "Read the error message slowly. Which line does it stop on, and what name or value is missing there?")
    if g.kind == "arithmetic":
        return ("इसे छोटे हिस्सों में तोड़ो। पहले कौन सा आसान हिस्सा निकालोगे?" if hi else
                "Try breaking it into smaller, friendlier parts. Which easy part would you work out first?")
    return ("अच्छा सवाल है। तुम पहला कदम क्या लोगे, और क्यों?" if hi else
            "Good question. What would your very first step be, and why do you think so?")


def _parse_review(text: str) -> Dict[str, str]:
    out = {"verdict": "", "issues": "", "better": ""}
    m = re.search(r"Verdict:\s*(PASS|FAIL)", text, re.I)
    out["verdict"] = m.group(1).upper() if m else ""
    m = re.search(r"Issues:\s*(.+?)(?:\n\s*Better reply:|\Z)", text, re.I | re.S)
    out["issues"] = m.group(1).strip() if m else ""
    m = re.search(r"Better reply:\s*(.+)", text, re.I | re.S)
    better = m.group(1).strip().strip('"').strip() if m else ""
    out["better"] = "" if better.lower() in {"same", "none", "n/a", ""} else better
    return out


def _spoken(text: str) -> str:
    """Strip markdown that a voice would read out literally."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"[*_#`>]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class HumexCoach:
    """Runs coach -> reviewer -> safety net for one learner turn."""

    def __init__(self, client: ModelClient) -> None:
        self.client = client

    def respond(self, message: str, history: Optional[List[Dict[str, str]]] = None,
                language: str = "en", subject: str = "") -> HumexReply:
        started = time.time()
        history = clean_history(history or [])
        language = language if language in LANGUAGES else "en"
        problem = _problem_text(history, message)
        g = gr.ground(problem, subject)
        coding = is_coding(g, problem, subject)
        focus = turn_focus(message, history, g)
        level = min(3, hint_level(history) + 1) if focus == "stuck" else hint_level(history)
        facts = g.facts_block().replace("Verified facts", "Private facts") or "Private facts: none for this message."

        # 1. Coach draft
        system = HUMEX_COACH.format(language_rule=LANGUAGES[language], hint_level=HUMEX_HINT_LEVELS[level],
                                    focus=HUMEX_FOCUS[focus] + (" This is a programming question: ideas in words, no code."
                                                                 if coding else ""))
        convo = history + [{"role": "user", "content": f"{message}\n\n{facts}"}]
        draft_res = self.client.chat([{"role": "system", "content": system}] + convo, max_tokens=220, temperature=0.4)
        draft_raw = trim_run_on(draft_res.text)   # a reply that ran on wrote the learner's next turn itself
        draft = _spoken(draft_raw)
        checks = check_reply(draft, g, problem, coding, raw=draft_raw)

        # 2. Reviewer: model critique with the exact check results, may rewrite the reply
        transcript = "\n".join(f"{'Learner' if t['role'] == 'user' else 'Humo'}: {t['content']}" for t in history[-6:])
        check_lines = "\n".join(f"- {c.name}: {'ok' if c.ok else 'FAILED (' + c.detail + ')'}" for c in checks)
        review_prompt = (f"Conversation so far:\n{transcript or '(none)'}\nLearner: {message}\n\n{facts}\n\n"
                         f"Humo's draft reply:\n{draft}\n\nAutomatic checks:\n{check_lines}")
        review = {"verdict": "", "issues": "", "better": ""}
        try:
            review_res = self.client.chat(
                [{"role": "system", "content": HUMEX_REVIEWER.format(language_rule=LANGUAGES[language])},
                 {"role": "user", "content": review_prompt}],
                max_tokens=240, temperature=0.2)
            review = _parse_review(review_res.text)
        except Exception:  # noqa: BLE001 - the exact checks below still protect the learner
            review["issues"] = "model review unavailable"

        issues = [c.detail for c in checks if not c.ok and c.detail]
        if review["issues"] and review["issues"].lower() != "none":
            issues += [i.strip() for i in review["issues"].split(";") if i.strip()]

        reply, verdict = draft, "PASS"
        needs_fix = review["verdict"] == "FAIL" or bool(_blocking(checks))
        if needs_fix and review["better"]:
            better_raw = trim_run_on(review["better"])
            candidate = _spoken(better_raw)
            if candidate and not _blocking(check_reply(candidate, g, problem, coding, raw=better_raw)):
                reply, verdict = candidate, "REVISED"

        # 3. Safety net: the learner must never hear the answer
        final_checks = check_reply(reply, g, problem, coding, raw=draft_raw if reply == draft else None)
        if _blocking(final_checks):
            reply, verdict = fallback_hint(g, language, coding), "FALLBACK"
            final_checks = check_reply(reply, g, problem, coding)

        return HumexReply(reply=reply, verdict=verdict, issues=issues, checks=final_checks, hint_level=level, focus=focus,
                          kind=g.kind, seconds=round(time.time() - started, 2), model=draft_res.model)


def get_coach(client: Optional[ModelClient] = None) -> HumexCoach:
    """Uses the tutor pipeline's model client, so Humex talks to the same fine-tuned model as the rest of the app."""
    if client is None:
        from .pipeline import get_pipeline
        client = get_pipeline().client
    return HumexCoach(client)


__all__ = ["HumexCoach", "HumexReply", "check_reply", "fallback_hint", "get_coach", "is_coding", "turn_focus"]
