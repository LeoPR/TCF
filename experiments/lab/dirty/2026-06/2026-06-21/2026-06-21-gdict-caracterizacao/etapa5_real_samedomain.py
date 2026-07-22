"""B1 Etapa 5 — cross-dict em DADOS REAIS com colunas same-domain-ref.

READ-ONLY. Le raw de Z:/tcf-data/external/ (dados ficam em Z:; no projeto so'
este script + provenance). SEM gate de brotli (correcao owner): mede TCF-nativo
(textual + paralelismo + lazy).

Datasets (same-domain-ref reais):
  - OpenFlights routes: source_airport / dest_airport (codigos IATA, mesmo dominio);
    e source_airport_id / dest_airport_id (ids, mesmo dominio) — 2 grupos.
  - SNAP ca-GrQc: from_node / to_node (edge-list, mesmo dominio de nos).

Cada grupo same-domain e' o que o hibrido V2 pool. Compara V0 (per-column @dict)
vs V1/V2 (dict compartilhado do grupo).
"""
from __future__ import annotations

import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
from etapa4_lazy_parallel import measure  # noqa: E402

EXT = Path("Z:/tcf-data/external")


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def load_openflights():
    rows = []
    for line in (EXT / "openflights" / "routes.dat").read_text(encoding="utf-8", errors="replace").splitlines():
        p = line.split(",")
        if len(p) >= 6:
            rows.append(p)
    return {
        "source_airport": [r[2] for r in rows],
        "dest_airport":   [r[4] for r in rows],
        "source_airport_id": [r[3] for r in rows],
        "dest_airport_id":   [r[5] for r in rows],
    }


def load_grqc():
    src, dst = [], []
    for line in (EXT / "snap-ca-grqc" / "ca-GrQc.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        a, b = line.split()
        src.append(a); dst.append(b)
    return {"from_node": src, "to_node": dst}


def show(label, group):
    n = len(next(iter(group.values())))
    cols = list(group)
    jac = jaccard(group[cols[0]], group[cols[1]]) if len(cols) == 2 else None
    m = measure(group)
    print(f"\n{'='*72}\n{label}\n{'='*72}")
    print(f"  cols={cols}  N={n}  K_global={m['Kg']} (w={m['wg']})"
          + (f"  Jaccard(par)={jac:.3f}" if jac is not None else ""))
    print(f"  TEXTUAL:     V0={m['v0_txt']}  V1/V2={m['v1_txt']}  net={m['net_txt_pct']:+.1f}%")
    print(f"  PARALELISMO: preludio serial V1={m['v1_prelude']}B (depois as colunas paralelizam)")
    print(f"  LAZY single-col group_count: V0={m['v0_single_touch']}B  V1={m['v1_single_touch']}B "
          f"({'V1 pior' if m['v1_single_touch']>m['v0_single_touch'] else 'igual/melhor'})")
    print(f"  LAZY cross-col (ex: 'tudo que toca o no/aeroporto X' = scan dos 2 streams):")
    print(f"     bytes V0={m['v0_cross_touch']}  V1={m['v1_cross_touch']}  "
          f"net={100*(m['v1_cross_touch']-m['v0_cross_touch'])/m['v0_cross_touch']:+.1f}%  "
          f"| dict-decodes V0={m['v0_cross_decodes']} V1={m['v1_cross_decodes']}")


if __name__ == "__main__":
    of = load_openflights()
    show("OpenFlights — IATA codes (source_airport ~ dest_airport)",
         {"source_airport": of["source_airport"], "dest_airport": of["dest_airport"]})
    show("OpenFlights — airport IDs (source_airport_id ~ dest_airport_id)",
         {"source_airport_id": of["source_airport_id"], "dest_airport_id": of["dest_airport_id"]})
    g = load_grqc()
    show("SNAP ca-GrQc — edge-list (from_node ~ to_node)", g)
