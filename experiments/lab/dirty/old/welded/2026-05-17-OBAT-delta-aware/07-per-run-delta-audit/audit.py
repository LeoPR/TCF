"""Audit: identifica pares qualificaveis pra per-run delta encoding.

Critierios:
- mesmo length
- runs em mesmas posicoes (runs_a == runs_b)
- NEM todas runs tem mesmo delta (caso contrario detector atual pega)
- pelo menos UMA run tem delta != 0 (ha' algo pra encodar)

Reporta por dataset + total.
"""

from __future__ import annotations

import sys
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
HCC_FORK_DIR = LAB / "02-hcc-sozinho-rle-near-identical"
sys.path.insert(0, str(HCC_FORK_DIR))

from hcc_fork import find_escape_digit_runs  # noqa: E402


# Source de bodies pra auditar
SOURCES = [
    # (label, sub-exp dir, dataset)
    ("D11a (fork+fork)", "04-obat-shape-consistency-hint", "D11a-datas-dia"),
    ("D11b (fork+fork)", "04-obat-shape-consistency-hint", "D11b-datas-borda"),
    ("D11c (fork+fork)", "04-obat-shape-consistency-hint", "D11c-datas-mensal"),
    ("D11d (fork+fork)", "04-obat-shape-consistency-hint", "D11d-datetime-min"),
    ("D11e (fork+fork)", "04-obat-shape-consistency-hint", "D11e-datetime-mensal"),
    ("D11f (fork+fork)", "04-obat-shape-consistency-hint", "D11f-datetime-ms"),
    ("D11g (fork+fork)", "04-obat-shape-consistency-hint", "D11g-datetime-us"),
    ("D11h (fork+fork)", "04-obat-shape-consistency-hint", "D11h-datetime-ns"),
    ("D16a (fork+fork)", "05-numeric-ids-h-da-06", "D16a-ids-3digits"),
    ("D16b (fork+fork)", "05-numeric-ids-h-da-06", "D16b-ids-4digits"),
    ("D16c (fork+fork)", "05-numeric-ids-h-da-06", "D16c-ids-prefixados"),
]


def is_compacted_marker(line):
    if not line.startswith("*"):
        return False
    return "|" in line


def check_per_run_delta(line_a, line_b):
    """Retorna (qualifica?, runs_info, motivo)."""
    if len(line_a) != len(line_b):
        return False, None, "lengths diferem"
    runs_a = find_escape_digit_runs(line_a)
    runs_b = find_escape_digit_runs(line_b)
    if runs_a != runs_b:
        return False, None, "runs em posicoes diferentes"
    if not runs_a:
        return False, None, "sem escape-digit runs"
    deltas = []
    for s, e in runs_a:
        a_int = int(line_a[s:e])
        b_int = int(line_b[s:e])
        deltas.append(b_int - a_int)
    # Detector atual ja' pega se todos deltas iguais
    if len(set(deltas)) == 1:
        # Detector atual ja' compactou
        return False, runs_a, f"detector atual ja' pega (delta uniforme {deltas[0]})"
    # Pelo menos uma run mudou (delta != 0)?
    if all(d == 0 for d in deltas):
        return False, runs_a, "nenhuma run mudou"
    # Qualifica!
    return True, runs_a, f"runs deltas mixtos: {deltas}"


def audit_dataset(label, subexp_dir, ds):
    body_path = LAB / subexp_dir / "outputs" / ds / "4-body-fork-fork-obat.tcf"
    if not body_path.exists():
        return {"label": label, "error": f"nao existe: {body_path}"}
    text = body_path.read_text(encoding="utf-8")
    lines = text.rstrip('\n').split('\n')

    qualifica_pairs = []
    i = 0
    while i < len(lines) - 1:
        a = lines[i]
        b = lines[i + 1]
        if is_compacted_marker(a) or is_compacted_marker(b):
            i += 1
            continue
        ok, runs, motivo = check_per_run_delta(a, b)
        if ok:
            qualifica_pairs.append({
                'line_a': i + 1,
                'line_b': i + 2,
                'a': a,
                'b': b,
                'runs': runs,
                'motivo': motivo,
            })
        i += 1

    # Estimativa: marker custa len(template) + len(numbers) + extras
    # Pra par de 2 linhas: marker custa pelo menos len(a) + ~6 chars
    # original 2 linhas: 2*(len(a)+1)
    bytes_potencial = 0
    for p in qualifica_pairs:
        orig_bytes = 2 * (len(p['a']) + 1)
        # Marker estimado: `*2+1@k|<template>` = ~5 + len(template) + 1
        marker_bytes = 5 + len(p['a']) + 1
        bytes_potencial += max(0, orig_bytes - marker_bytes)

    return {
        'label': label,
        'dataset': ds,
        'total_lines': len(lines),
        'qualifica_pairs': qualifica_pairs,
        'bytes_potencial': bytes_potencial,
    }


def render_audit(results):
    out = [
        "# Audit per-run delta encoding (H-DA-08)",
        "",
        "## Resumo",
        "",
        "| Dataset | total lines | pairs qualificaveis | bytes potencial (savings) |",
        "|---|---:|---:|---:|",
    ]
    total_pairs = 0
    total_bytes = 0
    for r in results:
        if 'error' in r:
            out.append(f"| {r['label']} | ERROR | - | - |")
            continue
        out.append(f"| {r['label']} | {r['total_lines']} | "
                   f"{len(r['qualifica_pairs'])} | {r['bytes_potencial']} |")
        total_pairs += len(r['qualifica_pairs'])
        total_bytes += r['bytes_potencial']
    out.append(f"| **TOTAL** | | **{total_pairs}** | **{total_bytes}** |")
    out.append("")
    out.append("## Detalhes — pares qualificaveis")
    out.append("")
    for r in results:
        if 'error' in r or not r.get('qualifica_pairs'):
            continue
        out.append(f"### {r['label']}")
        out.append("")
        for p in r['qualifica_pairs']:
            out.append(f"- Linhas {p['line_a']}-{p['line_b']}: "
                       f"`{p['a']}` → `{p['b']}` ({p['motivo']})")
        out.append("")
    return "\n".join(out) + "\n"


def main():
    print("=== Sub-exp 07 — Per-run delta audit ===\n")
    results = []
    for label, subexp_dir, ds in SOURCES:
        r = audit_dataset(label, subexp_dir, ds)
        results.append(r)
        if 'error' in r:
            print(f"  {label}: ERROR {r['error']}")
        else:
            print(f"  {label:30}  qualifica={len(r['qualifica_pairs']):2}  "
                  f"bytes_potencial={r['bytes_potencial']:3}")

    out = render_audit(results)
    (THIS / "audit.md").write_bytes(out.encode("utf-8"))
    total_bytes = sum(r.get('bytes_potencial', 0) for r in results)
    total_pairs = sum(len(r.get('qualifica_pairs', [])) for r in results)
    print()
    print(f"audit.md: {THIS / 'audit.md'}")
    print(f"Total: {total_pairs} pairs, {total_bytes} bytes potencial")


if __name__ == "__main__":
    main()
