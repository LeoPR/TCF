"""Etapa 2 Expandida — adicionar 5 modelos novos ao benchmark.

Reusa run_etapa2.py mas acrescenta os modelos novos instalados em 2026-04-09.
Resultados sao gravados no MESMO manifest de etapa2 (incremental, idempotente).

Lotes (para analise intermediaria + resilencia a restart):
    LOTE 1 (pequenos):    qwen3:0.6b, gemma3:1b, qwen3:1.7b   — ~30min
    LOTE 2 (medio):       gemma3:4b                            — ~30min
    LOTE 3 (grande):      qwen3:14b                            — ~60min

Cada lote pode ser interrompido/retomado — manifest cache funciona.

Usage:
    python experiments/eval/run_etapa2_extended.py --lote 1
    python experiments/eval/run_etapa2_extended.py --lote 2
    python experiments/eval/run_etapa2_extended.py --lote 3
    python experiments/eval/run_etapa2_extended.py --all  # todos os lotes
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_etapa2 import run

LOTES = {
    1: ["qwen3:0.6b", "gemma3:1b", "qwen3:1.7b"],
    2: ["gemma3:4b"],
    3: ["qwen3:14b"],
}


def main():
    parser = argparse.ArgumentParser(description="Etapa 2 Extended: new models")
    parser.add_argument("--lote", type=int, choices=[1, 2, 3], help="Run specific lote")
    parser.add_argument("--all", action="store_true", help="Run all lotes")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()

    if args.all:
        models = LOTES[1] + LOTES[2] + LOTES[3]
    elif args.lote:
        models = LOTES[args.lote]
    else:
        parser.print_help()
        sys.exit(1)

    print(f"[Etapa 2 Extended] Running models: {models}")
    run(models, args.endpoint)


if __name__ == "__main__":
    main()
