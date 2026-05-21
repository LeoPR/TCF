"""Caracteriza escapes no encode HCC em datasets variados.

Conta:
- N escapes total
- H-ED-01 candidatos (linha 1 do body — count=0)
- H-ED-02 candidatos (digit-run apos `*` separator — lit context)
- H-ED-03 candidatos (estimativa rough)

Para cada coluna individualmente. Tabela consolidada por dataset.
"""

from __future__ import annotations

import csv
import io
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = ROOT / "experiments" / "lab" / "clean" / "EXP-011-multi-column-basic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode  # noqa: E402
from multi_col import encode_table  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def count_escapes_in_body(body_text):
    """Conta escapes em body single-col. Retorna dict por categoria."""
    lines = body_text.split('\n')
    stats = {
        'total_escapes_digits': 0,
        'total_escapes_ops': 0,
        'h_ed_01_line1_digits': 0,
        'h_ed_01_line1_ops': 0,
        'h_ed_02_after_sep_digits': 0,
        'other_digits': 0,
        'other_ops': 0,
        'bytes_savable_h_ed_01': 0,  # 1 byte por escape removido
        'bytes_savable_h_ed_02': 0,
    }
    for li, line in enumerate(lines):
        i = 0
        prev_was_sep = False
        while i < len(line):
            if line[i] == '\\':
                if i + 1 < len(line):
                    next_c = line[i + 1]
                    if next_c.isdigit():
                        # digit run escape
                        stats['total_escapes_digits'] += 1
                        if li == 0:
                            stats['h_ed_01_line1_digits'] += 1
                            stats['bytes_savable_h_ed_01'] += 1
                        elif prev_was_sep:
                            stats['h_ed_02_after_sep_digits'] += 1
                            stats['bytes_savable_h_ed_02'] += 1
                        else:
                            stats['other_digits'] += 1
                        # skip digit-run
                        j = i + 2
                        while j < len(line) and line[j].isdigit():
                            j += 1
                        i = j
                        prev_was_sep = False
                        continue
                    elif next_c in ('*', '\\', '~'):
                        stats['total_escapes_ops'] += 1
                        if li == 0:
                            stats['h_ed_01_line1_ops'] += 1
                            stats['bytes_savable_h_ed_01'] += 1
                        else:
                            stats['other_ops'] += 1
                        i += 2
                        prev_was_sep = False
                        continue
            # not escape
            if line[i] == '*':
                prev_was_sep = True
            elif line[i] not in (',', '~', '\n', ' '):
                # any literal char (ou outro op) reseta o flag
                # Convention: prev_was_sep so' se ULTIMO char foi *
                prev_was_sep = (line[i] == '*')
            i += 1
    return stats


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def split_multi_col_body(tcf_text):
    """Multi-col tcf: '#TCF.6 M\\n# size=name,...\\n<body_concat>'.
    Retorna lista de (col_name, body_text)."""
    raw = tcf_text.encode("utf-8")
    nl1 = raw.find(b"\n")
    nl2 = raw.find(b"\n", nl1 + 1)
    meta = raw[nl1 + 1:nl2].decode("utf-8")
    if not meta.startswith("# "):
        return None
    pairs = []
    for p in meta[2:].split(","):
        size_str, name = p.split("=", 1)
        pairs.append((int(size_str), name))
    cursor = nl2 + 1
    bodies = []
    for size, name in pairs:
        body_bytes = raw[cursor:cursor + size]
        bodies.append((name, body_bytes.decode("utf-8")))
        cursor += size
    return bodies


def analyze_single_col(name, linhas):
    """Pra D1-D9: single-col com shebang `#TCF.6` + body."""
    tcf = encode(linhas)
    # split header (shebang)
    raw = tcf.encode("utf-8")
    nl = raw.find(b"\n")
    body = raw[nl + 1:].decode("utf-8")
    bytes_total = len(raw)
    bytes_header = nl + 1
    bytes_body = len(body.encode("utf-8"))
    stats = count_escapes_in_body(body)
    return {
        "dataset": name,
        "n_cols": 1,
        "bytes_total": bytes_total,
        "bytes_body": bytes_body,
        **stats,
    }


def analyze_multi_col(label, cols):
    """Multi-col table: sum stats per coluna."""
    tcf_text, info = encode_table(cols)
    bodies = split_multi_col_body(tcf_text)
    if not bodies:
        return None
    total = {
        'total_escapes_digits': 0, 'total_escapes_ops': 0,
        'h_ed_01_line1_digits': 0, 'h_ed_01_line1_ops': 0,
        'h_ed_02_after_sep_digits': 0,
        'other_digits': 0, 'other_ops': 0,
        'bytes_savable_h_ed_01': 0, 'bytes_savable_h_ed_02': 0,
    }
    bytes_body = 0
    for cname, body in bodies:
        s = count_escapes_in_body(body)
        for k in total:
            total[k] += s[k]
        bytes_body += len(body.encode("utf-8"))
    bytes_total = len(tcf_text.encode("utf-8"))
    return {
        "dataset": label,
        "n_cols": len(cols),
        "bytes_total": bytes_total,
        "bytes_body": bytes_body,
        **total,
    }


def fmt_row(r):
    total_esc = r['total_escapes_digits'] + r['total_escapes_ops']
    sav_01 = r['bytes_savable_h_ed_01']
    sav_02 = r['bytes_savable_h_ed_02']
    pct_01 = sav_01 / r['bytes_body'] * 100 if r['bytes_body'] else 0
    pct_02 = sav_02 / r['bytes_body'] * 100 if r['bytes_body'] else 0
    pct_total = (sav_01 + sav_02) / r['bytes_body'] * 100 if r['bytes_body'] else 0
    return (
        f"| {r['dataset']} | {r['n_cols']} | {r['bytes_total']:,} | "
        f"{r['bytes_body']:,} | "
        f"{total_esc} ({r['total_escapes_digits']}d/{r['total_escapes_ops']}o) | "
        f"{sav_01} ({pct_01:.1f}%) | "
        f"{sav_02} ({pct_02:.1f}%) | "
        f"{sav_01 + sav_02} ({pct_total:.1f}%) |"
    )


def main():
    print("=== Caracterizacao escapes em encode HCC ===\n")

    results = []

    # D1-D9
    print(">> D1-D9 (controle, single-col)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    for name in D1_D9:
        linhas = ler_csv(datasets_dir / f"{name}.csv")
        r = analyze_single_col(name, linhas)
        results.append(r)
        print(f"  {name}: body={r['bytes_body']}B, escapes={r['total_escapes_digits']+r['total_escapes_ops']}, "
              f"H-ED-01 savable={r['bytes_savable_h_ed_01']}, H-ED-02 savable={r['bytes_savable_h_ed_02']}")

    # Adult Census 1k + 5k
    print("\n>> Adult Census")
    try:
        reader = DatasetReader("adult-census")
        for vol in [1000, 5000]:
            rows = reader.rows("adult", limit=vol)
            cols = rows_to_cols(rows)
            r = analyze_multi_col(f"adult-{vol}", cols)
            if r:
                results.append(r)
                print(f"  adult-{vol}: body={r['bytes_body']:,}B, escapes={r['total_escapes_digits']+r['total_escapes_ops']}, "
                      f"savable={r['bytes_savable_h_ed_01']+r['bytes_savable_h_ed_02']}")
        reader.close()
    except Exception as e:
        print(f"  ERROR: {e}")

    # TPC-H 3 tabelas
    print("\n>> TPC-H selected")
    try:
        reader = DatasetReader("tpch-sf001")
        for table in ["region", "customer", "lineitem"]:
            rows = reader.rows(table, limit=5000)
            cols = rows_to_cols(rows)
            r = analyze_multi_col(f"tpch.{table}-5k", cols)
            if r:
                results.append(r)
                print(f"  tpch.{table}-5k: body={r['bytes_body']:,}B, "
                      f"escapes={r['total_escapes_digits']+r['total_escapes_ops']}, "
                      f"savable={r['bytes_savable_h_ed_01']+r['bytes_savable_h_ed_02']}")
        reader.close()
    except Exception as e:
        print(f"  ERROR: {e}")

    # Report
    print("\n=== Tabela consolidada ===\n")
    report = [
        "# Sub-exp 01 — caracterizacao escapes (resultado)",
        "",
        "| dataset | n_cols | total | body | escapes | sav H-ED-01 | sav H-ED-02 | sav total |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        report.append(fmt_row(r))
        print(fmt_row(r))

    # Aggregate
    total_body = sum(r["bytes_body"] for r in results)
    total_esc = sum(r['total_escapes_digits'] + r['total_escapes_ops']
                    for r in results)
    total_sav_01 = sum(r['bytes_savable_h_ed_01'] for r in results)
    total_sav_02 = sum(r['bytes_savable_h_ed_02'] for r in results)

    report.extend([
        "",
        "## Agregado",
        "",
        f"- Total body: {total_body:,}B",
        f"- Total escapes: {total_esc}",
        f"- Savable H-ED-01 (linha 1): {total_sav_01} bytes ({total_sav_01/total_body*100:.2f}%)",
        f"- Savable H-ED-02 (apos sep): {total_sav_02} bytes ({total_sav_02/total_body*100:.2f}%)",
        f"- **Savable combinado**: {total_sav_01 + total_sav_02} bytes "
        f"({(total_sav_01 + total_sav_02)/total_body*100:.2f}%)",
        "",
        "## Analise",
        "",
        "*(preencher apos rodar)*",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")
    print(f"Aggregate savable: {total_sav_01 + total_sav_02} bytes "
          f"= {(total_sav_01 + total_sav_02)/total_body*100:.2f}% do body")


if __name__ == "__main__":
    main()
