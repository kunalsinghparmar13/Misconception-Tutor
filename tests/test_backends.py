"""Adapter selection and Qwen/Gemma handling in the model loader (no GPU needed: only the helpers run)."""

import json

import pytest

from tutor_agents import backends as b


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("LLM_ADAPTER_PATH", "LLM_NOTEBOOK_ADAPTER_PATH", "LLM_ADAPTER_ID", "LLM_MODEL_FAMILY", "LLM_THINKING"):
        monkeypatch.delenv(name, raising=False)


def write_adapter(folder, base):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": base}))
    return folder


def test_humex_qwen_adapter_is_the_default(monkeypatch, tmp_path):
    llm = tmp_path / "LLM"
    write_adapter(llm, "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit")
    humex = write_adapter(llm / "humex", "unsloth/Qwen3.5-4B")
    monkeypatch.setattr(b, "LLM_DIR", llm)
    monkeypatch.setattr(b, "HUMEX_DIR", humex)
    assert b.adapter_location() == str(humex)
    assert b.model_family() == "qwen"
    assert b.default_model_name().startswith("humex-qwen35-4b")


def test_falls_back_to_gemma_when_humex_is_missing(monkeypatch, tmp_path):
    llm = write_adapter(tmp_path / "LLM", "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit")
    monkeypatch.setattr(b, "LLM_DIR", llm)
    monkeypatch.setattr(b, "HUMEX_DIR", llm / "humex")
    assert b.adapter_location() == str(llm)
    assert b.model_family() == "gemma"


def test_explicit_settings_win(monkeypatch, tmp_path):
    gemma = write_adapter(tmp_path / "g", "unsloth/gemma-4-E4B-it")
    monkeypatch.setenv("LLM_ADAPTER_PATH", str(gemma))
    assert b.adapter_location() == str(gemma) and b.model_family() == "gemma"
    monkeypatch.setenv("LLM_MODEL_FAMILY", "qwen")
    assert b.model_family() == "qwen"


def test_hub_id_family_is_guessed_from_its_name(monkeypatch):
    monkeypatch.setenv("LLM_ADAPTER_ID", "someone/humex-qwen35-4b-lora")
    assert b.model_family() == "qwen"


def test_thinking_is_off_for_serving_unless_asked(monkeypatch):
    assert b.template_kwargs("qwen") == {"enable_thinking": False}
    monkeypatch.setenv("LLM_THINKING", "1")
    assert b.template_kwargs("qwen") == {"enable_thinking": True}
    assert b.template_kwargs("gemma") == {}   # Gemma's template has no thinking switch


@pytest.mark.parametrize("raw, spoken", [
    ("<think>\nthe answer is 5/12\n</think>\n\nWhat number can 4 and 6 share?", "What number can 4 and 6 share?"),
    ("reasoning the prompt opened</think>Nice try! What is 4 x 3?", "Nice try! What is 4 x 3?"),
    ("Plain reply without thinking?", "Plain reply without thinking?"),
    ("<think>still thinking when tokens ran out", ""),
])
def test_thinking_is_never_spoken(raw, spoken):
    assert b.strip_thinking(raw) == spoken


def test_repo_humex_folder_is_a_loadable_qwen_adapter():
    humex = b.LLM_DIR / "humex"
    assert b.model_family(str(humex)) == "qwen"
    assert b.base_model_id(str(humex)) == "unsloth/Qwen3.5-4B"
    for name in ("adapter_config.json", "tokenizer_config.json", "tokenizer.json", "chat_template.jinja"):
        assert (humex / name).exists(), name
    assert "enable_thinking" in (humex / "chat_template.jinja").read_text()
