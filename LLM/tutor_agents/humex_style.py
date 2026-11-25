"""Shaping Humo's spoken reply so it teaches well even when the small model's draft is thin.

A 200-question test of the fine-tuned humex model (2026-11-25) found three habits that prompts alone did not fix:

1. It never told a learner their answer was wrong; it just asked the next question.
2. Asked for "another way", it re-suggested the usual method.
3. Replies were terse (median 12 words): fine as text, cold when a 3D tutor says them out loud.

The tools already know when a maths answer is wrong and often which mistake it is, so these are fixed here with exact,
safe text that never contains the answer. Retraining the model (more Socratic dialogue data) is the long-term fix.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Tuple

from . import grounding as gr

Message = Dict[str, str]

# ------------------------------------------------------------------ 1. say kindly that it is wrong, and name the mistake

# The repo's known fraction misconceptions (backend_code.BUGS_ADD / BUGS_DIV), in words a learner understands.
MISTAKES = {
    "M1_add_across": ("Not quite. It looks like you added the tops together and the bottoms together.",
                      "पूरी तरह सही नहीं। लगता है तुमने ऊपर वाले अंक आपस में और नीचे वाले अंक आपस में जोड़ दिए।"),
    "M2_tops_add_bottoms_multiply": ("Not quite. It looks like you added the tops but multiplied the bottoms.",
                                     "पूरी तरह सही नहीं। लगता है तुमने ऊपर वाले अंक जोड़े पर नीचे वाले गुणा कर दिए।"),
    "M3_no_scaling": ("Close! You found a common bottom, but the tops need to change by the same amount too.",
                      "लगभग! साझा हर तो मिल गया, पर ऊपर वाले अंकों को भी उतना ही बदलना होगा।"),
    "M4_divide_multiply_across": ("Not quite. It looks like you multiplied straight across, but dividing works differently.",
                                  "पूरी तरह सही नहीं। लगता है तुमने सीधा गुणा कर दिया, पर भाग अलग तरह से होता है।"),
    "M5_flip_wrong_fraction": ("Close! You flipped a fraction, but it was the first one instead of the second.",
                               "लगभग! तुमने भिन्न उलटी तो की, पर दूसरी की जगह पहली।"),
}
# Words that show a reply already describes the specific mistake (so naming it again would repeat it).
MISTAKE_WORDS = {
    "M1_add_across": ("tops and the bottoms", "tops and bottoms", "added the tops", "add the tops", "added across",
                      "add across", "numerators and denominators", "numerators and the denominators"),
    "M2_tops_add_bottoms_multiply": ("multiplied the bottoms", "multiply the bottoms", "multiplied the denominators"),
    "M3_no_scaling": ("same amount", "scale the top", "scale the numerator", "change the tops", "change the numerators"),
    "M4_divide_multiply_across": ("straight across", "multiplied across", "multiply across"),
    "M5_flip_wrong_fraction": ("flipped the first", "flip the first", "wrong fraction"),
}
# A bare "not quite, 2/13 isn't right yet." sentence that says it is wrong without saying why.
_GENERIC_ACK = re.compile(r"^\s*(not quite|close|almost|hmm|nice try|good try|good effort)[^.!?]*?(isn'?t (yet )?right|not (yet )?right|"
                          r"isn'?t correct|not correct)?( yet)?[.!]\s*", re.IGNORECASE)
_ACKNOWLEDGES = re.compile(r"\b(not quite|close|almost|nearly|not (yet )?right|isn'?t (yet )?right|not correct|"
                           r"isn'?t correct|careful|mistake|hmm|wrong|good try|nice try|so close|let'?s check|"
                           r"doesn'?t (work|balance|match)|won'?t work|not the)\b|सही नहीं|लगभग|गलत", re.IGNORECASE)


def name_mistake(g: gr.Grounding, language: str = "en") -> Optional[str]:
    """One kind sentence saying the learner's answer is not right yet, naming the mistake when it is known.
    It may repeat the learner's own (wrong) answer, never the right one."""
    hi = language == "hi"
    if g.student_correct is not False:
        return None
    if g.misconception_id in MISTAKES:
        return MISTAKES[g.misconception_id][1 if hi else 0]
    their = g.student_answer or ""
    if g.kind == "equation" and their:
        return (f"लगभग, पर {their} रखकर देखो: दोनों तरफ़ बराबर नहीं होते।" if hi else
                f"Not quite. If you put {their} back into the equation, the two sides don't balance.")
    if their:
        return f"अभी {their} सही नहीं है।" if hi else f"Not quite, {their} isn't right yet."
    return "अभी पूरी तरह सही नहीं है।" if hi else "Not quite yet."


def acknowledges_mistake(reply: str) -> bool:
    return bool(_ACKNOWLEDGES.search(reply or ""))


# ------------------------------------------------------------------ 2. "another way": a genuinely different method

# Each method: (keywords that show it was already used, a spoken hint that describes it without the answer or code).
METHODS: Dict[str, List[Tuple[Tuple[str, ...], str]]] = {
    "fraction": [
        (("picture", "draw", "bar", "pizza"), "Try drawing it: sketch each fraction as a bar cut into equal pieces, then make the pieces the same size."),
        (("decimal",), "Here's a different way: turn each fraction into a decimal first, then combine the decimals."),
        (("number line",), "Here's a different way: put both fractions on a number line and count in equal steps."),
        (("list", "equivalent", "multiples"), "Here's a different way: list a few equivalent fractions for each one until two of them share a bottom."),
        (("multiply the bottoms", "product"), "Here's a different way: use the two bottoms multiplied together as the shared bottom, and simplify at the very end."),
    ],
    "percent": [
        (("10%", "ten percent", "divide by 10"), "Here's a different way: find 10% first by dividing by ten, then build up to the percent you need."),
        (("fraction", "quarter", "half"), "Here's a different way: turn the percent into a simple fraction, like 25% is one quarter."),
        (("decimal",), "Here's a different way: turn the percent into a decimal and multiply."),
    ],
    "equation": [
        (("balance", "scale"), "Try picturing a balance scale: whatever you do to one side, you must do to the other."),
        (("backwards", "undo", "reverse"), "Here's a different way: work backwards, undoing each step in reverse order."),
        (("guess", "try a value", "check"), "Here's a different way: guess a value for x, check both sides, then adjust up or down."),
    ],
    "arithmetic": [
        (("split", "tens", "break"), "Here's a different way: split one number into tens and ones, work out each part, then add them."),
        (("round",), "Here's a different way: round to an easier number first, then fix the small difference."),
        (("double", "halve"), "Here's a different way: double one number and halve the other to make an easier pair."),
    ],
    "python": [
        (("loop", "one at a time", "each item"), "Here's a different way: walk through the items one at a time with a loop and build the result yourself."),
        (("built-in", "builtin", "method"), "Here's a different way: look for a built-in function or method that already does most of the work."),
        (("slice", "slicing"), "Here's a different way: think about slicing, taking a piece of the sequence with a start, stop and step."),
        (("comprehension", "one line"), "Here's a different way: build the whole result in one line with a comprehension."),
        (("dictionary", "dict"), "Here's a different way: keep track of things in a dictionary, with a key for each item."),
        (("while",), "Here's a different way: use a while loop with your own counter instead of a for loop."),
        (("recursion", "recursive", "calls itself"), "Here's a different way: think recursively, solving a smaller version and building up."),
    ],
    "general": [
        (("smaller", "simpler"), "Here's a different way: try the same idea on a much smaller example first."),
        (("picture", "draw", "table"), "Here's a different way: draw a quick picture or a table of what you know."),
        (("backwards",), "Here's a different way: start from what you want to find and work backwards."),
    ],
}


def problem_kind(g: gr.Grounding, problem: str, coding: bool) -> str:
    if coding:
        return "python"
    if "%" in problem or "percent" in problem.lower():
        return "percent"
    return g.kind if g.kind in METHODS else "general"


def _stable_index(text: str, n: int) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % n if n else 0


def pick_method(kind: str, history: List[Message], message: str) -> str:
    """A method not already used in this conversation (checked by keywords), varied by the question."""
    seen = " ".join(t["content"] for t in history).lower()
    options = [desc for words, desc in METHODS[kind] if not any(w in seen for w in words)] or [d for _, d in METHODS[kind]]
    return options[_stable_index(message, len(options))]


def offers_new_method(reply: str, method: str) -> bool:
    """Did the reply describe the chosen method (any of its keywords), or say it is a different way?"""
    kind_words = next((words for kind in METHODS.values() for words, desc in kind if desc == method), ())
    low = (reply or "").lower()
    return any(w in low for w in kind_words)


# ------------------------------------------------------------------ 3. warmer, fuller replies for a spoken tutor

OPENERS = {
    "start": (["Good question!", "Nice, let's work it out together.", "Great question to ask."],
              ["अच्छा सवाल!", "चलो, साथ मिलकर हल करते हैं।"]),
    "right": (["Yes, that's right!", "Spot on!", "Exactly right, well done!"],
              ["हाँ, बिल्कुल सही!", "शाबाश, सही है!"]),
    "stuck": (["I know it feels tricky, and that's okay.", "No worries, we'll take it one small step at a time."],
              ["कोई बात नहीं, यह थोड़ा मुश्किल लगता है।", "चिंता मत करो, एक-एक छोटा कदम लेते हैं।"]),
    "continue": (["Okay, let's keep going.", "Good, let's build on that."],
                 ["ठीक है, आगे बढ़ते हैं।", "अच्छा, इसी पर आगे बढ़ते हैं।"]),
    "check_plan": (["Let's test your plan.", "Good that you planned first, let's check it."],
                   ["चलो तुम्हारी योजना जाँचते हैं।", "अच्छा किया कि पहले योजना बनाई, चलो जाँचें।"]),
}
_WARM_START = re.compile(r"^(yes|good|great|nice|well done|exactly|spot on|okay|ok|sure|let'?s|i know|i understand|"
                         r"no worries|that'?s|that is|you'?re|you are|close|not quite|almost|हाँ|अच्छा|शाबाश|ठीक|चलो|"
                         r"कोई बात)", re.IGNORECASE)
# Already warm anywhere in the reply (praise or encouragement): adding an opener would just repeat it.
_WARM_ANYWHERE = re.compile(r"\b(correct|well done|great|exactly|spot on|nice work|good job|good thinking|"
                            r"that'?s right|you got it)\b|शाबाश|बिल्कुल सही", re.IGNORECASE)
SHORT_REPLY_WORDS = 15


def warm_opener(focus: str, message: str, language: str = "en") -> Optional[str]:
    options = OPENERS.get(focus)
    if not options:
        return None
    pool = options[1 if language == "hi" else 0]
    return pool[_stable_index(focus + message, len(pool))]


def repeats_question(reply: str, message: str) -> bool:
    """A 'hint' that is just the learner's own question asked back ('What is 2/4 + 1/2?') teaches nothing."""
    core = lambda s: re.sub(r"[^a-z0-9/+\-*=×÷.]", "", (s or "").lower())   # noqa: E731
    r, m = core(reply), core(message)
    return len(r) >= 5 and r in m


def shape(reply: str, focus: str, g: gr.Grounding, message: str, language: str = "en",
          method: Optional[str] = None) -> Tuple[str, List[str]]:
    """Add what the model left out. Returns the reply and the list of changes made (for the review record)."""
    opener, change = None, ""
    known = g.misconception_id in MISTAKES
    if focus == "wrong" and known and not any(w in reply.lower() for w in MISTAKE_WORDS.get(g.misconception_id, ())):
        # The tools know exactly which mistake it is: say it, replacing a bare "not quite" so it is not said twice.
        rest = _GENERIC_ACK.sub("", reply.strip(), count=1) if acknowledges_mistake(reply) else reply.strip()
        return f"{name_mistake(g, language)} {rest}".strip(), ["named the mistake"]
    if focus == "wrong" and not acknowledges_mistake(reply):
        opener, change = name_mistake(g, language), "named the mistake"
    elif focus == "another_way" and method and language == "en" and not offers_new_method(reply, method):
        # The draft re-suggested the usual method: say the new one instead (mixing both would confuse the learner).
        return f"{method} Can you try the first step that way?", ["gave a different method"]
    elif (len(reply.split()) < SHORT_REPLY_WORDS and not _WARM_START.match(reply.strip())
          and not _WARM_ANYWHERE.search(reply)):
        opener, change = warm_opener(focus, message, language), "added a warm opener"
    if not opener:
        return reply.strip(), []
    return f"{opener} {reply.strip()}".strip(), [change]


# ------------------------------------------------------------------ 4. spoken maths -> symbols, for the exact checks

# Humex is voice-first: learners say "is 34 times 5 equal to 160", which the exact maths checks can't read. Converting
# it to "is 34 * 5 = 160" lets Humo know the answer is wrong (and keeps the answer-leak check working). Only used to
# ground the problem; the learner's own words are what the model reads.
_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_NUMBER_WORDS = re.compile(r"\b(?:(?:%s)(?:[\s-](?:%s))?|(?:%s)|(?:a|one) hundred)\b" % (
    "|".join(_TENS), "|".join(list(_UNITS)[1:10]), "|".join(_UNITS)), re.IGNORECASE)
_SPOKEN_OPS = [
    (r"\b(multiplied by|times)\b", " * "),
    (r"\bdivided by\b", " ÷ "),
    (r"\b(plus|added to)\b", " + "),
    (r"\b(minus|take away|subtract(ed)?)\b", " - "),
    (r"\b(?<=\d)\s*over\s*(?=\d)", "/"),            # "3 over 4" -> 3/4
    (r"\b(is equal to|equal to|equals|makes)\b", " = "),
    (r"\b(\d+)\s*percent\b", r"\1%"),
]


def _number_word(m: "re.Match[str]") -> str:
    words = m.group(0).lower().replace("-", " ").split()
    if words[-1] == "hundred":
        return "100"
    return str(sum(_TENS.get(w, _UNITS.get(w, 0)) for w in words))


def spoken_to_math(text: str) -> str:
    """'Is thirty four times five equal to one hundred sixty?' -> 'Is 34 * 5 = 100 60?' style symbols for the checks."""
    out = _NUMBER_WORDS.sub(_number_word, text or "")
    for pattern, repl in _SPOKEN_OPS:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", out)
