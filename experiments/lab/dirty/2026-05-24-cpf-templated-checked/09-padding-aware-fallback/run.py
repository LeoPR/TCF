"""Sub-exp 09 — Padding-aware fallback (resolve RT FAIL sub-exp 08).

Sub-exp 08 mostrou RT FAIL em D-IP-mixed (572/1000) e D-IP-extra-hostile
(824/1000) nas variantes B/C: encoder normalizava silenciosamente
leading zeros (`192.168.001.001` -> `192.168.1.1`).

Sub-exp 09 estende `classify_ip` com novo status `format_padded_zeros`
que cai em fallback literal. Aplica mesmo principio do sub-exp 05 (CPF
check_invalid -> literal): qualquer ambiguidade representacional vai
pra literal preservando byte-canonical.

Variantes testadas:
- A (M10 puro): comparacao baseline (mesma de sub-exp 08)
- B' (32-bit base94 com padded-aware): resolve mixed/hostile
- C' (padded 12-digit com padded-aware): resolve mixed/hostile

Objetivo: RT 100% em TODOS os 9 datasets.

Tradeoff esperado: ratio leve aumento em mixed (overhead marker pra
500 padded literal) mas RT 100% em todo lugar.
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


_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`_')
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
MARKER_LITERAL = '_'

IP_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
B_ENCODED_LEN = 6


def classify_ip_padded_aware(v: str) -> str:
    """Estendido vs sub-exp 08: detecta padded zeros como fallback.

    Status possiveis:
    - compressible: canonical (sem leading zeros), octetos 0-255
    - format_padded_zeros: matches IP_RE MAS tem leading zeros num
      octeto (representacao nao-canonical; preserve via literal)
    - format_mismatch: nao casa IP_RE
    - range_invalid: octeto > 255
    - empty_value: string vazia
    """
    if not v:
        return 'empty_value'
    m = IP_RE.match(v)
    if not m:
        return 'format_mismatch'
    parts = m.groups()
    octets = [int(p) for p in parts]
    if any(o > 255 for o in octets):
        return 'range_invalid'
    # Check padded zeros: cada parte deve ser representacao canonical de int
    for p, o in zip(parts, octets):
        if str(o) != p:
            return 'format_padded_zeros'
    return 'compressible'


# Encoders/decoders (mesma logica sub-exp 08, mas classify_ip_padded_aware
# garante que padded zeros viram literal)

def encode_ip_to_b(v: str) -> tuple[str, str]:
    status = classify_ip_padded_aware(v)
    if status != 'compressible':
        return MARKER_LITERAL + v, status
    m = IP_RE.match(v)
    octets = [int(g) for g in m.groups()]
    n = octets[0] * 256**3 + octets[1] * 256**2 + octets[2] * 256 + octets[3]
    chars = []
    for _ in range(B_ENCODED_LEN):
        chars.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(chars)), status


def decode_b_to_ip(payload: str) -> str:
    if payload.startswith(MARKER_LITERAL):
        return payload[1:]
    if len(payload) == B_ENCODED_LEN and all(c in BASE94 for c in payload):
        n = 0
        for c in payload:
            n = n * len(BASE94) + BASE94.index(c)
        o = [(n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF]
        return '.'.join(str(x) for x in o)
    return payload


def encode_ip_to_c(v: str) -> tuple[str, str]:
    status = classify_ip_padded_aware(v)
    if status != 'compressible':
        return MARKER_LITERAL + v, status
    m = IP_RE.match(v)
    octets = [int(g) for g in m.groups()]
    return ''.join(f"{o:03d}" for o in octets), status


def decode_c_to_ip(payload: str) -> str:
    if payload.startswith(MARKER_LITERAL):
        return payload[1:]
    if len(payload) == 12 and payload.isdigit():
        o1, o2, o3, o4 = payload[0:3], payload[3:6], payload[6:9], payload[9:12]
        return f"{int(o1)}.{int(o2)}.{int(o3)}.{int(o4)}"
    return payload


def load_ips(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] if row else '' for row in r]


def measure_variant(values: list[str], variant: str, name: str) -> dict:
    raw_bytes = sum(len(v.encode("utf-8")) for v in values) + max(0, len(values))
    if not values:
        return {"variant": variant, "dataset": name, "n_rows": 0,
                "rt_all": True, "note": "empty"}

    statuses = [classify_ip_padded_aware(v) for v in values]

    if variant == 'A':
        side = SideOutputs()
        text = encode(values, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = decoded_raw
    elif variant == 'B':
        encoded = [encode_ip_to_b(v)[0] for v in values]
        side = SideOutputs()
        text = encode(encoded, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = [decode_b_to_ip(d) for d in decoded_raw]
    elif variant == 'C':
        encoded = [encode_ip_to_c(v)[0] for v in values]
        side = SideOutputs()
        text = encode(encoded, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = [decode_c_to_ip(d) for d in decoded_raw]
    else:
        raise ValueError(variant)

    tcf_bytes = len(text.encode("utf-8"))
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    counts = Counter(statuses)

    # Outputs heavy
    out_dir = THIS / "out_tcf" / variant
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))

    sample_lines = [
        f"# Sub-exp 09 (padded-aware) Variante {variant} | {name}",
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)} | mismatched={len(values)-n_rt_ok}",
        f"# cadence_detected={side.cadence_detected} | seq_rle_runs={len(side.seq_rle_runs)}",
        f"# Status counts: {dict(counts)}",
        "# Primeiras 15: ' ' = OK, '!' = MISMATCH",
    ]
    for i in range(min(15, len(values))):
        marker = " " if rt_per_row[i] else "!"
        sample_lines.append(f"{marker} orig={values[i]!r}  rec={reconstructed[i]!r}")
    (out_dir / f"{name}-decoded-sample15.txt").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )

    if not rt_all:
        mismatch_lines = [f"# Mismatches variante {variant} / {name}:"]
        for i, ok in enumerate(rt_per_row):
            if not ok:
                mismatch_lines.append(
                    f"row {i}: orig={values[i]!r} rec={reconstructed[i]!r} status={statuses[i]}"
                )
        (out_dir / f"{name}-mismatches.txt").write_text(
            "\n".join(mismatch_lines) + "\n", encoding="utf-8"
        )

    return {
        "variant": variant,
        "dataset": name,
        "n_rows": len(values),
        "raw_bytes": raw_bytes,
        "tcf_bytes": tcf_bytes,
        "ratio_pct": round(tcf_bytes / raw_bytes * 100, 2) if raw_bytes > 0 else 0.0,
        "rt_all": rt_all,
        "n_rt_ok": n_rt_ok,
        "n_mismatched": len(values) - n_rt_ok,
        "cadence_detected": side.cadence_detected,
        "seq_rle_runs": len(side.seq_rle_runs),
        "status_counts": dict(counts),
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
    variants = ['A', 'B', 'C']

    print("=== Sub-exp 09 — Padding-aware fallback (RT 100% obrigatorio) ===\n")
    print(f"{'var':3s} {'dataset':22s} {'rows':>6} {'raw':>9} {'tcf':>9} "
          f"{'ratio':>7} {'cad':>4} {'rle':>5} {'rt_ok':>10}")
    print("-" * 100)

    all_results = []
    for name in datasets:
        values = load_ips(name)
        for variant in variants:
            r = measure_variant(values, variant, name)
            all_results.append(r)
            rt_lbl = f"{r['n_rt_ok']}/{r['n_rows']}"
            rt_mk = "" if r['rt_all'] else " FAIL"
            cad = 'Y' if r['cadence_detected'] else 'n'
            print(f"{variant:3s} {name:22s} {r['n_rows']:>6} "
                  f"{r['raw_bytes']:>9} {r['tcf_bytes']:>9} "
                  f"{r['ratio_pct']:>6.2f}% {cad:>4} {r['seq_rle_runs']:>5} "
                  f"{rt_lbl:>10}{rt_mk}")
        print()

    all_rt_ok = all(r['rt_all'] for r in all_results)
    out = THIS / "manifest.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in all_results) + "\n", encoding="utf-8")

    print(f"\nRT 100% em TODAS variantes/datasets: {all_rt_ok}")

    # Comparacao 09 vs 08 (mixed e hostile)
    print("\nComparacao 09 (padded-aware) vs 08 (silent norm):")
    print(f"  D-IP-mixed B: 09={[r for r in all_results if r['variant']=='B' and r['dataset']=='D-IP-mixed'][0]['tcf_bytes']}B / "
          f"08=7608B (RT FAIL 572/1000)")
    print(f"  D-IP-mixed C: 09={[r for r in all_results if r['variant']=='C' and r['dataset']=='D-IP-mixed'][0]['tcf_bytes']}B / "
          f"08=14632B (RT FAIL 572/1000)")
    print(f"  D-IP-hostile B: 09={[r for r in all_results if r['variant']=='B' and r['dataset']=='D-IP-extra-hostile'][0]['tcf_bytes']}B / "
          f"08=8218B (RT FAIL 824/1000)")
    print(f"  D-IP-hostile C: 09={[r for r in all_results if r['variant']=='C' and r['dataset']=='D-IP-extra-hostile'][0]['tcf_bytes']}B / "
          f"08=11386B (RT FAIL 824/1000)")

    print(f"\nManifest: {out}")
    print(f"Outputs:  {THIS / 'out_tcf'}/{{A,B,C}}/")


if __name__ == "__main__":
    main()
