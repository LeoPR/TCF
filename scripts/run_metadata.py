"""Helpers de metadata pra runs de experimento.

Uso tipico — importar em `run.py` de EXP-NNN clean e merge no manifest entry:

    from scripts.run_metadata import get_run_metadata

    entry = {
        **get_run_metadata(),
        "experiment_id": "EXP-007-...",
        "metrics": {...},
    }
    with manifest_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")

Funcoes sao no-fail (retornam None / fallback) se git nao disponivel ou
projeto nao for repo. Sem dep externa.

Adicionado 2026-05-20 (avaliacao de metodologia §13.2 — gap "git_sha em
manifest" em EXP novos).
"""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_git_sha(cwd: Path | str | None = None, short: bool = False) -> str | None:
    """Retorna SHA do HEAD atual; None se nao for repo git ou git ausente.

    Args:
        cwd: diretorio do repo (default = cwd atual)
        short: se True, retorna SHA curto (7 chars); senao SHA completo (40)
    """
    cmd = ["git", "rev-parse", "--short", "HEAD"] if short else ["git", "rev-parse", "HEAD"]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_git_dirty(cwd: Path | str | None = None) -> bool | None:
    """True se working tree tem mudancas nao-commitadas; None se nao for repo."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_run_metadata(cwd: Path | str | None = None) -> dict:
    """Retorna dict pronto pra merge em manifest entry.

    Campos:
        timestamp: ISO 8601 UTC
        git_sha: SHA completo do HEAD (None se nao for repo)
        git_dirty: True se ha mudancas nao-commitadas
        python: versao do Python rodando
        platform: sistema operacional + versao
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": get_git_sha(cwd),
        "git_dirty": get_git_dirty(cwd),
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(get_run_metadata(), indent=2))
