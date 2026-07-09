"""run.py — F3 misto seletivo: bN como candidato do min() gated a w<=4 (k<=16). Byte-SAFE por construção.

Mede o ganho MARGINAL de ADICIONAR bN ao min(tcf/raw/v2b/split) da produção, restrito a w<=4, em 8 fontes
reais (weighted), pré e pós-brotli. Decompõe: w<=4 (F3, honesto) vs o extra de k 17..256 (w=8, que o D3
contava mas F3 descarta — lá bN=v2b, é só "1 byte < 2 chars", não bit-packing).

Roda com python3 (src + brotli). `python3 run.py` regenera artifacts/. NÃO toca src/tcf.
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
import bn_f3 as F                                        # noqa: E402
import brotli                                            # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
INTERIM = Path("Z:/tcf-data/interim")
EXTERNAL = Path("Z:/tcf-data/external")
CAP = 20000


def brz(b): return len(brotli.compress(b, quality=11))
def wf(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


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
    prod_table, parsed = F.extract_table(cols)
    prod_parts, f3_parts = [], []
    save_f3, save_wide = 0, 0
    by_w = {1: [0, 0], 2: [0, 0], 4: [0, 0], 8: [0, 0]}   # w → [n_wins, bytes_saved]
    per = []
    for (name, mode, pb) in parsed:
        vals = [str(x) for x in cols[name]]
        k = len(set(vals))
        b4 = F.bn_body(vals, k, wide=False)               # F3: w<=4
        bw = F.bn_body(vals, k, wide=True)                # D3-style: até w=8
        win4 = b4 is not None and len(b4) < len(pb)
        winw = bw is not None and len(bw) < len(pb)
        if b4 is not None:
            assert F.bn_decode(b4, n, wide=False) == vals, f"RT F3 falhou {tag}.{name}"
        if bw is not None:
            assert F.bn_decode(bw, n, wide=True) == vals, f"RT wide falhou {tag}.{name}"
        prod_parts.append(pb)
        f3_parts.append(b4 if win4 else pb)               # F3 = min(prod, bN-w<=4)
        if win4:
            s = len(pb) - len(b4)
            save_f3 += s
            w = F.width_f3(k)
            by_w[w][0] += 1
            by_w[w][1] += s
        if winw:
            sw = len(pb) - len(bw)
            save_wide += sw
            if not win4:                                  # ganho que SÓ existe no wide (k 17..256, w=8)
                by_w[8][0] += 1
                by_w[8][1] += sw
        per.append((name, k, mode, len(pb),
                    (len(b4) if b4 is not None else None), win4,
                    (F.width_f3(k) if F.width_f3(k) else (8 if bw is not None else None))))
    prod_cat = b"".join(prod_parts)
    f3_cat = b"".join(f3_parts)
    prod_brz, f3_brz = brz(prod_cat), brz(f3_cat)
    return {
        "tag": tag, "n": n, "ncols": len(cols), "prod_table": prod_table,
        "save_f3": save_f3, "save_wide": save_wide,
        "pre_pct": 100 * save_f3 / prod_table if prod_table else 0,
        "prod_brz": prod_brz, "f3_brz": f3_brz,
        "pos_pct": 100 * (prod_brz - f3_brz) / prod_brz if prod_brz else 0,
        "wide_pct": 100 * save_wide / prod_table if prod_table else 0,
        "by_w": by_w, "per": per,
    }


def main():
    res = []
    for tag, loader in SOURCES:
        print(f"... {tag}", flush=True)
        res.append(measure(tag, loader()))
    print("... agregando", flush=True)

    # 01 — por coluna
    P = ["# F3 por coluna — bN-w<=4 (min com produção) por fonte", "",
         "| fonte | coluna | k | modo-prod | prod B | bN B | w | F3 vence? |",
         "|---|---|---|---|---|---|---|---|"]
    for m in res:
        for (c, k, mode, pbz, bnz, win, w) in m["per"]:
            P.append(f"| {m['tag']} | {c} | {k} | {mode} | {pbz} | {bnz if bnz is not None else '-'} | "
                     f"{w if w is not None else '-'} | {'SIM' if win else 'nao'} |")
    wf("01-por-coluna.txt", "\n".join(P) + "\n")

    # 02 — nível-tabela weighted
    T = ["# F3 nível-tabela — ganho MARGINAL de bN-w<=4 sobre a produção, PRE e POS brotli", "",
         "| fonte | N | cols | prod tabela B | econ w<=4 B | **pre %** | prod+brz | F3+brz | **pos %** | (wide w<=8 pre %) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    tp, sf, sw_, pbz_, f3bz_ = 0, 0, 0, 0, 0
    for m in res:
        T.append(f"| {m['tag']} | {m['n']} | {m['ncols']} | {m['prod_table']} | {m['save_f3']} | "
                 f"**{m['pre_pct']:.1f}%** | {m['prod_brz']} | {m['f3_brz']} | **{m['pos_pct']:.1f}%** | "
                 f"{m['wide_pct']:.1f}% |")
        tp += m["prod_table"]; sf += m["save_f3"]; sw_ += m["save_wide"]
        pbz_ += m["prod_brz"]; f3bz_ += m["f3_brz"]
    agg_pre = 100 * sf / tp if tp else 0
    agg_pos = 100 * (pbz_ - f3bz_) / pbz_ if pbz_ else 0
    agg_wide = 100 * sw_ / tp if tp else 0
    T += ["", f"**WEIGHTED ({len(res)} fontes)**: F3 (w<=4) pre-brotli **{agg_pre:.1f}%** · "
          f"pos-brotli **{agg_pos:.1f}%** · (wide w<=8 pre-brotli {agg_wide:.1f}%, = D3)",
          "", "LEITURA: 'pre %' = ganho de ADICIONAR bN-w<=4 ao min() da produção; byte-SAFE só no TERMINAL",
          "(F3<=prod em bytes terminais). PÓS-brotli NÃO é safe: receita = -0.2% (bits densos comprimem pior",
          "que o stream base-94 repetitivo). Denominador: 'pre %' usa prod_table (com header, sem comprimir);",
          "'pos %' compara corpos-concat pós-brotli (sem header) — o ~1 byte/coluna do discriminador de modo bN",
          f"é omitido (~20 B, desprezível vs economia). 'wide' = até w=8 (k 95..256). LIMIT={CAP} (declarado)."]
    wf("02-tabela-weighted.txt", "\n".join(T) + "\n")

    # 03 — decomposição por largura
    agg_w = {1: [0, 0], 2: [0, 0], 4: [0, 0], 8: [0, 0]}
    for m in res:
        for w, (nw, sb) in m["by_w"].items():
            agg_w[w][0] += nw; agg_w[w][1] += sb
    D = ["# F3 decomposição — de onde vem o ganho terminal (por largura w)", "",
         "| w | k | tile-de-byte? | colunas que vencem | bytes economizados | % do prod total |",
         "|---|---|---|---|---|---|"]
    labels = {1: "<=2", 2: "<=4", 4: "<=16", 8: "95..256*"}
    tile = {1: "sim (8/byte)", 2: "sim (4/byte)", 4: "sim (2/byte)", 8: "NÃO (1 val/byte)"}
    for w in (1, 2, 4, 8):
        nw, sb = agg_w[w]
        D.append(f"| {w} | {labels[w]} | {tile[w]} | {nw} | {sb} | {100*sb/tp if tp else 0:.2f}% |")
    D += ["", "* w=8 vence v2b SÓ p/ k 95..256 (v2b usa 2 chars/idx; bN 1 byte). Em k 17..94 bN=v2b=1 byte → 0 wins.",
          f"F3 (w<=4) soma = {agg_w[1][1]+agg_w[2][1]+agg_w[4][1]} B ({agg_pre:.1f}% do prod).",
          f"w=8 extra = {agg_w[8][1]} B ({100*agg_w[8][1]/tp if tp else 0:.2f}%) — F3 DESCARTA: 8 bits = 1 byte exato",
          "(sem densidade sub-byte); só ganha de v2b trocando 2 chars por 1 byte, não é bit-packing.",
          "CONCLUSÃO: o bit-packing sub-byte verdadeiro mora em w<=4; e mesmo esse colapsa pós-brotli — pode ir",
          "NET-NEGATIVO (receita -0.2%), pois bits densos comprimem pior que o base-94 repetitivo do v2b."]
    wf("03-decomposicao-w.txt", "\n".join(D) + "\n")

    # 00 — resumo
    R = ["# F3 misto seletivo (bN-w<=4 no min) — 8 fontes [resumo]", "",
         f"## WEIGHTED: F3 pre-brotli {agg_pre:.1f}% · pos-brotli {agg_pos:.1f}% · (wide w<=8: {agg_wide:.1f}%)",
         "", "## Por fonte (F3 pre % / pos %)"]
    for m in res:
        R.append(f"  {m['tag']:16s} pre={m['pre_pct']:5.1f}%  pos={m['pos_pct']:5.1f}%  (N={m['n']}, cols={m['ncols']})")
    R += ["", "## Veredito (do número)",
          f"- BYTE-SAFE só no TERMINAL por construção (min em bytes terminais → F3<=prod terminal). Weighted {agg_pre:.1f}%.",
          f"- Pós-brotli weighted {agg_pos:.1f}%: NÃO é byte-safe — pode ir NET-NEGATIVO (receita -0.2%). Bits densos",
          "  comprimem pior que o base-94 repetitivo. Nicho é terminal/streaming, não re-comprimido.",
          f"- Decomposição: w<=4 (bit-packing sub-byte) = {agg_pre:.1f}%; o extra até w=8 ({agg_wide-agg_pre:.1f} p.p., k 95..256)",
          "  NÃO é bit-packing (8 bits=1 byte; só vence v2b trocando 2 chars por 1 byte) — F3 descarta.",
          "- Reproduz D3 (wide=8.8%) e casa com F1 (o valor é latência/terminal, não byte re-comprimido)."]
    wf("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
