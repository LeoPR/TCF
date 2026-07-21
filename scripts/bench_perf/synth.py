"""Gerador sintetico do pivo — o unico jeito de variar UM fator por vez (V6).

Dado real nao permite isolar escala: mudar de dataset muda R, C, L, K e forma ao
mesmo tempo. Aqui cada eixo se move sozinho, com semente registrada no workload —
o `.9` regenera o mesmo dado bit-a-bit.

  R  linhas · C  colunas · L  comprimento medio do valor · K  |unicos|/R
"""

from __future__ import annotations

import random
import string

from .pivot import Pivot

_ALFA = string.ascii_lowercase


def _vocab(seed: int, n: int = 4000) -> list[str]:
    """Vocabulario pseudo-aleatorio DETERMINISTICO, grande o bastante pra dar
    TRIGRAMAS DIVERSOS (como free-text real). Um vocabulario pequeno degenera o
    indice do OBAT e cria um penhasco ARTIFICIAL — o caso `structured` ja' cobre
    o regime de prefixo compartilhado de proposito; free-text nao deve faze-lo
    por acidente."""
    rng = random.Random(seed ^ 0x5F3759DF)
    palavras: list[str] = []
    for _ in range(n):
        L = rng.randint(3, 11)
        palavras.append("".join(rng.choice(_ALFA) for _ in range(L)))
    return palavras


def _valor(rng: random.Random, forma: str, L: int, i: int, vocab: list[str]) -> str:
    if forma == "structured":
        # cadencia forte: prefixo fixo + contador zero-padded (exercita pre-pass).
        # Este E' o caso de prefixo compartilhado, DECLARADO — nao acidental.
        return f"REG-{i:0{max(4, L - 4)}d}"
    if forma == "low-entropy":
        return vocab[i % 12]
    if forma == "free-text":
        # frases de vocabulario DIVERSO, comprimento com cauda (regime real do HCC)
        n = max(4, int(rng.gauss(L, L * 0.45)))
        return " ".join(rng.choice(vocab) for _ in range(max(1, n // 7)))
    # flat-mixed: comprimento ~uniforme em torno de L, alfabeto pleno
    n = max(1, L + rng.randint(-2, 2))
    return "".join(rng.choice(_ALFA) for _ in range(n))


def synth_pivot(R: int, C: int, L: int = 32, K: float = 0.1,
                forma: str = "flat-mixed", seed: int = 20260721) -> Pivot:
    """Pivo determinístico com os 4 eixos de escala controlados independentemente."""
    rng = random.Random(seed)
    vocab = _vocab(seed)
    n_unicos = max(1, min(R, int(round(R * K))))
    piv: Pivot = {}
    for c in range(C):
        rc = random.Random(seed + c * 7919)
        pool = [_valor(rc, forma, L, i, vocab) for i in range(n_unicos)]
        # repete o pool ate R deterministicamente (cardinalidade = K por construcao)
        col = [pool[i % n_unicos] for i in range(R)]
        if forma != "structured":
            rc.shuffle(col)          # structured mantem a cadencia (e' o ponto dela)
        piv[f"col{c:02d}"] = col
    return piv


def descrever(piv: Pivot) -> dict:
    """Metadados do workload — vao no registro pra o `.9` conferir que e' o mesmo dado."""
    nomes = list(piv.keys())
    R = len(piv[nomes[0]]) if nomes else 0
    tamanhos = [len(v) for col in piv.values() for v in col]
    tamanhos.sort()
    n_cells = R * len(nomes)
    return {
        "n_rows": R,
        "n_cols": len(nomes),
        "n_cells": n_cells,
        "bytes_utf8": sum(len(v.encode()) for col in piv.values() for v in col),
        "mean_value_len": round(sum(tamanhos) / len(tamanhos), 2) if tamanhos else 0,
        "p95_value_len": tamanhos[int(0.95 * (len(tamanhos) - 1))] if tamanhos else 0,
        "cardinality_ratio": round(
            sum(len(set(col)) for col in piv.values()) / n_cells, 6) if n_cells else 0,
    }


__all__ = ["synth_pivot", "descrever"]
