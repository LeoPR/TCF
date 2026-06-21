"""Sub-exp 04 — Variante C (hibrido): strip + check elide + M10.

Pre-tx mais leve que B:
1. Strip marcadores `.` e `-`
2. Remove 2 ultimos digitos (check)
3. **Mantem 9 digitos visiveis** (sem base-encode)
4. M10 encode

Hipotese H1: OBAT pode achar padrao em prefixos administrativos
mesmo nos digitos. Base-encode (variante B) destruiria essa
visibilidade.

Decoder espelho:
1. M10 decode -> 9-digit body
2. Recalcular check
3. Re-inserir marcadores
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


CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')


def calc_check(digits: list[int], weights: range) -> int:
    s = sum(d * w for d, w in zip(digits, weights))
    rem = (s * 10) % 11
    return 0 if rem == 10 else rem


def encode_cpf_hibrido(cpf: str) -> str | None:
    """CPF formatado -> 9 digitos visiveis. None se nao casa."""
    m = CPF_RE.match(cpf)
    if not m:
        return None
    return m.group(1) + m.group(2) + m.group(3)


def decode_hibrido_to_cpf(s: str) -> str:
    """9 digitos -> CPF formatado (regen check)."""
    if len(s) != 9:
        return s  # fallback
    digits = [int(d) for d in s]
    digits.append(calc_check(digits, range(10, 1, -1)))
    digits.append(calc_check(digits, range(11, 1, -1)))
    full = ''.join(str(d) for d in digits)
    return f"{full[:3]}.{full[3:6]}.{full[6:9]}-{full[9:]}"


def load_cpfs(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def reconstruct(dec_str: str) -> str:
    """Reverte pre-tx C: 9-digit -> CPF formatado + check regen."""
    if len(dec_str) == 9 and dec_str.isdigit():
        try:
            return decode_hibrido_to_cpf(dec_str)
        except Exception:
            return dec_str
    return dec_str


def measure_variant_c(name: str) -> dict:
    values = load_cpfs(name)
    n_valid_format = sum(1 for v in values if CPF_RE.match(v))

    encoded_values: list[str] = []
    for v in values:
        h = encode_cpf_hibrido(v)
        encoded_values.append(h if h is not None else v)

    text = encode(encoded_values)
    m10_bytes = len(text.encode("utf-8"))
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)

    # DECODE + RT per-value (feedback owner)
    decoded_raw = decode(text)
    reconstructed = [reconstruct(d) for d in decoded_raw]
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    n_mismatched = len(values) - n_rt_ok

    # Salva .tcf + pre-tx + decoded sample em out_tcf/
    out_dir = THIS / "out_tcf"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))
    pretx_sample = "\n".join(encoded_values[:20])
    (out_dir / f"{name}-pretx-sample20.txt").write_text(
        f"# Pre-tx sample (primeiras 20 strings apos strip+check, 9 digitos):\n{pretx_sample}\n",
        encoding="utf-8",
    )
    sample_lines = [
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)} | mismatched={n_mismatched}",
        "# Primeiras 20: ' ' = OK, '!' = MISMATCH",
    ]
    for i in range(min(20, len(values))):
        marker = " " if rt_per_row[i] else "!"
        sample_lines.append(f"{marker} orig={values[i]!r}  reconstructed={reconstructed[i]!r}")
    (out_dir / f"{name}-decoded-sample20.txt").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )
    if not rt_all:
        mismatch_lines = ["# Lista completa de mismatches:"]
        for i, ok in enumerate(rt_per_row):
            if not ok:
                mismatch_lines.append(f"row {i}: {values[i]!r} -> {reconstructed[i]!r}")
        (out_dir / f"{name}-mismatches.txt").write_text(
            "\n".join(mismatch_lines) + "\n", encoding="utf-8"
        )

    return {
        "dataset": name,
        "variant": "C-hibrido",
        "n_rows": len(values),
        "n_valid_format": n_valid_format,
        "raw_bytes": raw_bytes,
        "m10_bytes": m10_bytes,
        "ratio_pct": round(m10_bytes / raw_bytes * 100, 2),
        "bytes_per_cpf": round(m10_bytes / len(values), 2),
        "rt_all": rt_all,
        "n_rt_ok": n_rt_ok,
        "n_mismatched": n_mismatched,
    }


def main():
    datasets = ["D-CPF-uniform", "D-CPF-clustered", "D-CPF-mixed", "D-CPF-corrupt"]
    results = [measure_variant_c(name) for name in datasets]

    print("=== Sub-exp 04 — Variante C (hibrido, RT validado per-row) ===\n")
    print(f"{'dataset':22s} {'rows':>5} {'raw':>8} {'m10':>8} "
          f"{'ratio':>7} {'b/cpf':>7} {'rt_ok':>9} {'mismatch':>9}")
    print("-" * 95)
    for r in results:
        rt_label = f"{r['n_rt_ok']}/{r['n_rows']}"
        print(f"{r['dataset']:22s} {r['n_rows']:>5} "
              f"{r['raw_bytes']:>8} {r['m10_bytes']:>8} "
              f"{r['ratio_pct']:>6.2f}% {r['bytes_per_cpf']:>7.2f} "
              f"{rt_label:>9} {r['n_mismatched']:>9}")

    out = THIS / "manifest.jsonl"
    out.write_text(
        "\n".join(json.dumps(r) for r in results) + "\n",
        encoding="utf-8",
    )
    print(f"\nManifest: {out}")


if __name__ == "__main__":
    main()
