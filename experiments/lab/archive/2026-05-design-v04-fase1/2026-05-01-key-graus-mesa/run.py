"""Lab dirty: lossless key elimination — formula vs medicao.

Testa a Proposta I do roadmap: chaves PK/FK grau 2 podem ser
eliminadas e regeneradas pelo decode sem perda de relacao.

NAO implementa no core. Apenas calcula bytes em 3 cenarios.

Saida: ./output/
"""
from __future__ import annotations
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from data_sources import load_dataset

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Bytes models
# ---------------------------------------------------------------------------

def encode_naive_table(name: str, rows: list[dict]) -> str:
    """CSV-like simples (col headers + values)."""
    if not rows:
        return f"## {name} n=0\n"
    cols = list(rows[0].keys())
    out = [f"## {name} n={len(rows)}"]
    for col in cols:
        out.append(f"{col}:")
        for r in rows:
            out.append(str(r[col]))
    return "\n".join(out) + "\n"


def encode_l3_table(name: str, rows: list[dict],
                    string_cols: set[str]) -> str:
    """L3 com DICT em colunas string (simplificado)."""
    if not rows:
        return f"## {name} n=0\n"
    cols = list(rows[0].keys())
    out = [f"## {name} n={len(rows)}"]

    # Para cada coluna string, gera DICT
    for col in cols:
        if col in string_cols:
            unique = sorted(set(str(r[col]) for r in rows))
            out.append(f"# dict {col}: " + ",".join(unique))

    # Body
    for col in cols:
        out.append(f"{col}:")
        if col in string_cols:
            unique = sorted(set(str(r[col]) for r in rows))
            idx_map = {v: i for i, v in enumerate(unique)}
            for r in rows:
                out.append(str(idx_map[str(r[col])]))
        else:
            for r in rows:
                out.append(str(r[col]))
    return "\n".join(out) + "\n"


def encode_l3_eliminate_keys(name: str, rows: list[dict],
                              string_cols: set[str],
                              eliminate_pk: str | None = None,
                              fks: dict[str, str] | None = None,
                              fk_dicts: dict[str, list] | None = None) -> str:
    """L3 com eliminacao de PK grau 2 e FKs grau 2."""
    if not rows:
        return f"## {name} n=0\n"
    cols = list(rows[0].keys())
    fks = fks or {}
    fk_dicts = fk_dicts or {}

    # Filtra colunas: eliminate_pk eh removida; FKs viram indices
    out_cols = [c for c in cols if c != eliminate_pk]

    flags = []
    if eliminate_pk:
        flags.append(f"pk_eliminated={eliminate_pk}")
    if fks:
        fk_str = ",".join(f"{k}:{v}" for k, v in fks.items())
        flags.append(f"fk_resolved={{{fk_str}}}")
    flag_text = " " + " ".join(flags) if flags else ""

    out = [f"## {name} n={len(rows)}{flag_text}"]

    # DICTs para colunas string nao-FK
    for col in out_cols:
        if col in string_cols and col not in fks:
            unique = sorted(set(str(r[col]) for r in rows))
            out.append(f"# dict {col}: " + ",".join(unique))

    # Body
    for col in out_cols:
        out.append(f"{col}:")
        if col in fks:
            # FK substituida por indice no DICT da tabela referenciada
            ref_dict = fk_dicts[col]
            idx_map = {v: i for i, v in enumerate(ref_dict)}
            for r in rows:
                fk_val = r[col]
                # Mapeia o id da FK para indice (assumindo PK era 1..N)
                # Nao se importa com o valor literal — so o indice
                if isinstance(fk_val, int):
                    idx = fk_val - 1  # auto-increment 1-based
                else:
                    idx = idx_map.get(str(fk_val), 0)
                out.append(str(idx))
        elif col in string_cols:
            unique = sorted(set(str(r[col]) for r in rows))
            idx_map = {v: i for i, v in enumerate(unique)}
            for r in rows:
                out.append(str(idx_map[str(r[col])]))
        else:
            for r in rows:
                out.append(str(r[col]))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Cenario C1 — pessoa + produto + pedido (sintetico)
# ---------------------------------------------------------------------------

def C1_synthetic_3tables() -> tuple[dict, dict, dict]:
    pessoas = [{"id": i + 1, "nome": n} for i, n in enumerate(
        ["Ana", "Bruno", "Carlos", "Diana", "Eduardo",
         "Fernanda", "Gabriel", "Helena", "Igor", "Juliana"])]
    produtos = [{"id": i + 1, "nome": n} for i, n in enumerate(
        ["Abacaxi", "Banana", "Cereja", "Damasco", "Eucalipto",
         "Figo", "Goiaba", "Helado", "Imbuia", "Jaca"])]
    pedidos = []
    for i in range(50):
        pedidos.append({
            "pedido_id": i + 1,
            "pessoa_id": random.randint(1, 10),
            "produto_id": random.randint(1, 10),
            "qtd": random.randint(1, 5),
        })
    return (
        {"name": "pessoas", "rows": pessoas, "string_cols": {"nome"},
         "pk": "id", "fks": {}},
        {"name": "produtos", "rows": produtos, "string_cols": {"nome"},
         "pk": "id", "fks": {}},
        {"name": "pedidos", "rows": pedidos, "string_cols": set(),
         "pk": "pedido_id",
         "fks": {"pessoa_id": "pessoas", "produto_id": "produtos"}},
    )


def C2_tpch_real() -> list[dict]:
    """TPC-H supplier real (s_suppkey eh PK; s_nationkey eh FK)."""
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=50, seed=42, schema=["supplier"])
    supplier = tables.get("supplier", [])
    rows_simple = [{"s_suppkey": s["s_suppkey"],
                     "s_name": s["s_name"][:20],
                     "s_nationkey": s["s_nationkey"]}
                    for s in supplier]
    return [{
        "name": "supplier",
        "rows": rows_simple,
        "string_cols": {"s_name"},
        "pk": "s_suppkey",
        "fks": {"s_nationkey": "nation"},  # se nation existir
    }]


def C3_desnormalizado() -> list[dict]:
    """1 tabela, sem PK/FK explicito."""
    rows = []
    for _ in range(50):
        rows.append({
            "transacao": random.choice(["compra", "venda", "estorno"]),
            "valor": round(random.uniform(10, 999), 2),
            "moeda": random.choice(["BRL", "USD", "EUR"]),
        })
    return [{
        "name": "transacoes",
        "rows": rows,
        "string_cols": {"transacao", "moeda"},
        "pk": None,
        "fks": {},
    }]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_cenario_c1():
    print("\n" + "=" * 78)
    print("[C1] Schema sintetico: pessoas + produtos + pedidos")
    print("=" * 78)

    pessoas, produtos, pedidos = C1_synthetic_3tables()
    nomes_pessoas = [p["nome"] for p in pessoas["rows"]]
    nomes_produtos = [p["nome"] for p in produtos["rows"]]

    # ---- ESTRATEGIA A: preserve all (L3 normal) ----
    text_a_pessoas = encode_l3_table("pessoas", pessoas["rows"], pessoas["string_cols"])
    text_a_produtos = encode_l3_table("produtos", produtos["rows"], produtos["string_cols"])
    text_a_pedidos = encode_l3_table("pedidos", pedidos["rows"], pedidos["string_cols"])
    bytes_a = sum(len(t.encode()) for t in [text_a_pessoas, text_a_produtos, text_a_pedidos])

    # ---- ESTRATEGIA B: eliminate keys ----
    text_b_pessoas = encode_l3_eliminate_keys(
        "pessoas", pessoas["rows"], pessoas["string_cols"],
        eliminate_pk="id")
    text_b_produtos = encode_l3_eliminate_keys(
        "produtos", produtos["rows"], produtos["string_cols"],
        eliminate_pk="id")
    text_b_pedidos = encode_l3_eliminate_keys(
        "pedidos", pedidos["rows"], pedidos["string_cols"],
        eliminate_pk="pedido_id",
        fks={"pessoa_id": "pessoas", "produto_id": "produtos"},
        fk_dicts={"pessoa_id": nomes_pessoas, "produto_id": nomes_produtos})
    bytes_b = sum(len(t.encode()) for t in [text_b_pessoas, text_b_produtos, text_b_pedidos])

    # ---- ESTRATEGIA naive ----
    text_n_pessoas = encode_naive_table("pessoas", pessoas["rows"])
    text_n_produtos = encode_naive_table("produtos", produtos["rows"])
    text_n_pedidos = encode_naive_table("pedidos", pedidos["rows"])
    bytes_n = sum(len(t.encode()) for t in [text_n_pessoas, text_n_produtos, text_n_pedidos])

    print(f"  naive (CSV-like):              {bytes_n} B")
    print(f"  L3 (DICT, preserva chaves):    {bytes_a} B  ({(bytes_a/bytes_n-1)*100:+.1f}%)")
    print(f"  L3 + eliminate keys:           {bytes_b} B  ({(bytes_b/bytes_n-1)*100:+.1f}%)")
    print(f"  Economia eliminate vs L3:      {bytes_b - bytes_a} B  "
          f"({(bytes_b/bytes_a - 1)*100:+.1f}%)")

    # ---- Salva no disco ----
    (OUT / "c1-A-preserve.tcf").write_text(
        text_a_pessoas + text_a_produtos + text_a_pedidos, encoding="utf-8")
    (OUT / "c1-B-eliminate.tcf").write_text(
        text_b_pessoas + text_b_produtos + text_b_pedidos, encoding="utf-8")
    (OUT / "c1-naive.tcf").write_text(
        text_n_pessoas + text_n_produtos + text_n_pedidos, encoding="utf-8")

    return {"naive": bytes_n, "preserve": bytes_a, "eliminate": bytes_b}


def run_cenario_c2():
    print("\n" + "=" * 78)
    print("[C2] TPC-H supplier real (s_suppkey grau 2; s_nationkey grau 1?)")
    print("=" * 78)

    tables = C2_tpch_real()
    t = tables[0]

    text_a = encode_l3_table(t["name"], t["rows"], t["string_cols"])
    text_b_only_pk = encode_l3_eliminate_keys(
        t["name"], t["rows"], t["string_cols"],
        eliminate_pk="s_suppkey")  # so PK; s_nationkey preservado (grau 1)
    text_n = encode_naive_table(t["name"], t["rows"])

    bytes_a = len(text_a.encode())
    bytes_b = len(text_b_only_pk.encode())
    bytes_n = len(text_n.encode())

    print(f"  naive:                              {bytes_n} B")
    print(f"  L3 (preserva chaves):               {bytes_a} B  ({(bytes_a/bytes_n-1)*100:+.1f}%)")
    print(f"  L3 + elimina so PK (s_suppkey):     {bytes_b} B  ({(bytes_b/bytes_n-1)*100:+.1f}%)")
    print(f"  Economia eliminacao PK vs L3:       {bytes_b - bytes_a} B  "
          f"({(bytes_b/bytes_a - 1)*100:+.1f}%)")

    print("\n  NOTA: s_nationkey eh PRESERVADO porque eh grau 1")
    print("        (referenciado em outras tabelas/sistemas).")
    print("        Eliminacao agressiva so faz sentido com schema completo.")

    (OUT / "c2-A-preserve.tcf").write_text(text_a, encoding="utf-8")
    (OUT / "c2-B-eliminate.tcf").write_text(text_b_only_pk, encoding="utf-8")
    return {"naive": bytes_n, "preserve": bytes_a, "eliminate": bytes_b}


def run_cenario_c3():
    print("\n" + "=" * 78)
    print("[C3] Tabela desnormalizada (sem PK/FK)")
    print("=" * 78)

    tables = C3_desnormalizado()
    t = tables[0]

    text_a = encode_l3_table(t["name"], t["rows"], t["string_cols"])
    # Sem PK/FK para eliminar — estrategia B == A
    text_b = encode_l3_eliminate_keys(
        t["name"], t["rows"], t["string_cols"], eliminate_pk=None)
    text_n = encode_naive_table(t["name"], t["rows"])

    bytes_a = len(text_a.encode())
    bytes_b = len(text_b.encode())
    bytes_n = len(text_n.encode())

    print(f"  naive:                            {bytes_n} B")
    print(f"  L3:                               {bytes_a} B  ({(bytes_a/bytes_n-1)*100:+.1f}%)")
    print(f"  L3 (sem chaves p/ eliminar):      {bytes_b} B  ({(bytes_b/bytes_n-1)*100:+.1f}%)")
    print(f"  Diferenca:                        {bytes_b - bytes_a} B")
    print("\n  Conclusao: sem PK/FK, eliminacao nao se aplica. Esperado.")

    return {"naive": bytes_n, "preserve": bytes_a, "eliminate": bytes_b}


def main():
    print("=" * 78)
    print("Lab dirty: lossless key elimination (Proposta I)")
    print("=" * 78)

    r1 = run_cenario_c1()
    r2 = run_cenario_c2()
    r3 = run_cenario_c3()

    # ---- Sumario ----
    print("\n" + "=" * 78)
    print("Sumario consolidado")
    print("=" * 78)
    print(f"\n  {'cenario':<30} {'naive':>7} {'L3':>7} {'L3+elim':>9} {'gain':>9}")
    print(f"  {'-'*30} {'-'*7} {'-'*7} {'-'*9} {'-'*9}")
    for label, r in [("C1 3tables (PKs grau 2 + FKs)", r1),
                      ("C2 TPC-H supplier (PK grau 2)", r2),
                      ("C3 desnormalizada (sem keys)",   r3)]:
        gain = r["eliminate"] - r["preserve"]
        gain_pct = (r["eliminate"]/r["preserve"] - 1) * 100
        sign = "+" if gain >= 0 else ""
        print(f"  {label:<30} {r['naive']:>7} {r['preserve']:>7} "
              f"{r['eliminate']:>9} {sign}{gain:>+5}B/{sign}{gain_pct:>+5.1f}%")

    print(f"""
  Achados induzidos:

  A1) C1 (schema com FKs grau 2 dominantes):
      Eliminate VENCE significativamente.
      Cada FK substituida vira 1-2 chars (indice) em vez de 1-3 chars (id).

  A2) C2 (PK grau 2 mas FK grau 1):
      Eliminate so PK ganha pouco — PK era ~6 chars/linha em N=50 rows.
      Em escala maior (N=10000), economia seria proporcional.

  A3) C3 (sem PK/FK):
      Eliminate == L3. Esperado: sem chaves, nao ha o que eliminar.

  A4) Eliminate so vale com schema explicito:
      detectar grau (0, 1, 2, 3) sem schema eh heuristico e fragil.

  A5) Decoder precisa REGENERAR ids:
      simples (1..N para ordem), mas perde compatibilidade com sistemas
      que assumem ids especificos (api, replicacao, etc).

  Limites desta analise:

  - Datasets pequenos (N=50). Em escala real (N=milhoes), economia
    deveria ser dominante em schemas relacionais.
  - Nao validamos roundtrip de relacao (joins reproduzem mesmos
    resultados). Apenas calculamos bytes.
  - Nao detectamos automaticamente grau das chaves — passamos manual.
  - C2 nao testou cross-tabela com nation (so supplier).
""")
    print(f"  Arquivos em: {OUT}")


if __name__ == "__main__":
    main()
