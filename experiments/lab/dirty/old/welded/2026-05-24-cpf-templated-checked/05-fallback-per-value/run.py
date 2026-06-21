"""Sub-exp 05 — Fallback per-value com marker explicito.

Resolve o RT FAIL das variantes B/C em datasets dirty.

Design:
- Marker prefix `_` distingue literal vs compressed
- `_<original>`: fallback literal (decoder strips prefix)
- `<5char base94>`: compressed (decoder regen check + reformat)
- `_` nao aparece em CPFs (so' digitos + `.` + `-`); safe.

Validacao:
- Encoder pre-tx STRITTA: rejeita check_invalid + format_mismatch
  + chars_invalid + length_wrong. Todos viram literal.
- RT byte-canonical 100% obrigatorio em TODOS datasets.

Datasets (progressao dirty etapa 1, 3, 4):
- Etapa 1: uniform/clustered/mixed/corrupt
- Etapa 3 (bordas): edge-single/edge-allsame/edge-allcorrupt
- Etapa 4 (extrapolacao): extra-large10k/extra-hostile

Outputs heavy: .tcf + decoded-sample + mismatches (lista completa)
+ stats per-tipo de fallback.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode  # noqa: E402


# Base-94 safe (mesma definicao do sub-exp 03)
_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`_')  # adicionei _ pra evitar conflito com marker
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
assert len(BASE94) >= 50

CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')
MARKER_LITERAL = '_'


def calc_check(digits: list[int], weights: range) -> int:
    s = sum(d * w for d, w in zip(digits, weights))
    rem = (s * 10) % 11
    return 0 if rem == 10 else rem


def classify_fallback(cpf: str) -> str:
    """Retorna 'compressible' OR razao especifica de fallback."""
    if not cpf:
        return 'empty_value'
    if len(cpf) != 14:
        # 11 digit unmasked? 11 chars exactly
        if len(cpf) == 11 and cpf.isdigit():
            return 'format_unmasked'
        return 'length_wrong'
    if not CPF_RE.match(cpf):
        return 'format_mismatch'  # tem `.` ou `-` em posicao errada, ou chars invalid
    # Format OK, validar check
    digits_str = cpf.replace('.', '').replace('-', '')
    body = [int(d) for d in digits_str[:9]]
    d1_expected = calc_check(body, range(10, 1, -1))
    d2_expected = calc_check(body + [d1_expected], range(11, 1, -1))
    d1_actual = int(digits_str[9])
    d2_actual = int(digits_str[10])
    if (d1_expected, d2_expected) != (d1_actual, d2_actual):
        return 'check_invalid'
    return 'compressible'


def encode_cpf_v05(cpf: str) -> tuple[str, str]:
    """Retorna (encoded, status) onde status eh 'compressible' ou razao."""
    status = classify_fallback(cpf)
    if status != 'compressible':
        return MARKER_LITERAL + cpf, status

    digits_str = cpf.replace('.', '').replace('-', '')
    body_int = int(digits_str[:9])
    chars = []
    n = body_int
    for _ in range(5):
        chars.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(chars)), 'compressible'


def decode_cpf_v05(payload: str) -> str:
    """Reverte encode_cpf_v05."""
    if payload.startswith(MARKER_LITERAL):
        return payload[1:]
    if len(payload) == 5 and all(c in BASE94 for c in payload):
        n = 0
        for c in payload:
            n = n * len(BASE94) + BASE94.index(c)
        body_str = str(n).zfill(9)
        digits = [int(d) for d in body_str]
        digits.append(calc_check(digits, range(10, 1, -1)))
        digits.append(calc_check(digits, range(11, 1, -1)))
        full = ''.join(str(d) for d in digits)
        return f"{full[:3]}.{full[3:6]}.{full[6:9]}-{full[9:]}"
    # Caso inesperado: devolve cru (nao deveria acontecer)
    return payload


def load_cpfs(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # skip header
        return [row[0] if row else '' for row in r]


def measure(name: str) -> dict:
    values = load_cpfs(name)
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + max(0, len(values))

    if not values:
        # Edge case: empty dataset — pular encode
        return {
            "dataset": name,
            "n_rows": 0,
            "raw_bytes": 0,
            "tcf_bytes": 0,
            "ratio_pct": 0.0,
            "rt_all": True,
            "n_rt_ok": 0,
            "n_mismatched": 0,
            "fallback_counts": {},
            "note": "empty dataset (no encode)",
        }

    # Pre-tx com classificacao
    encoded_values: list[str] = []
    statuses: list[str] = []
    for v in values:
        enc, st = encode_cpf_v05(v)
        encoded_values.append(enc)
        statuses.append(st)

    # Encode TCF
    text = encode(encoded_values)
    tcf_bytes = len(text.encode("utf-8"))

    # DECODE + RT per-value
    decoded_raw = decode(text)
    reconstructed = [decode_cpf_v05(d) for d in decoded_raw]
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    n_mismatched = len(values) - n_rt_ok

    # Stats: contagem de cada tipo de classificacao
    fallback_counts: dict[str, int] = {}
    for st in statuses:
        fallback_counts[st] = fallback_counts.get(st, 0) + 1

    # OUTPUTS HEAVY pra auditoria
    out_dir = THIS / "out_tcf"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))

    # Pre-tx sample com status per linha
    pretx_lines = [f"# Sub-exp 05 pre-tx sample (status per linha):"]
    for i in range(min(20, len(values))):
        pretx_lines.append(
            f"[{statuses[i]:18s}] orig={values[i]!r}  -> enc={encoded_values[i]!r}"
        )
    (out_dir / f"{name}-pretx-sample20.txt").write_text(
        "\n".join(pretx_lines) + "\n", encoding="utf-8"
    )

    # Decoded sample com marker OK/MISMATCH
    sample_lines = [
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)} | mismatched={n_mismatched}",
        f"# Fallback counts: {fallback_counts}",
        "# Primeiras 20: ' ' = OK, '!' = MISMATCH (compressao quebrou o original)",
    ]
    for i in range(min(20, len(values))):
        marker = " " if rt_per_row[i] else "!"
        sample_lines.append(f"{marker} orig={values[i]!r}  reconstructed={reconstructed[i]!r}")
    (out_dir / f"{name}-decoded-sample20.txt").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )

    # Mismatches completos (se houver)
    if not rt_all:
        mismatch_lines = [f"# Lista COMPLETA de mismatches em {name}:"]
        for i, ok in enumerate(rt_per_row):
            if not ok:
                mismatch_lines.append(
                    f"row {i}: orig={values[i]!r}  reconstructed={reconstructed[i]!r}  status={statuses[i]}"
                )
        (out_dir / f"{name}-mismatches.txt").write_text(
            "\n".join(mismatch_lines) + "\n", encoding="utf-8"
        )

    return {
        "dataset": name,
        "n_rows": len(values),
        "raw_bytes": raw_bytes,
        "tcf_bytes": tcf_bytes,
        "ratio_pct": round(tcf_bytes / raw_bytes * 100, 2) if raw_bytes > 0 else 0.0,
        "rt_all": rt_all,
        "n_rt_ok": n_rt_ok,
        "n_mismatched": n_mismatched,
        "fallback_counts": fallback_counts,
    }


def main():
    print(f"BASE94 alphabet ({len(BASE94)} chars; marker '_' reservado)\n")

    datasets = [
        # Etapa 1 — ilustrativo
        "D-CPF-uniform",
        "D-CPF-clustered",
        "D-CPF-mixed",
        "D-CPF-corrupt",
        # Etapa 3 — bordas
        "D-CPF-edge-single",
        "D-CPF-edge-allsame",
        "D-CPF-edge-allcorrupt",
        # Etapa 4 — extrapolacao
        "D-CPF-extra-large10k",
        "D-CPF-extra-hostile",
    ]
    results = [measure(name) for name in datasets]

    print("=== Sub-exp 05 — Fallback marker (RT 100% obrigatorio) ===\n")
    print(f"{'dataset':26s} {'rows':>6} {'raw':>9} {'tcf':>9} "
          f"{'ratio':>7} {'rt_ok':>10} {'mismatch':>9}")
    print("-" * 100)
    for r in results:
        rt_label = f"{r['n_rt_ok']}/{r['n_rows']}"
        rt_marker = "" if r['rt_all'] else " FAIL"
        print(f"{r['dataset']:26s} {r['n_rows']:>6} "
              f"{r['raw_bytes']:>9} {r['tcf_bytes']:>9} "
              f"{r['ratio_pct']:>6.2f}% {rt_label:>10}{rt_marker} "
              f"{r['n_mismatched']:>4}")

    print("\nFallback counts per dataset:")
    for r in results:
        fb = ', '.join(f"{k}={v}" for k, v in sorted(r['fallback_counts'].items()))
        print(f"  {r['dataset']:26s}: {fb}")

    out = THIS / "manifest.jsonl"
    out.write_text(
        "\n".join(json.dumps(r) for r in results) + "\n",
        encoding="utf-8",
    )
    print(f"\nManifest: {out}")
    print(f"Outputs visiveis em: {THIS / 'out_tcf'}/")


if __name__ == "__main__":
    main()
