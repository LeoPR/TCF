"""TESTE EM MASSA da hierarquia com DADO REAL — shaper/FK montando o dataset (owner 2026-07-14).

Owner: "depois precisamos de um teste em massa disso, nem que o esquema hierárquico venha do
shaper montando pra gente nosso dataset de teste." O fuzz sintético (lab 2120) cobre a FORMA;
aqui é dado REAL em massa, aninhado pela FK do TPC-H (o shaper achata via join.py; isto é o
INVERSO — pega as tabelas normalizadas e ANINHA pela FK).

Cadeia real: customer (c_custkey) <- orders (o_custkey) <- lineitem (l_orderkey). 1:N em 2 níveis.
Classe coberta = all-string → str() em TODA folha ANTES (input == decode output, RT byte-exato).

Gate: decode(encode_hierarchical(docs)) == docs em massa · invariantes estruturais (nº de filhos
preservado) · byte-determinismo (encode 2×). NÃO toca src/tcf (usa a API pública read-only).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402

HUB = Path("Z:/tcf-data/interim/tpch-sf001.db")


def _rows(con, table, cols):
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(f"SELECT {','.join(cols)} FROM {table}")]


def _s(v):  # coerção all-string (classe coberta; tipos = camada ortogonal)
    return "" if v is None else str(v)


def load_nested(con):
    """customer -> [orders] -> [lineitem], aninhado pela FK. Todas as folhas string."""
    cust_cols = ["c_custkey", "c_name", "c_address", "c_phone", "c_mktsegment", "c_acctbal"]
    ord_cols = ["o_orderkey", "o_custkey", "o_orderstatus", "o_totalprice", "o_orderdate", "o_orderpriority"]
    li_cols = ["l_orderkey", "l_linenumber", "l_quantity", "l_extendedprice", "l_discount",
               "l_returnflag", "l_shipdate", "l_shipmode", "l_comment"]

    customers = _rows(con, "customer", cust_cols)
    orders = _rows(con, "orders", ord_cols)
    lineitems = _rows(con, "lineitem", li_cols)

    # index filhos por FK
    li_by_order: dict = {}
    for li in lineitems:
        li_by_order.setdefault(li["l_orderkey"], []).append(li)
    ord_by_cust: dict = {}
    for o in orders:
        ord_by_cust.setdefault(o["o_custkey"], []).append(o)

    docs = []
    for c in customers:
        c_orders = []
        for o in sorted(ord_by_cust.get(c["c_custkey"], []), key=lambda x: x["o_orderkey"]):
            items = sorted(li_by_order.get(o["o_orderkey"], []), key=lambda x: x["l_linenumber"])
            c_orders.append({
                "orderkey": _s(o["o_orderkey"]), "status": _s(o["o_orderstatus"]),
                "total": _s(o["o_totalprice"]), "data": _s(o["o_orderdate"]),
                "prioridade": _s(o["o_orderpriority"]),
                "itens": [{"linha": _s(li["l_linenumber"]), "qtd": _s(li["l_quantity"]),
                           "preco": _s(li["l_extendedprice"]), "desconto": _s(li["l_discount"]),
                           "flag": _s(li["l_returnflag"]), "envio": _s(li["l_shipdate"]),
                           "modo": _s(li["l_shipmode"]), "obs": _s(li["l_comment"])}
                          for li in items],
            })
        docs.append({
            "custkey": _s(c["c_custkey"]), "nome": _s(c["c_name"]),
            "endereco": _s(c["c_address"]), "fone": _s(c["c_phone"]),
            "segmento": _s(c["c_mktsegment"]), "saldo": _s(c["c_acctbal"]),
            "pedidos": c_orders,
        })
    return docs


def load_orders_lineitem(con):
    """orders -> [lineitem] (parent diferente, 1 nível). Segunda forma real."""
    ord_cols = ["o_orderkey", "o_orderstatus", "o_totalprice", "o_orderpriority"]
    li_cols = ["l_orderkey", "l_linenumber", "l_quantity", "l_returnflag", "l_shipmode"]
    orders = _rows(con, "orders", ord_cols)
    lineitems = _rows(con, "lineitem", li_cols)
    li_by_order: dict = {}
    for li in lineitems:
        li_by_order.setdefault(li["l_orderkey"], []).append(li)
    docs = []
    for o in orders:
        items = sorted(li_by_order.get(o["o_orderkey"], []), key=lambda x: x["l_linenumber"])
        docs.append({"orderkey": _s(o["o_orderkey"]), "status": _s(o["o_orderstatus"]),
                     "total": _s(o["o_totalprice"]), "prioridade": _s(o["o_orderpriority"]),
                     "itens": [{"linha": _s(li["l_linenumber"]), "qtd": _s(li["l_quantity"]),
                                "flag": _s(li["l_returnflag"]), "modo": _s(li["l_shipmode"])}
                               for li in items]})
    return docs


def gate(name, docs, out):
    """RT byte-exato + invariantes estruturais + byte-determinismo."""
    blob = encode_hierarchical(docs)
    blob2 = encode_hierarchical(docs)
    back = decode(blob)
    rt_ok = back == docs
    det_ok = blob == blob2
    # invariante estrutural: nº total de filhos preservado
    def count_leaves(d):
        n = 0
        for rec in d:
            for v in rec.values():
                if isinstance(v, list):
                    n += len(v)
                    n += sum(len(x.get("itens", [])) if isinstance(x, dict) else 0 for x in v)
        return n
    inv_ok = count_leaves(docs) == count_leaves(back)
    nbytes = len(blob.encode("utf-8"))
    n_leaf = count_leaves(docs)
    status = "OK" if (rt_ok and det_ok and inv_ok) else "FALHA"
    out.append(f"  [{status}] {name}: {len(docs)} docs · {n_leaf} filhos aninhados · "
               f"{nbytes} B · RT={rt_ok} determinismo={det_ok} invariante={inv_ok}")
    if not (rt_ok and det_ok and inv_ok):
        # localizar o 1º doc que difere
        for i, (a, b) in enumerate(zip(docs, back)):
            if a != b:
                out.append(f"      1º doc divergente: idx {i}")
                break
    return rt_ok and det_ok and inv_ok, blob


def main():
    if not HUB.exists():
        print(f"HUB ausente: {HUB} — pulando (requires_data)."); return
    con = sqlite3.connect(str(HUB))
    out = ["TESTE EM MASSA — hierarquia com DADO REAL (TPC-H sf001, aninhado pela FK)", ""]

    chain = load_nested(con)          # customer -> [orders] -> [lineitem]
    ol = load_orders_lineitem(con)    # orders -> [lineitem]

    out.append("Formas reais (aninhamento via FK; o shaper achata, aqui invertemos):")
    ok1, blob_chain = gate("customer>orders>lineitem (2 níveis)", chain, out)
    ok2, _ = gate("orders>lineitem (1 nível, outro pai)", ol, out)

    # amostra diffável (primeiros 3 customers) — extensões reais
    sample = chain[:3]
    (HERE / "intermediates" / "01-nested-sample.json").write_bytes(
        (json.dumps(sample, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    blob_sample = encode_hierarchical(sample)
    (HERE / "outputs" / "01-sample.tcf").write_bytes(blob_sample.encode("utf-8"))
    rt_sample = decode(blob_sample)
    (HERE / "outputs" / "02-roundtrip-sample.json").write_bytes(
        (json.dumps(rt_sample, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    assert rt_sample == sample, "RT da amostra diffável falhou"

    out += ["",
            f"amostra diffável: intermediates/01-nested-sample.json -> outputs/01-sample.tcf "
            f"-> outputs/02-roundtrip-sample.json (byte-idêntico ao intermediate: "
            f"{rt_sample == sample})",
            "",
            "VEREDITO: " + ("TODAS as formas reais fazem RT byte-exato em massa."
                            if (ok1 and ok2) else "HÁ FALHA — ver acima."),
            "Escopo: classe coberta (all-string via str(); tipos/null = camada ortogonal, pro fim).",
            "Zero mudança em src/tcf (API pública read-only)."]
    (HERE / "outputs" / "03-massa-result.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    if not (ok1 and ok2):
        sys.exit(1)


if __name__ == "__main__":
    main()
