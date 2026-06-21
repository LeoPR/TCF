"""Estagio A: identificacao do tipo/formato/granularidade.

Recebe linhas brutas, retorna **metadata** sobre o tipo de dado.
**Nao transforma os dados** — saida e' so' descricao.

Versao naive (esta iteracao):
- Inspeciona apenas a primeira linha
- Detecta data ISO `YYYY-MM-DD` -> type=date, granularidade=day
- Fallback: type=string (passthrough nas etapas seguintes)

Iteracoes futuras (deixar registrado):
- Inspecionar mais linhas (sample) pra detectar coerencia
- Detectar `HH:MM:SS`, `HH:MM`, datetime ISO
- Detectar numericos puros
- Detectar templates (CPF, UUID, email, ...) — entrara em T02
- Cogitar "tipo misto" como erro / fallback
"""

from __future__ import annotations

import re
from datetime import date


# Regex base — checa formato; date.fromisoformat valida calendarmente
_RE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def identify(linhas: list[str]) -> dict:
    """Detecta tipo/formato/granularidade a partir da primeira linha.

    Returns:
        dict com pelo menos as chaves `type`, `format`, `granularity`.
        Pode incluir `n_samples` e outras descobertas.
    """
    meta: dict = {"n_samples": len(linhas)}
    if not linhas:
        meta["type"] = "unknown"
        meta["format"] = None
        meta["granularity"] = None
        return meta

    sample = linhas[0]

    # Tentativa 1: data ISO YYYY-MM-DD
    if _RE_YMD.match(sample):
        try:
            date.fromisoformat(sample)
            meta["type"] = "date"
            meta["format"] = "YYYY-MM-DD"
            meta["granularity"] = "day"
            return meta
        except ValueError:
            pass  # nao e' data valida apesar do regex

    # Fallback: string (passthrough)
    meta["type"] = "string"
    meta["format"] = None
    meta["granularity"] = None
    return meta
