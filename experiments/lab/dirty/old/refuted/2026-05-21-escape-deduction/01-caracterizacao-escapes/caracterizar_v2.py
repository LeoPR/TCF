"""Caracterizacao v2 — adiciona H-ED-original (valor > count).

H-ED-original: um digit-run literal com valor V e' deduzivel se
V > current_node_count no momento do emit. Decoder rastreia count
crescendo conforme parse.

Pra simplicidade, usamos APROXIMACAO conservadora:
- N_atoms_max = numero total de atoms na coluna
- Digit-run com valor V > N_atoms_max e' DEFINITIVAMENTE deduzivel
  (count nunca passa N_atoms_max)
- Lower bound do ganho real (real seria > este, ate' upper bound = H-ED-01).
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


def count_escapes_v2(body_text, n_atoms_max):
    """v2: adiciona contagem de \\digit-runs com valor > n_atoms_max.

    Lower bound de H-ED-original (count cresce ate' n_atoms_max,
    qualquer V > esse limite e' deduzivel SEMPRE).
    """
    lines = body_text.split('\n')
    stats = {
        'total_escapes_digits': 0,
        'total_escapes_ops': 0,
        'h_ed_01_line1_digits': 0,
        'h_ed_01_line1_ops': 0,
        'h_ed_02_after_sep_digits': 0,
        'h_ed_original_value_gt_max': 0,  # NOVO
        'sum_bytes_digit_escapes': 0,  # apenas o `\` (1 byte)
        'bytes_savable_h_ed_01': 0,
        'bytes_savable_h_ed_02': 0,
        'bytes_savable_h_ed_original': 0,  # NOVO
    }
    for li, line in enumerate(lines):
        i = 0
        prev_was_sep = False
        while i < len(line):
            if line[i] == '\\':
                if i + 1 < len(line):
                    next_c = line[i + 1]
                    if next_c.isdigit():
                        # extract digit value
                        j = i + 2
                        while j < len(line) and line[j].isdigit():
                            j += 1
                        digit_str = line[i + 1:j]
                        try:
                            value = int(digit_str)
                        except ValueError:
                            value = 0
                        stats['total_escapes_digits'] += 1
                        stats['sum_bytes_digit_escapes'] += 1
                        if li == 0:
                            stats['h_ed_01_line1_digits'] += 1
                            stats['bytes_savable_h_ed_01'] += 1
                        elif prev_was_sep:
                            stats['h_ed_02_after_sep_digits'] += 1
                            stats['bytes_savable_h_ed_02'] += 1
                        # H-ED-original: valor > n_atoms_max → deduzivel
                        if value > n_atoms_max:
                            stats['h_ed_original_value_gt_max'] += 1
                            stats['bytes_savable_h_ed_original'] += 1
                        i = j
                        prev_was_sep = False
                        continue
                    elif next_c in ('*', '\\', '~'):
                        stats['total_escapes_ops'] += 1
                        if li == 0:
                            stats['h_ed_01_line1_ops'] += 1
                            stats['bytes_savable_h_ed_01'] += 1
                        i += 2
                        prev_was_sep = False
                        continue
            if line[i] == '*':
                prev_was_sep = True
            else:
                prev_was_sep = False
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


def n_atoms_in_col(values):
    """Numero aproximado de atoms = unicas (cada unica gera ~1 atom no HCC).

    Aproximacao conservadora — real n_atoms pode ser maior se houver
    fragmentation. Pra lower bound H-ED-original isso e' OK
    (subestima count → poucos digit-runs marcados deduziveis;
    real impl teria MAIS deduziveis).
    """
    return len(dedup_preserve_order(values))


def analyze_single_col(name, linhas):
    tcf = encode(linhas)
    raw = tcf.encode("utf-8")
    nl = raw.find(b"\n")
    body = raw[nl + 1:].decode("utf-8")
    n_atoms = n_atoms_in_col(linhas)
    stats = count_escapes_v2(body, n_atoms)
    bytes_total = len(raw)
    bytes_body = len(body.encode("utf-8"))
    return {
        "dataset": name, "n_cols": 1,
        "bytes_total": bytes_total, "bytes_body": bytes_body,
        "n_atoms_total": n_atoms,
        **stats,
    }


def analyze_multi_col(label, cols):
    tcf_text, info = encode_table(cols)
    bodies = split_multi_col_body(tcf_text)
    if not bodies:
        return None
    total = {
        'total_escapes_digits': 0, 'total_escapes_ops': 0,
        'h_ed_01_line1_digits': 0, 'h_ed_01_line1_ops': 0,
        'h_ed_02_after_sep_digits': 0,
        'h_ed_original_value_gt_max': 0,
        'sum_bytes_digit_escapes': 0,
        'bytes_savable_h_ed_01': 0,
        'bytes_savable_h_ed_02': 0,
        'bytes_savable_h_ed_original': 0,
    }
    bytes_body = 0
    n_atoms_total = 0
    for cname, body in bodies:
        n_atoms = n_atoms_in_col(cols[cname])
        n_atoms_total += n_atoms
        s = count_escapes_v2(body, n_atoms)
        for k in total:
            total[k] += s[k]
        bytes_body += len(body.encode("utf-8"))
    bytes_total = len(tcf_text.encode("utf-8"))
    return {
        "dataset": label, "n_cols": len(cols),
        "bytes_total": bytes_total, "bytes_body": bytes_body,
        "n_atoms_total": n_atoms_total,
        **total,
    }


def main():
    print("=== Caracterizacao v2: H-ED-01/02/original ===\n")

    results = []

    print(">> D1-D9")
    datasets_dir = ROOT / "datasets" / "synthetic"
    for name in D1_D9:
        linhas = ler_csv(datasets_dir / f"{name}.csv")
        r = analyze_single_col(name, linhas)
        results.append(r)

    print(">> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        r = analyze_multi_col(f"adult-{vol}", rows_to_cols(rows))
        if r:
            results.append(r)
    reader.close()

    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        r = analyze_multi_col(f"tpch.{table}-5k", rows_to_cols(rows))
        if r:
            results.append(r)
    reader.close()

    # Tabela
    print("\n=== Tabela consolidada ===\n")
    print(f"{'dataset':<25} {'body':>10} {'esc_d':>6} {'atoms':>6} "
          f"{'H-01':>5} {'H-02':>5} {'H-orig':>7} {'orig %':>8}")
    print("-" * 80)
    for r in results:
        pct_orig = r['bytes_savable_h_ed_original'] / r['bytes_body'] * 100 if r['bytes_body'] else 0
        print(f"{r['dataset']:<25} {r['bytes_body']:>10,} {r['total_escapes_digits']:>6} "
              f"{r['n_atoms_total']:>6} {r['bytes_savable_h_ed_01']:>5} "
              f"{r['bytes_savable_h_ed_02']:>5} {r['bytes_savable_h_ed_original']:>7} "
              f"{pct_orig:>7.2f}%")

    # Aggregate
    total_body = sum(r["bytes_body"] for r in results)
    total_esc = sum(r['total_escapes_digits'] for r in results)
    total_sav_01 = sum(r['bytes_savable_h_ed_01'] for r in results)
    total_sav_02 = sum(r['bytes_savable_h_ed_02'] for r in results)
    total_sav_orig = sum(r['bytes_savable_h_ed_original'] for r in results)

    print(f"\n{'TOTAL':<25} {total_body:>10,} {total_esc:>6} "
          f"{'':>6} {total_sav_01:>5} {total_sav_02:>5} {total_sav_orig:>7} "
          f"{total_sav_orig/total_body*100:>7.2f}%")

    # Report
    report = [
        "# Sub-exp 01 v2 — caracterizacao escapes (com H-ED-original)",
        "",
        "## Tabela completa",
        "",
        "| dataset | n_cols | body | digits_esc | atoms | H-ED-01 | H-ED-02 | **H-ED-original** | orig % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        pct_orig = r['bytes_savable_h_ed_original'] / r['bytes_body'] * 100 if r['bytes_body'] else 0
        report.append(
            f"| {r['dataset']} | {r['n_cols']} | {r['bytes_body']:,} | "
            f"{r['total_escapes_digits']} | {r['n_atoms_total']} | "
            f"{r['bytes_savable_h_ed_01']} | {r['bytes_savable_h_ed_02']} | "
            f"**{r['bytes_savable_h_ed_original']}** | {pct_orig:.2f}% |"
        )

    report.extend([
        "",
        "## Agregado",
        "",
        f"- Total body: {total_body:,}B",
        f"- Total digit escapes: {total_esc}",
        f"- H-ED-01 savable: {total_sav_01}B ({total_sav_01/total_body*100:.2f}%)",
        f"- H-ED-02 savable: {total_sav_02}B ({total_sav_02/total_body*100:.2f}%)",
        f"- **H-ED-original savable**: {total_sav_orig}B "
        f"({total_sav_orig/total_body*100:.2f}%) ← lower bound",
        "",
        "## Interpretacao",
        "",
        "**H-ED-original** captura digit-runs cujo valor > n_atoms_total da",
        "coluna. Esse e' LOWER BOUND — implementacao real (count crescendo",
        "linha-a-linha) detectaria MAIS (count_at_emit < n_atoms_total na",
        "maioria das emissoes).",
        "",
        "Se H-ED-original lower bound >= 1%, vale prosseguir pra sub-exp 02",
        "(implementacao). Senao, fechar Pacote 2 como insuficiente em real-world.",
        "",
    ])

    out = THIS / "result_v2.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult_v2.md: {out}")


if __name__ == "__main__":
    main()
