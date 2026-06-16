"""Lazy-view — passo L2: QUANTIFICAR a venda ("descomprimir so' o suficiente").

Mede, num dataset real (online-retail, tem CustomerID + Quantity), quanto do blob
cada query precisa MATERIALIZAR (descomprimir) pra responder — a dimensao
memoria/latencia. Inclui o exemplo do owner: "quantidade comprada por um usuario".

FORK (nao toca src/tcf). Reusa LazyTCF do PoC.
"""
from __future__ import annotations
import csv, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))   # importar o PoC vizinho
from tcf import encode                                       # noqa: E402
from lazy_query_poc import LazyTCF                           # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 5000


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f); header = next(r)
                cols = {h: [] for h in header}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    return {}


def materialized(v):
    """Bytes do blob que a query precisou descomprimir (soma dos corpos tocados)."""
    return sum(v.column_bytes(n) for n in v.touched)


def main():
    table = load(EXT / "online-retail" / "online_retail.csv", ROWS)
    if not table:
        print("SKIP: dataset indisponivel"); return
    blob = encode(table)
    total = len(blob.encode("utf-8"))
    ncols = len(table); nrows = len(next(iter(table.values())))
    top_user = Counter(c for c in table["CustomerID"] if c).most_common(1)[0][0]

    print(f"blob = {total} B  ({ncols} colunas x {nrows} linhas)")
    print(f"{'query':56s} {'resp':>10s} {'materializou':>22s}  colunas")
    print("-" * 110)

    def run(label, fn):
        v = LazyTCF(blob)
        res = fn(v)
        mat = materialized(v)
        print(f"{label:56s} {str(res):>10s} {f'{mat}B de {total}B ({100*mat/total:4.1f}%)':>22s}  {v.touched}")

    run("count()", lambda v: v.count())
    run("sum('Quantity')  [total de itens]", lambda v: v.sum("Quantity"))
    run(f"where(CustomerID={top_user}).sum('Quantity')  [qtd do usuario]",
        lambda v: v.where("CustomerID", top_user).sum("Quantity"))
    run(f"where(CustomerID={top_user}).count()  [pedidos do usuario]",
        lambda v: v.where("CustomerID", top_user).count())
    run("where(Country='France').sum('Quantity')",
        lambda v: v.where("Country", "France").sum("Quantity"))

    print("-" * 110)
    print(f"Controle: decode() completo materializa 100% ({total}B), todas as {ncols} colunas.")
    print("A 'venda': responder tocando 2 de", ncols, "colunas = fracao pequena do blob,")
    print("sem alocar memoria pra descomprimir o resto (latencia + memoria baixas).")


if __name__ == "__main__":
    main()
