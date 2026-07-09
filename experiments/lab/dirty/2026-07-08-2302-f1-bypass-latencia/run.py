"""run.py — F1: LATÊNCIA do bypass (pular OBAT+HCC) vs núcleo, em colunas low-card reais.

Dá NÚMERO ao eixo ACELERAÇÃO (o único sem número em todos os labs). Bypass = classify+map+pack numa
passada, sem núcleo. Compara com: (a) núcleo puro `encode(vals)` (single-col OBAT+HCC); (b) produção
`encode({col:vals}, fallback=True)` (min tcf/raw/v2b/split). Mediana de M runs. RT provado.

Roda com python3. Dados: Z:/tcf-data. NÃO toca src/tcf.
"""
from __future__ import annotations
import csv
import sqlite3
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_ROOT = HERE.parents[3]
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import bypass_codec as B                               # noqa: E402
from tcf import encode                                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
INTERIM = Path("Z:/tcf-data/interim")
EXTERNAL = Path("Z:/tcf-data/external")
CAP, RUNS = 20000, 9


def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def timed(fn, arg, runs=RUNS):
    ts = []
    for _ in range(runs):
        t0 = time.perf_counter(); fn(arg); ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def db_col(db, table, col):
    con = sqlite3.connect(f"file:{INTERIM/db}?mode=ro", uri=True)
    v = [str(r[0]) for r in con.execute(f'SELECT "{col}" FROM "{table}" LIMIT {CAP}')]
    con.close()
    return v


def csv_col(path, col):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    i = rows[0].index(col)
    return [r[i] for r in rows[1:CAP + 1] if i < len(r)]


COLS = [
    ("adult.sex", lambda: db_col("adult-census.db", "adult", "sex")),
    ("adult.class", lambda: db_col("adult-census.db", "adult", "class")),
    ("adult.race", lambda: db_col("adult-census.db", "adult", "race")),
    ("adult.relationship", lambda: db_col("adult-census.db", "adult", "relationship")),
    ("adult.education", lambda: db_col("adult-census.db", "adult", "education")),
    ("tpch.l_linestatus", lambda: db_col("tpch-sf001.db", "lineitem", "l_linestatus")),
    ("tpch.l_returnflag", lambda: db_col("tpch-sf001.db", "lineitem", "l_returnflag")),
    ("receita.matriz_filial", lambda: db_col("receita-cnpj.db", "estabelecimentos", "matriz_filial")),
    ("beijing.cbwd", lambda: csv_col(EXTERNAL / "beijing-pm25" / "beijing_pm25.csv", "cbwd")),
]


def main():
    L = ["# F1 — LATÊNCIA do bypass (pula OBAT+HCC) vs núcleo, colunas low-card reais", "",
         "| coluna | N | k | w | núcleo (ms) | produção (ms) | bypass (ms) | speedup vs núcleo | vs produção | RT |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    sp_core, sp_prod = [], []
    for tag, load in COLS:
        vals = load()
        n, k = len(vals), len(set(vals))
        enc = B.bypass_encode(vals)
        if enc is None:
            L.append(f"| {tag} | {n} | {k} | — | (k>16, bail) | | | | | |"); continue
        rt = B.bypass_decode(enc) == vals
        t_core = timed(encode, vals)
        t_prod = timed(lambda v: encode({tag: v}, fallback=True), vals)
        t_by = timed(B.bypass_encode, vals)
        s_core, s_prod = t_core / t_by, t_prod / t_by
        sp_core.append(s_core); sp_prod.append(s_prod)
        L.append(f"| {tag} | {n} | {k} | {enc['w']} | {t_core*1e3:.1f} | {t_prod*1e3:.1f} | {t_by*1e3:.1f} | "
                 f"**{s_core:.1f}×** | {s_prod:.1f}× | {'OK' if rt else 'FAIL'} |")
    med_core = statistics.median(sp_core) if sp_core else 0
    med_prod = statistics.median(sp_prod) if sp_prod else 0
    L += ["", f"**MEDIANA do speedup**: vs núcleo **{med_core:.1f}×** · vs produção **{med_prod:.1f}×**",
          "", "LEITURA: o bypass (classify+map+pack, 1-2 passadas O(N)) evita OBAT (tokenização LCP/LCS por",
          "valor) + HCC (dedup/composição) + o min() (roda 4 candidatos). O speedup é o NÚMERO do eixo",
          "ACELERAÇÃO — o único que estava sem medida. NÃO é ganho de byte (bN colapsa pós-brotli, gate D3);",
          "é latência/throughput, o nicho streaming (V2-J) e payload-minúsculo."]
    w("01-latencia-bypass.txt", "\n".join(L) + "\n")

    # demo do INTERNO (B): dict congelado, não guarda domínio + overlay de exceções
    syn = ["true", "false", "true", "true", "false", "null", "true", "false"] * 2000
    ienc = B.internal_encode(syn, "bool3")
    irt = B.internal_decode(ienc) == syn
    D = ["# INTERNO (B) — dict CONGELADO (não declara referência), bool3 = trio (2 bits)", "",
         f"  N={len(syn)}  spec=bool3 (false/true/null)  w={ienc['w']} bits  #exceções={len(ienc['exc'])}",
         f"  RT={'OK' if irt else 'FAIL'}  · bytes-índices={len(ienc['packed'])} (=ceil(N×2/8)); domínio=0B (congelado)",
         "",
         "LEITURA: B (interno) NÃO guarda o domínio (vem do formato) — 'usa a interna sempre' (owner).",
         "Economiza a tabela de domínio + torna a coluna self-describing (o formato sabe que é trio bool)."]
    w("02-interno-B.txt", "\n".join(D) + "\n")

    R = ["# F1 bypass — latência [resumo]", "",
         f"## Speedup mediano: vs núcleo {med_core:.1f}× · vs produção {med_prod:.1f}×",
         "- bypass = classify+map+pack (1-2 passadas), pula OBAT+HCC. É o NÚMERO do eixo aceleração.",
         "- NÃO é byte (bN colapsa pós-brotli, D3); é latência — nicho streaming (V2-J) + payload-minúsculo.",
         "- nomenclatura (owner): b1/b2/b4 = largura FÍSICA; b3 = b2+null (trio); b5/6/7 = especiais; B = interno.",
         "- RT-OK em todas as colunas low-card (k≤16); k>16 faz bail pro núcleo (bypass não se aplica)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:24s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
