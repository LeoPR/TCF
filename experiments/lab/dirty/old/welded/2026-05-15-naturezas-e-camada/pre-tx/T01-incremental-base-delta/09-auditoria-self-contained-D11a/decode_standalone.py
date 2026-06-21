"""Decoder standalone — prova de auto-containment de D11a.tcf.

Recebe APENAS o path do .tcf. Reconstroi as linhas originais sem
qualquer dependencia externa alem de:
- Algoritmo TCF compartilhado (src/tcf.decode) — conhecimento publico
- Logica de pre-tx day-granularity inline neste arquivo (poderia
  estar em biblioteca, mantida inline pra deixar explicito)

NAO recebe:
- D11a.csv original
- metadata externo (JSON sidecar)
- hint sobre natureza ou granularidade
- count de linhas esperadas

Princípio: "tudo que e' necessario tem que estar no arquivo tcf
pra ele desempacotar." O arquivo .tcf carrega: dados, refs, e
permite **auto-deducao** de natureza pela primeira linha.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


# === 1) Algoritmo compartilhado: TCF decode (HCC + OBAT) ============
# Importa de src/tcf — conhecimento publico, equivalente a `gunzip`.

THIS = Path(__file__).parent
SRC = THIS.parents[6] / "src"
sys.path.insert(0, str(SRC))

from tcf import decode as tcf_decode  # noqa: E402


# === 2) Stage A inline (identify) ==================================

_RE_YMD_HMS_NS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{9}$")
_RE_YMD_HMS_US = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{6}$")
_RE_YMD_HMS_MS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d{3}$")
_RE_YMD_HMS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}$")
_RE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def identify_from_first_line(first_line: str) -> dict:
    """Detecta type/granularity a partir da primeira linha (auto)."""
    if _RE_YMD_HMS_NS.match(first_line):
        return {"type": "date", "granularity": "ns"}
    if _RE_YMD_HMS_US.match(first_line):
        return {"type": "date", "granularity": "us"}
    if _RE_YMD_HMS_MS.match(first_line):
        return {"type": "date", "granularity": "ms"}
    if _RE_YMD_HMS.match(first_line):
        return {"type": "date", "granularity": "second"}
    if _RE_YMD.match(first_line):
        try:
            date.fromisoformat(first_line)
            return {"type": "date", "granularity": "day"}
        except ValueError:
            pass
    return {"type": "string"}


# === 3) Stage C inverso + Stage B inverso para day-granularity ==========
# (Esta demo cobre day. Outras granularidades usam sub-exp 08 modules.)

def _parse_delta_day(s: str) -> tuple[str, int]:
    """Parse `<N>` (default=dia), `<N>Y`, `<N>M`. Sinal `-` opcional."""
    if not s:
        return ("d", 0)
    if s[-1] == "Y":
        return ("Y", int(s[:-1]))
    if s[-1] == "M":
        return ("M", int(s[:-1]))
    return ("d", int(s))


def decode_day_pretx(pretx_output: list[str]) -> list[str]:
    """Aplica Stage C + B inversos pra day granularity."""
    if not pretx_output:
        return []
    current = date.fromisoformat(pretx_output[0])
    out = [pretx_output[0]]
    for s in pretx_output[1:]:
        scale, n = _parse_delta_day(s)
        if scale == "Y":
            current = date(current.year + n, current.month, current.day)
        elif scale == "M":
            total = current.year * 12 + (current.month - 1) + n
            current = date(total // 12, total % 12 + 1, current.day)
        else:
            current = current + timedelta(days=n)
        out.append(current.isoformat())
    return out


# === 4) Decoder de alto nivel: file -> linhas =========================

def decode_self_contained(tcf_path: Path | str) -> tuple[list[str], dict]:
    """Decoder principal — recebe APENAS path do .tcf.

    Returns:
        (linhas_reconstruidas, metadata_inferido)
    """
    tcf_text = Path(tcf_path).read_text(encoding="utf-8")

    # Passo 1: TCF.decode -> pre-tx output (lista de strings)
    pretx_output = tcf_decode(tcf_text)
    if not pretx_output:
        return [], {"type": "empty"}

    # Passo 2: Stage A inferido da primeira linha (auto-deducao)
    meta = identify_from_first_line(pretx_output[0])

    # Passo 3: Stage C + B inversos baseado em meta
    if meta.get("type") == "date" and meta.get("granularity") == "day":
        linhas = decode_day_pretx(pretx_output)
    else:
        # Outras granularidades: usar modulos do sub-exp 08
        # (esta demo se foca em day pra simplificar)
        raise NotImplementedError(
            f"Esta demo cobre apenas day-granularity (D11a). "
            f"Detectado: {meta}. Usar sub-exp 08 modules pra outras."
        )

    return linhas, meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python decode_standalone.py <path-to-tcf-file>")
        sys.exit(1)

    tcf_path = sys.argv[1]
    linhas, meta = decode_self_contained(tcf_path)
    print(f"=== Decoder standalone ===")
    print(f"Input: {tcf_path}")
    print(f"Auto-detectado: {meta}")
    print(f"Linhas reconstruidas ({len(linhas)}):")
    for i, l in enumerate(linhas):
        print(f"  [{i}] {l}")
