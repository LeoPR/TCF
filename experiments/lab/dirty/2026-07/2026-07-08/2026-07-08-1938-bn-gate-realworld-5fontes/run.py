"""run.py — GATE real-world do bN (D3, H-TYPE-02) em 8 fontes reais distintas.

Mede bN vs PRODUCAO REAL (fallback=True, min tcf/raw/v2b/split) no nivel-TABELA (weighted), pre e pos-brotli.
Gate CLAUDE.md ponto 5: bytes absolutos >=5% weighted real-world. Margem terminal: H-TYPE-03.

Fontes (>=5, inclui beijing-pm25 = ponto cego do ADR-0018): adult, tpch/lineitem, receita, br/pessoas,
ibge, beijing, online-retail, wine. Tabelas grandes amostradas (LIMIT) — declarado. Roda com python3 (brotli).
`python3 run.py` regenera artifacts/. NAO toca src/tcf.
"""
from __future__ import annotations
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_ROOT = HERE.parents[3]
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import bn_gate as G                                  # noqa: E402
from tcf import encode                               # noqa: E402
import brotli                                        # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
INTERIM = Path("Z:/tcf-data/interim")
EXTERNAL = Path("Z:/tcf-data/external")
CAP = 20000                                          # amostra p/ tabelas grandes (declarado)


def nb(s): return len(s.encode()) if isinstance(s, str) else len(s)
def brz(b): return len(brotli.compress(b if isinstance(b, bytes) else b.encode(), quality=11))
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def load_db(db, table, cap=CAP):
    con = sqlite3.connect(f"file:{INTERIM/db}?mode=ro", uri=True)
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    d = {c: [str(r[0]) for r in con.execute(f'SELECT "{c}" FROM "{table}" LIMIT {cap}')] for c in cols}
    con.close()
    return d


def load_csv(path, cap=CAP):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:cap + 1]
    return {h: [r[i] if i < len(r) else "" for r in data] for i, h in enumerate(header)}


SOURCES = [
    ("adult", lambda: load_db("adult-census.db", "adult")),
    ("tpch.lineitem", lambda: load_db("tpch-sf001.db", "lineitem")),
    ("receita.estab", lambda: load_db("receita-cnpj.db", "estabelecimentos")),
    ("br.pessoas", lambda: load_db("br-identidades.db", "pessoas")),
    ("ibge.municipios", lambda: load_db("ibge-municipios.db", "municipios")),
    ("beijing-pm25", lambda: load_csv(EXTERNAL / "beijing-pm25" / "beijing_pm25.csv")),
    ("online-retail", lambda: load_csv(EXTERNAL / "online-retail" / "online_retail.csv")),
    ("wine", lambda: load_csv(EXTERNAL / "wine-quality" / "wine.csv")),
]


def measure(tag, cols):
    n = len(next(iter(cols.values()))) if cols else 0
    prod_table, parsed = G.extract_table(cols)          # UMA passada de encode
    ref_parts, bn_parts, per = [], [], []
    tot_bn_saving = 0
    for (name, mode, pb) in parsed:
        vals = [str(x) for x in cols[name]]
        k = len(set(vals))
        bn_body, _dom = G.bn_encode(vals)
        wins = bn_body is not None and len(bn_body) < len(pb)
        if bn_body is not None:
            assert G.bn_decode(bn_body, n) == vals, f"RT bN falhou {tag}.{name}"
        ref_parts.append(pb)
        bn_parts.append(bn_body if wins else pb)
        if wins:
            tot_bn_saving += len(pb) - len(bn_body)
        per.append((name, k, mode, len(pb), (len(bn_body) if bn_body is not None else None), wins))
    ref_cat = b"".join(ref_parts)
    bn_cat = b"".join(bn_parts)
    pre_pct = 100 * tot_bn_saving / prod_table if prod_table else 0
    ref_brz, bn_brz = brz(ref_cat), brz(bn_cat)
    pos_pct = 100 * (ref_brz - bn_brz) / ref_brz if ref_brz else 0
    return {"tag": tag, "n": n, "ncols": len(cols), "prod_table": prod_table,
            "saving_pre": tot_bn_saving, "pre_pct": pre_pct,
            "ref_brz": ref_brz, "bn_brz": bn_brz, "pos_pct": pos_pct, "per": per}


def main():
    res = []
    per_lines = ["# POR COLUNA — bN vs producao real (min tcf/raw/v2b/split) por fonte", "",
                 "| fonte | coluna | k | modo-prod | prod B | bN B | bN vence? |", "|---|---|---|---|---|---|---|"]
    for tag, loader in SOURCES:
        cols = loader()
        m = measure(tag, cols)
        res.append(m)
        for (c, k, mode, pbz, bnz, wins) in m["per"]:
            per_lines.append(f"| {tag} | {c} | {k} | {mode} | {pbz} | {bnz if bnz is not None else '-'} | "
                             f"{'SIM' if wins else 'nao'} |")
    w("01-por-coluna.txt", "\n".join(per_lines) + "\n")

    T = ["# NIVEL-TABELA — weighted % de economia do bN vs producao, PRE e POS brotli", "",
         "| fonte | N | cols | prod tabela B | economia pre B | **pre %** | ref+brz | bN+brz | **pos %** |",
         "|---|---|---|---|---|---|---|---|---|"]
    tot_prod, tot_save, tot_refbrz, tot_bnbrz = 0, 0, 0, 0
    for m in res:
        T.append(f"| {m['tag']} | {m['n']} | {m['ncols']} | {m['prod_table']} | {m['saving_pre']} | "
                 f"**{m['pre_pct']:.1f}%** | {m['ref_brz']} | {m['bn_brz']} | **{m['pos_pct']:.1f}%** |")
        tot_prod += m["prod_table"]; tot_save += m["saving_pre"]
        tot_refbrz += m["ref_brz"]; tot_bnbrz += m["bn_brz"]
    agg_pre = 100 * tot_save / tot_prod if tot_prod else 0
    agg_pos = 100 * (tot_refbrz - tot_bnbrz) / tot_refbrz if tot_refbrz else 0
    T += ["", f"**WEIGHTED AGREGADO ({len(res)} fontes)**: pre-brotli **{agg_pre:.1f}%** · "
          f"pos-brotli **{agg_pos:.1f}%**",
          "", "LEITURA: 'pre %' = economia do bN vs producao no nivel-tabela (nicho TERMINAL, sem re-compressao).",
          "'pos %' = a mesma tabela apos brotli q11 (nicho re-comprimido). O gate CLAUDE.md ponto 5 pede >=5%",
          "weighted real-world. Tabelas grandes amostradas a LIMIT=" + str(CAP) + " (declarado)."]
    w("02-tabela-weighted.txt", "\n".join(T) + "\n")

    R = ["# GATE real-world do bN (D3, H-TYPE-02) — 8 fontes [resumo]", "",
         f"## WEIGHTED AGREGADO: pre-brotli {agg_pre:.1f}% · pos-brotli {agg_pos:.1f}%", "",
         "## Por fonte (pre % / pos %)"]
    for m in res:
        R.append(f"  {m['tag']:16s} pre={m['pre_pct']:5.1f}%  pos={m['pos_pct']:5.1f}%  (N={m['n']}, cols={m['ncols']})")
    veredito_pre = ">=5% (passa o gate ponto-5 no nicho terminal)" if agg_pre >= 5 else "<5% (NAO passa o gate ponto-5)"
    veredito_pos = ">=5%" if agg_pos >= 5 else "<5% (colapsa sob brotli)"
    R += ["", "## Veredito (do numero)",
          f"- Terminal (pre-brotli): weighted {agg_pre:.1f}% → {veredito_pre}.",
          f"- Re-comprimido (pos-brotli): weighted {agg_pos:.1f}% → {veredito_pos}.",
          "- Baseline = PRODUCAO real (min tcf/raw/v2b/split), N=8 fontes reais distintas (inclui beijing-pm25,",
          "  o ponto cego do ADR-0018). bN RT-OK em toda coluna aplicavel. Tabelas grandes amostradas (LIMIT).",
          "- H-TYPE-02: atualizar status conforme o numero (ver result.md)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
