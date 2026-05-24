"""Sub-exp 03 — Variante B: strip + check elide + base-encode + M10.

Pre-tx mais agressivo:
1. Strip marcadores `.` e `-`
2. Remove 2 ultimos digitos (check)
3. Base-94 encode dos 9 digitos restantes (10^9 cabe em 94^5 = 5 chars)
4. M10 encode dos resultados

Decoder espelho:
1. M10 decode -> 5-char base-94
2. Base-94 decode -> 9-digit body
3. Recalcular 2 check digits
4. Re-inserir marcadores `.` e `-`

Validacao: RT byte-canonical. Strings malformadas seriam fallback
em sub-exp 05, aqui assumimos todos validos (D-CPF-uniform/clustered).
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


# Base-94: printable ASCII excluindo chars reservados pelo TCF
# Reservados: \n , ~ * \ # = (espaco tambem evitar)
_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`')
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
# Confirma cabe em 10^9 (precisa 30 bits, 94^5 ~= 7.3 bilhoes)
assert len(BASE94) >= 50, f"base alphabet only {len(BASE94)} chars"

CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')


def calc_check(digits: list[int], weights: range) -> int:
    s = sum(d * w for d, w in zip(digits, weights))
    rem = (s * 10) % 11
    return 0 if rem == 10 else rem


def encode_cpf_to_base(cpf: str) -> str | None:
    """CPF formatado -> 5 chars base-94. Retorna None se nao casa."""
    m = CPF_RE.match(cpf)
    if not m:
        return None
    body_digits = m.group(1) + m.group(2) + m.group(3)
    body_int = int(body_digits)
    if body_int >= len(BASE94) ** 5:
        return None
    # Encode base-94 fixed width 5
    chars = []
    n = body_int
    for _ in range(5):
        chars.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(chars))


def decode_base_to_cpf(s: str) -> str:
    """5 chars base-94 -> CPF formatado (regen check digits)."""
    n = 0
    for c in s:
        n = n * len(BASE94) + BASE94.index(c)
    body_str = str(n).zfill(9)
    digits = [int(d) for d in body_str]
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


def reconstruct(orig: str, dec_str: str) -> str:
    """Reverte pre-tx pra reconstruir o valor original.

    Se decoded eh 5-char base-94: decode + regen check + reformat.
    Caso contrario: literal (fallback inline).
    """
    if len(dec_str) == 5 and all(c in BASE94 for c in dec_str):
        try:
            return decode_base_to_cpf(dec_str)
        except Exception:
            return dec_str
    return dec_str


def measure_variant_b(name: str) -> dict:
    values = load_cpfs(name)
    n_valid_format = sum(1 for v in values if CPF_RE.match(v))

    # Pre-tx: tenta encode-to-base; se nao casa, fallback inline (raw)
    encoded_values: list[str] = []
    for v in values:
        b = encode_cpf_to_base(v)
        encoded_values.append(b if b is not None else v)

    text = encode(encoded_values)
    m10_bytes = len(text.encode("utf-8"))
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + len(values)

    # DECODE + RT per-value (feedback owner: compressao nao validada sem RT)
    decoded_raw = decode(text)
    reconstructed = [reconstruct(o, d) for o, d in zip(values, decoded_raw)]
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    n_mismatched = len(values) - n_rt_ok

    # Salva .tcf + pre-tx + decoded sample em out_tcf/ (auditoria)
    out_dir = THIS / "out_tcf"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))
    pretx_sample = "\n".join(encoded_values[:20])
    (out_dir / f"{name}-pretx-sample20.txt").write_text(
        f"# Pre-tx sample (primeiras 20 strings apos strip+check+base94):\n{pretx_sample}\n",
        encoding="utf-8",
    )
    # Decoded sample com mismatches marcados
    sample_lines = [
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)} | mismatched={n_mismatched}",
        "# Primeiras 20: ' ' = OK, '!' = MISMATCH (compressao quebrou o original)",
    ]
    for i in range(min(20, len(values))):
        marker = " " if rt_per_row[i] else "!"
        sample_lines.append(f"{marker} orig={values[i]!r}  reconstructed={reconstructed[i]!r}")
    (out_dir / f"{name}-decoded-sample20.txt").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )
    # Se houve mismatches, salvar lista completa pra auditoria
    if not rt_all:
        mismatch_lines = ["# Lista completa de mismatches (original -> reconstructed):"]
        for i, ok in enumerate(rt_per_row):
            if not ok:
                mismatch_lines.append(f"row {i}: {values[i]!r} -> {reconstructed[i]!r}")
        (out_dir / f"{name}-mismatches.txt").write_text(
            "\n".join(mismatch_lines) + "\n", encoding="utf-8"
        )

    return {
        "dataset": name,
        "variant": "B-base-encoded",
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
    print(f"Base-94 alphabet ({len(BASE94)} chars): {BASE94[:40]}...")
    print()
    datasets = ["D-CPF-uniform", "D-CPF-clustered", "D-CPF-mixed", "D-CPF-corrupt"]
    results = [measure_variant_b(name) for name in datasets]

    print("=== Sub-exp 03 — Variante B (base-94, RT validado per-row) ===\n")
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
