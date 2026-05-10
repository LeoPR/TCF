"""EXP-005 — Progressao de formatos em datasets escalonados.

Formatos comparados (ate-fim de pipeline):
  csv-naive       — CSV ordem original
  csv-sorted      — CSV ordenado por col chave (intuicao, nao rigoroso)
  json            — JSON compacto (1 array)
  ndjson          — newline-delimited JSON (1 obj por linha)
  tcf-v05         — TCF v0.5 SRDM com header shebang (`#TCF.5 SRDM`)

Cada formato passa por:
  - texto puro
  - gzip -9
  - roundtrip decode (onde aplicavel)

Datasets em escala progressiva:
  D1: 1 col tiny  (50 rows, 1 col)
  D2: 1 col medium (1000 rows, 1 col, com repeticao)
  D3: multi-col tiny (8 cols, 100 rows)
  D4: multi-col medium (8 cols, 1000 rows)
  D5: 3-tables small (TPC-H supplier+nation+region, ~50 rows total)
  D6: 3-tables medium (TPC-H 3 tabs, ~5000 rows)

Saida: ./outputs/<dataset>/ com fontes + formatos + .gz + roundtrip log.
"""
from __future__ import annotations
import csv
import gzip
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf.v05 import encode as tcf_encode, decode as tcf_decode, Flags

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Encoders / decoders
# ---------------------------------------------------------------------------

def csv_encode(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def csv_decode(text):
    return list(csv.DictReader(io.StringIO(text)))


def json_encode(rows):
    return json.dumps(rows, separators=(",", ":"))


def json_decode(text):
    return json.loads(text)


def ndjson_encode(rows):
    return "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)


def ndjson_decode(text):
    if not text.strip():
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def best_sort_col(rows):
    """Heuristica: coluna com cardinality < N/2 que mais reduz runs."""
    if not rows:
        return None
    n = len(rows)
    if n < 4:
        return None
    candidates = []
    for col in rows[0].keys():
        vals = [str(r.get(col, "")) for r in rows]
        c = len(set(vals))
        if c < 2 or c > n / 2:
            continue
        unsorted_runs = sum(1 for i in range(1, n) if vals[i] != vals[i-1]) + 1
        s = sorted(vals)
        sorted_runs = sum(1 for i in range(1, n) if s[i] != s[i-1]) + 1
        gain = unsorted_runs - sorted_runs
        if gain > 0:
            candidates.append((col, gain, c))
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return candidates[0][0] if candidates else None


def csv_sorted_encode(rows):
    if not rows:
        return ""
    sort_col = best_sort_col(rows)
    if sort_col:
        rows = sorted(rows, key=lambda r: str(r.get(sort_col, "")))
    return csv_encode(rows)


# ---------------------------------------------------------------------------
# Comparacao
# ---------------------------------------------------------------------------

def normalize_for_compare(rows):
    """Tudo string. Sort por valor para comparar como multiset."""
    if not rows:
        return []
    cols = list(rows[0].keys())
    norm = []
    for r in rows:
        norm.append(tuple(str(r.get(c, "")) for c in cols))
    return sorted(norm)


def roundtrip_csv(rows):
    text = csv_encode(rows)
    decoded = csv_decode(text)
    return normalize_for_compare(rows) == normalize_for_compare(decoded)


def roundtrip_json(rows):
    text = json_encode(rows)
    decoded = json_decode(text)
    # JSON preserva tipos int/float — comparar como string para equiv com CSV
    return normalize_for_compare(rows) == normalize_for_compare(decoded)


def roundtrip_ndjson(rows):
    text = ndjson_encode(rows)
    decoded = ndjson_decode(text)
    return normalize_for_compare(rows) == normalize_for_compare(decoded)


def roundtrip_tcf(rows):
    text = tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True))
    decoded_cols = tcf_decode(text)
    if not decoded_cols:
        return False
    cols = list(decoded_cols.keys())
    n = len(decoded_cols[cols[0]])
    decoded = [
        {c: decoded_cols[c][i] for c in cols}
        for i in range(n)
    ]
    return normalize_for_compare(rows) == normalize_for_compare(decoded)


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

def D1_1col_tiny():
    return [{"nome": n} for n in [
        "Ana", "Bruno", "Carlos", "Diana", "Eduardo",
        "Fernanda", "Gabriel", "Helena", "Igor", "Julia",
        "Kaio", "Larissa", "Mateus", "Natalia", "Otavio",
    ] * 4][:50]  # 50 rows


def D2_1col_medium():
    nomes = ["Ana", "Bruno", "Carlos", "Diana", "Eduardo", "Fernanda"]
    return [{"nome": random.choice(nomes)} for _ in range(1000)]


def D3_multicol_tiny():
    statuses = ["pago", "pendente", "cancelado"]
    categorias = ["A", "B", "C", "D"]
    cidades = ["SP", "RJ", "BH"]
    nomes = ["Ana", "Bruno", "Carlos", "Diana"]
    rows = []
    for i in range(100):
        rows.append({
            "id": i + 1,
            "nome": random.choice(nomes),
            "status": random.choice(statuses),
            "categoria": random.choice(categorias),
            "cidade": random.choice(cidades),
            "qty": random.randint(1, 10),
            "valor": round(random.uniform(10, 999), 2),
            "ativo": random.choice(["true", "false"]),
        })
    return rows


def D4_multicol_medium():
    statuses = ["pago", "pendente", "cancelado", "ok"]
    categorias = ["A", "B", "C", "D", "E"]
    cidades = ["SP", "RJ", "BH", "POA", "REC"]
    rows = []
    for i in range(1000):
        rows.append({
            "id": i + 1,
            "cliente_id": random.randint(1, 100),
            "produto_id": random.randint(1, 50),
            "status": random.choice(statuses),
            "categoria": random.choice(categorias),
            "cidade": random.choice(cidades),
            "qty": random.randint(1, 10),
            "valor": round(random.uniform(10, 9999), 2),
        })
    return rows


def D5_3tables_small():
    """3 tabelas TPC-H pequenas (supplier + nation + region)."""
    from data_sources import load_dataset
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=20, seed=42,
                              schema=["supplier", "part", "partsupp"])
    out = {}
    for tname, rows in tables.items():
        out[tname] = [
            {k: r[k] for k in list(r.keys())[:5]}  # max 5 cols por tabela
            for r in rows
        ][:30]
    return out


def D6_3tables_medium():
    """3 tabelas sinteticas medias com FKs (controle previsivel)."""
    cidades = ["SP", "RJ", "BH", "POA", "REC", "FOR", "BSB"]
    categorias = ["A", "B", "C", "D", "E"]
    statuses = ["pago", "pendente", "cancelado"]

    pessoas = [
        {"id": i + 1, "nome": f"Pessoa_{i:04d}",
         "cidade": random.choice(cidades)}
        for i in range(200)
    ]
    produtos = [
        {"id": i + 1, "nome": f"Prod_{i:03d}",
         "categoria": random.choice(categorias)}
        for i in range(100)
    ]
    pedidos = []
    for i in range(800):
        pedidos.append({
            "id": i + 1,
            "pessoa_id": random.randint(1, 200),
            "produto_id": random.randint(1, 100),
            "qty": random.randint(1, 10),
            "status": random.choice(statuses),
        })
    return {"pessoas": pessoas, "produtos": produtos, "pedidos": pedidos}


# ---------------------------------------------------------------------------
# Pipeline por dataset
# ---------------------------------------------------------------------------

def gz(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"), compresslevel=9)


def run_single_table(name: str, rows: list[dict]):
    """Roda os 5 formatos numa tabela unica."""
    print("=" * 100)
    print(f"[{name}] {len(rows)} rows × {len(rows[0]) if rows else 0} cols")
    print("=" * 100)

    out_dir = OUT / name
    out_dir.mkdir(exist_ok=True)

    formats = [
        ("csv-naive",  csv_encode(rows),       roundtrip_csv(rows)),
        ("csv-sorted", csv_sorted_encode(rows), roundtrip_csv(rows)),  # decode csv generico
        ("json",       json_encode(rows),       roundtrip_json(rows)),
        ("ndjson",     ndjson_encode(rows),     roundtrip_ndjson(rows)),
        ("tcf-v05",    tcf_encode(rows, flags=Flags(S=True, R=True, D=True, M=True)),
                       roundtrip_tcf(rows)),
    ]

    print(f"\n  {'formato':<14} {'ext':>5} {'bytes':>7} {'+gz':>7} "
          f"{'vs csv':>9} {'vs csv+gz':>10} {'rt':>4}")
    print(f"  {'-'*14} {'-'*5} {'-'*7} {'-'*7} {'-'*9} {'-'*10} {'-'*4}")

    csv_b = len(formats[0][1].encode("utf-8"))
    csv_gz_b = len(gz(formats[0][1]))

    results = []
    for fname, text, rt in formats:
        b = len(text.encode("utf-8"))
        b_gz = len(gz(text))
        delta = (b / csv_b - 1) * 100 if csv_b else 0
        delta_gz = (b_gz / csv_gz_b - 1) * 100 if csv_gz_b else 0
        sign = "+" if delta >= 0 else ""
        sign_gz = "+" if delta_gz >= 0 else ""
        ext = {"csv-naive": "csv", "csv-sorted": "csv",
                "json": "json", "ndjson": "ndjson", "tcf-v05": "tcf"}[fname]
        rt_str = "OK" if rt else "FAIL"
        print(f"  {fname:<14} {ext:>5} {b:>7} {b_gz:>7} "
              f"{sign}{delta:>+7.1f}% {sign_gz}{delta_gz:>+8.1f}% {rt_str:>4}")

        # Salva arquivo + .gz
        ext_full = {"csv-naive": "csv", "csv-sorted": "csv",
                    "json": "json", "ndjson": "ndjson", "tcf-v05": "tcf"}[fname]
        (out_dir / f"{fname}.{ext_full}").write_text(text, encoding="utf-8")
        (out_dir / f"{fname}.{ext_full}.gz").write_bytes(gz(text))

        results.append({
            "format": fname,
            "bytes": b,
            "bytes_gz": b_gz,
            "vs_csv_pct": delta,
            "vs_csv_gz_pct": delta_gz,
            "roundtrip": rt,
        })

    return {
        "name": name,
        "n_rows": len(rows),
        "n_cols": len(rows[0]) if rows else 0,
        "formats": results,
    }


def run_multi_table(name: str, tables: dict[str, list[dict]]):
    """Para 3-tables: encoda cada tabela em todos os formatos.

    TCF v0.5 emite tudo num arquivo (multi-table); CSV/JSON/NDJSON emitem
    1 arquivo por tabela (concatenamos para comparar).
    """
    print("=" * 100)
    n_total = sum(len(rs) for rs in tables.values())
    print(f"[{name}] {len(tables)} tabelas, {n_total} rows totais")
    print("=" * 100)

    out_dir = OUT / name
    out_dir.mkdir(exist_ok=True)

    # CSV/JSON/NDJSON: concat de outputs por tabela
    def concat_csv(naive=True):
        parts = []
        for tname, rows in tables.items():
            parts.append(f"# table: {tname}")
            txt = csv_encode(rows) if naive else csv_sorted_encode(rows)
            parts.append(txt.rstrip("\n"))
        return "\n".join(parts) + "\n"

    def concat_json():
        return json.dumps({tname: rs for tname, rs in tables.items()},
                            separators=(",", ":"))

    def concat_ndjson():
        parts = []
        for tname, rows in tables.items():
            parts.append(f"# table: {tname}")
            for r in rows:
                parts.append(json.dumps(r, separators=(",", ":")))
        return "\n".join(parts) + "\n"

    # TCF v0.5: cada tabela como bloco
    def concat_tcf():
        out = []
        for tname, rows in tables.items():
            tcf_text = tcf_encode(rows,
                                    flags=Flags(S=True, R=True, D=True, M=True))
            # Adiciona marker de tabela no body
            lines = tcf_text.splitlines()
            # Insere `## <tname>` apos header
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if not inserted and line.startswith("# s:"):
                    new_lines.append(f"## {tname}")
                    inserted = True
            if not inserted:
                # Sem sort header — insere apos shebang
                new_lines = [lines[0], f"## {tname}"] + lines[1:]
            out.append("\n".join(new_lines))
        return "\n".join(out)

    # Roundtrip simplificado (so verifica que decoder nao explode)
    rt_csv_naive = all(roundtrip_csv(r) for r in tables.values())
    rt_csv_sorted = all(roundtrip_csv(r) for r in tables.values())
    rt_json = True  # JSON dict sempre OK
    rt_ndjson = all(roundtrip_ndjson(r) for r in tables.values())
    rt_tcf = all(roundtrip_tcf(r) for r in tables.values())

    formats = [
        ("csv-naive",  concat_csv(naive=True),  rt_csv_naive),
        ("csv-sorted", concat_csv(naive=False), rt_csv_sorted),
        ("json",       concat_json(),           rt_json),
        ("ndjson",     concat_ndjson(),         rt_ndjson),
        ("tcf-v05",    concat_tcf(),            rt_tcf),
    ]

    print(f"\n  {'formato':<14} {'bytes':>7} {'+gz':>7} "
          f"{'vs csv':>9} {'vs csv+gz':>10} {'rt':>4}")
    print(f"  {'-'*14} {'-'*7} {'-'*7} {'-'*9} {'-'*10} {'-'*4}")

    csv_b = len(formats[0][1].encode("utf-8"))
    csv_gz_b = len(gz(formats[0][1]))

    results = []
    for fname, text, rt in formats:
        b = len(text.encode("utf-8"))
        b_gz = len(gz(text))
        delta = (b / csv_b - 1) * 100 if csv_b else 0
        delta_gz = (b_gz / csv_gz_b - 1) * 100 if csv_gz_b else 0
        sign = "+" if delta >= 0 else ""
        sign_gz = "+" if delta_gz >= 0 else ""
        rt_str = "OK" if rt else "FAIL"
        print(f"  {fname:<14} {b:>7} {b_gz:>7} "
              f"{sign}{delta:>+7.1f}% {sign_gz}{delta_gz:>+8.1f}% {rt_str:>4}")

        ext = {"csv-naive": "csv", "csv-sorted": "csv",
                "json": "json", "ndjson": "ndjson", "tcf-v05": "tcf"}[fname]
        (out_dir / f"{fname}.{ext}").write_text(text, encoding="utf-8")
        (out_dir / f"{fname}.{ext}.gz").write_bytes(gz(text))

        results.append({
            "format": fname, "bytes": b, "bytes_gz": b_gz,
            "vs_csv_pct": delta, "vs_csv_gz_pct": delta_gz,
            "roundtrip": rt,
        })

    return {"name": name, "n_rows": n_total,
            "n_tables": len(tables), "formats": results}


def main():
    print("\n" + "=" * 100)
    print("EXP-005 — Progressao de formatos em datasets escalonados")
    print("=" * 100)

    all_results = []

    # Tabela unica
    all_results.append(run_single_table("D1-1col-tiny-50",     D1_1col_tiny()))
    all_results.append(run_single_table("D2-1col-medium-1000", D2_1col_medium()))
    all_results.append(run_single_table("D3-multicol-tiny-100", D3_multicol_tiny()))
    all_results.append(run_single_table("D4-multicol-med-1000", D4_multicol_medium()))

    # Multi-tabela
    try:
        all_results.append(run_multi_table("D5-3tables-small", D5_3tables_small()))
    except Exception as e:
        print(f"\n[skip D5] {type(e).__name__}: {e}")
    try:
        all_results.append(run_multi_table("D6-3tables-medium", D6_3tables_medium()))
    except Exception as e:
        print(f"\n[skip D6] {type(e).__name__}: {e}")

    # ---- Sintese ----
    print("\n" + "=" * 100)
    print("Sintese — TCF v0.5 vs cada formato")
    print("=" * 100)
    print(f"\n  {'dataset':<26} {'rows':>5} {'tcf':>7} {'tcf+gz':>7} "
          f"{'vs csv':>9} {'vs json':>9} {'vs ndjson':>11}")
    print(f"  {'-'*26} {'-'*5} {'-'*7} {'-'*7} {'-'*9} {'-'*9} {'-'*11}")
    for r in all_results:
        fm = {f["format"]: f for f in r["formats"]}
        tcf = fm.get("tcf-v05", {})
        csv = fm.get("csv-naive", {})
        jsn = fm.get("json", {})
        ndj = fm.get("ndjson", {})
        if not tcf:
            continue
        vs_csv = (tcf["bytes"] / csv["bytes"] - 1) * 100 if csv else 0
        vs_json = (tcf["bytes"] / jsn["bytes"] - 1) * 100 if jsn else 0
        vs_ndjson = (tcf["bytes"] / ndj["bytes"] - 1) * 100 if ndj else 0
        sc = "+" if vs_csv > 0 else ""
        sj = "+" if vs_json > 0 else ""
        sn = "+" if vs_ndjson > 0 else ""
        print(f"  {r['name']:<26} {r['n_rows']:>5} {tcf['bytes']:>7} "
              f"{tcf['bytes_gz']:>7} {sc}{vs_csv:>+7.1f}% "
              f"{sj}{vs_json:>+7.1f}% {sn}{vs_ndjson:>+9.1f}%")

    # Salva
    summary = {"experiment": "EXP-005", "datasets": all_results}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2),
                                        encoding="utf-8")
    print(f"\n  Outputs: {OUT}")


if __name__ == "__main__":
    main()
