"""Lab: caminho feliz — banco sintetico didatico com auto-tudo.

Banco minusculo (didatico, ampliado): pessoas, produtos, categorias,
pedidos. Aplica TODAS as compactacoes automaticamente quando possivel.

Compara:
  1. naive (CSV-like)
  2. L3 atual (DICT por coluna)
  3. L3 + auto-tudo (Propostas E + H + I + auto-bypass agressivo)

Mostra o output final lado a lado para inspecao didatica.

NAO modifica core TCF. Demonstrativo apenas.

Saida: ./output/
"""
from __future__ import annotations
import random
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Banco sintetico didatico
# ---------------------------------------------------------------------------

CATEGORIAS = ["frutas", "doces", "bebidas", "limpeza"]
STATUS_PED = ["pago", "pendente", "cancelado"]


def build_synthetic_db():
    """4 tabelas: pessoas, produtos, categorias, pedidos."""

    pessoas = [
        {"id": i + 1,
         "nome": n,
         "categoria_preferida": random.choice(CATEGORIAS)}
        for i, n in enumerate(["Ana", "Bruno", "Carlos", "Diana", "Eduardo",
                                "Fernanda", "Gabriel", "Helena"])
    ]

    produtos = [
        {"id": i + 1,
         "nome": f"Produto-{i+1:03d}",
         "categoria": random.choice(CATEGORIAS),
         "preco": round(random.uniform(5, 100), 2)}
        for i in range(15)
    ]

    pedidos = []
    for i in range(40):
        pedidos.append({
            "pedido_id": i + 1,
            "pessoa_id": random.randint(1, 8),
            "produto_id": random.randint(1, 15),
            "qtd": random.randint(1, 5),
            "status": random.choice(STATUS_PED),
        })

    return {
        "pessoas": pessoas,
        "produtos": produtos,
        "pedidos": pedidos,
    }


# ---------------------------------------------------------------------------
# Encoder naive (CSV-like)
# ---------------------------------------------------------------------------

def encode_table_naive(name: str, rows: list[dict]) -> str:
    if not rows:
        return f"## {name} n=0\n"
    cols = list(rows[0].keys())
    out = [f"## {name} n={len(rows)}"]
    for col in cols:
        out.append(f"{col}:")
        for r in rows:
            out.append(str(r[col]))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Encoder L3 (atual: DICT por coluna string)
# ---------------------------------------------------------------------------

def detect_string_cols(rows: list[dict]) -> set[str]:
    """Heuristica: coluna eh string se algum valor for str e nao numerico."""
    if not rows:
        return set()
    cols = set()
    for col in rows[0].keys():
        sample = rows[0][col]
        if isinstance(sample, str):
            cols.add(col)
    return cols


def encode_table_l3(name: str, rows: list[dict]) -> str:
    """L3 com auto-bypass: so emite DICT se cardinality < N/2."""
    if not rows:
        return f"## {name} n=0\n"
    cols = list(rows[0].keys())
    string_cols = detect_string_cols(rows)
    n = len(rows)
    out = [f"## {name} n={n}"]

    # Decide DICT por coluna (auto-bypass)
    dict_cols = {}
    for col in string_cols:
        unique = sorted(set(str(r[col]) for r in rows))
        if len(unique) < n / 2:  # auto-bypass: so DICT se cardinality baixa
            dict_cols[col] = unique
            out.append(f"# dict {col}: " + ",".join(unique))

    for col in cols:
        out.append(f"{col}:")
        if col in dict_cols:
            idx_map = {v: i for i, v in enumerate(dict_cols[col])}
            for r in rows:
                out.append(str(idx_map[str(r[col])]))
        else:
            for r in rows:
                out.append(str(r[col]))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Encoder L3 + auto-tudo (caminho feliz)
# ---------------------------------------------------------------------------

def detect_pk_grade2(rows: list[dict], col: str) -> bool:
    """Detecta se coluna eh PK auto-increment (grau 2): valores 1..N."""
    n = len(rows)
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return sorted(values) == list(range(1, n + 1))


def detect_fk_grade2(rows: list[dict], col: str,
                     ref_table_pk_values: set) -> bool:
    """Detecta FK grau 2: ints, todos pertencem a referenced PK."""
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return all(v in ref_table_pk_values for v in values)


def detect_cross_dict(tables: dict[str, list[dict]],
                      string_cols_per_table: dict[str, set]) -> dict:
    """Detecta colunas com vocabulario compartilhado (cross-column DICT).

    Retorna dict: nome_dict_global -> {tabelas: cols, vocab: list}
    """
    cross_dicts = {}
    # Coleta todos vocabularios
    voc_per_col = {}
    for tname, rows in tables.items():
        for col in string_cols_per_table[tname]:
            unique = frozenset(str(r[col]) for r in rows)
            voc_per_col[(tname, col)] = unique

    # Procura intersecoes
    pairs = list(voc_per_col.items())
    used = set()
    for i, (key1, voc1) in enumerate(pairs):
        if key1 in used:
            continue
        group = [key1]
        for key2, voc2 in pairs[i + 1:]:
            if key2 in used:
                continue
            # Vocabularios totalmente compartilhados
            if voc1 == voc2 and len(voc1) > 1:
                group.append(key2)
                used.add(key2)
        if len(group) > 1:
            used.add(key1)
            dict_name = f"GLOBAL_{len(cross_dicts)+1}"
            cross_dicts[dict_name] = {
                "cols": group,  # [(tabela, col), ...]
                "vocab": sorted(voc1),
            }
    return cross_dicts


def encode_db_caminho_feliz(tables: dict[str, list[dict]],
                              schema: dict) -> str:
    """Encode com TODAS as compactacoes automaticas ativas.

    Aplica:
      - L3 (DICT por coluna) com auto-bypass
      - Proposta E (cross-column DICT) com auto-detect
      - Proposta I (eliminate PK/FK grau 2) com schema
      - Auto-bypass em tudo
    """
    out = ["# TCF v0.4 lv=3 mode=caminho-feliz"]

    # 1. Detecta cross-DICTs
    string_cols_per_table = {
        tname: detect_string_cols(rows)
        for tname, rows in tables.items()
    }
    cross_dicts = detect_cross_dict(tables, string_cols_per_table)

    # 2. Emite cross-DICTs (Proposta E)
    cross_resolved = {}  # (tabela, col) -> (dict_name, idx_map)
    for dict_name, info in cross_dicts.items():
        out.append(f"# dict {dict_name}: " + ",".join(info["vocab"]))
        idx_map = {v: i for i, v in enumerate(info["vocab"])}
        for (tname, col) in info["cols"]:
            cross_resolved[(tname, col)] = (dict_name, idx_map)

    out.append("")

    # 3. Emite tabelas
    pk_values_per_table = {}
    for tname, rows in tables.items():
        n = len(rows)
        cols = list(rows[0].keys())
        scols = string_cols_per_table[tname]
        sch = schema.get(tname, {})

        # Detecta PK grau 2
        pk_col = sch.get("pk")
        pk_eliminated = False
        if pk_col and detect_pk_grade2(rows, pk_col):
            pk_eliminated = True
            pk_values_per_table[tname] = {r[pk_col] for r in rows}

        # Detecta FKs grau 2
        fks = sch.get("fks", {})
        fks_eliminated = {}
        for fk_col, ref_table in fks.items():
            if ref_table in pk_values_per_table:
                if detect_fk_grade2(rows, fk_col,
                                     pk_values_per_table[ref_table]):
                    fks_eliminated[fk_col] = ref_table

        # Header da tabela
        flags = []
        if pk_eliminated:
            flags.append(f"pk_eliminated={pk_col}")
        if fks_eliminated:
            fk_str = ",".join(f"{k}->{v}" for k, v in fks_eliminated.items())
            flags.append(f"fk_resolved={{{fk_str}}}")
        flag_text = " " + " ".join(flags) if flags else ""
        out.append(f"## {tname} n={n}{flag_text}")

        # DICTs por coluna (com auto-bypass)
        out_cols = [c for c in cols if c != pk_col or not pk_eliminated]
        per_col_dicts = {}
        for col in out_cols:
            if col in scols and (tname, col) not in cross_resolved:
                unique = sorted(set(str(r[col]) for r in rows))
                if len(unique) < n / 2:
                    per_col_dicts[col] = unique
                    out.append(f"# dict {col}: " + ",".join(unique))

        # Body
        for col in out_cols:
            out.append(f"{col}:")
            if col in fks_eliminated:
                # Substitui FK por indice (simplificado: usa o id - 1)
                for r in rows:
                    out.append(str(r[col] - 1))
            elif (tname, col) in cross_resolved:
                _, idx_map = cross_resolved[(tname, col)]
                for r in rows:
                    out.append(str(idx_map[str(r[col])]))
            elif col in per_col_dicts:
                idx_map = {v: i for i, v in enumerate(per_col_dicts[col])}
                for r in rows:
                    out.append(str(idx_map[str(r[col])]))
            else:
                for r in rows:
                    out.append(str(r[col]))
        out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("Lab: caminho feliz — auto-tudo no banco didatico")
    print("=" * 80)

    db = build_synthetic_db()

    schema = {
        "pessoas":  {"pk": "id", "fks": {}},
        "produtos": {"pk": "id", "fks": {}},
        "pedidos":  {"pk": "pedido_id",
                      "fks": {"pessoa_id": "pessoas",
                              "produto_id": "produtos"}},
    }

    print(f"\n  Banco:")
    for name, rows in db.items():
        print(f"    {name}: {len(rows)} rows, {len(rows[0])} cols, "
              f"chaves: {list(rows[0].keys())[:2]}...")

    # ---- 3 estrategias ----
    text_naive = "".join(encode_table_naive(n, r) for n, r in db.items())
    text_l3 = "".join(encode_table_l3(n, r) for n, r in db.items())
    text_feliz = encode_db_caminho_feliz(db, schema)

    b_naive = len(text_naive.encode())
    b_l3 = len(text_l3.encode())
    b_feliz = len(text_feliz.encode())

    print(f"\n  {'estrategia':<40} {'bytes':>7} {'vs naive':>10}")
    print(f"  {'-'*40} {'-'*7} {'-'*10}")
    print(f"  {'1. naive (CSV-like)':<40} {b_naive:>7}  {0:>+9.1f}%")
    print(f"  {'2. L3 (DICT auto-bypass)':<40} {b_l3:>7}  "
          f"{(b_l3/b_naive-1)*100:>+9.1f}%")
    print(f"  {'3. caminho feliz (E + I + L3 + bypass)':<40} {b_feliz:>7}  "
          f"{(b_feliz/b_naive-1)*100:>+9.1f}%")
    print(f"\n  Caminho feliz vs L3 atual: "
          f"{(b_feliz - b_l3)} B  ({(b_feliz/b_l3-1)*100:+.1f}%)")

    # ---- Salva ----
    (OUT / "1-naive.tcf").write_text(text_naive, encoding="utf-8")
    (OUT / "2-l3.tcf").write_text(text_l3, encoding="utf-8")
    (OUT / "3-caminho-feliz.tcf").write_text(text_feliz, encoding="utf-8")

    # ---- Mostra os tres outputs lado a lado (so primeiras 30 linhas) ----
    print("\n" + "=" * 80)
    print("Inspecao didatica: caminho feliz")
    print("=" * 80)
    print()
    for line in text_feliz.splitlines()[:50]:
        print(f"    {line}")
    if len(text_feliz.splitlines()) > 50:
        print(f"    ... ({len(text_feliz.splitlines())-50} linhas a mais)")

    # ---- Decisoes automaticas tomadas ----
    print("\n" + "=" * 80)
    print("Decisoes automaticas tomadas pelo encoder")
    print("=" * 80)
    print(f"""
  Cross-DICTs detectados (Proposta E):
""")
    string_cols_per_table = {
        tname: detect_string_cols(rows) for tname, rows in db.items()
    }
    cross = detect_cross_dict(db, string_cols_per_table)
    for name, info in cross.items():
        cols = ", ".join(f"{t}.{c}" for (t, c) in info["cols"])
        print(f"    {name}: {cols}  (vocab: {info['vocab']})")
    if not cross:
        print("    (nenhum)")

    print(f"\n  PKs/FKs eliminadas (Proposta I):")
    for tname, rows in db.items():
        sch = schema.get(tname, {})
        pk = sch.get("pk")
        if pk and detect_pk_grade2(rows, pk):
            print(f"    {tname}.{pk} (PK grau 2)  → eliminada, regenerada no decode")
        for fk_col, ref in sch.get("fks", {}).items():
            ref_pk_values = {r[schema[ref]["pk"]] for r in db[ref]}
            if detect_fk_grade2(rows, fk_col, ref_pk_values):
                print(f"    {tname}.{fk_col} → {ref}  (FK grau 2)")

    print(f"\n  Auto-bypass DICT por cardinality:")
    for tname, rows in db.items():
        n = len(rows)
        for col in detect_string_cols(rows):
            uniq = len(set(str(r[col]) for r in rows))
            verdict = "DICT" if uniq < n/2 else "BYPASS"
            print(f"    {tname}.{col}: cardinality={uniq}/{n} → {verdict}")

    print(f"\n  Arquivos: {OUT}")


if __name__ == "__main__":
    main()
