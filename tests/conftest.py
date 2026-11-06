"""Shared test setup: keep tests away from the real dataset/database and the real model."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "LLM"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Legacy tests exercise the deterministic engine; model-only behaviour has its own tests.
os.environ.setdefault("LLM_ONLY_MODEL", "0")
os.environ.setdefault("TUTOR_FAST", "0")  # fast mode has its own tests
os.environ.setdefault("TUTOR_CACHE", "0")
os.environ.pop("LLM_BACKEND_URL", None)
os.environ.pop("LLM_LOCAL_MODEL", None)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_dataset(tmp_path, monkeypatch):
    """Never append test traffic to the committed training dataset."""
    try:
        from backend import llm_engine as engine_module
    except Exception:  # pragma: no cover
        yield
        return
    monkeypatch.setattr(engine_module, "TRAINING_DATASET_PATH", tmp_path / "dataset.jsonl")
    engine_module.llm_engine._seed_initial_training_samples()
    yield
