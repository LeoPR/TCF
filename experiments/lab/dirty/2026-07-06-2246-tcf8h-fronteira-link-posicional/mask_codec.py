"""mask_codec — Ciclo 1c: a fronteira do LINK POSICIONAL, e o fix da família "retângulo/nullable".

O modelo colunar do TCF.8H supõe RETÂNGULO HOMOGÊNEO (toda linha tem toda coluna, um tipo por coluna).
4 formas quebram isso — todas por falta de um canal de PRESENÇA/POSIÇÃO:
  B1 chave-ausente     [{a,b},{a}]            linha sem a coluna        -> PRESENÇA (bitmap)
  B2 null-em-coluna    [{x:1},{x:null}]       célula null numa coluna    -> NULL-mask (nullable)
  B3 array-em-array    {m:[[1,2],[3]]}        aninhamento repetido       -> REPETITION level (Dremel)
  B4 N:N               [{a:1,t:x},{a:1,t:y}]  many-to-many               -> ponte / rep level

Este lab PROVA o fix de B1+B2 (família nullable/presença) com uma máscara de 3 estados por célula:
  '.' = tem valor · '0' = null · '-' = ausente.  Dense body = só as células com valor.
B3/B4 (rep/def levels) ficam CARACTERIZADOS e deferidos (welding). Prior-art: Dremel (rep/def levels,
Melnik 2010), factorized DBs, H-CARD-06 (order dependency). Engenhoca — não toca src/tcf.
"""
from __future__ import annotations

MISSING = object()                                    # sentinela: chave ausente (≠ None)


def encode_sparse_column(values):
    """[valores com None e MISSING] -> (densos_só-com-valor, máscara 3-estados)."""
    dense, mask = [], []
    for v in values:
        if v is MISSING:
            mask.append("-")
        elif v is None:
            mask.append("0")
        else:
            mask.append(".")
            dense.append(v)
    return dense, "".join(mask)


def decode_sparse_column(dense, mask):
    """(densos, máscara) -> [valores com None e MISSING] (inverso exato)."""
    out, it = [], iter(dense)
    for m in mask:
        if m == "-":
            out.append(MISSING)
        elif m == "0":
            out.append(None)
        else:
            out.append(next(it))
    return out


def array_to_masked(rows):
    """array-de-objetos (linhas heterogêneas) -> {coluna: (densos, máscara)} + ordem das colunas.
    União de chaves preservando ordem de aparição."""
    cols_order = []
    for r in rows:
        for k in r:
            if k not in cols_order:
                cols_order.append(k)
    masked = {}
    for k in cols_order:
        col = [r.get(k, MISSING) for r in rows]        # MISSING se a chave não existe na linha
        masked[k] = encode_sparse_column(col)
    return masked, cols_order


def masked_to_array(masked, cols_order, n):
    """{coluna:(densos,máscara)} -> array-de-objetos (omite chave ausente; None em null). RT exato."""
    per_col = {k: decode_sparse_column(d, m) for k, (d, m) in masked.items()}
    rows = []
    for i in range(n):
        row = {}
        for k in cols_order:
            v = per_col[k][i]
            if v is MISSING:
                continue                               # chave ausente: não entra na linha
            row[k] = v
        rows.append(row)
    return rows
