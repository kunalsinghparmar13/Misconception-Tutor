# Hugging Face GPU deployment

The free CPU tier can host the web UI, but it cannot load the published
4-bit Gemma adapter. Use a Hugging Face Space with GPU hardware, such as a
T4 Small, to get answers from:

`kunalsinghparmar/misconception-tutor-gemma4-e4b`

GPU hardware is billed by Hugging Face. Stop the Space when you are not testing.

## Create the Space

1. Open <https://huggingface.co/new-space>.
2. Create a **Docker** Space named `misconception-tutor`.
3. Select GPU hardware in the Space settings.
4. From this repository, push the GPU Dockerfile:

```bash
git remote add space https://huggingface.co/spaces/<HF_USERNAME>/misconception-tutor
cp Dockerfile.hf-gpu Dockerfile
git add Dockerfile .dockerignore HF_GPU_DEPLOYMENT.md
git commit -m "deploy tutor on Hugging Face GPU"
git push space main
```

## Space variables

Add these public variables in **Settings → Variables and secrets**:

```text
LLM_ADAPTER_ID=kunalsinghparmar/misconception-tutor-gemma4-e4b
LLM_ONLY_MODEL=1
```

If the model repository is private or gated, add `HF_TOKEN` as a secret.
Never commit the token or put it in a public variable.

## Verify the model

Open the Space URL and check:

```text
/api/health
```

The response should report:

```json
{
  "llm": {
    "loaded": true,
    "modelOnly": true,
    "mode": "PEFT Adapter (Gemma-4B)"
  }
}
```

Then send a question in the UI. If the response says `model_unavailable`, read
the Space logs. The usual causes are insufficient GPU memory, a missing
Hugging Face secret for a private model, or a mismatch between the adapter and
its base model.
