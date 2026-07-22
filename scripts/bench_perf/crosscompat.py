"""Alertas de cross-compatibilidade — a camada de DETECCAO (owner, 2026-07-21).

"ser melhor que o json nao gera clareza sozinho": se o TCF deixa um dataset que
uma libjson popular (ou de outra linguagem) NAO round-trip'a, sem avisar,
confunde. Este modulo DETECTA essas condicoes e as reporta como alertas
estruturados. O MECANISMO DE COMUNICACAO com o usuario (manual? citar RFC? um
"extrapolamos a limitacao"?) fica pos-.8, indefinido (H-JSON-CLARITY-WARN-01) —
aqui so' se constroi o que detectar.

Cada condicao e' um dataset que o Python round-trip'a (logo esta' na classe do
.8, N1) mas que carrega RISCO cross-linguagem — a distincao N1-fica / N2-ressalva.
Alerta e' SINAL, nunca recusa. A recusa dura (fora do JSON valido: NaN/Infinity,
chave nao-string, tipo estranho) e' do gate G2, nao daqui.

Severidades:
  interop     — round-trip'a no Python, mas outra linguagem perde/diverge
  transmissao — nao e' UTF-8 transmissivel (o texto nao atravessa o fio)
"""

from __future__ import annotations

from typing import Any

_MAX_SAFE_INT = 2 ** 53 - 1          # RFC 7493 I-JSON (double-seguro)
_DEPTH_INTEROP = 100                  # muitos parsers limitam recursao ~ esta ordem


def _tem_surrogate(s: str) -> bool:
    # str do Python pode conter surrogate solo (U+D800..U+DFFF); UTF-8 nao o codifica
    try:
        s.encode("utf-8")
        return False
    except UnicodeEncodeError:
        return True


def alertas(obj: Any, caminho: str = "$", prof: int = 0,
            out: list[dict] | None = None) -> list[dict]:
    """Lista de alertas cross-compat. Nao levanta — e' sinal, o gate G2 e' que recusa."""
    if out is None:
        out = []
    if prof == _DEPTH_INTEROP + 1:
        out.append({"tipo": "profundidade", "caminho": caminho,
                    "detalhe": f"aninhamento > {_DEPTH_INTEROP} (parsers de outras linguagens "
                               f"podem estourar a pilha)", "severidade": "interop"})
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and _tem_surrogate(k):
                out.append({"tipo": "surrogate-solo", "caminho": f"{caminho}.<chave>",
                            "detalhe": "chave com surrogate solo — nao e' UTF-8 transmissivel",
                            "severidade": "transmissao"})
            alertas(v, f"{caminho}.{k}", prof + 1, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            alertas(v, f"{caminho}[{i}]", prof + 1, out)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, int):
        if not (-_MAX_SAFE_INT <= obj <= _MAX_SAFE_INT):
            out.append({"tipo": "int-fora-I-JSON", "caminho": caminho,
                        "detalhe": f"{obj} fora de ±2^53-1 — parser int64/double perde precisao",
                        "severidade": "interop"})
    elif isinstance(obj, str):
        if _tem_surrogate(obj):
            out.append({"tipo": "surrogate-solo", "caminho": caminho,
                        "detalhe": "string com surrogate solo — nao e' UTF-8 transmissivel",
                        "severidade": "transmissao"})
    return out


def resumo(alertas_lista: list[dict]) -> dict:
    """Agrega por tipo — o que vai no cabecalho do registro/relatorio."""
    por_tipo: dict[str, int] = {}
    for a in alertas_lista:
        por_tipo[a["tipo"]] = por_tipo.get(a["tipo"], 0) + 1
    return {"n": len(alertas_lista), "por_tipo": por_tipo}


__all__ = ["alertas", "resumo"]
