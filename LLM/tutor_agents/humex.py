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
from .model_client import ModelClient
from .prompts import HUMEX_COACH, HUMEX_HINT_LEVELS, HUMEX_REVIEWER

Message = Dict[str, str]

MAX_TURNS = 10            # conversation turns sent to the model
MAX_SPOKEN_WORDS = 90     # longer replies are too long to listen to
LANGUAGES = {
    "hi": "Reply in simple Hindi written in Devanagari script.",
    "en": "Reply in simple English.",
}

_ANSWER_PHRASES = re.compile(
    r"\b(final answer|the answer is|answer\s*(is|=|:)|the solution is|correct answer|so it equals|= *the answer)\b",
    re.IGNORECASE,
)
_CODE_BLOCK = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
_GIVE_UP = re.compile(r"\b(just tell me|give me the answer|tell me the answer|what'?s the answer|show me the answer)\b", re.I)


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


def check_reply(reply: str, g: gr.Grounding, learner_text: str) -> List[HumexCheck]:
    """Exact checks that do not trust the model."""
    checks: List[HumexCheck] = []
    learner_has_it = g.student_correct is True or _reveals_value(learner_text, g.verified_answer)

    leak = bool(g.verified_answer) and not learner_has_it and _reveals_value(reply, g.verified_answer)
    checks.append(HumexCheck("no_answer_leak", not leak,
                             f"says the answer {g.verified_answer}" if leak else ""))

    phrase = _ANSWER_PHRASES.search(reply)
    checks.append(HumexCheck("no_answer_phrase", phrase is None, f"uses '{phrase.group(0)}'" if phrase else ""))

    big_code = any(len([ln for ln in block.splitlines() if ln.strip()]) >= 3 for block in _CODE_BLOCK.findall(reply))
    checks.append(HumexCheck("no_full_code", not big_code, "contains a full code block" if big_code else ""))

    asks = "?" in reply or "？" in reply
    checks.append(HumexCheck("asks_question", asks, "" if asks else "does not ask the learner a question"))

    words = len(reply.split())
    checks.append(HumexCheck("short_for_voice", words <= MAX_SPOKEN_WORDS, f"{words} words" if words > MAX_SPOKEN_WORDS else ""))
    return checks


def _blocking(checks: List[HumexCheck]) -> List[HumexCheck]:
    """Leaks are never allowed through; the other checks are style and can be fixed by the reviewer."""
    return [c for c in checks if not c.ok and c.name in {"no_answer_leak", "no_answer_phrase", "no_full_code"}]


def fallback_hint(g: gr.Grounding, language: str) -> str:
    """A safe hint that cannot leak anything, used only when every model reply leaked the answer."""
    hi = language == "hi"
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
        level = 3 if _GIVE_UP.search(message) and hint_level(history) < 3 else hint_level(history)
        problem = _problem_text(history, message)
        g = gr.ground(problem, subject)
        facts = g.facts_block().replace("Verified facts", "Private facts") or "Private facts: none for this message."

        # 1. Coach draft
        system = HUMEX_COACH.format(language_rule=LANGUAGES[language], hint_level=HUMEX_HINT_LEVELS[level])
        convo = history + [{"role": "user", "content": f"{message}\n\n{facts}"}]
        draft_res = self.client.chat([{"role": "system", "content": system}] + convo, max_tokens=220, temperature=0.4)
        draft = _spoken(draft_res.text)
        checks = check_reply(draft, g, problem)

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
            candidate = _spoken(review["better"])
            if not _blocking(check_reply(candidate, g, problem)):
                reply, verdict = candidate, "REVISED"

        # 3. Safety net: the learner must never hear the answer
        final_checks = check_reply(reply, g, problem)
        if _blocking(final_checks):
            reply, verdict = fallback_hint(g, language), "FALLBACK"
            final_checks = check_reply(reply, g, problem)

        return HumexReply(reply=reply, verdict=verdict, issues=issues, checks=final_checks, hint_level=level,
                          kind=g.kind, seconds=round(time.time() - started, 2), model=draft_res.model)


def get_coach(client: Optional[ModelClient] = None) -> HumexCoach:
    """Uses the tutor pipeline's model client, so Humex talks to the same fine-tuned model as the rest of the app."""
    if client is None:
        from .pipeline import get_pipeline
        client = get_pipeline().client
    return HumexCoach(client)


__all__ = ["HumexCoach", "HumexReply", "check_reply", "fallback_hint", "get_coach"]
