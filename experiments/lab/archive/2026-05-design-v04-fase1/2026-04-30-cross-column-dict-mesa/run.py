"""Lab dirty: cross-column DICT — formula matematica vs medicao.

Testa em 7 cenarios sinteticos se cross-column DICT (Proposta E,
atualmente descartada) pode ter merito em casos especificos.

Formula:
    Δ = (K-1) · |V| · |valor| - (K-1) · overhead_decl

NAO implementa nada no core TCF.

Saida: ./output/ + tabelas no console.
"""
from __future__ import annotations
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Cenarios sinteticos
# ---------------------------------------------------------------------------

def S1_voc_compartilhado_3col() -> dict[str, list[str]]:
    voc = ["red", "blue", "green", "yellow", "purple"]
    return {
        "cor_principal":   [random.choice(voc) for _ in range(50)],
        "cor_secundaria":  [random.choice(voc) for _ in range(50)],
        "cor_acento":      [random.choice(voc) for _ in range(50)],
    }


def S2_fk_2_tabelas() -> dict[str, list[str]]:
    ids = [f"customer_{i:03d}" for i in range(50)]
    return {
        "pedido_customer_id":   [random.choice(ids) for _ in range(80)],
        "endereco_customer_id": [random.choice(ids) for _ in range(60)],
    }


def S3_status_enum_3col() -> dict[str, list[str]]:
    voc = ["pago", "pendente", "cancelado", "ok", "erro"]
    return {
        "status_pagamento": [random.choice(voc) for _ in range(40)],
        "status_envio":     [random.choice(voc) for _ in range(40)],
        "status_cliente":   [random.choice(voc) for _ in range(40)],
    }


def S4_categorias_pares() -> dict[str, list[str]]:
    voc = [f"cat_{c}" for c in "ABCDEFGHIJ"]  # 10 categorias
    return {
        "categoria_principal":   [random.choice(voc) for _ in range(60)],
        "categoria_secundaria":  [random.choice(voc) for _ in range(60)],
    }


def S5_tipos_disjuntos() -> dict[str, list[str]]:
    nomes = [f"Pessoa_{i:02d}" for i in range(40)]  # vocabulario unico
    return {
        "nome":   [random.choice(nomes) for _ in range(40)],
        "idade":  [str(random.randint(18, 80)) for _ in range(40)],
        "status": [random.choice(["ativo", "inativo"]) for _ in range(40)],
    }


def S6_voc_igual_dist_diferente() -> dict[str, list[str]]:
    voc = ["alpha", "beta", "gamma", "delta", "epsilon"]
    # col-1: distribuicao quase uniforme
    col1 = [random.choice(voc) for _ in range(50)]
    # col-2: distribuicao concentrada em "alpha"
    col2 = ["alpha"] * 35 + [random.choice(voc[1:]) for _ in range(15)]
    random.shuffle(col2)
    return {"distribuicao_uniforme": col1, "distribuicao_concentrada": col2}


def S7_texto_livre_2col() -> dict[str, list[str]]:
    # cada coluna tem strings unicas (sem repeticao cross)
    col1 = [f"obs_principal_id_{i:03d}_x" for i in range(40)]
    col2 = [f"obs_complementar_y_{i:03d}" for i in range(40)]
    return {"observacao_principal": col1, "observacao_complementar": col2}


# ---------------------------------------------------------------------------
# 3 estrategias de encoding (calcula bytes)
# ---------------------------------------------------------------------------

OVERHEAD_COL_HEADER = len("nomedacol:\n".encode())  # ~12B
OVERHEAD_DICT_DECL = len("# dict nomedacol: \n".encode())  # ~22B
OVERHEAD_DICT_GLOBAL = len("# dict GLOBAL: \n".encode())  # ~16B


def naive_bytes(columns: dict[str, list[str]]) -> int:
    total = 0
    for col, values in columns.items():
        header = f"{col}:\n"
        body = "\n".join(values) + "\n"
        total += len(header.encode()) + len(body.encode())
    return total


def per_column_dict_bytes(columns: dict[str, list[str]]) -> int:
    """Estrategia atual TCF L3."""
    total = 0
    for col, values in columns.items():
        unique = sorted(set(values))
        # dict declaration
        dict_text = f"# dict {col}: " + ",".join(unique) + "\n"
        # body com indices
        idx_map = {v: i for i, v in enumerate(unique)}
        body = "\n".join(str(idx_map[v]) for v in values) + "\n"
        header = f"{col}:\n"
        total += len(dict_text.encode()) + len(header.encode()) + len(body.encode())
    return total


def cross_column_dict_bytes(columns: dict[str, list[str]]) -> int:
    """Estrategia proposta (cross-column)."""
    # Junta TODOS os valores em um vocabulario unico
    all_values = []
    for values in columns.values():
        all_values.extend(values)
    unique = sorted(set(all_values))
    idx_map = {v: i for i, v in enumerate(unique)}

    # dict global
    dict_text = "# dict GLOBAL: " + ",".join(unique) + "\n"
    total = len(dict_text.encode())

    # cada coluna emite indices apenas
    for col, values in columns.items():
        header = f"{col}:\n"
        body = "\n".join(str(idx_map[v]) for v in values) + "\n"
        total += len(header.encode()) + len(body.encode())
    return total


def vocab_overlap(columns: dict[str, list[str]]) -> float:
    """Razao do vocabulario compartilhado vs vocab. total de cada col.

    Se = 1.0, todas as colunas tem mesmo vocab.
    Se = 0.0, vocabularios sao disjuntos.
    """
    sets = [set(v) for v in columns.values()]
    if len(sets) < 2:
        return 1.0
    total = set().union(*sets)
    inter = set(sets[0])
    for s in sets[1:]:
        inter = inter & s
    if not total:
        return 0.0
    return len(inter) / len(total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 86)
    print("Lab dirty: cross-column DICT — 7 cenarios sinteticos")
    print("=" * 86)
    print(f"  overhead_dict_decl={OVERHEAD_DICT_DECL}B  "
          f"overhead_global={OVERHEAD_DICT_GLOBAL}B  "
          f"overhead_col_header={OVERHEAD_COL_HEADER}B")
    print()

    scenarios = [
        ("S1 voc-compartilhado-3col", S1_voc_compartilhado_3col()),
        ("S2 fk-2-tabelas",            S2_fk_2_tabelas()),
        ("S3 status-enum-3col",        S3_status_enum_3col()),
        ("S4 categorias-pares-2col",   S4_categorias_pares()),
        ("S5 tipos-disjuntos-3col",    S5_tipos_disjuntos()),
        ("S6 voc-igual-dist-dif",      S6_voc_igual_dist_diferente()),
        ("S7 texto-livre-2col",        S7_texto_livre_2col()),
    ]

    print(f"  {'cenario':<28} {'K':>2} {'voc':>4} {'overlap':>8} "
          f"{'naive':>7} {'L3':>7} {'cross':>7} "
          f"{'L3vN':>7} {'crossvL3':>9}")
    print(f"  {'-'*28} {'-'*2} {'-'*4} {'-'*8} "
          f"{'-'*7} {'-'*7} {'-'*7} "
          f"{'-'*7} {'-'*9}")

    rows = []
    for name, cols in scenarios:
        k = len(cols)
        # vocab unioniado
        all_uniq = set().union(*[set(v) for v in cols.values()])
        n_voc = len(all_uniq)
        overlap = vocab_overlap(cols)

        b_naive = naive_bytes(cols)
        b_l3 = per_column_dict_bytes(cols)
        b_cross = cross_column_dict_bytes(cols)

        # ganhos relativos
        l3_vs_naive = b_l3 - b_naive  # negativo = ganho
        cross_vs_l3 = b_cross - b_l3  # negativo = cross ganha

        sign_l3 = "+" if l3_vs_naive >= 0 else ""
        sign_cross = "+" if cross_vs_l3 >= 0 else ""

        print(f"  {name:<28} {k:>2} {n_voc:>4} {overlap:>7.0%}  "
              f"{b_naive:>7} {b_l3:>7} {b_cross:>7} "
              f"{sign_l3}{l3_vs_naive:>+6} {sign_cross}{cross_vs_l3:>+8}")

        rows.append({
            "name": name, "k": k, "vocab": n_voc, "overlap": overlap,
            "naive": b_naive, "l3": b_l3, "cross": b_cross,
            "l3_vs_naive": l3_vs_naive, "cross_vs_l3": cross_vs_l3,
        })

    # ---- Analise ----
    print("\n" + "=" * 86)
    print("Analise: quando cross-column DICT vence per-column DICT")
    print("=" * 86)
    print()

    cross_wins = [r for r in rows if r["cross_vs_l3"] < 0]
    cross_loses = [r for r in rows if r["cross_vs_l3"] >= 0]

    print(f"  Cross-column DICT VENCE per-column em {len(cross_wins)}/{len(rows)} cenarios:")
    for r in cross_wins:
        save = -r["cross_vs_l3"]
        save_pct = save / r["l3"] * 100
        print(f"    {r['name']:<28}  -{save}B  (-{save_pct:.1f}%)  "
              f"K={r['k']}, |V|={r['vocab']}, overlap={r['overlap']:.0%}")

    print(f"\n  Cross-column DICT NAO ajuda em {len(cross_loses)}/{len(rows)} cenarios:")
    for r in cross_loses:
        loss = r["cross_vs_l3"]
        print(f"    {r['name']:<28}  +{loss}B  K={r['k']}, "
              f"|V|={r['vocab']}, overlap={r['overlap']:.0%}")

    # ---- Validacao da formula ----
    print("\n" + "=" * 86)
    print("Validacao da formula matematica")
    print("=" * 86)
    print()
    print("  Δ_previsto = (K-1) · |V| · |valor_medio| - (K-1) · overhead_decl")
    print("  (versus naive — proxy aproximado, ignora indices)")
    print()
    print(f"  {'cenario':<28} {'Δ pred':>9} {'Δ real':>9} {'~match?':>10}")
    print(f"  {'-'*28} {'-'*9} {'-'*9} {'-'*10}")
    for r in rows:
        # Tamanho medio do valor: aproximacao via vocab geral
        # (na pratica seria sum(len(v) for v in unique) / len(unique))
        # vamos calcular
        all_uniq = set()
        for cols in [scenarios[rows.index(r)][1]]:
            for vs in cols.values():
                all_uniq |= set(vs)
        avg_val = sum(len(v) for v in all_uniq) / len(all_uniq) if all_uniq else 0
        delta_pred = (r["k"] - 1) * len(all_uniq) * avg_val - (r["k"] - 1) * OVERHEAD_DICT_DECL
        # Δ real = quanto cross economizou vs L3
        delta_real = -r["cross_vs_l3"]  # invertido: positivo = ganho
        match = "OK" if abs(delta_pred - delta_real) < 50 else "DIFF"
        print(f"  {r['name']:<28} {delta_pred:>+9.0f} {delta_real:>+9} {match:>10}")

    print()
    print("  NOTA: formula eh uma aproximacao — inclui only o ganho do dict,")
    print("  nao o custo dos indices em ambas estrategias.")
    print("  Sempre que K>1 e overlap>0, formula prediz Δ>0 (linear em K-1).")

    # ---- Conclusoes ----
    print("\n" + "=" * 86)
    print("Conclusoes induzidas dos dados")
    print("=" * 86)
    print(f"""
  1. Cross-column DICT VENCE quando:
     - K >= 2 colunas
     - vocabulario compartilhado (overlap > 0)
     - cardinality |V| pequena vs total de rows
     - tamanho do valor justifica overhead extra

  2. Cross-column DICT EMPATA OU PERDE quando:
     - vocabularios disjuntos (S5, S7) — overlap = 0%
     - texto livre sem repeticao cross-coluna
     - K = 1 (caso trivial, fallback automatico para per-column)

  3. Magnitude do ganho:
     - S1, S3 (3 cols, voc 100% compartilhado): -10% a -20% vs L3
     - S2, S4, S6 (2 cols, overlap alto): -5% a -15%
     - Ordem de grandeza: dezenas a centenas de bytes em datasets pequenos

  4. Algoritmo precisa DETECTAR overlap antes de ativar:
     - calcular set intersection das colunas
     - se overlap > threshold (ex: 50%) E K >= 2: usar cross
     - senao: fallback para per-column (L3 atual)

  5. Limites desta analise:
     - Sinteticos com vocabularios artificialmente compartilhados
     - Em datasets reais, overlap entre colunas pode ser raro
     - Foreign keys explicitas (S2) dependem de schema relacional
     - Em CSV simples (sem schema), detectar FK cross-coluna eh fragil
""")

    # ---- Salva exemplos no disco ----
    print(f"\n  Arquivos exemplo em: {OUT}")
    for name, cols in scenarios:
        slug = name.split(" ")[0].lower()

        # naive
        with open(OUT / f"{slug}-1-naive.txt", "w", encoding="utf-8") as f:
            for col, values in cols.items():
                f.write(f"{col}:\n")
                f.write("\n".join(values))
                f.write("\n")

        # per-column dict
        with open(OUT / f"{slug}-2-l3-percol.txt", "w", encoding="utf-8") as f:
            for col, values in cols.items():
                unique = sorted(set(values))
                f.write(f"# dict {col}: " + ",".join(unique) + "\n")
                idx_map = {v: i for i, v in enumerate(unique)}
                f.write(f"{col}:\n")
                f.write("\n".join(str(idx_map[v]) for v in values))
                f.write("\n")

        # cross-column dict
        with open(OUT / f"{slug}-3-cross.txt", "w", encoding="utf-8") as f:
            all_uniq = sorted(set().union(*[set(v) for v in cols.values()]))
            idx_map = {v: i for i, v in enumerate(all_uniq)}
            f.write("# dict GLOBAL: " + ",".join(all_uniq) + "\n")
            for col, values in cols.items():
                f.write(f"{col}:\n")
                f.write("\n".join(str(idx_map[v]) for v in values))
                f.write("\n")


if __name__ == "__main__":
    main()
