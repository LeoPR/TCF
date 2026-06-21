"""Sub-exp 13 — Base-aware seq-RLE (testar hipotese owner 2026-05-24).

Hipotese: HCC seq-RLE generalizada com BaseAlphabet (decimal + hex)
deveria atingir compressao similar a C decimal padded em datasets
onde input eh naturalmente hex (variante D do sub-exp 12).

Arquitetura honrando "separacao de responsabilidades":
- BaseAlphabet: dataclass pura (so' nome, chars, base)
- SeqRLEEngine: engine generico parametrizado por alphabet
- MultiBaseSeqRLE: detector que tenta multiplos engines

Testes cientificos:
1. **Regressao obrigatoria**: MultiBaseSeqRLE([DECIMAL]) deve produzir
   output BYTE-IDENTICO a HCCSeqRLE (M10 canonical). Se quebrar, bug.
2. **Hipotese principal**: MultiBaseSeqRLE([DECIMAL, HEX_LOWER]) em
   D-IP variant D (hex) deve melhorar significativamente vs M10
   canonical em datasets cadenced (subnet).
3. **Cross-test**: nao regredir CPF/decimal datasets.

Workflow:
- Encode via TCF M10 standard (gera body via M8AVirtualRefsSyntax)
- Substituir HCCSeqRLE post-process por MultiBaseSeqRLE custom
- Decode espelho usando MultiBaseSeqRLE
- Validar RT byte-canonical
- Medir bytes
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(THIS))

from base_alphabet import BaseAlphabet, DECIMAL, HEX_LOWER, BASE_MARKER  # noqa: E402
from seq_rle_engine import MultiBaseSeqRLE  # noqa: E402

from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402


# ===========================================================================
# Custom HCC com base-aware seq-RLE substituindo HCCSeqRLE
# ===========================================================================

class HCCBaseAwareSeqRLE(M8AVirtualRefsSyntax):
    """HCC + MultiBaseSeqRLE substituindo HCCSeqRLE.

    Mesma interface de HCCSeqRLE (encode/decode), mas usa
    MultiBaseSeqRLE em vez do digit-only do M10.
    """

    name = "M8-A-base-aware-seq-rle"

    def __init__(self, alphabets: list[BaseAlphabet] | None = None):
        super().__init__()
        self.compactor = MultiBaseSeqRLE(alphabets)
        self._seq_info: list[dict] = []

    def get_seq_info(self) -> list[dict]:
        return self._seq_info

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super().encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text.rstrip('\n').split('\n')
        compacted, info = self.compactor.compact_body(body_lines)
        self._seq_info = info
        return '\n'.join(compacted) + '\n'

    def decode(self, tcf_text):
        expanded_lines = []
        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha:
                expanded_lines.append(raw)
                continue
            expanded = self.compactor.expand_marker(linha)
            if expanded is not None:
                expanded_lines.extend(expanded)
            else:
                expanded_lines.append(raw)
        expanded_text = '\n'.join(expanded_lines) + '\n'
        return super().decode(expanded_text)


def encode_with_syntax(values: list[str], syn):
    """Pipeline encode com syntax customizada (replaces HCCSeqRLE)."""
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    features = analyze_column(values)
    cadence_detected, _ = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)
    if cadence_detected:
        tokens, _ = processar_with_hint(unicas, min_len=min_len, prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=min_len)
    return syn.encode(values, unicas, tokens, "val")


# ===========================================================================
# Helper pra carregar/encodar pra hex (variante D do sub-exp 12)
# ===========================================================================

MARKER_LITERAL = '_'
IP_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')


def classify_ip(v: str) -> str:
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


def encode_ip_to_hex(v: str) -> str:
    """IP -> 8-char hex (variante D do sub-exp 12)."""
    if classify_ip(v) != 'compressible':
        return MARKER_LITERAL + v
    m = IP_RE.match(v)
    octets = [int(g) for g in m.groups()]
    return ''.join(f"{o:02x}" for o in octets)


def decode_hex_to_ip(payload: str) -> str:
    if payload.startswith(MARKER_LITERAL):
        return payload[1:]
    if len(payload) == 8 and all(c in "0123456789abcdef" for c in payload):
        octets = [int(payload[i:i+2], 16) for i in range(0, 8, 2)]
        return '.'.join(str(o) for o in octets)
    return payload


# ===========================================================================
# Testes
# ===========================================================================

def load(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] if row else '' for row in r]


def regression_test():
    """Test 1: MultiBaseSeqRLE([DECIMAL]) deve produzir output identico a HCCSeqRLE.

    Roda nos datasets D-CPF e D-IP. Output deve bater byte-a-byte.
    """
    print("\n=== Test 1: REGRESSAO (decimal only == M10 canonical) ===\n")
    datasets = [
        "D-CPF-uniform", "D-CPF-clustered", "D-CPF-mixed",
        "D-IP-uniform", "D-IP-subnet",
    ]
    all_match = True
    for name in datasets:
        values = load(name)
        if not values:
            continue
        text_m10 = encode_with_syntax(values, HCCSeqRLE())
        text_baseaware = encode_with_syntax(values, HCCBaseAwareSeqRLE([DECIMAL]))
        match = (text_m10 == text_baseaware)
        all_match = all_match and match
        bytes_m10 = len(text_m10.encode("utf-8"))
        bytes_ba = len(text_baseaware.encode("utf-8"))
        print(f"  {name:25s}: M10={bytes_m10}B BaseAware={bytes_ba}B "
              f"{'BYTE-IDENTICAL OK' if match else 'DIFFER FAIL'}")
    print(f"\nRegression test: {'PASS' if all_match else 'FAIL'}")
    return all_match


def main_hypothesis_test():
    """Test 2: Hex IPs com base-aware [DECIMAL, HEX_LOWER] vs M10 canonical."""
    print("\n=== Test 2: HEX IPs — base-aware vs M10 canonical ===\n")
    datasets = [
        "D-IP-uniform", "D-IP-subnet", "D-IP-mixed",
        "D-IP-corrupt", "D-IP-edge-single", "D-IP-edge-allsame",
        "D-IP-extra-large10k",
    ]

    print(f"{'dataset':22s} {'rows':>6} {'hex_raw':>9} "
          f"{'M10':>9} {'BaseAware':>10} {'delta':>8} {'rt':>3}")
    print("-" * 90)
    results = []
    for name in datasets:
        values = load(name)
        if not values:
            continue
        # Pre-tx hex (variante D)
        hex_values = [encode_ip_to_hex(v) for v in values]
        hex_raw = sum(len(s.encode("utf-8")) for s in hex_values) + len(hex_values)

        # Encode com M10 standard (current digit-only)
        text_m10 = encode_with_syntax(hex_values, HCCSeqRLE())
        bytes_m10 = len(text_m10.encode("utf-8"))

        # Encode com base-aware [DECIMAL, HEX_LOWER]
        text_ba = encode_with_syntax(hex_values, HCCBaseAwareSeqRLE([DECIMAL, HEX_LOWER]))
        bytes_ba = len(text_ba.encode("utf-8"))

        # RT validation
        ba_syn = HCCBaseAwareSeqRLE([DECIMAL, HEX_LOWER])
        decoded = ba_syn.decode(text_ba)
        rt_ok = (decoded == hex_values)

        delta = bytes_ba - bytes_m10
        delta_pct = (delta / bytes_m10 * 100) if bytes_m10 > 0 else 0

        results.append({
            "dataset": name,
            "n_rows": len(values),
            "hex_raw": hex_raw,
            "m10_bytes": bytes_m10,
            "baseaware_bytes": bytes_ba,
            "delta_bytes": delta,
            "delta_pct": round(delta_pct, 2),
            "rt_ok": rt_ok,
        })
        print(f"{name:22s} {len(values):>6} {hex_raw:>9} "
              f"{bytes_m10:>9} {bytes_ba:>10} "
              f"{delta:>+8d} {'OK' if rt_ok else 'FAIL':>3}")

    return results


def cross_test():
    """Test 3: Cross-test — base-aware com [DECIMAL, HEX] nao regredir decimal."""
    print("\n=== Test 3: CROSS-TEST (decimal datasets nao podem regredir) ===\n")
    datasets = [
        "D-CPF-uniform", "D-CPF-clustered", "D-CPF-corrupt",
        "D-IP-uniform", "D-IP-extra-large10k",
    ]
    print(f"{'dataset':22s} {'M10 only':>10} {'+ HEX':>10} {'delta':>8} {'verdict':>10}")
    print("-" * 75)
    results = []
    for name in datasets:
        values = load(name)
        if not values:
            continue
        text_m10 = encode_with_syntax(values, HCCSeqRLE())
        text_ba = encode_with_syntax(values, HCCBaseAwareSeqRLE([DECIMAL, HEX_LOWER]))
        bytes_m10 = len(text_m10.encode("utf-8"))
        bytes_ba = len(text_ba.encode("utf-8"))
        delta = bytes_ba - bytes_m10
        verdict = "OK" if delta <= 0 else ("REGRESSAO" if delta > 5 else "marginal")
        results.append({
            "dataset": name,
            "m10_bytes": bytes_m10,
            "baseaware_bytes": bytes_ba,
            "delta_bytes": delta,
            "verdict": verdict,
        })
        print(f"{name:22s} {bytes_m10:>10} {bytes_ba:>10} "
              f"{delta:>+8d} {verdict:>10}")
    return results


def save_artifacts(name: str, syn, hex_values: list[str], text: str):
    """Salva outputs visiveis pra auditoria."""
    out_dir = THIS / "out_tcf"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{name}.tcf").write_text(text, encoding="utf-8")
    info = syn.get_seq_info() if hasattr(syn, 'get_seq_info') else []
    (out_dir / f"{name}-seq_runs.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8"
    )


def main():
    print("=== Sub-exp 13 — Base-aware seq-RLE generalizada ===")

    regression_ok = regression_test()
    hypothesis_results = main_hypothesis_test()
    cross_results = cross_test()

    # Save outputs pra D-IP-subnet (hex, mais interessante)
    subnet_hex = [encode_ip_to_hex(v) for v in load("D-IP-subnet")]
    ba_syn = HCCBaseAwareSeqRLE([DECIMAL, HEX_LOWER])
    text_ba_subnet = encode_with_syntax(subnet_hex, ba_syn)
    save_artifacts("D-IP-subnet-hex-baseaware", ba_syn, subnet_hex, text_ba_subnet)

    m10_syn = HCCSeqRLE()
    text_m10_subnet = encode_with_syntax(subnet_hex, m10_syn)
    save_artifacts("D-IP-subnet-hex-M10", m10_syn, subnet_hex, text_m10_subnet)

    # Manifest
    manifest = {
        "regression_test_passed": regression_ok,
        "hypothesis_results": hypothesis_results,
        "cross_test_results": cross_results,
    }
    (THIS / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print("\n=== Summary ===")
    print(f"Regression OK: {regression_ok}")
    print(f"Outputs em: {THIS / 'out_tcf'}/")
    print(f"Manifest: {THIS / 'manifest.json'}")


if __name__ == "__main__":
    main()
