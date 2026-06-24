"""Encode de colunas — serial + paralelo (HOST so'-Python).

Paralelismo via `ProcessPoolExecutor` (Fase 1b: work-stealing). E' concern de
HOSPEDEIRO (multiprocessing do Python), NAO do core portavel — um port C/Rust
re-implementa o paralelismo no seu proprio runtime. Output byte-identico ao
serial (paralelismo so' reordena computacao, nao bytes).

Concern isolado de `multi.core` (P1 modularizacao, 2026-06-24).
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed

from tcf.encoder import _encode_column
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs


def _encode_columns_serial(
    table_str: dict[str, list[str]],
    want_side: bool,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas serialmente (comportamento original)."""
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for col_name, str_values in table_str.items():
        side = SideOutputs() if want_side else None
        body = _encode_column(str_values, header=col_name, side=side, cfg=cfg,
                              min_len=min_len)
        col_bodies.append((col_name, body.encode("utf-8")))
        if want_side:
            per_col_sides[col_name] = side
    return col_bodies, per_col_sides


def _encode_columns_parallel(
    table_str: dict[str, list[str]],
    want_side: bool,
    n_workers: int,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas em paralelo via ProcessPoolExecutor (Fase 1b: work-stealing).

    Estrategia (sub-fase otimizacao 2026-05-24):
    1. **Ordena colunas por workload descendente** (sum de bytes por coluna)
       — heavyweights submetidos primeiro, workers ocupam mais cedo
    2. **Submit + as_completed** ao inves de map — work-stealing dinamico
       (workers pegam proxima coluna assim que terminam, sem esperar
       fila sequencial)
    3. **Reordena resultado** por ordem original do dict (output
       byte-identico independente da ordem de conclusao)

    Output byte-identico ao serial — paralelismo apenas reordena
    computacao, nao bytes.
    """
    original_order = list(table_str.keys())

    # Heuristica de workload: sum de bytes de cada coluna (proxy razoavel
    # pra custo HCC que e' dominado pelo tamanho dos valores). Sorted desc.
    cols_with_work = sorted(
        (
            (sum(len(v) for v in table_str[name]), name)
            for name in original_order
        ),
        key=lambda x: -x[0],
    )

    results_by_name: dict[str, tuple[str, SideOutputs | None]] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        future_to_name = {
            ex.submit(_worker_encode_column,
                      (name, table_str[name], want_side, cfg, min_len)): name
            for _, name in cols_with_work
        }
        for future in as_completed(future_to_name):
            col_name, body_str, side = future.result()
            results_by_name[col_name] = (body_str, side)

    # Reordena pela ordem original do dict (output deterministico)
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for name in original_order:
        body_str, side = results_by_name[name]
        col_bodies.append((name, body_str.encode("utf-8")))
        if want_side:
            per_col_sides[name] = side
    return col_bodies, per_col_sides


def _worker_encode_column(args) -> tuple[str, str, SideOutputs | None]:
    """Worker module-level (picklavel) pra ProcessPoolExecutor.

    Recebe (col_name, str_values, want_side, cfg, min_len); retorna
    (col_name, body_str, side).
    """
    col_name, str_values, want_side, cfg, min_len = args
    side = SideOutputs() if want_side else None
    body = _encode_column(str_values, header=col_name, side=side, cfg=cfg,
                          min_len=min_len)
    return col_name, body, side
