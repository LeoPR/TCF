"""B1.0 — cross-dict (H-GDICT): medicao analitica em sinteticos minimos.

READ-ONLY. NAO toca src/tcf. Usa os internos reais do V2-B (_v2b_encode,
_encode_column, _v2b_width) pra modelar com bytes exatos:

  - @dict per-column (HOJE): cada coluna carrega <len(tab)>\\n + tabela + stream(N*w(K_c))
  - cross-dict GLOBAL: 1 tabela compartilhada no header + cada coluna = stream(N*w(K_global))

Net = (tabelas duplicadas que colapsam) - (indice global mais largo pago em toda linha).
Mede textual E sob brotli. So' o corpo do dict (tabela+stream); meta do header e'
secundaria e estimada a parte.
"""
from __future__ import annotations

import brotli

from tcf.encoder import _encode_column
from tcf.multi import _v2b_encode, _v2b_width, _V2B_BASE
from tcf.pipeline import PipelineConfig

CFG = PipelineConfig()


def br(s: bytes) -> int:
    return len(brotli.compress(s, quality=11))


def per_column_dict(table: dict[str, list[str]]):
    """Modo HOJE: cada coluna = body V2-B independente (tabela propria + stream)."""
    bodies = {}
    for name, vals in table.items():
        body = _v2b_encode(vals, cfg=CFG, min_len=None)
        bodies[name] = body  # bytes ou None (se nao aplicavel)
    return bodies


def global_dict(table: dict[str, list[str]]):
    """Modo CROSS-DICT: 1 tabela global (uniao dos unicos) + streams por coluna."""
    # uniao preservando ordem first-seen global
    gseen: dict[str, int] = {}
    gunicas: list[str] = []
    for vals in table.values():
        for v in vals:
            if v not in gseen:
                gseen[v] = len(gunicas)
                gunicas.append(v)
    K = len(gunicas)
    w = _v2b_width(K)
    gtable = _encode_column(gunicas, header="val", cfg=CFG, min_len=None).encode("utf-8")
    streams = {}
    for name, vals in table.items():
        streams[name] = "".join(
            _v2b_idx(gseen[v], w) for v in vals
        ).encode("utf-8")
    return gtable, streams, K, w


def _v2b_idx(idx: int, width: int) -> str:
    alpha = "".join(chr(c) for c in range(0x21, 0x7F))
    if width == 1:
        return alpha[idx]
    out = []
    for _ in range(width):
        out.append(alpha[idx % _V2B_BASE])
        idx //= _V2B_BASE
    return "".join(reversed(out))


def analyze(label: str, table: dict[str, list[str]]):
    print(f"\n{'='*70}\n{label}\n{'='*70}")
    nrows = len(next(iter(table.values())))
    cards = {n: len(set(v)) for n, v in table.items()}
    print(f"colunas={list(table)}  N={nrows}  card_por_col={cards}")

    # --- HOJE: @dict per-column ---
    bodies = per_column_dict(table)
    pc_total = 0
    pc_concat = b""
    n_dict_cols = 0
    for name, body in bodies.items():
        if body is None:
            print(f"  [per-col] {name}: V2-B nao aplicavel (high-card/sem repeticao) -> ficaria tcf/raw")
            continue
        n_dict_cols += 1
        pc_total += len(body)
        pc_concat += body
    print(f"  PER-COLUMN @dict: {pc_total} B textual  |  {br(pc_concat)} B brotli  ({n_dict_cols} cols dict)")

    # --- CROSS-DICT global ---
    gtable, streams, K, w = global_dict(table)
    g_table_part = f"{len(gtable)}\n".encode("utf-8") + gtable
    g_streams = b"".join(streams.values())
    g_total = len(g_table_part) + len(g_streams)
    g_concat = g_table_part + g_streams
    print(f"  CROSS-DICT global: {g_total} B textual  |  {br(g_concat)} B brotli  "
          f"(K_global={K}, width={w})")
    print(f"     tabela global={len(g_table_part)} B + streams={len(g_streams)} B")

    # --- decomposicao do net (so' colunas que seriam dict) ---
    dict_cols = {n: table[n] for n, b in bodies.items() if b is not None}
    if dict_cols:
        sum_tables = 0
        sum_stream_pc = 0
        for n, vals in dict_cols.items():
            seen, uni = {}, []
            for v in vals:
                if v not in seen:
                    seen[v] = len(uni); uni.append(v)
            t = _encode_column(uni, header="val", cfg=CFG, min_len=None).encode("utf-8")
            sum_tables += len(f"{len(t)}\n".encode()) + len(t)
            sum_stream_pc += len(vals) * _v2b_width(len(uni))
        # recomputa global so' sobre as dict_cols (comparacao justa)
        gt, gs, Kg, wg = global_dict(dict_cols)
        gt_part = f"{len(gt)}\n".encode() + gt
        save_table = sum_tables - len(gt_part)
        pay_width = sum(len(v) * (wg - _v2b_width(len(set(v)))) for v in dict_cols.values())
        print(f"  NET (so' dict-cols): economia_tabela={save_table:+d} B  "
              f"custo_indice_largo={-pay_width:+d} B  -> net={save_table - pay_width:+d} B textual")
        print(f"     (net>0 = cross-dict ganha; K_global={Kg} width={wg} vs widths_locais)")


if __name__ == "__main__":
    N = 24
    cyc = lambda *xs: [xs[i % len(xs)] for i in range(N)]  # noqa: E731

    # E1 — ALTO OVERLAP, card pequena: 3 flags compartilham {SIM,NAO}
    E1 = {
        "ativo":   cyc("SIM", "NAO"),
        "premium": cyc("SIM", "SIM", "NAO"),
        "mei":     cyc("NAO", "SIM"),
    }
    analyze("E1 — alto overlap, low-card (3 flags SIM/NAO, K_global=2)", E1)

    # E2 — DISJUNTO, uniao cruza 94: 3 cols de 40 valores distintos cada, SEM overlap,
    # com N grande pra (a) cada coluna REPETIR (V2-B aplica, width local=1, K_c=40<=94)
    # e (b) a uniao = 120 > 94 -> width global = 2. Custo do indice largo aparece.
    N2 = 200
    def repeating(prefix, k, n):
        base = [f"{prefix}{i:02d}" for i in range(k)]
        return [base[i % k] for i in range(n)]
    E2 = {
        "colA": repeating("A", 40, N2),
        "colB": repeating("B", 40, N2),
        "colC": repeating("C", 40, N2),
    }
    analyze("E2 — disjunto, uniao cruza 94 (3x40 distintos, N=200 -> K_global=120, width 1->2)", E2)

    # E3 — MISTO realista: flags compartilham SIM/NAO; uf_* compartilham UFs; porte disjunto pequeno
    ufs = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "GO", "PE", "CE"]
    E3 = {
        "flag_ativo":   cyc("SIM", "NAO"),
        "flag_premium": cyc("SIM", "SIM", "NAO"),
        "flag_mei":     cyc("NAO", "SIM", "SIM"),
        "uf_empresa":   [ufs[i % len(ufs)] for i in range(N)],
        "uf_socio":     [ufs[(i * 3) % len(ufs)] for i in range(N)],
        "porte":        cyc("ME", "EPP", "GRANDE"),
    }
    analyze("E3 — misto (flags+uf compartilham, porte disjunto; K_global=15 width 1)", E3)
