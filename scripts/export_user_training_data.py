"""Export learners' questions + approved tutor answers as fine-tuning data (same format as the training notebook).

    python scripts/export_user_training_data.py                 # new examples since the last export
    python scripts/export_user_training_data.py --all           # everything collected so far
    python scripts/export_user_training_data.py --mark-exported # remember what was exported

Needs SUPABASE_SECRET_KEY (env or .env). Keeps only examples that are reviewer-approved, verified by the exact
maths/code checks, not rated unhelpful, and that don't tell a correct learner they made a mistake. Drops user ids.
Writes LLM/data/user_training.jsonl (git-ignored: it contains learners' questions):
    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}], "source": "user-questions", "subject": ...}
Upload that file as a Kaggle dataset and run LLM/train/continue_training.py to keep training your adapter on it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import auth  # noqa: E402
from backend.training_store import TABLE, _MISTAKE_CLAIM  # noqa: E402

DEFAULT_OUT = ROOT / "LLM" / "data" / "user_training.jsonl"
PAGE = 500


def load_env_file() -> None:
    for name in (".env", ".env.local"):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def fetch(key: str, include_exported: bool) -> list:
    params = {
        "select": "id,subject,question,answer,student_correct,approved,verified,rating,created_at",
        "approved": "eq.true",
        "verified": "eq.true",
        "order": "created_at.asc",
    }
    if not include_exported:
        params["exported_at"] = "is.null"
    rows, start = [], 0
    while True:
        res = requests.get(f"{auth.supabase_url()}/rest/v1/{TABLE}", params=params, timeout=30,
                           headers={"apikey": key, "Range": f"{start}-{start + PAGE - 1}"})
        if res.status_code not in (200, 206):
            raise SystemExit(f"Supabase returned HTTP {res.status_code}: {res.text[:300]}")
        batch = res.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        start += PAGE


def keep(row: dict) -> tuple[bool, str]:
    if row.get("rating") == "unhelpful":
        return False, "rated unhelpful"
    q, a = (row.get("question") or "").strip(), (row.get("answer") or "").strip()
    if len(q) < 5 or len(a) < 20:
        return False, "too short"
    if row.get("student_correct") is True and _MISTAKE_CLAIM.search(a):
        return False, "told a correct learner they were wrong"
    return True, ""


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def to_training_row(row: dict) -> dict:
    return {
        "messages": [
            {"role": "user", "content": row["question"].strip()},
            {"role": "assistant", "content": row["answer"].strip()},
        ],
        "source": "user-questions",
        "subject": row.get("subject") or "",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--all", action="store_true", help="include examples exported before")
    ap.add_argument("--mark-exported", action="store_true", help="mark the exported examples so the next run skips them")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    load_env_file()
    key = (os.getenv("SUPABASE_SECRET_KEY") or "").strip()
    if not key:
        print("Set SUPABASE_SECRET_KEY in .env (Supabase dashboard > Settings > API Keys > Secret keys).", file=sys.stderr)
        return 2

    rows = fetch(key, include_exported=args.all)
    kept, skipped, seen = [], {}, set()
    for row in rows:
        ok, why = keep(row)
        if ok:
            k = normalise(row["question"])
            if k in seen:
                ok, why = False, "duplicate question"
            seen.add(k)
        if ok:
            kept.append(row)
        else:
            skipped[why] = skipped.get(why, 0) + 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(to_training_row(row), ensure_ascii=False) + "\n")

    if args.mark_exported and kept:
        now = datetime.now(timezone.utc).isoformat()
        ids = [r["id"] for r in kept]
        for i in range(0, len(ids), 100):
            res = requests.patch(f"{auth.supabase_url()}/rest/v1/{TABLE}", params={"id": f"in.({','.join(ids[i:i + 100])})"},
                                 json={"exported_at": now}, headers={"apikey": key, "Content-Type": "application/json"}, timeout=30)
            if res.status_code not in (200, 204):
                print(f"Warning: could not mark exported (HTTP {res.status_code})", file=sys.stderr)

    subjects = {}
    for r in kept:
        subjects[r.get("subject") or "?"] = subjects.get(r.get("subject") or "?", 0) + 1
    print(f"Fetched {len(rows)} approved+verified examples; kept {len(kept)}; skipped {sum(skipped.values())} {skipped or ''}")
    print(f"By subject: {subjects}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
