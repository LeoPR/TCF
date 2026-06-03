"""Log GPU VRAM use + Ollama's size_vram every 10s to a CSV.

Used to prove that num_gpu=0 calls keep Ollama models out of VRAM while
another process may be consuming the GPU.
"""
import subprocess, time, sys, requests
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "results" / "rle_notation" / "vram_log.csv"
LOG.parent.mkdir(parents=True, exist_ok=True)

MAX_SEC = int(sys.argv[1]) if len(sys.argv) > 1 else 3600


def snap():
    try:
        r = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5).strip()
        mem, util = [x.strip() for x in r.split(",")]
    except Exception:
        mem, util = "?", "?"
    try:
        d = requests.get("http://localhost:11434/api/ps", timeout=3).json()
        total = sum(m.get("size_vram", 0) for m in d.get("models", [])) / 1e6
        names = ",".join(m["name"] for m in d.get("models", [])) or "-"
    except Exception:
        total, names = -1, "err"
    return mem, util, total, names


with LOG.open("w") as f:
    f.write("timestamp,vram_used_mib,gpu_util_pct,ollama_size_vram_mb,ollama_models\n")
    f.flush()
    start = time.time()
    while True:
        t = time.time() - start
        mem, util, ollama_vram, names = snap()
        line = f"{t:.0f},{mem},{util},{ollama_vram:.0f},{names}\n"
        f.write(line)
        f.flush()
        if t > MAX_SEC:
            break
        time.sleep(10)
