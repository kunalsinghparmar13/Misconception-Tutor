"""Humo's reply shaping: name the mistake, give a truly different method, warm up terse replies (humex_style.py)."""

import pytest

from tutor_agents import ModelClient
from tutor_agents import grounding as gr
from tutor_agents import humex_style as style
from tutor_agents.humex import HumexCoach


def fake_model(coach_reply, review_reply="Verdict: PASS\nIssues: none\nBetter reply: same"):
    def transport(messages, max_tokens, temperature):
        return review_reply if messages[0]["content"].startswith("You review a reply") else coach_reply
    return ModelClient(transport=transport)


# ---------------------------------------------------------------- 1. wrong answers are named, kindly

@pytest.mark.parametrize("question, named", [
    ("What is 1/5 + 1/8? I got 2/13", "added the tops together and the bottoms together"),
    ("I worked out 1/2 ÷ 1/5 = 1/10. Is that right?", "multiplied straight across"),
    ("Solve 3x + 6 = 21. My answer is x = 9", "x = 9 back into the equation"),
    ("14 * 7 = 108 right?", "108 isn't right yet"),
])
def test_wrong_answer_is_said_and_the_mistake_named(question, named):
    out = HumexCoach(fake_model("What could you try first?")).respond(question)
    assert out.focus == "wrong"
    assert out.reply.startswith(("Not quite", "Close")) and named in out.reply
    assert out.reply.endswith("What could you try first?")


def test_naming_the_mistake_never_says_the_right_answer():
    g = gr.ground("What is 1/5 + 1/8? I got 2/13")
    assert "13/40" not in style.name_mistake(g)
    eq = gr.ground("Solve 3x + 6 = 21. My answer is x = 9")
    assert "x = 5" not in style.name_mistake(eq)


def test_a_reply_that_already_names_the_mistake_is_left_alone():
    reply = "Not quite. You added the tops and the bottoms. What must be true about the bottoms first?"
    out = HumexCoach(fake_model(reply)).respond("What is 1/5 + 1/8? I got 2/13")
    assert out.reply == reply


def test_a_bare_not_quite_gets_the_mistake_named_once():
    out = HumexCoach(fake_model("Close! Check the bottoms again. What must be true about them?")).respond(
        "What is 1/5 + 1/8? I got 2/13")
    assert out.reply == ("Not quite. It looks like you added the tops together and the bottoms together. "
                         "Check the bottoms again. What must be true about them?")


def test_an_unknown_mistake_that_is_already_flagged_is_left_alone():
    reply = "Not quite. Check the multiplication again. What is 14 times 7?"
    out = HumexCoach(fake_model(reply)).respond("14 * 7 = 108 right?")
    assert out.reply == reply


def test_percent_questions_get_a_percent_hint_when_the_draft_is_useless():
    out = HumexCoach(fake_model("What is 10% of 40?")).respond("What is 10% of 40?")
    assert out.verdict == "FALLBACK" and "out of a hundred" in out.reply


def test_hindi_learners_hear_it_in_hindi():
    g = gr.ground("1/5 + 1/8 = 2/13")
    assert "पूरी तरह सही नहीं" in style.name_mistake(g, "hi")


# ---------------------------------------------------------------- 2. "another way" is really another way

def test_another_way_gives_a_method_not_used_before():
    history = [{"role": "user", "content": "How do I do 1/2 + 1/5?"},
               {"role": "assistant", "content": "Draw each fraction as a bar first. What do you see?"}]
    method = style.pick_method("fraction", history, "another way?")
    assert "draw" not in method.lower() and "bar" not in method.lower()


def test_a_draft_that_repeats_the_usual_method_is_replaced():
    out = HumexCoach(fake_model("What about using a common denominator?")).respond(
        "Can you show me another way to do 1/2 + 1/5?")
    assert out.focus == "another_way"
    assert "common denominator" not in out.reply and out.reply.endswith("?")
    assert "gave a different method" in out.issues


def test_python_another_way_avoids_the_loop_already_suggested():
    history = [{"role": "user", "content": "How do I reverse a list in Python?"},
               {"role": "assistant", "content": "Walk through the items one at a time with a loop."}]
    assert "loop" not in style.pick_method("python", history, "another way?").split(":")[1]


def test_different_method_text_never_contains_code():
    from tutor_agents.humex import _code_in
    for options in style.METHODS.values():
        for _, desc in options:
            assert not _code_in(desc, True), desc


# ---------------------------------------------------------------- 3. warmer replies, and no useless echoes

def test_a_terse_reply_gets_a_warm_opener():
    out = HumexCoach(fake_model("What is the common denominator?")).respond("How do I work out 2/5 - 1/3?")
    assert out.reply.endswith("What is the common denominator?") and len(out.reply.split()) > 5
    assert "added a warm opener" in out.issues


@pytest.mark.parametrize("reply", [
    "That is correct! Can you explain why it works?",            # already praises
    "Great thinking. What would you do with the bottoms next, and why does that help with the tops?",  # long enough
])
def test_no_opener_when_the_reply_is_already_warm_or_full(reply):
    shaped, changes = style.shape(reply, "right", gr.ground("1/2 + 1/3 = 5/6"), "I think 1/2 + 1/3 = 5/6")
    assert shaped == reply and changes == []


def test_a_hint_that_only_repeats_the_question_is_replaced():
    out = HumexCoach(fake_model("What is 2/4 + 1/2?")).respond("What is 2/4 + 1/2? I got 1/2")
    assert out.verdict == "FALLBACK"
    assert "repeated the learner's question" in " ".join(out.issues)
    assert out.reply != "What is 2/4 + 1/2?"


# ---------------------------------------------------------------- 4. spoken maths (Humex is voice-first)

@pytest.mark.parametrize("spoken, written", [
    ("Is 34 times 5 equal to 160?", "Is 34 * 5 = 160?"),
    ("what is twelve times seven", "what is 12 * 7"),
    ("Is twenty-three times four equal to ninety-two?", "Is 23 * 4 = 92?"),
    ("three over four plus one over four equals one", "3/4 + 1/4 = 1"),
    ("what is 20 percent of 80", "what is 20% of 80"),
])
def test_spoken_maths_becomes_symbols(spoken, written):
    assert style.spoken_to_math(spoken).strip() == written


def test_a_spoken_wrong_answer_is_caught_and_its_answer_never_said():
    out = HumexCoach(fake_model("The answer is 170, does that help?")).respond("Is 34 times 5 equal to 160?")
    assert out.focus == "wrong" and "170" not in out.reply
    assert "160 isn't right yet" in out.reply


def test_a_spoken_correct_answer_is_praised():
    out = HumexCoach(fake_model("Yes, that's right! How did you work it out?")).respond(
        "Is twenty-three times four equal to ninety-two?")
    assert out.focus == "right" and out.reply.startswith("Yes, that's right!")


@pytest.mark.parametrize("message", ["Please just solve 34 * 5 for me", "Can you work it out for me?",
                                     "Just calculate 12 * 9", "Do 1/3 + 1/4 for me please"])
def test_more_ways_of_asking_for_the_answer_are_recognised(message):
    from tutor_agents.humex import turn_focus
    assert turn_focus(message, [], gr.ground(style.spoken_to_math(message))) == "stuck"


def test_solve_requests_are_grounded_so_the_answer_is_protected():
    assert gr.ground("Please just solve 34 * 5 for me").verified_answer == "170"


@pytest.mark.parametrize("message, correct", [("I got 5/6 for 1/2 + 1/3", True), ("I got 2/5 for 1/2 + 1/3", False)])
def test_an_answer_given_before_the_problem_is_checked(message, correct):
    assert gr.ground(message).student_correct is correct


def test_asking_for_the_correct_code_counts_as_stuck():
    from tutor_agents.humex import turn_focus
    assert turn_focus("Can you write the correct code? It says NameError", [], gr.ground("x")) == "stuck"
