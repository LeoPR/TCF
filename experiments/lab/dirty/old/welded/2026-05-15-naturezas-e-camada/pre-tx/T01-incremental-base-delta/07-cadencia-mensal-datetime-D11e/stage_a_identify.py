"""Estagio A: identificacao do tipo/formato/granularidade.

Versao estendida (sub-exp 06): alem de YYYY-MM-DD (granularity=day),
detecta YYYY-MM-DD HH:MM:SS (granularity=second). Captura tambem
o separador (`T` ou ` `).

Nao transforma os dados — saida e' so' descricao.
"""

from __future__ import annotations

import re
from datetime import date, datetime


_RE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_YMD_HMS = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}$")


def identify(linhas: list[str]) -> dict:
    """Detecta tipo/formato/granularidade da primeira linha."""
    meta: dict = {"n_samples": len(linhas)}
    if not linhas:
        meta["type"] = "unknown"
        meta["format"] = None
        meta["granularity"] = None
        return meta

    sample = linhas[0]

    # Tentativa 1: datetime YYYY-MM-DD HH:MM:SS (ou T)
    if _RE_YMD_HMS.match(sample):
        sep = "T" if "T" in sample else " "
        try:
            datetime.fromisoformat(sample.replace(" ", "T"))
            meta["type"] = "date"
            meta["format"] = f"YYYY-MM-DD{sep}HH:MM:SS"
            meta["separator"] = sep
            meta["granularity"] = "second"
            return meta
        except ValueError:
            pass

    # Tentativa 2: data YYYY-MM-DD
    if _RE_YMD.match(sample):
        try:
            date.fromisoformat(sample)
            meta["type"] = "date"
            meta["format"] = "YYYY-MM-DD"
            meta["granularity"] = "day"
            return meta
        except ValueError:
            pass

    # Fallback
    meta["type"] = "string"
    meta["format"] = None
    meta["granularity"] = None
    return meta
