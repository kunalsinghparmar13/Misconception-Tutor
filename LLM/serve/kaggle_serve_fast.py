"""Fast Kaggle launcher: your fine-tuned LoRA on llama.cpp (4-bit GGUF, CUDA) instead of Unsloth.

Why: on Kaggle's T4 Unsloth runs Gemma 4 in float32 split across two GPUs (~2 tokens/s). llama.cpp runs the
same base model quantised to Q4_K_M with your adapter applied at runtime (``--lora``), typically 10-20x faster.
The adapter is NOT retrained or merged; it is only converted to GGUF format.

Kaggle cell (GPU T4, Internet on, adapter dataset attached as input):
    !rm -rf /kaggle/working/app && git clone --depth 1 https://github.com/kunalsinghparmar13/Misconception-Tutor.git /kaggle/working/app
    !python /kaggle/working/app/LLM/serve/kaggle_serve_fast.py

It prints LLM_BACKEND_URL / LLM_BACKEND_TOKEN like kaggle_serve.py. If any llama.cpp step fails it falls back
to the Unsloth server (kaggle_serve.py) so the model still comes up. Keep the cell running.

Env overrides: BASE_GGUF_REPO, BASE_GGUF_FILE, BASE_HF_ID, LLAMA_CTX, LLAMA_PARALLEL.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kaggle_serve  # noqa: E402  (find_adapter, tunnel helpers)

WORK = Path(os.getenv("FAST_WORKDIR", "/kaggle/working" if Path("/kaggle/working").exists() else "/tmp")) / "fast"
LLAMA_DIR = WORK / "llama.cpp"
PORT = 8001
BASE_GGUF_REPO = os.getenv("BASE_GGUF_REPO", "unsloth/gemma-4-E4B-it-GGUF")
BASE_GGUF_FILE = os.getenv("BASE_GGUF_FILE", "gemma-4-E4B-it-Q4_K_M.gguf")
BASE_HF_ID = os.getenv("BASE_HF_ID", "unsloth/gemma-4-E4B-it")


def sh(cmd: list[str], **kw) -> None:
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def build_llama_server() -> Path:
    binary = LLAMA_DIR / "build" / "bin" / "llama-server"
    if binary.exists():
        return binary
    WORK.mkdir(parents=True, exist_ok=True)
    if not LLAMA_DIR.exists():
        sh(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", str(LLAMA_DIR)])
    # sm_75 = T4 (P100 is sm_60); building one architecture and one target keeps this to ~10 minutes.
    arch = os.getenv("CUDA_ARCH", "75;60")
    sh(["cmake", "-S", str(LLAMA_DIR), "-B", str(LLAMA_DIR / "build"), "-DGGML_CUDA=ON",
        f"-DCMAKE_CUDA_ARCHITECTURES={arch}", "-DLLAMA_CURL=OFF", "-DCMAKE_BUILD_TYPE=Release"])
    sh(["cmake", "--build", str(LLAMA_DIR / "build"), "--config", "Release", "-j", str(os.cpu_count() or 4),
        "--target", "llama-server"])
    return binary


def base_model() -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(BASE_GGUF_REPO, BASE_GGUF_FILE, local_dir=str(WORK / "base"),
                           token=os.getenv("HF_TOKEN") or None)


def convert_adapter(adapter_dir: str) -> Path:
    out = WORK / "tutor-lora-f16.gguf"
    if out.exists():
        return out
    sh([sys.executable, "-m", "pip", "install", "-q", "-e", str(LLAMA_DIR / "gguf-py")])
    sh([sys.executable, str(LLAMA_DIR / "convert_lora_to_gguf.py"), adapter_dir,
        "--base-model-id", BASE_HF_ID, "--outtype", "f16", "--outfile", str(out)])
    return out


def wait_ready(proc: subprocess.Popen, timeout: float = 600) -> None:
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {proc.returncode}")
        try:
            if requests.get(f"http://127.0.0.1:{PORT}/health", timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise RuntimeError("llama-server did not become ready in time")


def self_test(token: str) -> None:
    import requests

    t = time.time()
    r = requests.post(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"messages": [{"role": "user", "content": "A student says 1/4 + 1/6 = 2/10. In two sentences, what mistake is that?"}],
              "max_tokens": 120, "temperature": 0},
        timeout=300,
    )
    r.raise_for_status()
    body = r.json()
    text = body["choices"][0]["message"]["content"]
    toks = (body.get("usage") or {}).get("completion_tokens") or len(text.split())
    secs = time.time() - t
    print(f"Self-test ({toks} tokens in {secs:.1f}s = {toks / max(secs, 0.01):.1f} tok/s): {text[:200]}", flush=True)
    if not text.strip():
        raise RuntimeError("empty self-test reply")


def main() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "huggingface_hub", "requests"], check=True)
    adapter = kaggle_serve.find_adapter()
    token = secrets.token_urlsafe(24)
    print("Adapter:", adapter, flush=True)
    try:
        server = build_llama_server()
        base = base_model()
        lora = convert_adapter(adapter)
        cmd = [
            str(server), "-m", base, "--lora", str(lora),
            "--host", "127.0.0.1", "--port", str(PORT), "--api-key", token,
            "-ngl", "999", "-c", os.getenv("LLAMA_CTX", "8192"), "-np", os.getenv("LLAMA_PARALLEL", "2"),
            "--jinja", "--alias", "misconception-tutor-gemma4-e4b", "--no-webui",
        ]
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=os.getenv("CUDA_VISIBLE_DEVICES", "0"))
        print("$", " ".join(c if c != token else "<token>" for c in cmd), flush=True)
        proc = subprocess.Popen(cmd, env=env)
        wait_ready(proc)
        self_test(token)
    except Exception as exc:  # noqa: BLE001
        print(f"\nFast path failed ({type(exc).__name__}: {exc}). Falling back to the Unsloth server.\n", flush=True)
        try:
            proc.terminate()  # type: ignore[possibly-undefined]
        except Exception:  # noqa: BLE001
            pass
        kaggle_serve.main()
        return

    url = kaggle_serve.open_tunnel(PORT)
    kaggle_serve.announce(url, token)
    while True:
        if proc.poll() is not None:
            raise SystemExit(f"llama-server stopped (code {proc.returncode}). Re-run this cell.")
        time.sleep(30)


if __name__ == "__main__":
    main()
