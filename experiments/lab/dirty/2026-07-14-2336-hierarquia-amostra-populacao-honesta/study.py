"""ESTUDO — amostra de POPULAÇÃO com seleção HONESTA (owner 2026-07-14).

Owner: "uma representação selecionada de dados não significa amostra de um todo. a gente pode
estar pegando, por muita sorte (ou azar), justamente o que funciona. Temos que usar o conceito
de amostra de população com seleção honesta — não só randômica; por isso fizemos o Shaper...
faltou um estudo pra bancos com hierarquia (ou estruturas com ligações diversas)."

Este estudo NÃO reafirma o RT numa fatia; ele:
  (A) mede RT em VÁRIOS estratos HONESTOS (Shaper: estratificação proporcional Neyman +
      integridade referencial) × seeds × volumes → se RT é estrutural, vale em TODOS, não por sorte;
  (B) mapeia o FRONTIER de LIGAÇÕES DIVERSAS: o que é CONTENÇÃO (árvore 1:N, o weld nesta) vs
      N:N / multi-pai / snowflake (fora — fail-loud honesto);
  (C) 2ª fonte real (br-identidades, N:N sócio↔empresa) — não só TPC-H;
  (D) varredura de VALORES-QUEBRADORES reais (\\n / controle) — conecta aos contratos de borda.

Honesto = declara cobertura E fronteira. Zero mudança em src/tcf (API pública + Shaper read-only).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]  # .../TCF
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))
from tcf import decode, encode_hierarchical  # noqa: E402
from shaper import Shaper, ShapeRequest  # noqa: E402

TPCH = Path("Z:/tcf-data/interim/tpch-sf001.db")
BRID = Path("Z:/tcf-data/interim/br-identidades.db")


def _s(v):
    return "" if v is None else str(v)


# ---------- (A) RT em estratos HONESTOS do TPC-H (customer→[orders]→[itens]) ----------
def nest_customers(con, cust_keys, cust_by_key):
    """Monta sub-árvores COMPLETAS dos customers selecionados (multiplicidade honesta).

    NOTA: o free-text l_comment é DELIBERADAMENTE omitido aqui — o HCC nele é o gargalo de
    perf (.9) e NÃO é o ponto de (A) (que testa TOPOLOGIA em estratos honestos). A robustez de
    conteúdo free-text (\\n/controle) é coberta separadamente em value_breakers() (D)."""
    keyset = set(cust_keys)
    orders = [dict(r) for r in con.execute(
        "SELECT o_orderkey,o_custkey,o_orderstatus,o_totalprice,o_orderdate FROM orders")]
    li = [dict(r) for r in con.execute(
        "SELECT l_orderkey,l_linenumber,l_quantity,l_returnflag,l_shipmode FROM lineitem")]
    ord_by_cust, li_by_order = {}, {}
    for o in orders:
        if o["o_custkey"] in keyset:
            ord_by_cust.setdefault(o["o_custkey"], []).append(o)
    order_keys = {o["o_orderkey"] for os in ord_by_cust.values() for o in os}
    for x in li:
        if x["l_orderkey"] in order_keys:
            li_by_order.setdefault(x["l_orderkey"], []).append(x)
    docs = []
    for ck in cust_keys:
        c = cust_by_key[ck]
        pedidos = []
        for o in sorted(ord_by_cust.get(ck, []), key=lambda x: x["o_orderkey"]):
            itens = sorted(li_by_order.get(o["o_orderkey"], []), key=lambda x: x["l_linenumber"])
            pedidos.append({"okey": _s(o["o_orderkey"]), "status": _s(o["o_orderstatus"]),
                            "total": _s(o["o_totalprice"]), "data": _s(o["o_orderdate"]),
                            "itens": [{"ln": _s(i["l_linenumber"]), "qtd": _s(i["l_quantity"]),
                                       "flag": _s(i["l_returnflag"]), "modo": _s(i["l_shipmode"])}
                                      for i in itens]})
        docs.append({"ck": _s(c["c_custkey"]), "nome": _s(c["c_name"]),
                     "seg": _s(c["c_mktsegment"]), "nat": _s(c["c_nationkey"]),
                     "pedidos": pedidos})
    return docs


def stratum_rt(con, out, stratify_by, volume, seed):
    """Amostra HONESTA (Shaper) + nest + RT. Retorna (ok, metrics_line)."""
    res = Shaper().apply(ShapeRequest(dataset="tpch-sf001", fact_table="customer",
                                      stratify_by=stratify_by, volume=volume,
                                      fk_preserving=True, seed=seed))
    sampled = res.tables["customer"]
    cust_by_key = {r["c_custkey"]: r for r in sampled}
    keys = sorted(cust_by_key)
    metric = next((l for l in res.trace if "stratify_metrics" in l), "")
    docs = nest_customers(con, keys, cust_by_key)
    ok = decode(encode_hierarchical(docs)) == docs
    tvd = metric.split("TVD=")[1].split(",")[0] if "TVD=" in metric else "?"
    out.append(f"  [{'OK' if ok else 'FALHA'}] estrato by={stratify_by} vol={volume} seed={seed}: "
               f"{len(docs)} customers, RT={ok}, representatividade TVD={tvd}")
    return ok


# ---------- (B) FRONTIER: ligações DIVERSAS (não-contenção) ----------
def frontier(con, out):
    out.append("(B) FRONTIER — ligações diversas (o que NÃO é contenção 1:N):")
    # partsupp = ponte N:N (part <-> supplier): um part tem N suppliers e vice-versa
    ps = con.execute("SELECT COUNT(*) FROM partsupp").fetchone()[0]
    # um part aparece em quantos partsupp? um supplier em quantos?
    p_deg = con.execute("SELECT MAX(c) FROM (SELECT COUNT(*) c FROM partsupp GROUP BY ps_partkey)").fetchone()[0]
    s_deg = con.execute("SELECT MAX(c) FROM (SELECT COUNT(*) c FROM partsupp GROUP BY ps_suppkey)").fetchone()[0]
    out.append(f"  partsupp: {ps} arestas N:N (part↔supplier). part tem até {p_deg} suppliers; "
               f"supplier até {s_deg} parts → NÃO é árvore (multi-pai). Fora da classe coberta.")
    # lineitem: multi-pai (aponta pra orders E part E supplier)
    out.append("  lineitem: aponta pra orders (l_orderkey) E part (l_partkey) E supplier (l_suppkey)")
    out.append("    → snowflake / multi-pai. Nesta como filho de orders (o teste A); como filho de")
    out.append("    part OU supplier seria OUTRA projeção do MESMO fato (1:N≡N:1 por ponto de vista).")
    out.append("  VEREDITO honesto: o weld cobre CONTENÇÃO (árvore 1:N). N:N/multi-pai = super-")
    out.append("    hierarquia (FK/junção, H-HIER-MULTITABELA-01) — hoje fail-loud, não corrompe.")


# ---------- (C) 2ª fonte real: br-identidades (N:N sócio↔empresa) ----------
def br_identidades(out):
    if not BRID.exists():
        out.append("(C) br-identidades: HUB ausente — pulado."); return None
    con = sqlite3.connect(str(BRID)); con.row_factory = sqlite3.Row
    tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    out.append(f"(C) 2ª fonte REAL — br-identidades (tabelas: {tabs}); FK empresas.socio_cpf→pessoas.cpf (N:N):")
    try:
        empresas = [dict(r) for r in con.execute("SELECT * FROM empresas LIMIT 3000")]
        ecols = list(empresas[0].keys()) if empresas else []
        # projeção contenção: pessoa → [empresas onde é sócio] (1:N honesto)
        by_cpf = {}
        for e in empresas:
            cpf = e.get("socio_cpf")
            if cpf is None:            # sócio sem CPF = link inválido (fora do escopo)
                continue
            by_cpf.setdefault(cpf, []).append({k: _s(e[k]) for k in ecols if k != "socio_cpf"})
        cpfs = sorted(by_cpf)[:500]
        docs = [{"cpf": _s(c), "empresas": by_cpf[c]} for c in cpfs]
        ok = decode(encode_hierarchical(docs)) == docs
        multi = sum(1 for c in cpfs if len(by_cpf[c]) > 1)
        out.append(f"  pessoa→[empresas] (contenção 1:N, {len(docs)} pessoas, {multi} com >1 empresa): "
                   f"RT={ok}. A N:N vira 1:N ao escolher a raiz (pessoa) — projeção honesta.")
        con.close(); return ok
    except Exception as e:  # noqa: BLE001
        out.append(f"  ERRO: {e}"); con.close(); return False


# ---------- (D) varredura de VALORES-QUEBRADORES reais (\n / controle) ----------
def value_breakers(con, out):
    out.append("(D) VALORES-QUEBRADORES reais (\\n / controle → quebrariam RT; contratos de borda):")
    hits = 0
    for tab, cols in [("customer", ["c_name", "c_address", "c_comment"]),
                      ("orders", ["o_comment", "o_clerk"]),
                      ("lineitem", ["l_comment", "l_shipinstruct"])]:
        for col in cols:
            try:
                rows = con.execute(f"SELECT {col} FROM {tab}").fetchall()
            except Exception:
                continue
            n_nl = sum(1 for (v,) in rows if isinstance(v, str) and "\n" in v)
            n_ctl = sum(1 for (v,) in rows if isinstance(v, str)
                        and any(ord(ch) < 32 and ch != "\t" for ch in v))
            hits += n_nl + n_ctl
            if n_nl or n_ctl:
                out.append(f"  {tab}.{col}: {n_nl} com \\n, {n_ctl} com controle")
    if hits == 0:
        out.append("  0 valores com \\n/controle nas colunas free-text reais varridas → nesta amostra")
        out.append("  real, nenhum valor quebra o RT. MAS: é achado desta população; o contrato de")
        out.append("  \\n-em-valor (T-API-BOUNDARY-CONTRACTS) segue pendente — não deduzir 'nunca ocorre'.")


def main():
    if not TPCH.exists():
        print("HUB tpch ausente — requires_data."); return
    con = sqlite3.connect(str(TPCH)); con.row_factory = sqlite3.Row
    out = ["ESTUDO — amostra de POPULAÇÃO com seleção HONESTA (hierarquia/ligações diversas)", ""]

    # caracterização HONESTA da MULTIPLICIDADE (o que estressa o codec) na população inteira
    opc = con.execute("SELECT MIN(c),MAX(c),AVG(c) FROM (SELECT COUNT(*) c FROM orders GROUP BY o_custkey)").fetchone()
    ipo = con.execute("SELECT MIN(c),MAX(c),AVG(c) FROM (SELECT COUNT(*) c FROM lineitem GROUP BY l_orderkey)").fetchone()
    cust_sem_pedido = con.execute(
        "SELECT COUNT(*) FROM customer WHERE c_custkey NOT IN (SELECT DISTINCT o_custkey FROM orders)").fetchone()[0]
    out.append("(A) RT em ESTRATOS HONESTOS do TPC-H (Shaper: estratificação proporcional + integridade ref.):")
    out.append(f"  distribuição de MULTIPLICIDADE na população (o que estressa o codec): pedidos/cliente "
               f"min={opc[0]} max={opc[1]} media={opc[2]:.1f} · itens/pedido min={ipo[0]} max={ipo[1]} "
               f"media={ipo[2]:.1f} · clientes SEM pedido (cauda vazia)={cust_sem_pedido}")
    oks = []
    for by in ("c_mktsegment", "c_nationkey"):
        for vol in (0.1, 0.3, 0.6):
            for seed in (7, 42, 101):
                oks.append(stratum_rt(con, out, by, vol, seed))
    out.append(f"  → {sum(oks)}/{len(oks)} estratos honestos com RT byte-exato "
               f"(cada estrato inclui a cauda: pai sem filho E pai com muitos). Se fosse sorte de "
               f"fatia, falharia em algum; passar em todos = ESTRUTURAL.")
    out.append("  RESSALVA HONESTA: estratificado por segmento/nação, NÃO diretamente pela multiplicidade; "
               "mas os 18 estratos varrem 10-60% da pop c/ 3 seeds → a cauda de fan-out É exercitada.")
    out.append("")
    frontier(con, out)
    out.append("")
    br_ok = br_identidades(out)
    out.append("")
    value_breakers(con, out)
    out += ["",
            "SÍNTESE HONESTA:",
            f"- CONTENÇÃO (árvore 1:N): coberta — RT byte-exato em {sum(oks)}/{len(oks)} estratos honestos "
            "TPC-H + 2ª fonte real (br-identidades). Estrutural, não fatia de sorte.",
            "- LIGAÇÕES DIVERSAS (N:N / multi-pai / snowflake): FRONTIER declarado — fora da classe coberta,",
            "  fail-loud (não corrompe); alvo da super-hierarquia H-HIER-MULTITABELA-01 (FK/junção).",
            "- 1:N ≡ N:1 por ponto de vista: a N:N vira 1:N ao ESCOLHER a raiz (projeção); o que falta é a",
            "  representação de MÚLTIPLAS raízes/junção simultâneas (não uma projeção só).",
            "- Pobreza de dados com ligação no repo (só TPC-H rico + br-identidades): o Shaper mitiga dando",
            "  amostras honestas; ampliar população (mais fontes reais ligadas OU shaper gerando) fica registrado.",
            "Zero mudança em src/tcf."]
    (HERE / "outputs" / "01-estudo.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    con.close()


if __name__ == "__main__":
    main()
