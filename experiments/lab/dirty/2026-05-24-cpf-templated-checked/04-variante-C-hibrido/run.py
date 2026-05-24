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


def measure_variant_c(name: str) -> dict:
    values = load_cpfs(name)
    n_valid = sum(1 for v in values if CPF_RE.match(v))

    encoded_values: list[str] = []
    for v in values:
        h = encode_cpf_hibrido(v)
        if h is not None:
            encoded_values.append(h)
        else:
            encoded_values.append(v)  # fallback inline

    text = encode(encoded_values)
    m10_bytes = len(text.encode("utf-8"))
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)

    decoded = decode(text)
    rt_ok = True
    for orig, dec_str in zip(values, decoded):
        if CPF_RE.match(orig):
            reconstructed = decode_hibrido_to_cpf(dec_str) if len(dec_str) == 9 and dec_str.isdigit() else dec_str
            if reconstructed != orig:
                rt_ok = False
                break
        else:
            if dec_str != orig:
                rt_ok = False
                break

    return {
        "dataset": name,
        "variant": "C-hibrido",
        "n_rows": len(values),
        "n_valid": n_valid,
        "raw_bytes": raw_bytes,
        "m10_bytes": m10_bytes,
        "ratio_pct": round(m10_bytes / raw_bytes * 100, 2),
        "bytes_per_cpf": round(m10_bytes / len(values), 2),
        "rt_ok": rt_ok,
    }


def main():
    datasets = ["D-CPF-uniform", "D-CPF-clustered", "D-CPF-mixed", "D-CPF-corrupt"]
    results = [measure_variant_c(name) for name in datasets]

    print("=== Sub-exp 04 — Variante C (hibrido strip + check elide) ===\n")
    print(f"{'dataset':22s} {'rows':>5} {'valid':>6} {'raw':>8} {'m10':>8} "
          f"{'ratio':>7} {'b/cpf':>7} {'RT':>4}")
    print("-" * 80)
    for r in results:
        print(f"{r['dataset']:22s} {r['n_rows']:>5} {r['n_valid']:>6} "
              f"{r['raw_bytes']:>8} {r['m10_bytes']:>8} "
              f"{r['ratio_pct']:>6.2f}% {r['bytes_per_cpf']:>7.2f} "
              f"{'OK' if r['rt_ok'] else 'FAIL':>4}")

    out = THIS / "manifest.jsonl"
    out.write_text(
        "\n".join(json.dumps(r) for r in results) + "\n",
        encoding="utf-8",
    )
    print(f"\nManifest: {out}")


if __name__ == "__main__":
    main()
