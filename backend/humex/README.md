# Humex backend

The server side of **Humo**, the 3D voice tutor on the Humex page (`UI and UX/code.html`).
It takes what the learner said or typed from the app, gets a hint-only reply from the Humex LLM,
has a reviewer check that reply, and sends it back for the 3D avatar to speak.

## How a message travels

```
 Learner speaks or types
        │  (browser speech recognition turns voice into text)
        ▼
 Humex page  ── POST /api/humex/chat ─────────────────────────►  Humex backend (this folder)
 UI and UX/code.js   {message, history, language, subject}        routes.py
                                                                    1. clean the text, check sign-in,
                                                                       block prompt injection
                                                                    2. ask the Humex LLM ───────────────►  model server (GPU)
                                                                       coach: one hint or question         LLM/serve/model_server.py
                                                                       reviewer: is it correct? does it    + LLM/humex adapter
                                                                       give away the answer? rewrite if    (Qwen3.5-4B)
                                                                       needed  ◄──────────────────────────
                                                                    3. safety net: never the answer
 Humex page  ◄────────────── {reply, review} ──────────────────────
        │
        ▼
 The 3D avatar speaks the reply (browser speech synthesis + talking animation)
```

## Files

| File | What it does |
|---|---|
| `routes.py` | The HTTP routes: `POST /api/humex/chat` and `GET /api/humex/health` |
| `model.py` | The link to the Humex LLM: Humo's own model server, or the app's shared one |
| `config.py` | Settings read from environment variables |
| `server.py` | Runs only the Humex backend, if you want to host it separately |
| `../../LLM/tutor_agents/humex.py` | The coach and reviewer that write and check each reply |
| `../../LLM/humex/` | The fine-tuned Qwen3.5-4B adapter |

## API

**`POST /api/humex/chat`** (needs a signed-in user unless `AUTH_REQUIRED=0`)

```json
{
  "message": "What is 1/4 + 1/6? I got 2/10",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "language": "en",
  "subject": ""
}
```

Reply:

```json
{
  "status": "ok",
  "reply": "Nice try! Adding tops and bottoms only works when the pieces are the same size. What number could both 4 and 6 divide into evenly?",
  "review": {"verdict": "REVISED", "revised": true, "issues": ["says the answer 5/12"], "checks": [...]},
  "hint_level": 1
}
```

`review.verdict` is `PASS` (the coach's reply was fine), `REVISED` (the reviewer rewrote it) or `FALLBACK`
(every model reply gave the answer away, so a safe built-in hint was used). Other statuses:
`refused_injection` (200, with a polite reply), `model_unavailable` (503), busy (429).

**`GET /api/humex/health`** (public): `{"ready": true, "configured": true, "reachable": true, "model": "humex-qwen35-4b", "dedicated_model": true}`.
It never reveals the model server's address.

## Running it

**1. Start the model server on a GPU** (a Kaggle notebook with a T4, Modal, or your own GPU PC):

```bash
python LLM/serve/model_server.py          # loads LLM/humex by default, serves on :8001
```

Expose it with a tunnel (for example Cloudflare) and set `MODEL_SERVER_TOKEN` so only your app can call it.

**2. Point the app at it.** Either give Humo its own model server:

```bash
export HUMEX_MODEL_URL=https://<your-tunnel>
export HUMEX_MODEL_TOKEN=<the MODEL_SERVER_TOKEN you set>
```

or leave those unset and Humo shares the app's model (`LLM_BACKEND_URL` / `LLM_BACKEND_TOKEN`).

**3. Start the app**, which already includes the Humex backend:

```bash
./scripts/run_local.sh                    # http://localhost:8000, Humex page at /code.html
```

To host only the Humex API somewhere else: `PYTHONPATH=src:. .venv/bin/python -m backend.humex.server` (port 8002).

| Variable | Default | Meaning |
|---|---|---|
| `HUMEX_MODEL_URL` | unset | Humo's own model server; unset means share `LLM_BACKEND_URL` |
| `HUMEX_MODEL_TOKEN` | unset | bearer token for that server |
| `HUMEX_MODEL_NAME` | from the adapter | label sent as the OpenAI `model` field |
| `HUMEX_MAX_CONCURRENT` | `2` | replies generated at once (one GPU: keep it small) |
| `AUTH_REQUIRED` | `1` | `0` lets anyone chat without signing in (local testing only) |

Without any model, the page still works in a small guided demo mode and shows "Humo's model is offline".
