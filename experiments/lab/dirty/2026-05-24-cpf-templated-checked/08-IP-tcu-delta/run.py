"""Sub-exp 08 — IP TCU-Delta (SlotBehavior heterogeneo).

Hipotese H3 estendida: categoria "Templated + Checked + Unique" tem
sub-variantes por SlotBehavior. IP eh TCU-NoCheckVarLength com
sub-categoria TCU-Delta (ultimo octeto varia em subredes).

3 variantes testadas (mesma maquina logica, encodings diferentes):
- **A. M10 puro**: sem pre-tx. Hipotese: HCC seq-RLE detecta cadence
  no ultimo octeto de subredes automaticamente.
- **B. Strip + 32-bit base-94**: encode IP inteiro como int32, 6 chars
  base-94. Comprime maximo mas destroi visibilidade.
- **C. Pad + strip dots**: padding leading zeros (15 chars fixo),
  remove dots = 12 chars digit string. Preserva visibilidade pra OBAT.

Plus: analise SideOutputs em variante A pra confirmar/refutar
"M10 ja' captura TCU-Delta implicitamente".

Outputs heavy + RT 100% obrigatorio.
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


def classify_ip(v: str) -> str:
    """Kim 2003 taxonomy aplicado a IPv4."""
    if not v:
        return 'empty_value'
    m = IP_RE.match(v)
    if not m:
        return 'format_mismatch'
    octets = [int(g) for g in m.groups()]
    if any(o > 255 for o in octets):
        return 'range_invalid'
    return 'compressible'


# ============ Variante A: M10 puro (baseline) ============

def encode_a(values: list[str]) -> tuple[str, SideOutputs]:
    """Sem pre-tx. M10 puro."""
    side = SideOutputs()
    text = encode(values, side_outputs=side)
    return text, side


def decode_a(text: str) -> list[str]:
    return decode(text)


# ============ Variante B: 32-bit base-94 ============

# 80^6 = 2.6*10^11 > 2^32 = 4.3*10^9 ✓ (6 chars sufficient for IPv4)
B_ENCODED_LEN = 6


def encode_ip_to_b(v: str) -> tuple[str, str]:
    """IP -> 6-char base94 ou marker+literal."""
    status = classify_ip(v)
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


# ============ Variante C: padded + strip dots (preserve octets) ============

def encode_ip_to_c(v: str) -> tuple[str, str]:
    """IP -> 12-char zero-padded digit string."""
    status = classify_ip(v)
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


# ============ Measure helpers ============

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

    if variant == 'A':
        # M10 puro
        side = SideOutputs()
        text = encode(values, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = decoded_raw
        statuses = [classify_ip(v) for v in values]
        cadence_detected = side.cadence_detected
        n_seq_runs = len(side.seq_rle_runs) if side.seq_rle_runs else 0
    elif variant == 'B':
        encoded = []
        statuses = []
        for v in values:
            enc, st = encode_ip_to_b(v)
            encoded.append(enc)
            statuses.append(st)
        side = SideOutputs()
        text = encode(encoded, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = [decode_b_to_ip(d) for d in decoded_raw]
        cadence_detected = side.cadence_detected
        n_seq_runs = len(side.seq_rle_runs) if side.seq_rle_runs else 0
    elif variant == 'C':
        encoded = []
        statuses = []
        for v in values:
            enc, st = encode_ip_to_c(v)
            encoded.append(enc)
            statuses.append(st)
        side = SideOutputs()
        text = encode(encoded, side_outputs=side)
        decoded_raw = decode(text)
        reconstructed = [decode_c_to_ip(d) for d in decoded_raw]
        cadence_detected = side.cadence_detected
        n_seq_runs = len(side.seq_rle_runs) if side.seq_rle_runs else 0
    else:
        raise ValueError(f"variante invalida: {variant}")

    tcf_bytes = len(text.encode("utf-8"))
    rt_per_row = [o == r for o, r in zip(values, reconstructed)]
    rt_all = all(rt_per_row)
    n_rt_ok = sum(rt_per_row)
    counts = Counter(statuses)

    # Outputs heavy: subpasta por variante
    out_dir = THIS / "out_tcf" / variant
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))

    sample_lines = [
        f"# Variante {variant} | {name}",
        f"# RT_ALL={rt_all} | rt_ok={n_rt_ok}/{len(values)} | mismatched={len(values)-n_rt_ok}",
        f"# cadence_detected={cadence_detected} | seq_rle_runs={n_seq_runs}",
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
        "bytes_per_ip": round(tcf_bytes / len(values), 2),
        "rt_all": rt_all,
        "n_rt_ok": n_rt_ok,
        "n_mismatched": len(values) - n_rt_ok,
        "cadence_detected": cadence_detected,
        "seq_rle_runs": n_seq_runs,
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

    print("=== Sub-exp 08 — IP TCU-Delta (3 variantes) ===\n")
    print(f"{'var':3s} {'dataset':22s} {'rows':>6} {'raw':>9} {'tcf':>9} "
          f"{'ratio':>7} {'b/ip':>6} {'cad':>4} {'rle':>5} {'rt_ok':>10}")
    print("-" * 105)

    all_results = []
    for name in datasets:
        values = load_ips(name)
        for variant in variants:
            r = measure_variant(values, variant, name)
            all_results.append(r)
            rt_lbl = f"{r['n_rt_ok']}/{r['n_rows']}" if r['n_rows'] > 0 else "—"
            rt_mk = "" if r['rt_all'] else " FAIL"
            cad = 'Y' if r['cadence_detected'] else 'n'
            print(f"{variant:3s} {name:22s} {r['n_rows']:>6} "
                  f"{r['raw_bytes']:>9} {r['tcf_bytes']:>9} "
                  f"{r['ratio_pct']:>6.2f}% {r['bytes_per_ip']:>5.2f} "
                  f"{cad:>4} {r['seq_rle_runs']:>5} "
                  f"{rt_lbl:>10}{rt_mk}")
        print()

    out = THIS / "manifest.jsonl"
    out.write_text(
        "\n".join(json.dumps(r) for r in all_results) + "\n", encoding="utf-8"
    )

    # Resumo + analise SideOutputs subnet
    all_rt_ok = all(r['rt_all'] for r in all_results)

    # Vencedor por dataset
    by_dataset: dict[str, list[dict]] = {}
    for r in all_results:
        by_dataset.setdefault(r['dataset'], []).append(r)

    print(f"\nRT 100% em todas variantes: {all_rt_ok}\n")
    print("Vencedor por dataset (menor bytes):")
    for ds, results in by_dataset.items():
        valid = [r for r in results if r['rt_all'] and r['n_rows'] > 0]
        if not valid:
            continue
        winner = min(valid, key=lambda r: r['tcf_bytes'])
        print(f"  {ds:25s}: {winner['variant']} "
              f"({winner['tcf_bytes']}B, {winner['ratio_pct']:.2f}%)")

    print(f"\nManifest: {out}")
    print(f"Outputs:  {THIS / 'out_tcf'}/{{A,B,C}}/")


if __name__ == "__main__":
    main()
