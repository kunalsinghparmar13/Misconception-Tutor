"""Keep training your fine-tuned adapter on learners' questions (Kaggle, free T4 GPU).

The model keeps everything it already learned: training starts FROM your current adapter (not from the base
model) at a gentle learning rate, and a sample of your original training data is mixed in ("replay") so the
new learner examples add to the old skills instead of overwriting them. Same recipe as LLM/tutor-project.ipynb
(Unsloth + TRL SFT, Gemma-4 chat template, loss on the tutor's replies only).

Kaggle notebook: GPU T4, Internet on, and attach as inputs:
  1. your current adapter dataset (folder with adapter_config.json + adapter_model.safetensors)
  2. a dataset with user_training.jsonl     (from scripts/export_user_training_data.py)
  3. optional: a dataset with llm_train.jsonl (your original training data, for replay)
Then run:
  !rm -rf /kaggle/working/app && git clone --depth 1 https://github.com/kunalsinghparmar13/Misconception-Tutor.git /kaggle/working/app
  !pip install -q unsloth
  !python /kaggle/working/app/LLM/train/continue_training.py

Output: /kaggle/working/<adapter>-learners-<date>/ (+ .zip) - the new adapter. To serve it right away in the
same session:  LLM_ADAPTER_PATH=<that folder> python /kaggle/working/app/LLM/serve/kaggle_serve_fast.py
Settings (env): EPOCHS (1), LEARNING_RATE (2e-5), REPLAY_RATIO (3 old examples per learner example),
MAX_REPLAY (3000), MAX_SEQ (1024), EVAL_FRACTION (0.1), SEED (42).
"""

from __future__ import annotations

import glob
import json
import os
import random
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

INPUT = Path(os.getenv("KAGGLE_INPUT", "/kaggle/input"))
WORK = Path(os.getenv("KAGGLE_WORKING", "/kaggle/working"))
EPOCHS = float(os.getenv("EPOCHS", "1"))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "2e-5"))
REPLAY_RATIO = float(os.getenv("REPLAY_RATIO", "3"))
MAX_REPLAY = int(os.getenv("MAX_REPLAY", "3000"))
MAX_SEQ = int(os.getenv("MAX_SEQ", "1024"))
EVAL_FRACTION = float(os.getenv("EVAL_FRACTION", "0.1"))
SEED = int(os.getenv("SEED", "42"))
BASE_MODEL = os.getenv("BASE_MODEL", "unsloth/gemma-4-E4B-it")


def find_one(pattern: str, what: str, required: bool = True):
    explicit = os.getenv(what.upper().replace(" ", "_") + "_PATH")
    if explicit:
        return Path(explicit)
    hits = sorted(glob.glob(str(INPUT / "**" / pattern), recursive=True))
    if not hits:
        if required:
            raise SystemExit(f"Could not find {what} ({pattern}) under {INPUT}. Attach it as a notebook input.")
        return None
    print(f"{what}: {hits[0]}", flush=True)
    return Path(hits[0])


def load_jsonl(path: Path) -> list:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def valid(row: dict) -> bool:
    msgs = row.get("messages") or []
    return (len(msgs) >= 2 and msgs[0].get("role") == "user" and msgs[-1].get("role") == "assistant"
            and all(str(m.get("content", "")).strip() for m in msgs))


def build_dataset(rng: random.Random):
    learner = [r for r in load_jsonl(find_one("user_training*.jsonl", "learner data")) if valid(r)]
    if not learner:
        raise SystemExit("user_training.jsonl has no usable examples. Export again once learners have asked questions.")
    rng.shuffle(learner)
    n_eval = max(1, int(len(learner) * EVAL_FRACTION)) if len(learner) >= 10 else 0
    learner_eval, learner_train = learner[:n_eval], learner[n_eval:]

    replay = []
    original = find_one("llm_train.jsonl", "original data", required=False)
    if original:
        old = [r for r in load_jsonl(original) if valid(r)]
        rng.shuffle(old)
        replay = old[: min(MAX_REPLAY, int(len(learner_train) * REPLAY_RATIO))]
    else:
        print("No llm_train.jsonl attached: training on learner data only (still starting from your adapter).", flush=True)

    train = learner_train + replay
    rng.shuffle(train)
    print(f"Training rows: {len(learner_train)} learner + {len(replay)} replay = {len(train)}; eval rows: {len(learner_eval)}",
          flush=True)
    return train, learner_eval, {"learner_train": len(learner_train), "replay": len(replay), "eval": len(learner_eval)}


def main() -> None:
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template, train_on_responses_only

    rng = random.Random(SEED)
    adapter = find_one("adapter_config.json", "current adapter").parent
    train_rows, eval_rows, counts = build_dataset(rng)

    # Start FROM the current fine-tuned adapter, so everything it already learned is kept.
    model, tokenizer = FastModel.from_pretrained(model_name=str(adapter), max_seq_length=MAX_SEQ,
                                                 load_in_4bit=True, full_finetuning=False)
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    print("Loaded adapter:", adapter, "| GPU:", torch.cuda.get_device_name(0), flush=True)

    def fmt(row):
        merged = []
        for m in row["messages"]:
            content = str(m.get("content", "")).strip()
            if merged and merged[-1]["role"] == m["role"]:
                merged[-1]["content"] += "\n\n" + content
            else:
                merged.append({"role": m["role"], "content": content})
        return {"text": tokenizer.apply_chat_template(merged, tokenize=False, add_generation_prompt=False)}

    train_ds = Dataset.from_list(train_rows).map(fmt, remove_columns=list(train_rows[0].keys()))
    eval_ds = Dataset.from_list(eval_rows).map(fmt, remove_columns=list(eval_rows[0].keys())) if eval_rows else None

    args = SFTConfig(
        output_dir=str(WORK / "continue_outputs"),
        dataset_text_field="text",
        max_seq_length=MAX_SEQ,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=EPOCHS,
        learning_rate=LEARNING_RATE,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="epoch" if eval_ds is not None else "no",
        save_strategy="no",
        seed=SEED,
        report_to="none",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
    )
    try:
        trainer = SFTTrainer(model=model, processing_class=tokenizer, train_dataset=train_ds, eval_dataset=eval_ds, args=args)
    except TypeError:  # older TRL
        trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=train_ds, eval_dataset=eval_ds, args=args)
    # Learn the tutor's replies only, like the original training run.
    trainer = train_on_responses_only(trainer, instruction_part="<|turn>user\n", response_part="<|turn>model\n")

    before = trainer.evaluate()["eval_loss"] if eval_ds is not None else None
    started = time.time()
    stats = trainer.train()
    after = trainer.evaluate()["eval_loss"] if eval_ds is not None else None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    out = WORK / f"{adapter.name}-learners-{stamp}"
    model.save_pretrained(str(out))
    tokenizer.save_pretrained(str(out))
    template = adapter / "chat_template.jinja"
    if template.exists() and not (out / "chat_template.jinja").exists():
        shutil.copy(template, out / "chat_template.jinja")
    info = {
        "continued_from": str(adapter), "base_model": BASE_MODEL, "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
        "max_seq": MAX_SEQ, "rows": counts, "train_loss": round(stats.training_loss, 4),
        "eval_loss_before": before, "eval_loss_after": after, "minutes": round((time.time() - started) / 60, 1),
        "finished_utc": stamp,
    }
    (out / "run_info.json").write_text(json.dumps(info, indent=2))
    zip_path = shutil.make_archive(str(out), "zip", str(out))
    print(json.dumps(info, indent=2))
    if before is not None and after is not None:
        print(f"Loss on held-out learner questions: {before:.4f} -> {after:.4f} "
              f"({'better' if after < before else 'NOT better - check the data before using this adapter'})")
    print("New adapter:", out)
    print("Zip:", zip_path)
    print(f"Serve it now:  LLM_ADAPTER_PATH={out} python /kaggle/working/app/LLM/serve/kaggle_serve_fast.py")


if __name__ == "__main__":
    main()
