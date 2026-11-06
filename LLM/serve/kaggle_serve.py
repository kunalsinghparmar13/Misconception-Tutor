"""One-shot launcher for a Kaggle (or Colab) GPU notebook.

Kaggle cell:
    !git clone --depth 1 https://github.com/kunalsinghparmar13/Misconception-Tutor.git /kaggle/working/app
    !python /kaggle/working/app/LLM/serve/kaggle_serve.py

It finds the LoRA adapter (attach your Kaggle dataset as notebook input, or set LLM_ADAPTER_PATH),
loads it, serves the OpenAI-compatible API, opens a Cloudflare quick tunnel and prints
LLM_BACKEND_URL / LLM_BACKEND_TOKEN. Keep the cell running; stopping it takes the model offline.
"""

from __future__ import annotations

import glob
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LLM_DIR = HERE.parent


def find_adapter() -> str:
    explicit = os.getenv("LLM_ADAPTER_PATH")
    if explicit:
        return explicit
    hits = glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)
    if hits:
        return str(Path(sorted(hits)[0]).parent)
    local = LLM_DIR / "adapter_model.safetensors"
    if local.exists() and local.stat().st_size > 1_000_000:
        return str(LLM_DIR)
    raise SystemExit("No adapter found. Attach your adapter dataset as notebook input or set LLM_ADAPTER_PATH.")


def open_tunnel(port: int) -> str:
    """Start a Cloudflare quick tunnel to 127.0.0.1:port and return its public URL."""
    cf = "/tmp/cloudflared"
    if not Path(cf).exists():
        subprocess.run(
            ["curl", "-sL", "-o", cf, "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"],
            check=True,
        )
        os.chmod(cf, 0o755)
    tunnel = subprocess.Popen([cf, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = None
    deadline = time.time() + 120
    while time.time() < deadline and url is None:
        line = tunnel.stdout.readline()
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line or "")
        if m:
            url = m.group(0)
    if not url:
        raise SystemExit("Could not open the tunnel. Re-run this cell.")
    # Keep draining cloudflared's log; a full pipe would block it and stall the tunnel.
    threading.Thread(target=lambda: [None for _ in tunnel.stdout], daemon=True).start()
    return url


def announce(url: str, token: str) -> None:
    out = f"LLM_BACKEND_URL={url}\nLLM_BACKEND_TOKEN={token}\n"
    for dest in ("/kaggle/working/connection.txt", "connection.txt"):
        try:
            Path(dest).write_text(out)
            break
        except OSError:
            continue
    print("=" * 60)
    print(out, end="")
    print("=" * 60, flush=True)


def main() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "unsloth", "flask", "requests"], check=True)

    adapter = find_adapter()
    token = secrets.token_urlsafe(24)
    os.environ.update(MODEL_SERVER_TOKEN=token, LLM_ADAPTER_PATH=adapter, LLM_GEN_BACKEND="unsloth")
    print("Adapter:", adapter, flush=True)

    sys.path.insert(0, str(LLM_DIR))
    from serve import model_server  # noqa: E402

    model_server.load_model()
    print("Model loaded.", flush=True)

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 8001, model_server.app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    import requests

    r = requests.post(
        "http://127.0.0.1:8001/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"messages": [{"role": "user", "content": "A student says 1/4 + 1/6 = 2/10. In one sentence, what mistake is that?"}], "max_tokens": 80},
        timeout=300,
    )
    print("Self-test:", r.status_code, r.json()["choices"][0]["message"]["content"][:200], flush=True)

    announce(open_tunnel(8001), token)

    while True:  # keep the notebook cell alive
        time.sleep(60)


if __name__ == "__main__":
    main()
