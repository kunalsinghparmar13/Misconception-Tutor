"""Upload the fine-tuned LoRA adapter in LLM/ to the Hugging Face Hub (free).

Why: the adapter weights (139 MB) are stored with Git LFS, and GitHub's free LFS allowance is small
(1 GB/month of downloads), so every fresh GPU notebook that clones the repo eats into it. A Hub model repo
has no such limit, and any free GPU notebook can load it by name.

    pip install huggingface_hub
    git lfs pull                                    # make sure the real weights are present
    HF_TOKEN=hf_xxx python scripts/push_adapter_to_hf.py <your-username>/misconception-tutor-gemma4-e4b [--public]

Create the token at https://huggingface.co/settings/tokens (role: write). Repos are private unless --public.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

LLM_DIR = Path(__file__).resolve().parents[1] / "LLM"
FILES = [
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "chat_template.jinja",
    "processor_config.json",
    "README.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_id", help="<username>/<repo-name> to create or update")
    parser.add_argument("--public", action="store_true", help="make the repo public (default: private)")
    args = parser.parse_args()

    weights = LLM_DIR / "adapter_model.safetensors"
    if not weights.exists() or weights.stat().st_size < 1_000_000:
        print("adapter_model.safetensors is missing or is a Git LFS pointer. Run `git lfs pull` first.", file=sys.stderr)
        return 1
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Set HF_TOKEN to a Hugging Face token with write access.", file=sys.stderr)
        return 1

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(args.repo_id, repo_type="model", private=not args.public, exist_ok=True)
    api.upload_folder(
        folder_path=str(LLM_DIR),
        repo_id=args.repo_id,
        repo_type="model",
        allow_patterns=[f for f in FILES if (LLM_DIR / f).exists()],
        commit_message="Upload fine-tuned Misconception Tutor LoRA adapter",
    )
    print(f"Uploaded. Use it with LLM_ADAPTER_PATH={args.repo_id} (and HF_TOKEN if the repo is private).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
