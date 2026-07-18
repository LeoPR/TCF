"""Protótipo P4b — RAIZ GENERALIZADA por envelope discriminado (extrai a IDEIA; não copia o core).

O protótipo opera SOBRE a API pública do core (dataset↔wire já welded) — porque o mecanismo É
esse: a raiz generalizada não cria maquinário novo, ela DISCRIMINA e REUSA o dataset.

GRAMÁTICA (defaults recomendados; owner delegou com direito a veto):
  #TCF.8H<meta>       dataset (list[dict], ≥1 registro, ≥1 coluna)  — INTACTO (byte-compat total)
  #TCF.8H#D<N>        dataset SEM colunas: N registros vazios. N=0 → []  ·  N=1 → [{}]  ·  N=2 → [{},{}]
  #TCF.8H#O<meta>     objeto único NÃO-vazio na raiz (interno: dataset de 1 registro; decode desembrulha)
  #TCF.8H#E           objeto VAZIO {} na raiz — DEFINIÇÃO (H-STRUCT-DEF-01: forma opaca)
  #TCF.8H#V<meta>     VALOR na raiz via ENVELOPE (interno: dataset [{"": V}], campo único `\z`;
                      decode desembrulha e NUNCA devolve o envelope) — escalar, string (incl. ""),
                      null, {} vazio, array de escalares, array-em-array

POR QUE `#` como sentinela: hoje `#` na posição 0 do meta é FAIL-LOUD ("nome de campo vazio") —
nenhum wire válido o usa → decoders antigos falham ALTO em wires novos (pré-1.0 correto) e o
dataset (o caso dominante, todos os wires existentes) fica 0 B / byte-idêntico. O(1): 1 lookahead
em offset fixo. É a "capacidade extra" na direção do H-DISC-ACCEL-01 (dica de roteamento).

CANONICIDADE: [] → SEMPRE #D0 (o encoder nunca emite envelope-de-[]); [{"a":1},...] é DATASET
(em JSON, raiz-array-de-objetos E dataset são a MESMA coisa — não há ambiguidade a preservar).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from tcf import decode as _core_decode  # noqa: E402
from tcf import encode_hierarchical as _core_encode  # noqa: E402
from tcf.hierarchical import MAGIC, HierarchicalError  # noqa: E402


def encode_root(data) -> str:
    """Qualquer raiz D_json → wire. Dataset intacto; demais formas discriminadas."""
    if isinstance(data, list):
        if not data:
            return f"{MAGIC}#D0\n"                                   # []
        if all(isinstance(r, dict) for r in data):
            if any(data):                                            # ≥1 registro com campos
                return _core_encode(data)                            # DATASET — intacto
            return f"{MAGIC}#D{len(data)}\n"                         # [{}]×N
        if any(isinstance(r, dict) for r in data):                   # misto dict+valor = P5
            raise HierarchicalError(
                "raiz lista MISTA (objetos e valores) — fora da classe (P5 union)")
        # lista de VALORES (escalares/arrays) na raiz → envelope
        return _core_encode([{"": data}]).replace(MAGIC, MAGIC + "#V", 1)
    if isinstance(data, dict):
        if data:
            return _core_encode([data]).replace(MAGIC, MAGIC + "#O", 1)
        return MAGIC + "#E\n"                                        # {} vazio = DEFINIÇÃO
        # (o envelope não serve: campo-marcador {} não gera coluna -> problema B)
    # escalar / string / null na raiz → envelope
    return _core_encode([{"": data}]).replace(MAGIC, MAGIC + "#V", 1)


def decode_root(wire: str):
    """Wire → raiz original (tipo EXATO; o envelope nunca escapa)."""
    if not wire.startswith(MAGIC):
        raise HierarchicalError(f"magic inesperado (esperava {MAGIC})")
    resto = wire[len(MAGIC):]
    if not resto.startswith("#"):
        return _core_decode(wire)                                    # DATASET — caminho de hoje
    kind = resto[1:2]
    if kind == "D":
        corpo = resto[2:]
        linha, sep, sobra = corpo.partition("\n")
        if not linha or not linha.isascii() or not linha.isdigit():
            raise HierarchicalError(f"contagem inválida em #D: {linha!r}")
        if sobra:
            raise HierarchicalError(f"{len(sobra)} bytes após #D — blob adulterado?")
        return [dict() for _ in range(int(linha))]
    if kind == "E":
        if resto[2:] not in ("", "\n"):
            raise HierarchicalError(f"bytes após #E — blob adulterado? {resto[2:]!r}")
        return {}
    if kind == "O":
        recs = _core_decode(MAGIC + resto[2:])
        if len(recs) != 1:
            raise HierarchicalError(
                f"#O (objeto único) com {len(recs)} registros — blob adulterado?")
        return recs[0]
    if kind == "V":
        recs = _core_decode(MAGIC + resto[2:])
        if len(recs) != 1 or list(recs[0].keys()) != [""]:
            raise HierarchicalError(
                f"#V (envelope) não-canônico: {len(recs)} registro(s), campos "
                f"{[list(r.keys()) for r in recs]!r} — blob adulterado?")
        return recs[0][""]
    raise HierarchicalError(f"root-kind desconhecido '#{kind}' — versão mais nova ou blob adulterado")
