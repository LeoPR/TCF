"""Calibradores — medem a MAQUINA, nao o TCF.

O owner quer que o processo "repita de forma statisticamente similar pro .9".
O problema concreto (visto nesta sessao): a mesma versao do TCF mediu 5.45s e
depois 7.54s pro mesmo caso — a maquina estava ~38% mais lenta. Sem um
referencial da propria maquina, a comparacao .8 vs .9 confunde ganho de codigo
com estado do host.

Dois papeis, ambos rodando no MESMO processo e MESMO protocolo dos casos reais:

  C1/C2/C3 = CALIBRADORES: trabalho fixo, independente do TCF (aritmetica, hash,
    alocacao/copia). O .9 os re-mede; a razao C_{.9}/C_{.8} e' o fator de
    normalizacao entre maquinas/dias. Se o fator explica o delta observado num
    caso, aquele "ganho" era ambiente, nao codigo.

  SENTINELA = deriva DENTRO de uma rodada: um caso barato e fixo, re-medido a
    cada N casos. drift_ratio = sentinela_agora / sentinela_no_inicio. Passou de
    ~1.10 -> a rodada esta' termicamente suspeita. cv da sentinela ao longo da
    rodada = noise_floor: o piso abaixo do qual nenhum ganho .9 pode ser
    declarado (senao e' ruido).
"""

from __future__ import annotations

import hashlib

from . import probes as P

# Tamanhos fixos e pequenos: cada calibrador mira ~1-5 ms (tier micro, n alto).
_N_ARIT = 200_000
_N_HASH = 20_000
_N_ALLOC = 2_000


def _c1_aritmetica() -> None:
    # laco puro de inteiros/float: mede a CPU em trabalho escalar
    acc = 0
    for i in range(_N_ARIT):
        acc = (acc * 1103515245 + 12345) & 0x7FFFFFFF
    if acc == -1:            # impede o otimizador de eliminar o laco
        raise RuntimeError


def _c2_hash() -> None:
    # sha256 de strings: mede bytes por segundo em C, path comum de serializacao
    h = hashlib.sha256()
    for i in range(_N_HASH):
        h.update(b"calibrador-%d" % i)
    if h.digest() == b"":
        raise RuntimeError


def _c3_alloc() -> None:
    # alocacao + copia de listas: mede o allocator do CPython, que domina o encode
    xs: list[list[int]] = []
    for i in range(_N_ALLOC):
        xs.append(list(range(i % 64)))
    if len(xs) != _N_ALLOC:
        raise RuntimeError


CALIBRADORES = {"C1_aritmetica": _c1_aritmetica,
                "C2_hash": _c2_hash,
                "C3_alloc": _c3_alloc}


def medir_calibradores() -> dict:
    """Roda os 3 com o mesmo probe dos casos reais. Vai no manifesto do run."""
    return {nome: P.medir(fn) for nome, fn in CALIBRADORES.items()}


# ---------------------------------------------------------------- sentinela


def sentinela_fn():
    """Caso-sentinela barato e FIXO: um encode pequeno e estavel. Re-medido ao
    longo da rodada pra detectar deriva termica. Definido aqui (nao em cases.json)
    pra ser identico entre .8 e .9 sem depender da matriz."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
    from tcf import encode
    from .synth import synth_pivot
    piv = synth_pivot(2000, 4, 32, 0.1, "flat-mixed", seed=987654321)
    return lambda: encode(piv)


class DriftTracker:
    """Acumula as medias da sentinela ao longo da rodada."""

    def __init__(self) -> None:
        self._fn = sentinela_fn()
        self.pontos: list[dict] = []

    def bater(self, order_index: int) -> dict:
        r = P.medir(self._fn, tier=P.Tier("sentinela", 5, 1, "min", 5.0, "strong"))
        ponto = {"order_index": order_index, "point_ns": r["point_ns"],
                 "median_ns": r["median_ns"], "cv": r.get("cv")}
        self.pontos.append(ponto)
        return ponto

    def resumo(self) -> dict:
        if not self.pontos:
            return {}
        base = self.pontos[0]["point_ns"]
        pts = [p["point_ns"] for p in self.pontos]
        import statistics
        cv = (statistics.stdev(pts) / statistics.fmean(pts)) if len(pts) > 1 else 0.0
        return {
            "n_batidas": len(self.pontos),
            "drift_ratio_final": round(pts[-1] / base, 4) if base else None,
            "drift_ratio_max": round(max(pts) / base, 4) if base else None,
            "noise_floor_cv": round(cv, 6),   # piso abaixo do qual ganho .9 = ruido
            "thermally_suspect": (max(pts) / base) > 1.10 if base else None,
            "pontos": self.pontos,
        }


__all__ = ["CALIBRADORES", "medir_calibradores", "DriftTracker", "sentinela_fn"]
