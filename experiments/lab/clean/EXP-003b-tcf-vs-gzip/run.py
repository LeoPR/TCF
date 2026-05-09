"""EXP-003b — HP-T1 decisor principal: TCF modes + gzip.

Compara:
  - CSV + gzip                 (baseline do EXP-003a)
  - TCF raw + gzip             (colunar puro)
  - TCF compact + gzip         (RLE + sort automatico)
  - TCF smart + gzip           (auto-tudo: E + H + I + DICT inline + bypass)

Em 5 datasets variados.

Decide: smart vence compact por margem que justifica E/H/I no core?

Saida: ./results/ com arquivos + results.json
"""
from __future__ import annotations
import csv
import io
import gzip
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from data_sources import load_dataset

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Datasets (mesmos 5 do EXP-003a)
# ---------------------------------------------------------------------------

def get_datasets():
    out = []

    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    out.append({
        "name": "tpch-supplier-100",
        "rows": tables.get("supplier", []),
        "schema": {"pk": "s_suppkey", "fks": {}},
    })

    tables, _ = load_dataset("canonical:adult-census",
                              volume=1000, seed=42, schema=["adult"])
    out.append({
        "name": "adult-1k",
        "rows": tables.get("adult", []),
        "schema": {"pk": None, "fks": {}},
    })

    statuses = ["pago", "pendente", "cancelado", "ok"]
    categorias = ["A", "B", "C", "D"]
    cidades = ["SP", "RJ", "BH", "POA", "REC"]
    rows = []
    for i in range(500):
        rows.append({
            "id": i + 1,
            "status": random.choice(statuses),
            "categoria": random.choice(categorias),
            "cidade": random.choice(cidades),
            "valor": round(random.uniform(10, 999), 2),
            "qtd": random.randint(1, 10),
            "ativo": random.choice([True, False]),
        })
    out.append({"name": "categorical-heavy", "rows": rows,
                 "schema": {"pk": "id", "fks": {}}})

    from datetime import date, timedelta
    base = date(2026, 1, 1)
    rows = []
    for i in range(500):
        d = base + timedelta(days=i)
        rows.append({
            "data": d.isoformat(),
            "temperatura": round(20 + random.gauss(0, 5), 1),
            "umidade": round(60 + random.gauss(0, 10), 1),
            "pressao": round(1013 + random.gauss(0, 5), 2),
            "vento": round(random.uniform(0, 30), 1),
        })
    out.append({"name": "time-series", "rows": rows,
                 "schema": {"pk": None, "fks": {}}})

    nomes = [f"Cliente_{i:03d}" for i in range(50)]
    produtos = [f"Prod-{i:03d}" for i in range(20)]
    rows = []
    for i in range(800):
        rows.append({
            "pedido_id": i + 1,
            "cliente_id": random.randint(1, 50),
            "cliente_nome": random.choice(nomes),
            "produto_id": random.randint(1, 20),
            "produto_nome": random.choice(produtos),
            "qtd": random.randint(1, 5),
            "valor_unit": round(random.uniform(5, 500), 2),
            "status": random.choice(["pago", "pendente", "cancelado"]),
        })
    out.append({"name": "mixed-relational", "rows": rows,
                 "schema": {"pk": "pedido_id", "fks": {}}})

    return out


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------

def encode_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def encode_tcf_raw(rows, name="t"):
    """TCF raw: colunar puro, sem sort, sem RLE, sem DICT."""
    if not rows:
        return ""
    cols = list(rows[0].keys())
    out = [f"# TCF v0.4 lv=raw"]
    out.append(f"## {name} n={len(rows)}")
    for col in cols:
        out.append(f"{col}:")
        for r in rows:
            out.append(str(r[col]))
    return "\n".join(out) + "\n"


def detect_string_cols(rows):
    if not rows:
        return set()
    return {c for c in rows[0].keys() if isinstance(rows[0][c], str)}


def detect_pk_grade2(rows, col):
    if not col:
        return False
    n = len(rows)
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return sorted(values) == list(range(1, n + 1))


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


def detect_cross_dicts(tables_dict, threshold=0.5):
    """tables_dict = {name: rows}. Retorna {dict_name: {cols, vocab}}."""
    voc_per_col = {}
    for tname, rows in tables_dict.items():
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


def best_sort_col(rows):
    """Heuristica: coluna com menor cardinality < N/2 que economiza runs."""
    if not rows:
        return None
    n = len(rows)
    candidates = []
    for col in rows[0].keys():
        values = [r[col] for r in rows]
        cardinality = len(set(values))
        if cardinality > n / 2 or cardinality < 2:
            continue
        # Estima ganho por sort
        sorted_runs = count_runs(sorted([str(v) for v in values]))
        unsorted_runs = count_runs([str(v) for v in values])
        gain = unsorted_runs - sorted_runs
        candidates.append((col, gain, cardinality))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return candidates[0][0]


def count_runs(values):
    if not values:
        return 0
    runs = 1
    for i in range(1, len(values)):
        if values[i] != values[i - 1]:
            runs += 1
    return runs


def rle_line(values):
    """Retorna lista de strings com RLE aplicado."""
    if not values:
        return []
    out = []
    cur = values[0]
    cnt = 1
    for v in values[1:]:
        if v == cur:
            cnt += 1
        else:
            out.append(f"{cnt}*{cur}" if cnt > 1 else str(cur))
            cur, cnt = v, 1
    out.append(f"{cnt}*{cur}" if cnt > 1 else str(cur))
    return out


def encode_tcf_compact(rows, name="t"):
    """TCF compact: RLE + sort automatico. Sem DICT, sem cross, sem key-elim."""
    if not rows:
        return ""
    sort_col = best_sort_col(rows)
    if sort_col:
        rows = sorted(rows, key=lambda r: str(r[sort_col]))

    out = [f"# TCF v0.4 lv=compact"]
    sort_text = f" sort_by={sort_col}" if sort_col else ""
    out.append(f"## {name} n={len(rows)}{sort_text}")
    cols = list(rows[0].keys())
    for col in cols:
        out.append(f"{col}:")
        values = [str(r[col]) for r in rows]
        out.extend(rle_line(values))
    return "\n".join(out) + "\n"


def encode_tcf_smart(rows, name="t", schema=None,
                      cross_resolved=None):
    """TCF smart: auto-tudo (E + H + I + DICT inline + auto-bypass)."""
    if not rows:
        return ""
    schema = schema or {}
    cross_resolved = cross_resolved or {}

    cols = list(rows[0].keys())
    string_cols = detect_string_cols(rows)
    n = len(rows)

    pk_col = schema.get("pk")
    pk_eliminated = pk_col and detect_pk_grade2(rows, pk_col)

    # Sort_by automatico (excluindo PK se eliminada)
    candidate_rows = rows
    sort_col = best_sort_col(rows)
    if sort_col and sort_col != pk_col:
        candidate_rows = sorted(rows, key=lambda r: str(r[sort_col]))

    flags = []
    if pk_eliminated:
        flags.append(f"pk_eliminated={pk_col}")
    if sort_col and sort_col != pk_col:
        flags.append(f"sort_by={sort_col}")
    flag_text = " " + " ".join(flags) if flags else ""

    out = [f"# TCF v0.4 lv=smart"]
    out.append(f"## {name} n={n}{flag_text}")

    out_cols = [c for c in cols if c != pk_col or not pk_eliminated]

    for col in out_cols:
        values = [str(r[col]) for r in candidate_rows]
        unique = sorted(set(values))
        cardinality = len(unique)

        # Cross-DICT
        if (name, col) in cross_resolved:
            dname, idx_map = cross_resolved[(name, col)]
            out.append(f"{col}: dict_ref={dname}")
            out.extend(rle_line([str(idx_map[v]) for v in values]))
            continue

        # Affix
        if col in string_cols and cardinality >= n / 2:
            prefix = detect_affix(values)
            if len(prefix) >= 4:
                out.append(f"{col}: affix=\"{prefix}\"")
                processed = [v[len(prefix):] if v.startswith(prefix)
                              else "\\!" + v
                              for v in values]
                out.extend(rle_line(processed))
                continue

        # DICT inline (D16) com auto-bypass
        if col in string_cols and cardinality < n / 2:
            out.append(f"{col}: dict={','.join(unique)}")
            idx_map = {v: i for i, v in enumerate(unique)}
            out.extend(rle_line([str(idx_map[v]) for v in values]))
            continue

        # Bypass + RLE para tipos nao-string ou cardinality alta
        out.append(f"{col}:")
        out.extend(rle_line(values))

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("EXP-003b — TCF modes + gzip (HP-T1 decisor principal)")
    print("=" * 90)

    datasets = get_datasets()

    # Cross-DICTs entre datasets nao se aplicam (sao tabelas separadas).
    # Cross dentro de uma mesma tabela:
    cross_per_dataset = {}
    for ds in datasets:
        cross = detect_cross_dicts({ds["name"]: ds["rows"]}, threshold=0.5)
        # Resolve para o smart usar
        resolved = {}
        for dname, info in cross.items():
            idx_map = {v: i for i, v in enumerate(info["vocab"])}
            for tcol in info["cols"]:
                resolved[tcol] = (dname, idx_map)
        cross_per_dataset[ds["name"]] = (cross, resolved)

    print(f"\n  {'dataset':<22} {'csv':>8} {'csv+gz':>8} {'raw':>8} "
          f"{'raw+gz':>8} {'compact':>9} {'comp+gz':>9} "
          f"{'smart':>9} {'smt+gz':>9}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*9} "
          f"{'-'*9} {'-'*9} {'-'*9}")

    results = []
    for ds in datasets:
        name = ds["name"]
        rows = ds["rows"]
        if not rows:
            continue
        cross_info, cross_resolved = cross_per_dataset[name]

        # Encode em 4 estrategias
        text_csv = encode_csv(rows)
        text_raw = encode_tcf_raw(rows, name)
        text_compact = encode_tcf_compact(rows, name)
        text_smart = encode_tcf_smart(rows, name, schema=ds["schema"],
                                        cross_resolved=cross_resolved)

        b_csv = len(text_csv.encode("utf-8"))
        b_raw = len(text_raw.encode("utf-8"))
        b_compact = len(text_compact.encode("utf-8"))
        b_smart = len(text_smart.encode("utf-8"))

        # gzip de cada
        gz_csv = len(gzip.compress(text_csv.encode("utf-8"), compresslevel=9))
        gz_raw = len(gzip.compress(text_raw.encode("utf-8"), compresslevel=9))
        gz_compact = len(gzip.compress(text_compact.encode("utf-8"), compresslevel=9))
        gz_smart = len(gzip.compress(text_smart.encode("utf-8"), compresslevel=9))

        print(f"  {name:<22} {b_csv:>8} {gz_csv:>8} {b_raw:>8} {gz_raw:>8} "
              f"{b_compact:>9} {gz_compact:>9} {b_smart:>9} {gz_smart:>9}")

        # Salva arquivos
        (RESULTS / f"{name}-1-csv.txt").write_text(text_csv, encoding="utf-8")
        (RESULTS / f"{name}-2-tcf-raw.txt").write_text(text_raw, encoding="utf-8")
        (RESULTS / f"{name}-3-tcf-compact.txt").write_text(text_compact, encoding="utf-8")
        (RESULTS / f"{name}-4-tcf-smart.txt").write_text(text_smart, encoding="utf-8")
        for fname, content in [
            (f"{name}-1-csv.gz", text_csv.encode("utf-8")),
            (f"{name}-2-tcf-raw.gz", text_raw.encode("utf-8")),
            (f"{name}-3-tcf-compact.gz", text_compact.encode("utf-8")),
            (f"{name}-4-tcf-smart.gz", text_smart.encode("utf-8")),
        ]:
            (RESULTS / fname).write_bytes(gzip.compress(content, compresslevel=9))

        results.append({
            "dataset": name,
            "n_rows": len(rows),
            "n_cols": len(rows[0]),
            "bytes": {
                "csv": b_csv, "csv_gz": gz_csv,
                "tcf_raw": b_raw, "tcf_raw_gz": gz_raw,
                "tcf_compact": b_compact, "tcf_compact_gz": gz_compact,
                "tcf_smart": b_smart, "tcf_smart_gz": gz_smart,
            },
            "decisions": {
                "cross_dicts": list(cross_info.keys()),
                "pk_eliminated": ds["schema"].get("pk")
                                  if detect_pk_grade2(rows, ds["schema"].get("pk")) else None,
                "sort_by": best_sort_col(rows),
            },
        })

    # ---- Sintese: gain de smart+gz vs compact+gz ----
    print("\n" + "=" * 90)
    print("Sintese — HP-T1 (smart+gz vs compact+gz)")
    print("=" * 90)
    print()
    print(f"  {'dataset':<22} {'csv+gz':>8} {'raw+gz':>8} {'comp+gz':>8} "
          f"{'smt+gz':>8} {'smt vs comp':>12} {'smt vs csv':>12}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*12} {'-'*12}")

    for r in results:
        b = r["bytes"]
        smt_vs_comp = (b["tcf_smart_gz"] / b["tcf_compact_gz"] - 1) * 100
        smt_vs_csv = (b["tcf_smart_gz"] / b["csv_gz"] - 1) * 100
        sign1 = "+" if smt_vs_comp > 0 else ""
        sign2 = "+" if smt_vs_csv > 0 else ""
        print(f"  {r['dataset']:<22} {b['csv_gz']:>8} {b['tcf_raw_gz']:>8} "
              f"{b['tcf_compact_gz']:>8} {b['tcf_smart_gz']:>8} "
              f"{sign1}{smt_vs_comp:>+10.1f}% {sign2}{smt_vs_csv:>+10.1f}%")

    print()
    smt_vs_comp_avg = sum((r["bytes"]["tcf_smart_gz"] / r["bytes"]["tcf_compact_gz"] - 1) * 100
                          for r in results) / len(results)
    smt_vs_csv_avg = sum((r["bytes"]["tcf_smart_gz"] / r["bytes"]["csv_gz"] - 1) * 100
                         for r in results) / len(results)
    print(f"  Avg smart+gz vs compact+gz: {smt_vs_comp_avg:+.2f}%")
    print(f"  Avg smart+gz vs csv+gz:     {smt_vs_csv_avg:+.2f}%")

    # ---- Decisao em cascata ----
    print("\n" + "=" * 90)
    print("Decisao em cascata (criterio de pivot)")
    print("=" * 90)
    if smt_vs_comp_avg < -15:
        print(f"  CAMINHO A: smart+gz vence compact+gz por {smt_vs_comp_avg:.1f}%")
        print(f"  → vale implementar E/H/I no Sprint 1+2")
    elif abs(smt_vs_comp_avg) < 5:
        print(f"  CAMINHO B: smart+gz ≈ compact+gz (diff {smt_vs_comp_avg:+.1f}%)")
        print(f"  → compact basta como default; E/H/I viram opt-in v0.4.x")
    elif smt_vs_comp_avg > 0:
        print(f"  ATENCAO: smart+gz PIOR que compact+gz (diff {smt_vs_comp_avg:+.1f}%)")
        print(f"  → revisar Propostas; provavel bug ou interferencia com gzip")
    else:
        print(f"  INTERMEDIARIO: smart+gz vence compact+gz por {smt_vs_comp_avg:.1f}%")
        print(f"  → discussao caso a caso; ver dataset-por-dataset")

    # ---- Salva ----
    out = {
        "experiment": "EXP-003b-tcf-vs-gzip",
        "results": results,
        "summary": {
            "avg_smart_vs_compact_gz_pct": smt_vs_comp_avg,
            "avg_smart_vs_csv_gz_pct": smt_vs_csv_avg,
        },
    }
    (RESULTS / "results.json").write_text(json.dumps(out, indent=2),
                                            encoding="utf-8")
    print(f"\n  Resultados: {RESULTS / 'results.json'}")


if __name__ == "__main__":
    main()
