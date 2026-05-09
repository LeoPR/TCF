"""Mesa ampla: escalando do trivial ao complexo, todas tecnicas ativas.

Quatro niveis de escala progressiva, do dataset minimo ao banco
relacional pequeno. Para cada um:
  1. Naive (CSV-like, referencia)
  2. TCF v0.4 caminho feliz (auto-tudo com schema)

Mede onde cada tecnica COMECA a fazer sentido conforme escala
cresce. Sem comparar tecnicas obsoletas (D1-D16 aplicadas).

Saida: ./output/N1, /N2, /N3, /N4
"""
from __future__ import annotations
import random
import string
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Encoder helpers (forma vencedora)
# ---------------------------------------------------------------------------

def detect_string_cols(rows):
    if not rows:
        return set()
    return {c for c in rows[0].keys() if isinstance(rows[0][c], str)}


def detect_pk_grade2(rows, col):
    n = len(rows)
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return sorted(values) == list(range(1, n + 1))


def detect_fk_grade2(rows, col, ref_pk_values):
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return all(v in ref_pk_values for v in values)


def detect_affix(values):
    if not values:
        return ""
    p = values[0]
    for v in values[1:]:
        i = 0
        while i < min(len(p), len(v)) and p[i] == v[i]:
            i += 1
        p = p[:i]
        if not p:
            return ""
    return p


def detect_cross_dicts(tables, threshold=0.5):
    """Detecta colunas com vocabulario compartilhado >= threshold."""
    voc_per_col = {}
    for tname, t in tables.items():
        rows = t["rows"]
        for col in detect_string_cols(rows):
            voc_per_col[(tname, col)] = frozenset(str(r[col]) for r in rows)

    cross = {}
    used = set()
    items = list(voc_per_col.items())
    for i, (key1, voc1) in enumerate(items):
        if key1 in used or len(voc1) < 2:
            continue
        group = [key1]
        for key2, voc2 in items[i + 1:]:
            if key2 in used or len(voc2) < 2:
                continue
            inter = voc1 & voc2
            union = voc1 | voc2
            if len(inter) / len(union) >= threshold:
                group.append(key2)
                used.add(key2)
        if len(group) > 1:
            used.add(key1)
            shared_voc = sorted(voc_per_col[group[0]])
            for k in group[1:]:
                shared_voc = sorted(set(shared_voc) | voc_per_col[k])
            cross[f"GLOBAL_{len(cross)+1}"] = {
                "cols": group, "vocab": shared_voc,
            }
    return cross


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------

def encode_naive(tables):
    out = []
    for tname, t in tables.items():
        rows = t["rows"]
        if not rows:
            continue
        cols = list(rows[0].keys())
        out.append(f"## {tname} n={len(rows)}")
        for col in cols:
            out.append(f"{col}:")
            for r in rows:
                out.append(str(r[col]))
        out.append("")
    return "\n".join(out)


def encode_tcf_v04_caminho_feliz(tables, schema):
    """Aplica todas as tecnicas vencedoras automaticamente."""
    out = ["# TCF v0.4 lv=3 mode=caminho-feliz"]

    # 1. Detecta cross-DICTs (Proposta E)
    cross_dicts = detect_cross_dicts(tables, threshold=0.5)
    cross_resolved = {}
    for dname, info in cross_dicts.items():
        out.append(f"# dict {dname}: " + ",".join(info["vocab"]))
        idx_map = {v: i for i, v in enumerate(info["vocab"])}
        for tcol in info["cols"]:
            cross_resolved[tcol] = (dname, idx_map)
    if cross_dicts:
        out.append("")

    # 2. Coleta PKs grau 2 (Proposta I)
    pk_values = {}
    for tname, t in tables.items():
        sch = schema.get(tname, {})
        pk = sch.get("pk")
        if pk and detect_pk_grade2(t["rows"], pk):
            pk_values[tname] = {r[pk] for r in t["rows"]}

    # 3. Emite cada tabela
    for tname, t in tables.items():
        rows = t["rows"]
        if not rows:
            out.append(f"## {tname} n=0")
            continue
        n = len(rows)
        cols = list(rows[0].keys())
        scols = detect_string_cols(rows)
        sch = schema.get(tname, {})

        pk_col = sch.get("pk")
        pk_eliminated = pk_col and pk_col in {sch.get("pk")} and tname in pk_values

        # Detect FKs grau 2
        fks = sch.get("fks", {})
        fks_eliminated = {}
        for fk_col, ref in fks.items():
            if ref in pk_values and detect_fk_grade2(rows, fk_col, pk_values[ref]):
                fks_eliminated[fk_col] = ref

        # Header
        flags = []
        if pk_eliminated:
            flags.append(f"pk_eliminated={pk_col}")
        if fks_eliminated:
            fk_str = ",".join(f"{k}->{v}" for k, v in fks_eliminated.items())
            flags.append(f"fk_resolved={{{fk_str}}}")
        flag_text = " " + " ".join(flags) if flags else ""
        out.append(f"## {tname} n={n}{flag_text}")

        out_cols = [c for c in cols if c != pk_col or not pk_eliminated]

        # Body por coluna (DICT inline; auto-bypass; affix; cross)
        for col in out_cols:
            values = [str(r[col]) for r in rows]
            unique = sorted(set(values))
            cardinality = len(unique)

            # FK grau 2 → indice direto
            if col in fks_eliminated:
                out.append(f"{col}:")
                for r in rows:
                    out.append(str(r[col] - 1))
                continue

            # Cross-DICT (Proposta E)
            if (tname, col) in cross_resolved:
                dname, idx_map = cross_resolved[(tname, col)]
                out.append(f"{col}: dict_ref={dname}")
                for v in values:
                    out.append(str(idx_map[v]))
                continue

            # Affix-DICT (Proposta H) — quando prefixo > 4 chars
            if col in scols and cardinality >= n / 2:
                prefix = detect_affix(values)
                if len(prefix) >= 4:
                    out.append(f"{col}: affix=\"{prefix}\"")
                    for v in values:
                        if v.startswith(prefix):
                            out.append(v[len(prefix):])
                        else:
                            out.append("\\!" + v)
                    continue

            # L3 DICT inline (D16) — quando cardinality < N/2
            if col in scols and cardinality < n / 2:
                out.append(f"{col}: dict={','.join(unique)}")
                idx_map = {v: i for i, v in enumerate(unique)}
                for v in values:
                    out.append(str(idx_map[v]))
                continue

            # Bypass — sem DICT
            out.append(f"{col}:")
            for v in values:
                out.append(v)

        out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Datasets escalando
# ---------------------------------------------------------------------------

def N1_minimo():
    """1 tabela, 5 rows, 2 cols. Caso minimo absoluto."""
    rows = [
        {"nome": "Ana", "idade": 25},
        {"nome": "Bruno", "idade": 30},
        {"nome": "Carlos", "idade": 28},
        {"nome": "Diana", "idade": 35},
        {"nome": "Eduardo", "idade": 40},
    ]
    return {
        "pessoas": {"rows": rows},
    }, {
        "pessoas": {"pk": None, "fks": {}},
    }


def N2_unica_tabela_media():
    """1 tabela, 50 rows, 5 cols. Vocabulario com repeticao."""
    cidades = ["SP", "RJ", "BH", "POA", "REC"]
    estados = ["SP", "RJ", "MG", "RS", "PE"]
    cidade_to_estado = dict(zip(cidades, estados))
    rows = []
    for i in range(50):
        c = random.choice(cidades)
        rows.append({
            "id": i + 1,
            "nome": f"Cliente_{i+1:03d}",
            "cidade": c,
            "estado": cidade_to_estado[c],
            "categoria": random.choice(["A", "B", "C"]),
            "valor": round(random.uniform(100, 9999), 2),
        })
    return {
        "clientes": {"rows": rows},
    }, {
        "clientes": {"pk": "id", "fks": {}},
    }


def N3_mini_banco():
    """3 tabelas com FKs. Banco didatico pequeno."""
    pessoas = [
        {"id": i + 1, "nome": n, "categoria": random.choice(["A", "B", "C"])}
        for i, n in enumerate(
            ["Ana", "Bruno", "Carlos", "Diana", "Eduardo",
             "Fernanda", "Gabriel", "Helena", "Igor", "Juliana"])
    ]
    produtos = [
        {"id": i + 1, "nome": f"Prod-{i+1:03d}",
         "categoria": random.choice(["A", "B", "C"])}
        for i in range(20)
    ]
    pedidos = []
    for i in range(80):
        pedidos.append({
            "pedido_id": i + 1,
            "pessoa_id": random.randint(1, 10),
            "produto_id": random.randint(1, 20),
            "qtd": random.randint(1, 5),
            "status": random.choice(["pago", "pendente", "cancelado"]),
        })
    return {
        "pessoas": {"rows": pessoas},
        "produtos": {"rows": produtos},
        "pedidos": {"rows": pedidos},
    }, {
        "pessoas": {"pk": "id", "fks": {}},
        "produtos": {"pk": "id", "fks": {}},
        "pedidos": {"pk": "pedido_id",
                     "fks": {"pessoa_id": "pessoas",
                             "produto_id": "produtos"}},
    }


def N4_banco_completo():
    """5 tabelas, ~1300 rows totais. Banco didatico expandido."""
    pessoas = [
        {"id": i + 1,
         "nome": "".join(random.choices(string.ascii_uppercase, k=8)),
         "categoria_pref": random.choice(["A", "B", "C", "D"]),
         "cidade": random.choice(["SP", "RJ", "BH"])}
        for i in range(100)
    ]
    produtos = [
        {"id": i + 1,
         "codigo": f"PROD-2026-{i+1:05d}",
         "nome": f"Item-{i+1:04d}",
         "categoria": random.choice(["A", "B", "C", "D"]),
         "preco": round(random.uniform(5, 999), 2)}
        for i in range(50)
    ]
    pedidos = []
    for i in range(500):
        pedidos.append({
            "pedido_id": i + 1,
            "pessoa_id": random.randint(1, 100),
            "produto_id": random.randint(1, 50),
            "qtd": random.randint(1, 10),
            "status": random.choice(["pago", "pendente", "cancelado", "ok"]),
        })
    enderecos = []
    for i in range(150):
        enderecos.append({
            "id": i + 1,
            "pessoa_id": random.randint(1, 100),
            "tipo": random.choice(["residencial", "comercial"]),
            "cidade": random.choice(["SP", "RJ", "BH"]),
        })
    avaliacoes = []
    for i in range(300):
        avaliacoes.append({
            "id": i + 1,
            "produto_id": random.randint(1, 50),
            "pessoa_id": random.randint(1, 100),
            "nota": random.randint(1, 5),
            "categoria_pref": random.choice(["A", "B", "C", "D"]),
        })
    return {
        "pessoas": {"rows": pessoas},
        "produtos": {"rows": produtos},
        "pedidos": {"rows": pedidos},
        "enderecos": {"rows": enderecos},
        "avaliacoes": {"rows": avaliacoes},
    }, {
        "pessoas": {"pk": "id", "fks": {}},
        "produtos": {"pk": "id", "fks": {}},
        "pedidos": {"pk": "pedido_id",
                     "fks": {"pessoa_id": "pessoas",
                             "produto_id": "produtos"}},
        "enderecos": {"pk": "id",
                       "fks": {"pessoa_id": "pessoas"}},
        "avaliacoes": {"pk": "id",
                        "fks": {"produto_id": "produtos",
                                "pessoa_id": "pessoas"}},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("Mesa ampla: escalando do trivial ao complexo")
    print("=" * 80)

    levels = [
        ("N1", "1 tabela, 5 rows, 2 cols (minimo)", N1_minimo),
        ("N2", "1 tabela, 50 rows, 5 cols (medio)", N2_unica_tabela_media),
        ("N3", "3 tabelas com FKs (mini-banco)", N3_mini_banco),
        ("N4", "5 tabelas, ~1100 rows (banco completo)", N4_banco_completo),
    ]

    print(f"\n  {'nivel':<6} {'descricao':<42} {'n_rows':>7} {'naive':>7} "
          f"{'TCFv04':>8} {'gain':>9}")
    print(f"  {'-'*6} {'-'*42} {'-'*7} {'-'*7} {'-'*8} {'-'*9}")

    summary = []
    for level_id, desc, factory in levels:
        tables, schema = factory()
        n_rows = sum(len(t["rows"]) for t in tables.values())

        text_naive = encode_naive(tables)
        text_tcf = encode_tcf_v04_caminho_feliz(tables, schema)

        b_naive = len(text_naive.encode())
        b_tcf = len(text_tcf.encode())
        gain = (b_tcf / b_naive - 1) * 100

        sign = "+" if gain > 0 else ""
        print(f"  {level_id:<6} {desc:<42} {n_rows:>7} {b_naive:>7} "
              f"{b_tcf:>8} {sign}{gain:>+7.1f}%")

        # Salva
        level_dir = OUT / level_id
        level_dir.mkdir(exist_ok=True)
        (level_dir / "1-naive.tcf").write_text(text_naive, encoding="utf-8")
        (level_dir / "2-tcfv04-caminho-feliz.tcf").write_text(text_tcf, encoding="utf-8")

        summary.append({
            "level": level_id,
            "desc": desc,
            "n_rows": n_rows,
            "naive": b_naive,
            "tcf": b_tcf,
            "gain": gain,
            "tables": tables,
            "schema": schema,
        })

    # ---- Decisoes automaticas tomadas em cada nivel ----
    print("\n" + "=" * 80)
    print("Decisoes automaticas por nivel")
    print("=" * 80)

    for s in summary:
        print(f"\n  [{s['level']}] {s['desc']}")
        # Cross-DICTs
        cross = detect_cross_dicts(s["tables"], threshold=0.5)
        if cross:
            for name, info in cross.items():
                cols_disp = ", ".join(f"{t}.{c}" for (t, c) in info["cols"])
                print(f"    cross-DICT {name}: {cols_disp}  "
                      f"(vocab: {info['vocab'][:5]}...)" if len(info["vocab"]) > 5
                      else f"    cross-DICT {name}: {cols_disp}  (vocab: {info['vocab']})")
        else:
            print(f"    cross-DICT: nenhum")

        # PK eliminations
        pk_elims = []
        for tname, t in s["tables"].items():
            sch = s["schema"].get(tname, {})
            pk = sch.get("pk")
            if pk and detect_pk_grade2(t["rows"], pk):
                pk_elims.append(f"{tname}.{pk}")
        if pk_elims:
            print(f"    PK eliminations: {', '.join(pk_elims)}")

        # Affix possibilities
        for tname, t in s["tables"].items():
            for col in detect_string_cols(t["rows"]):
                values = [str(r[col]) for r in t["rows"]]
                prefix = detect_affix(values)
                if len(prefix) >= 4:
                    print(f"    affix detected in {tname}.{col}: \"{prefix}\"")

    # ---- Padrao emergente: em qual escala cada tecnica vale a pena ----
    print("\n" + "=" * 80)
    print("Padrao emergente: ganho em funcao da escala")
    print("=" * 80)
    print()
    print(f"  {'nivel':<6} {'rows':>7} {'gain':>8}  observacoes")
    print(f"  {'-'*6} {'-'*7} {'-'*8}  {'-'*40}")
    for s in summary:
        obs = []
        if s["gain"] < -25:
            obs.append("forte ganho")
        elif s["gain"] < -10:
            obs.append("ganho moderado")
        elif s["gain"] < 0:
            obs.append("ganho marginal")
        elif s["gain"] < 5:
            obs.append("empate / overhead domina")
        else:
            obs.append("formato perde — investigar")
        print(f"  {s['level']:<6} {s['n_rows']:>7} {s['gain']:>+7.1f}%  {', '.join(obs)}")

    print()
    print("  Conclusao: o ganho cresce com a escala. Em N1 (5 rows), o overhead")
    print("  dos markers (`pk_eliminated=`, `dict=`, etc) eh maior que o payload.")
    print("  A partir de N3-N4, propostas E/I/H comecam a economizar bytes")
    print("  significativamente.")

    print(f"\n  Arquivos por nivel: {OUT}/N1, /N2, /N3, /N4")


if __name__ == "__main__":
    main()
