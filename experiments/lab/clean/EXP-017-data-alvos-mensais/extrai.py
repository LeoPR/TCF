"""Extrai o corpus REAL de colunas de data dos hubs em Z:. `python extrai.py`

Roda UMA vez (ou quando quiser reamostrar). Grava fatias congeladas em `inputs/`, para
que `run.py` seja reproduzível **sem Z:** — mesma política dos fixtures de
`datasets/samples/`.

Regra do projeto: dados grandes vivem em `Z:/tcf-data/`, NUNCA se baixa nada quando o hub
já tem. Aqui só se lê.

Cada coluna é extraída em DUAS formas, porque a ordem é a maior alavanca conhecida do
projeto (lab 2026-07-23-1832: ordenar levou uma coluna de 6668 -> 102 B):

    <nome>.natural.json   a ordem em que o dado está armazenado
    <nome>.ordenado.json  a mesma multiset, ordenada

`N_MAX` fatia para manter o lab leve e commitável.
"""
from __future__ import annotations

import csv
import itertools
import json
import pathlib
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
INPUTS = RAIZ / "inputs"
INPUTS.mkdir(exist_ok=True)
HUB = pathlib.Path("Z:/tcf-data")
N_MAX = 3000

# (rotulo, fonte, seletor) — fonte 'db' usa SQLite; 'csv' usa arquivo em external/
FONTES = [
    # TPC-H: o clássico de data em regime comercial (datas de pedido/embarque)
    ("tpch-orderdate", "db", ("tpch-sf001.db", "orders", "o_orderdate")),
    ("tpch-shipdate", "db", ("tpch-sf001.db", "lineitem", "l_shipdate")),
    ("tpch-commitdate", "db", ("tpch-sf001.db", "lineitem", "l_commitdate")),
    ("tpch-receiptdate", "db", ("tpch-sf001.db", "lineitem", "l_receiptdate")),
    # sf01 com OFFSET: a cacada adversarial pegou que LIMIT 3000 puro devolve as MESMAS
    # linhas do sf001 (dbgen deterministico) — md5 identico, "escala" que nao escalava.
    ("tpch-sf01-orderdate", "db", ("tpch-sf01.db", "orders", "o_orderdate", 90000)),
    # BR: cadastro de pessoas/empresas (ISO, volume alto)
    ("br-data-cadastro", "db", ("br-identidades.db", "pessoas", "data_cadastro")),
    ("br-data-abertura", "db", ("br-identidades.db", "empresas", "data_abertura")),
    # Receita: YYYYMMDD COMPACTO — a grafia que o spec ISO recusa
    ("receita-data-inicio", "db", ("receita-cnpj.db", "estabelecimentos", "data_inicio")),
    # Retail: DATETIME (não é date puro) — a válvula tem de segurar
    ("retail-invoicedate", "db", ("online-retail.db", "online_retail", "InvoiceDate")),
    # Football: 1872..hoje — span gigante, densidade irregular
    ("football-date", "csv", ("football-results/results.csv", "date")),
]


def _de_db(arq: str, tabela: str, coluna: str, offset: int = 0) -> list[str]:
    p = HUB / "interim" / arq
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.text_factory = str
    try:
        cur = con.execute(
            f'SELECT "{coluna}" FROM "{tabela}" LIMIT {N_MAX} OFFSET {offset}')
        return [str(r[0]) for r in cur if r[0] is not None]
    finally:
        con.close()


def _de_csv(rel: str, coluna: str) -> list[str]:
    p = HUB / "external" / rel
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        i = hdr.index(coluna)
        return [row[i] for row in itertools.islice(r, N_MAX) if i < len(row) and row[i]]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not HUB.exists():
        print(f"Z: não montado ({HUB}) — inputs/ existentes ficam como estão.")
        return 1
    manifesto = []
    for rotulo, tipo, args in FONTES:
        try:
            vals = _de_db(*args) if tipo == "db" else _de_csv(*args)
        except Exception as e:
            print(f"  {rotulo:<22} FALHOU: {type(e).__name__}: {str(e)[:60]}")
            continue
        if len(vals) < 100:
            print(f"  {rotulo:<22} poucos valores ({len(vals)}), pulando")
            continue
        ordenado = sorted(vals)
        for suf, dados in (("natural", vals), ("ordenado", ordenado)):
            (INPUTS / f"{rotulo}.{suf}.json").write_text(
                json.dumps(dados, ensure_ascii=False), encoding="utf-8", newline="")
        k = len(set(vals))
        manifesto.append({"rotulo": rotulo, "n": len(vals), "k": k,
                          "exemplo": vals[0], "fonte": f"{tipo}:{args[0]}",
                          "ja_ordenado_na_origem": vals == ordenado})
        print(f"  {rotulo:<22} n={len(vals):<5} k={k:<5} ex={vals[0][:19]:<19} "
              f"{'(já ordenado na origem)' if vals == ordenado else ''}")
    (INPUTS / "_manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"\n{len(manifesto)} colunas × 2 ordens = {len(manifesto) * 2} inputs congelados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
