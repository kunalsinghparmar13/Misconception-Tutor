"""
Tests for Indic Multilingual Socratic Engine and Symbolic Entity Shield.
"""

from backend.indic_tutor import (
    SymbolicEntityShield,
    INDIC_LANGUAGES,
    localize_tutor_response,
)


def test_symbolic_entity_shield():
    shield = SymbolicEntityShield()
    raw = "Adding $\\frac{1}{4} + \\frac{1}{6}$ using Python `def add(a, b):` should give 5/12."
    shielded, vault = shield.shield(raw)

    # Protected tokens should exist
    assert "__MATH_LATEX_" in shielded or "__FRAC_" in shielded or "__CODE_BLOCK_" in shielded
    assert len(vault) > 0

    # Unshield should restore exact text
    unshielded = shield.unshield(shielded, vault)
    assert unshielded == raw


def test_supported_indic_languages():
    assert "en" in INDIC_LANGUAGES
    assert "hi" in INDIC_LANGUAGES
    assert "hinglish" in INDIC_LANGUAGES
    assert "ta" in INDIC_LANGUAGES
    assert "te" in INDIC_LANGUAGES
    assert "bn" in INDIC_LANGUAGES
    assert "mr" in INDIC_LANGUAGES
    assert "gu" in INDIC_LANGUAGES
    assert "kn" in INDIC_LANGUAGES
    assert "ml" in INDIC_LANGUAGES
    assert "pa" in INDIC_LANGUAGES
    assert "or" in INDIC_LANGUAGES
    assert "ur" in INDIC_LANGUAGES


def test_localize_tutor_response_hindi():
    sample_result = {
        "misconception": "M1_add_across",
        "answer": "You added numerators directly.",
        "subject": "Mathematics",
    }
    localized = localize_tutor_response(sample_result, lang="hi")
    assert localized["localized"] is True
    assert localized["language"] == "hi"
    assert "अंश और हर" in localized["answer"]
    assert "Common Denominator" in localized["answer"] or "LCM" in localized["answer"]


def test_localize_tutor_response_hinglish():
    sample_result = {
        "misconception": "M1_add_across",
        "answer": "Direct addition across.",
        "subject": "Mathematics",
    }
    localized = localize_tutor_response(sample_result, lang="hinglish")
    assert localized["localized"] is True
    assert "numerators aur denominators" in localized["answer"]


def test_localize_tutor_response_tamil():
    sample_result = {
        "misconception": "M1_add_across",
        "answer": "Direct addition.",
        "subject": "Mathematics",
    }
    localized = localize_tutor_response(sample_result, lang="ta")
    assert localized["localized"] is True
    assert "பகுதிகளையும்" in localized["answer"] or "பின்னங்கள்" in localized["answer"]
