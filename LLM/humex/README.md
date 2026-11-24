# humex: Qwen3.5-4B tutor adapter

The LoRA adapter the Humex 3D tutor uses to answer. It is not a full model: it sits on top of the
base model `unsloth/Qwen3.5-4B`, which is downloaded from Hugging Face the first time it loads.

| | |
|---|---|
| Base model | `unsloth/Qwen3.5-4B` |
| Adapter | LoRA, rank 32, alpha 32, about 65M trainable weights (1.41% of the model) |
| Version | v4 (Kaggle notebook version 13) |
| Accuracy on held-out math and logic | 12.5% (base model) to 73.4% |

## What it was trained on

Four rounds, each continuing from the previous adapter, about 22,800 rows from 18 datasets:

- **Socratic tutoring:** SocraTeach, SocratiQ, PACT, Socratic Dataset 1680, Socratic debugging dialogues
- **Math:** OpenR1-Math, OpenThoughts-114k, OpenThoughts3, EduMath, PyRe-v2 (GSM8K part)
- **Logic:** ProofWriter, FOLIO, P-FOLIO, RuleCollection-32K
- **Code:** NPset, OpenCodeReasoning-2, PyRe-v2 (code part), pythink-20k, CodeXGLUE Bugs2Fix

A fifth round on LIMO (v5) scored lower (70.3% to 62.5%), so v4 is the one kept here.

Several of these datasets are licensed for non-commercial use only (for example SocraTeach and
EduMath), so check them before using this adapter in a paid product.

## Loading it

```python
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoTokenizer

base = AutoModelForImageTextToText.from_pretrained("unsloth/Qwen3.5-4B", torch_dtype="auto", device_map="auto")
model = PeftModel.from_pretrained(base, "LLM/humex")
tokenizer = AutoTokenizer.from_pretrained("unsloth/Qwen3.5-4B")

messages = [{"role": "user", "content": "I think 1/2 + 1/3 = 2/5. Is that right?"}]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=True)
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
print(tokenizer.decode(model.generate(**inputs, max_new_tokens=1024)[0][inputs["input_ids"].shape[1]:]))
```

Use `enable_thinking=True` for math, logic and code (it was trained to reason in `<think>` first)
and `False` for short conversational replies. It needs a GPU with about 10 GB of memory in 16-bit.

## Serving it in the app

The model server picks this folder by default (before the older Gemma adapter in `LLM/`) and detects
from `adapter_config.json` that it is a Qwen adapter, so it uses the chat template saved here:

```bash
python LLM/serve/model_server.py        # on a GPU machine; serves an OpenAI-style API on :8001
```

Then start the app with `LLM_BACKEND_URL` pointing at that server. Humo (`/api/humex/chat`) sends every
reply through the hint-only coach and the reviewer before the 3D avatar speaks it.

| Setting | Default | Meaning |
|---|---|---|
| `LLM_ADAPTER_PATH` | `LLM/humex` | another adapter folder or Hugging Face repo id |
| `LLM_THINKING` | `0` | `1` lets Qwen think step by step first (better on hard problems, much slower to speak) |
| `LLM_LOAD_4BIT` | `1` | `0` loads 16-bit weights (needs about 10 GB of GPU memory) |
| `LLM_GEN_BACKEND` | `auto` | `unsloth` or `peft` |
