# Deploying Misconception Tutor for free

The app is two separate pieces, and they are hosted separately:

| Piece | What it is | Needs a GPU? | Where to host free |
|---|---|---|---|
| **Web app** | Flask + the UI (`Dockerfile`, `render.yaml`) | No | Render free web service |
| **Model server** | Your fine-tuned Gemma adapter behind an OpenAI-style API (`LLM/serve/model_server.py`) | Yes | Kaggle notebook + tunnel (free), Modal free credits, or your own GPU PC |

The app never loads the model itself in production. It calls `LLM_BACKEND_URL`. If the model is unreachable,
the app answers **503 "model offline"**; it does not make up canned text.

Free GPU hosting changes often. Everything below was checked in Nov 2026, but confirm each platform's current terms.

## Which free host should I use? (checked Nov 2026)

| Host | Charges? | How long it stays up | Verdict |
|---|---|---|---|
| **Modal** | $0 on the Starter plan: $30 of free credit every month, billed per second, nothing while idle | Always reachable, wakes itself in about a minute | **Best primary.** Roughly 35-50 GPU-hours/month for an L4/T4-class GPU. A card may be requested at signup; set a **spending limit of $0** in Settings so you can never be charged |
| **Kaggle + tunnel** | Never charges | Up to 12 h per session, about 30 GPU-hours/week, but you must start it by hand and the URL changes | **Best backup** (about 4x more free GPU time than Modal, zero billing risk) |
| **HF ZeroGPU** | Free | Only ~3.5-5 GPU-minutes per day on free accounts, and Spaces hosting is tied to Gradio `@spaces.GPU` calls | **Not usable**: one tutor answer makes four model calls |

Recommended: Modal for the live URL, Kaggle when the Modal credit runs out or for a long demo day.

## 1. Host the model

### Option A - Kaggle notebook + Cloudflare tunnel (free, temporary)
Best fit for you: your adapter was trained on Kaggle.

1. (Recommended) Upload the adapter to the Hugging Face Hub once, so notebooks don't pull 139 MB from GitHub LFS (small free bandwidth):
   `HF_TOKEN=hf_xxx python scripts/push_adapter_to_hf.py <user>/misconception-tutor-gemma4-e4b`
2. On Kaggle: New Notebook -> import `LLM/serve/serve-model.ipynb` -> Accelerator **GPU T4/P100**, **Internet on**.
3. Fill `HF_ADAPTER_ID` in cell 3 (or leave empty to use GitHub LFS), then Run All.
4. The last cells print `LLM_BACKEND_URL=https://....trycloudflare.com` and `LLM_BACKEND_TOKEN=...`.

Limits: the session ends when idle or when your weekly GPU quota runs out, and the URL changes every run, so you must update
`LLM_BACKEND_URL` in the app each time. Start it ~15 minutes before any demo. Check Kaggle's rules on running a public tunnel.
Google Colab's free tier reportedly restricts web servers/tunnels, so it isn't recommended.

### Option B - Modal (free monthly credits, stable URL, scales to zero)
```bash
pip install modal && modal setup
modal secret create tutor-model-secrets MODEL_SERVER_TOKEN=<long-random-string>   # add HF_TOKEN=... if the adapter repo is private
modal deploy modal_app.py
```
Modal prints a permanent `https://...modal.run` URL. Use that as `LLM_BACKEND_URL` and the same string as `LLM_BACKEND_TOKEN`.
The first request after idle takes about a minute (cold start). Free credits are limited; set a spend limit in the Modal dashboard.
`modal_app.py` was written but not deployed during development - watch the first build log.

### Option C - Your own GPU PC (free, you control it)
```bash
pip install -r requirements-gpu.txt -r LLM/serve/requirements-serve.txt
MODEL_SERVER_TOKEN=<random> LLM_ADAPTER_PATH=LLM python -m serve.model_server   # run from the LLM/ folder
cloudflared tunnel --url http://127.0.0.1:8001
```

### Not recommended
- **Hugging Face Docker Spaces with GPU**: paid. **ZeroGPU**: small daily quota and a different programming model.
- **CPU-only hosting** (Render, HF CPU Space): the 4-bit E4B model needs a GPU. A GGUF/llama.cpp conversion might run on CPU, but that is untested for this model.

## 2. Host the web app (Render free)
1. Push the repo to GitHub, then on render.com choose **New -> Blueprint** and select it (`render.yaml` is included).
2. Set the secret env vars: `LLM_BACKEND_URL`, `LLM_BACKEND_TOKEN`. `ADMIN_TOKEN` is generated for you.
3. Open the `/api/health` URL. `"loaded": true` means the app can reach your model.

Render's free tier sleeps after idle (about 30-60 s wake-up). Any Docker host works too: `docker compose up --build`.

## 3. Environment variables

| Variable | Where | Meaning |
|---|---|---|
| `LLM_BACKEND_URL` | app | Base URL of the model server (no trailing path) |
| `LLM_BACKEND_TOKEN` | app | Must equal the model server's `MODEL_SERVER_TOKEN` |
| `MODEL_SERVER_TOKEN` | model server | Bearer token required on `/v1/*` |
| `LLM_ADAPTER_PATH` / `LLM_ADAPTER_ID` | model server | Local folder or Hub id of the adapter |
| `LLM_ONLY_MODEL` | app | Default on: 503 instead of canned text |
| `LLM_PIPELINE` | app | `0` turns the 4-agent pipeline off |
| `TUTOR_MAX_CONCURRENT` | app | Simultaneous tutor requests (default 2) |
| `TUTOR_FAST` | app | Default `1`: short outputs, 3 practice problems, no retry or model self-review (about 3 model calls). `0` = full depth, much slower on a free T4 |
| `TUTOR_CACHE` | app | Default `1`: identical questions are replayed instantly. `0` turns it off |
| `PRACTICE_COUNT` | app | Practice problems per answer (default 3 in fast mode, else 6) |
| `LLM_BACKEND_TIMEOUT` | app | Seconds to wait for the model (default 180) |
| `LLM_LOCAL_MODEL` | app | `1` loads the model inside the app (GPU host only) |
| `ADMIN_TOKEN`, `APP_ENV` | app | Protect admin routes; `production` hardens defaults |

## 4. Troubleshooting
- Banner says "model offline": the notebook stopped or the tunnel URL changed. Rerun it and update `LLM_BACKEND_URL`.
- 401 from the model: `LLM_BACKEND_TOKEN` differs from `MODEL_SERVER_TOKEN`.
- Slow first answer: the four agents make several model calls; a T4 takes tens of seconds per full answer.

## 5. Deploy the web app on any free Docker host

The image reads `PORT` from the host, so the same `Dockerfile` works unchanged on Render, Koyeb, Fly.io, Google Cloud Run
and Railway (free tiers and limits change - check each). On every host you only set the variables in `.env.example`:
`LLM_BACKEND_URL`, `LLM_BACKEND_TOKEN` and `ADMIN_TOKEN` (plus `APP_ENV=production`, `LLM_ONLY_MODEL=1`).

- **Render:** New -> Blueprint -> pick this repo (uses `render.yaml`), then paste the two model values when asked.
- **Anywhere else:** create a web service from the GitHub repo using the `Dockerfile`, set the health check path to `/api/health`,
  add the variables above.
- **Your own computer:** `cp .env.example .env`, fill it in, then `docker compose up --build`.

Because the Kaggle tunnel address changes every restart, update `LLM_BACKEND_URL` / `LLM_BACKEND_TOKEN` on your host each time
(Modal's address is permanent, so it avoids this).
