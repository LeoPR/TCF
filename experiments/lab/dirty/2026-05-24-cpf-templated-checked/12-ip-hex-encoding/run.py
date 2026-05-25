"""Sub-exp 12 — IP em hex (8-char) — avaliacao byte-level.

Owner propos: "IP pode gastar 4 bytes se usar 0-255 em um byte, ou
ate 8 bytes se deixar em hexadecimal, e ele pode ser um incremental
de byte ou hexa".

Em TCF textual (UTF-8 .tcf), encoding binario raw (4 bytes) eh
problematico (chars 0-31 = control reservados; 128-255 = UTF-8 multi-
byte = 2 bytes serializados). Hex (8 chars 0-9a-f, todos ASCII = 1
byte) eh a alternativa segura.

Variantes testadas:
- A: M10 puro (baseline ja' em sub-exp 08)
- B: 32-bit base94 (6 chars, ja' em sub-exp 08)
- C: 12-digit padded (ja' em sub-exp 08)
- **D: 8-char hex** (NOVO — c0a80101 lowercase, zero-padded)

Hex eh interessante porque:
1. Length uniforme (sempre 8) -> HCC seq-RLE pode detectar
2. Mais curto que C (8 vs 12)
3. Mais visivel que B (random base94)
4. Subnet incremental: ultimos 2 chars variam (last octet 0x00-0xFF)

Hipotese: D fica entre B e C em ratio. Em subnet, D deve comprimir
similar a C (1-3%).
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode, SideOutputs  # noqa: E402


MARKER_LITERAL = '_'
IP_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')


def classify_ip(v: str) -> str:
    """Padded-aware classification (sub-exp 09)."""
    if not v:
        return 'empty_value'
    m = IP_RE.match(v)
    if not m:
        return 'format_mismatch'
    parts = m.groups()
    octets = [int(p) for p in parts]
    if any(o > 255 for o in octets):
        return 'range_invalid'
    for p, o in zip(parts, octets):
        if str(o) != p:
            return 'format_padded_zeros'
    return 'compressible'


def encode_ip_to_hex(v: str) -> tuple[str, str]:
    """IP -> 8-char hex zero-padded (`192.168.1.1` -> `c0a80101`)."""
    status = classify_ip(v)
    if status != 'compressible':
        return MARKER_LITERAL + v, status
    m = IP_RE.match(v)
    octets = [int(g) for g in m.groups()]
    return ''.join(f"{o:02x}" for o in octets), status


def decode_hex_to_ip(payload: str) -> str:
    if payload.startswith(MARKER_LITERAL):
        return payload[1:]
    if len(payload) == 8 and all(c in "0123456789abcdef" for c in payload):
        octets = [int(payload[i:i+2], 16) for i in range(0, 8, 2)]
        return '.'.join(str(o) for o in octets)
    return payload


def load_ips(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] if row else '' for row in r]


def measure(name: str) -> dict:
    values = load_ips(name)
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + max(0, len(values))
    if not values:
        return {"dataset": name, "n_rows": 0, "rt_all": True}

    encoded = []
    statuses = []
    for v in values:
        enc, st = encode_ip_to_hex(v)
        encoded.append(enc)
        statuses.append(st)

    side = SideOutputs()
    text = encode(encoded, side_outputs=side)
    tcf_bytes = len(text.encode("utf-8"))

    decoded_raw = decode(text)
    reconstructed = [decode_hex_to_ip(d) for d in decoded_raw]
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    n_mismatched = len(values) - n_rt_ok
    counts = Counter(statuses)

    out_dir = THIS / "out_tcf"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))

    pretx_sample = "\n".join(encoded[:20])
    (out_dir / f"{name}-pretx-sample20.txt").write_text(
        f"# Pre-tx D (hex 8-char): primeiras 20:\n{pretx_sample}\n",
        encoding="utf-8"
    )

    sample_lines = [
        f"# Variante D (hex 8-char) | {name}",
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)}",
        f"# cadence_detected={side.cadence_detected} | seq_rle_runs={len(side.seq_rle_runs)}",
        f"# Status: {dict(counts)}",
        "# Primeiras 15: ' ' = OK, '!' = MISMATCH",
    ]
    for i in range(min(15, len(values))):
        marker = " " if rt_per_row[i] else "!"
        sample_lines.append(f"{marker} orig={values[i]!r} rec={reconstructed[i]!r}")
    (out_dir / f"{name}-decoded-sample15.txt").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )

    if not rt_all:
        ml = [f"# Mismatches em {name}:"]
        for i, ok in enumerate(rt_per_row):
            if not ok:
                ml.append(f"row {i}: orig={values[i]!r} rec={reconstructed[i]!r}")
        (out_dir / f"{name}-mismatches.txt").write_text(
            "\n".join(ml) + "\n", encoding="utf-8"
        )

    return {
        "dataset": name,
        "variant": "D-hex",
        "n_rows": len(values),
        "raw_bytes": raw_bytes,
        "tcf_bytes": tcf_bytes,
        "ratio_pct": round(tcf_bytes / raw_bytes * 100, 2),
        "rt_all": rt_all,
        "n_rt_ok": n_rt_ok,
        "n_mismatched": n_mismatched,
        "cadence_detected": side.cadence_detected,
        "seq_rle_runs": len(side.seq_rle_runs),
    }


def main():
    datasets = [
        "D-IP-uniform",
        "D-IP-subnet",
        "D-IP-mixed",
        "D-IP-corrupt",
        "D-IP-edge-single",
        "D-IP-edge-allsame",
        "D-IP-edge-allcorrupt",
        "D-IP-extra-large10k",
        "D-IP-extra-hostile",
    ]

    print("=== Sub-exp 12 — IP variante D (hex 8-char) ===\n")
    print(f"{'dataset':22s} {'rows':>6} {'raw':>9} {'tcf':>9} "
          f"{'ratio':>7} {'cad':>4} {'rle':>5} {'rt_ok':>10}")
    print("-" * 90)

    # Carrega tabela 08/09 pra comparacao
    sub09 = LAB / "09-padding-aware-fallback" / "manifest.jsonl"
    sub09_data = {}
    if sub09.exists():
        for line in sub09.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                sub09_data.setdefault(r['dataset'], {})[r['variant']] = r

    results = []
    for name in datasets:
        r = measure(name)
        results.append(r)
        rt_lbl = f"{r['n_rt_ok']}/{r['n_rows']}"
        rt_mk = "" if r['rt_all'] else " FAIL"
        cad = 'Y' if r['cadence_detected'] else 'n'
        print(f"{name:22s} {r['n_rows']:>6} "
              f"{r['raw_bytes']:>9} {r['tcf_bytes']:>9} "
              f"{r['ratio_pct']:>6.2f}% {cad:>4} {r['seq_rle_runs']:>5} "
              f"{rt_lbl:>10}{rt_mk}")

    out = THIS / "manifest.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in results) + "\n",
                   encoding="utf-8")

    # Comparacao consolidada: A, B, C (do sub-exp 09) vs D (este)
    if sub09_data:
        print("\nComparacao A/B/C (sub-exp 09) vs D (hex, este sub-exp):")
        print(f"{'dataset':22s} {'A-M10':>10} {'B-base94':>10} {'C-padded':>10} {'D-hex':>10} {'Winner':>10}")
        print("-" * 90)
        for name in datasets:
            row_d = next(r for r in results if r['dataset'] == name)
            row_a = sub09_data.get(name, {}).get('A', {})
            row_b = sub09_data.get(name, {}).get('B', {})
            row_c = sub09_data.get(name, {}).get('C', {})

            candidates = [
                ('A', row_a.get('tcf_bytes', 0), row_a.get('rt_all', False)),
                ('B', row_b.get('tcf_bytes', 0), row_b.get('rt_all', False)),
                ('C', row_c.get('tcf_bytes', 0), row_c.get('rt_all', False)),
                ('D', row_d['tcf_bytes'], row_d['rt_all']),
            ]
            valid = [(n, b) for n, b, ok in candidates if ok and b > 0]
            winner = min(valid, key=lambda x: x[1])[0] if valid else '?'

            print(f"{name:22s} "
                  f"{row_a.get('tcf_bytes', '?'):>10} "
                  f"{row_b.get('tcf_bytes', '?'):>10} "
                  f"{row_c.get('tcf_bytes', '?'):>10} "
                  f"{row_d['tcf_bytes']:>10} "
                  f"{winner:>10}")

    print(f"\nManifest: {out}")
    print(f"Outputs:  {THIS / 'out_tcf'}/")


if __name__ == "__main__":
    main()
