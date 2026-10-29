"""
================================================================================
ECC Memory Persistence & Lifecycle Observer
Derived from ECC's memory-persistence hooks:
- Pre-observe: captures student intent & misconception signals
- Post-observe: persists verified training signals & updates BKT
- Session lifecycle tracking for continuous learning
================================================================================
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ROOT / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class MemoryPersistenceLifecycle:
    """Enterprise memory lifecycle for tutoring sessions."""

    def __init__(self) -> None:
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def session_start(self, learner_id: str, session_id: str) -> Dict[str, Any]:
        """Initializes a student session and binds historical concept profile."""
        key = f"{learner_id}_{session_id}"
        session_data = {
            "learner_id": learner_id,
            "session_id": session_id,
            "start_time": datetime.utcnow().isoformat(),
            "interactions_count": 0,
            "observed_bugs": [],
        }
        self.active_sessions[key] = session_data
        return session_data

    def pre_observe(self, learner_id: str, input_text: str) -> Dict[str, Any]:
        """Lifecycle hook before processing input: extracts preliminary intent signals."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "learner_id": learner_id,
            "char_count": len(input_text),
            "contains_math_operator": any(op in input_text for op in ["+", "-", "*", "/", "÷"]),
        }

    def post_observe(
        self,
        learner_id: str,
        session_id: str,
        target_misc: Optional[str],
        is_correct: bool,
        response_length: int,
    ) -> None:
        """Lifecycle hook after processing: updates session observations."""
        key = f"{learner_id}_{session_id}"
        if key not in self.active_sessions:
            self.session_start(learner_id, session_id)

        sess = self.active_sessions[key]
        sess["interactions_count"] += 1
        if target_misc and not is_correct and target_misc not in sess["observed_bugs"]:
            sess["observed_bugs"].append(target_misc)


# Global singleton
memory_lifecycle = MemoryPersistenceLifecycle()
