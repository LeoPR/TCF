"""Sondas de medicao do baseline de performance (perf-baseline-09/v1).

NAO substitui `scripts/bench_evidencia_probes.py` — aquele e' a regua de BYTES do
`.8` e fica intocado (a evidencia do release tem que continuar reproduzivel).
Este modulo e' o instrumento de PERFORMANCE, e conserta as lacunas que a
auditoria de 2026-07-21 achou no anterior:

  R1  AMOSTRAS CRUAS sao o artefato. `samples_ns[]` sempre persistido. A
      estatistica e' derivada DEPOIS — se em 2027 a certa for outra (bootstrap,
      Hodges-Lehmann, trimmed mean), o baseline `.8` e' recalculavel sem
      re-rodar. O anterior calculava 4 numeros e jogava o vetor fora.
  P95 o anterior usava nearest-rank `samples[round(0.95*(n-1))]`, que colapsa em
      `max` para todo n<=11 — e nenhum runner usava n>=12. Aqui: interpolacao
      linear e o campo so' EXISTE com n>=20. Sonda indisponivel = campo ausente
      (mesma filosofia do harness de bytes).
  CPU `cpu_time_ns()` existia no anterior e NUNCA era chamado, embora o
      env_fingerprint anunciasse a sonda. Aqui wall e cpu andam juntos:
      `wall_cpu_ratio` e' o unico jeito de distinguir "paralelo nao ajudou" de
      "paralelo nem rodou" (~1.0 serial ligado em CPU; <1.0 espera/IPC/spawn;
      >1.0 paralelismo real).
  MDE cada tier declara o efeito minimo detectavel. Fica NO REGISTRO, pra impedir
      que alguem no `.9` escreva "ganho de 6%" num caso cujo instrumento nao
      resolve abaixo de 20%.

Dispersao (mad/iqr/cv) e' METADADO DE QUALIDADE da medicao, nao resultado: e' o
que deixa o gate separar "regressao" de "medicao ruim".
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable

# ----------------------------------------------------------------- tiers
# O custo de 1 operacao define quantas repeticoes cabem. Sem isto, o caso de
# 600k (18 min/encode) exigiria 2h por celula na politica de orcamento fixo.


@dataclass(frozen=True)
class Tier:
    name: str
    n: int
    warmup: int
    estimator: str        # 'median' | 'min'  (min e' mais robusto quando n e' baixo)
    mde_pct: float        # efeito minimo detectavel, em %
    comparable: str       # 'strong' | 'weak'


TIERS = (
    #        nome      limite superior de 1 op (s)
    (0.050, Tier("micro",  31, 5, "median", 2.0, "strong")),
    (1.0,   Tier("small",  15, 3, "median", 3.0, "strong")),
    (30.0,  Tier("medium",  7, 1, "median", 5.0, "strong")),
    (300.0, Tier("large",   5, 1, "min",   10.0, "strong")),
)
TIER_XLARGE = Tier("xlarge", 3, 0, "min", 20.0, "weak")


def classify_tier(one_op_s: float) -> Tier:
    """Tier a partir da duracao de UMA operacao (medida no probe run)."""
    for limite, tier in TIERS:
        if one_op_s < limite:
            return tier
    return TIER_XLARGE


# ----------------------------------------------------------------- estatistica


def _percentile_linear(ordenado: list[int], q: float) -> float:
    """Percentil por interpolacao linear (metodo 'linear' do numpy/R-7).

    O nearest-rank do harness antigo devolvia `max` para n pequeno — um p95 que
    e' o maximo disfarcado nao e' percentil, e' rotulo.
    """
    if not ordenado:
        raise ValueError("amostra vazia")
    if len(ordenado) == 1:
        return float(ordenado[0])
    pos = q * (len(ordenado) - 1)
    baixo = int(pos)
    alto = min(baixo + 1, len(ordenado) - 1)
    frac = pos - baixo
    return ordenado[baixo] * (1.0 - frac) + ordenado[alto] * frac


P95_MIN_N = 20   # abaixo disso o p95 nao e' estimavel; o campo FICA AUSENTE


def resumir(samples_ns: list[int]) -> dict:
    """Estatistica derivada das amostras cruas. As cruas seguem no registro."""
    if not samples_ns:
        return {"n": 0}
    ordenado = sorted(samples_ns)
    n = len(ordenado)
    mediana = statistics.median(ordenado)
    media = statistics.fmean(ordenado)
    out: dict = {
        "n": n,
        "samples_ns": list(samples_ns),          # R1: o artefato de verdade
        "min_ns": ordenado[0],
        "max_ns": ordenado[-1],
        "median_ns": int(mediana),
        "mean_ns": int(media),
        "outliers_dropped": 0,                   # nunca descartar em silencio
    }
    if n >= 2:
        stdev = statistics.stdev(ordenado)
        out["stddev_ns"] = int(stdev)
        out["cv"] = round(stdev / media, 6) if media else None
        out["iqr_ns"] = int(_percentile_linear(ordenado, 0.75)
                            - _percentile_linear(ordenado, 0.25))
        desvios = [abs(x - mediana) for x in ordenado]
        out["mad_ns"] = int(statistics.median(desvios))
    if n >= P95_MIN_N:                            # senao: campo AUSENTE, de proposito
        out["p95_ns"] = int(_percentile_linear(ordenado, 0.95))
        out["percentile_method"] = "linear"
    return out


# ----------------------------------------------------------------- medicao


def medir(fn: Callable[[], object], *, tier: Tier | None = None,
          probe: bool = True) -> dict:
    """Cronometra `fn` com wall E cpu, devolvendo amostras cruas + derivadas.

    Se `tier` e' None e `probe` e' True, roda UMA vez pra classificar o tier —
    esse probe run tambem serve de warmup e NAO entra nas amostras.
    """
    if tier is None:
        t0, c0 = time.perf_counter_ns(), time.process_time_ns()
        fn()
        dur_ns = time.perf_counter_ns() - t0
        cpu_probe_ns = time.process_time_ns() - c0
        tier = classify_tier(dur_ns / 1e9)
        probe_info = {"probe_wall_ns": dur_ns, "probe_cpu_ns": cpu_probe_ns}
    else:
        probe_info = {}

    for _ in range(tier.warmup):
        fn()

    wall: list[int] = []
    cpu: list[int] = []
    for _ in range(tier.n):
        c0 = time.process_time_ns()
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        c1 = time.process_time_ns()
        wall.append(t1 - t0)
        cpu.append(c1 - c0)

    res = resumir(wall)
    res.update({
        "warmup": tier.warmup,
        "tier": tier.name,
        "estimator": tier.estimator,
        "mde_pct": tier.mde_pct,          # trava claims abaixo da resolucao
        "comparable": tier.comparable,
        "method": "wall-perf_counter_ns",
        "cpu": resumir(cpu),
        **probe_info,
    })
    # ~1.0 = serial ligado em CPU · <1.0 = espera/IPC/spawn · >1.0 = paralelo real
    w = res.get("median_ns") or 0
    c = res["cpu"].get("median_ns") or 0
    res["wall_cpu_ratio"] = round(c / w, 4) if w else None
    # o estimador primario do tier, explicito, pra o comparador nao ter que adivinhar
    res["point_ns"] = res["min_ns"] if tier.estimator == "min" else res["median_ns"]
    return res


__all__ = ["Tier", "TIERS", "TIER_XLARGE", "classify_tier", "resumir", "medir",
           "P95_MIN_N", "_percentile_linear"]
