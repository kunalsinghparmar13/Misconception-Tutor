import json
import os

from huggingface_hub import HfApi, hf_hub_download
from peft import PeftConfig

REPO_ID = os.getenv(
    "LLM_ADAPTER_ID",
    "kunalsinghparmar/misconception-tutor-gemma4-e4b",
)

TOKEN = os.getenv("HF_TOKEN")

api = HfApi(token=TOKEN)

print(f"Checking Hugging Face repository: {REPO_ID}")

info = api.model_info(REPO_ID)

files = {item.rfilename for item in info.siblings}

required = {
    "adapter_config.json",
    "adapter_model.safetensors",
}

missing = required - files

if missing:
    raise RuntimeError(f"Missing required adapter files: {missing}")

config_path = hf_hub_download(
    repo_id=REPO_ID,
    filename="adapter_config.json",
    token=TOKEN,
)

with open(config_path, encoding="utf-8") as f:
    config_json = json.load(f)

peft_config = PeftConfig.from_pretrained(
    REPO_ID,
    token=TOKEN,
)

print("\nAdapter files found.")
print("Base model:", peft_config.base_model_name_or_path)
print("Task type:", peft_config.task_type)
print("Architecture mapping:", config_json.get("auto_mapping"))
print("Adapter weights:", "adapter_model.safetensors")