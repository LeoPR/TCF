"""B1 Etapa 4 — teste TCF-nativo do cross-dict: textual + paralelismo + lazy.

READ-ONLY, src/tcf intocado. SEM gate de brotli (correcao do owner 2026-06-21:
brotli nem sempre e' aplicado e e' incompativel com lazy). Mede o que importa pro
TCF-nativo: bytes textuais, preludio serial (paralelismo), e lazy (bytes tocados +
dict-decodes) em query single-col e cross-col.

Modelo (exato, via internos V2-B):
  V0 per-column @dict: cada coluna = <len(tab)>\\n + tabela_c + stream_c (N*w(K_c))
  V1 global: 1 tabela global + streams (N*w(K_global)) por coluna

Cenarios: (a) flags full-share K pequeno; (b) same-domain refs K grande (caso-uso real:
origem/destino, de/para, source/target); (c) partial-share; (d) disjunto/entidade.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.encoder import _encode_column          # noqa: E402
from tcf.pipeline import PipelineConfig          # noqa: E402

CFG = PipelineConfig()


def w94(k):
    w, c = 1, 94
    while k > c:
        w += 1; c *= 94
    return w


def tbytes(vals_unique):
    return len(_encode_column(vals_unique, header="val", cfg=CFG, min_len=None).encode())


def col_model(vals):
    """(K, table_bytes, stream_bytes, body_bytes) do @dict per-column."""
    seen, uni = {}, []
    for v in vals:
        if v not in seen:
            seen[v] = len(uni); uni.append(v)
    K = len(uni)
    tb = tbytes(uni)
    sb = len(vals) * w94(K)
    body = len(f"{tb}\n".encode()) + tb + sb
    return K, tb, sb, body, uni


def measure(cols):
    pc = {n: col_model(v) for n, v in cols.items()}
    # V0
    v0_txt = sum(m[3] for m in pc.values())
    # global
    gseen, guni = {}, []
    for v in cols.values():
        for x in v:
            if x not in gseen:
                gseen[x] = len(guni); guni.append(x)
    Kg = len(guni); wg = w94(Kg)
    gtab = tbytes(guni)
    gtab_part = len(f"{gtab}\n".encode()) + gtab
    streams = {n: len(v) * wg for n, v in cols.items()}
    v1_txt = gtab_part + sum(streams.values())

    # --- metricas ---
    C = len(cols)
    first = next(iter(cols))
    return {
        "C": C, "Kg": Kg, "wg": wg,
        "v0_txt": v0_txt, "v1_txt": v1_txt,
        "net_txt_pct": 100 * (v1_txt - v0_txt) / v0_txt,
        # paralelismo: preludio serial (bytes lidos antes de qualquer coluna)
        "v0_prelude": 0,
        "v1_prelude": gtab_part,
        # lazy single-col group_count(first): bytes tocados + dict-decodes
        "v0_single_touch": pc[first][3], "v0_single_decodes": 1,
        "v1_single_touch": gtab_part + streams[first], "v1_single_decodes": 1,
        # lazy cross-col (todas as cols dict): bytes tocados + dict-decodes
        "v0_cross_touch": sum(m[3] for m in pc.values()), "v0_cross_decodes": C,
        "v1_cross_touch": gtab_part + sum(streams.values()), "v1_cross_decodes": 1,
    }


def report(label, cols):
    m = measure(cols)
    print(f"\n{'='*72}\n{label}\n{'='*72}")
    print(f"  C={m['C']} cols, K_global={m['Kg']} (width={m['wg']})")
    print(f"  TEXTUAL:      V0={m['v0_txt']}  V1={m['v1_txt']}  net={m['net_txt_pct']:+.1f}%")
    print(f"  PARALELISMO:  preludio serial  V0={m['v0_prelude']}B  V1={m['v1_prelude']}B "
          f"(V1 le' a tabela global antes de qualquer coluna)")
    print(f"  LAZY single-col group_count(1a):")
    print(f"     bytes tocados V0={m['v0_single_touch']}  V1={m['v1_single_touch']}  "
          f"({'V1 PIOR' if m['v1_single_touch']>m['v0_single_touch'] else ('igual' if m['v1_single_touch']==m['v0_single_touch'] else 'V1 melhor')})")
    print(f"     dict-decodes  V0={m['v0_single_decodes']}  V1={m['v1_single_decodes']}")
    print(f"  LAZY cross-col (todas as cols):")
    print(f"     bytes tocados V0={m['v0_cross_touch']}  V1={m['v1_cross_touch']}  "
          f"({'V1 melhor' if m['v1_cross_touch']<m['v0_cross_touch'] else 'igual/pior'})")
    print(f"     dict-decodes  V0={m['v0_cross_decodes']}  V1={m['v1_cross_decodes']}  "
          f"(V1 le' o dict 1x; V0 le' {m['C']}x)")


if __name__ == "__main__":
    rng = random.Random(7)
    N = 2000

    # (a) flags full-share, vocab pequeno
    flags = {f"q{c:02d}": rng.choices(["SIM", "NAO"], k=N) for c in range(16)}
    report("(a) FLAGS full-share K=2 (16 cols SIM/NAO)", flags)

    # (b) same-domain refs, vocab GRANDE compartilhado (caso-uso real)
    codes = [f"AP{i:03d}" for i in range(300)]   # ex: codigos de aeroporto
    sd = {name: rng.choices(codes, k=N) for name in ("origem", "conexao", "destino")}
    report("(b) SAME-DOMAIN refs K=300 (origem/conexao/destino — voos/grafo/transacao)", sd)

    # (c) partial-share: 4 cols, pools sobrepostos parcialmente
    pool = [f"X{i:02d}" for i in range(100)]
    pc_cols = {}
    for c in range(4):
        sub = pool[c*15: c*15+60]   # janelas deslizantes -> overlap parcial
        pc_cols[f"p{c}"] = rng.choices(sub, k=N)
    report("(c) PARTIAL-share (4 cols, overlap parcial -> uniao > cada col)", pc_cols)

    # (d) disjunto/entidade (como adult): 6 cols de dominios distintos
    dj = {}
    for c in range(6):
        dom = [f"d{c}_{i:02d}" for i in range(40)]
        dj[f"attr{c}"] = rng.choices(dom, k=N)
    report("(d) DISJUNTO/entidade (6 cols x 40 distintos -> uniao cruza 94)", dj)
