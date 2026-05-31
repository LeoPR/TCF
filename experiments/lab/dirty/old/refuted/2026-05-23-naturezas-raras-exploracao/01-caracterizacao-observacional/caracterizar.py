"""Sub-exp 01 — caracterizar padroes #5 (range) e #8 (arredondamento).

Pra cada coluna numerica em Adult+TPC-H + D1-D9:
1. Detectar suffix comum (mesma terminacao em >= 80% dos valores)
2. Detectar prefix comum LONGO (mesmo prefixo em >= 50% dos valores,
   length >= 50% do avg_len)
3. Range narrow (max/min ratio < 10, ou todos mesmo digit_count)
4. Estimar ganho potencial: bytes M10 vs "encoder com pattern dedicado"

Encoder #5 (range narrow):
- emit "base|local1,local2,..." onde local = value - base
- Bytes: len(str(base)) + N * len(str(max_local)) + seps
- Lower bound se max_local < max original

Encoder #8 (suffix comum):
- emit "suffix|prefix1,prefix2,..." onde prefix = value sem suffix
- Bytes: len(suffix) + N * len(avg_prefix) + seps

Se padroes existem E ganho potencial >= 5% weighted: GO.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode as tcf_encode  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def _is_numeric(v):
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def ler_csv_single_col(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def detect_common_suffix(values, min_frac=0.8, min_len=2):
    """Detecta suffix mais comum compartilhado por >= min_frac das strings.

    Retorna (suffix, fraction) ou (None, 0) se nao encontrar.
    """
    if not values:
        return None, 0
    # Sample top 100 pra eficiencia em datasets grandes
    sample = values[:min(1000, len(values))]
    # Para cada length de suffix candidato, contar mais frequente
    best = None
    best_frac = 0
    max_suf_len = min(10, min(len(v) for v in sample) if sample else 0)
    for suf_len in range(min_len, max_suf_len + 1):
        cnt = Counter(v[-suf_len:] for v in sample if len(v) >= suf_len)
        if not cnt:
            continue
        most_common, freq = cnt.most_common(1)[0]
        frac = freq / len(sample)
        if frac >= min_frac and frac > best_frac:
            best = most_common
            best_frac = frac
    return best, best_frac


def detect_common_prefix(values, min_frac=0.5, min_ratio=0.5):
    """Detecta prefix mais comum compartilhado por >= min_frac das strings,
    com tamanho >= min_ratio * avg_len.

    Retorna (prefix, fraction) ou (None, 0).
    """
    if not values:
        return None, 0
    sample = values[:min(1000, len(values))]
    avg_len = sum(len(v) for v in sample) / len(sample)
    best = None
    best_frac = 0
    max_pre_len = min(20, max(int(avg_len), 1))
    for pre_len in range(2, max_pre_len + 1):
        cnt = Counter(v[:pre_len] for v in sample if len(v) >= pre_len)
        if not cnt:
            continue
        most_common, freq = cnt.most_common(1)[0]
        frac = freq / len(sample)
        if frac >= min_frac and pre_len >= min_ratio * avg_len:
            if frac > best_frac:
                best = most_common
                best_frac = frac
    return best, best_frac


def detect_range_narrow(values):
    """Detecta se valores numericos tem range narrow.

    Retorna dict com {min, max, range_ratio, n_digits_all_same}.
    """
    nums = []
    for v in values:
        try:
            nums.append(float(v))
        except (ValueError, TypeError):
            return None
    if not nums:
        return None
    min_v = min(nums)
    max_v = max(nums)
    range_v = max_v - min_v
    # avoid div by zero
    if min_v == 0:
        range_ratio = float('inf') if range_v > 0 else 0
    else:
        range_ratio = abs(max_v / min_v) if min_v != 0 else 0
    # All same digit count (como strings)?
    digit_counts = Counter(len(v) for v in values[:100])
    n_digits_all_same = (len(digit_counts) == 1)
    return {
        'min': min_v, 'max': max_v, 'range_ratio': range_ratio,
        'n_digits_all_same': n_digits_all_same,
        'narrow': range_ratio < 10 or n_digits_all_same,
    }


def estimate_encoder_suffix(values, suffix):
    """Lower bound bytes com encoder #8 (suffix comum)."""
    if not suffix:
        return None
    prefixes = [v[:-len(suffix)] for v in values if v.endswith(suffix)]
    others = [v for v in values if not v.endswith(suffix)]
    # bytes = len(suffix) + sum(len(p) for p in prefixes) + (N_prefixes - 1) seps
    #       + len(others as M10)
    n_pref = len(prefixes)
    pref_bytes = sum(len(p) for p in prefixes) + max(0, n_pref - 1)
    suffix_overhead = len(suffix) + 2  # marker + sep
    # others sao codificados separado (estimar como soma de lens)
    others_bytes = sum(len(o) for o in others) + max(0, len(others) - 1)
    return suffix_overhead + pref_bytes + others_bytes


def estimate_encoder_range(values):
    """Lower bound bytes com encoder #5 (base + local)."""
    nums = []
    for v in values:
        try:
            nums.append(int(float(v)))
        except (ValueError, TypeError):
            return None
    if not nums:
        return None
    base = min(nums)
    locals_v = [n - base for n in nums]
    max_local = max(locals_v)
    if max_local == 0:
        local_digits = 1
    else:
        local_digits = len(str(max_local))
    base_bytes = len(str(base)) + 1  # base + sep
    body_bytes = len(nums) * local_digits + max(0, len(nums) - 1)
    return base_bytes + body_bytes


def analyze_col(source, name, values):
    if not values:
        return None
    n_rows = len(values)
    avg_len = sum(len(v) for v in values) / n_rows
    sample = values[:min(20, n_rows)]
    is_num = all(_is_numeric(v) for v in sample) if sample else False

    body_m10 = tcf_encode(values)
    bytes_m10 = len(body_m10.encode("utf-8"))

    result = {
        'source': source,
        'col': name,
        'n_rows': n_rows,
        'avg_len': avg_len,
        'is_numeric': is_num,
        'bytes_m10': bytes_m10,
    }

    # Detect suffix
    suffix, suf_frac = detect_common_suffix(values)
    result['common_suffix'] = suffix
    result['suffix_frac'] = suf_frac
    if suffix and suf_frac >= 0.8:
        est = estimate_encoder_suffix(values, suffix)
        if est is not None:
            result['bytes_enc_suffix'] = est
            result['gain_suffix_pct'] = (bytes_m10 - est) / bytes_m10 * 100

    # Detect prefix
    prefix, pre_frac = detect_common_prefix(values)
    result['common_prefix'] = prefix
    result['prefix_frac'] = pre_frac

    # Detect range narrow (so' pra numericos)
    if is_num:
        range_info = detect_range_narrow(values)
        if range_info:
            result['range_info'] = range_info
            if range_info['narrow']:
                est = estimate_encoder_range(values)
                if est is not None:
                    result['bytes_enc_range'] = est
                    result['gain_range_pct'] = (bytes_m10 - est) / bytes_m10 * 100

    return result


def main():
    print("=== Sub-exp 01 — caracterizar padroes #5 (range) e #8 (suffix) ===\n")
    datasets_dir = ROOT / "datasets" / "synthetic"

    all_results = []

    # D1-D9
    print(">> D1-D9 controle")
    for ds in D1_D9:
        values = ler_csv_single_col(datasets_dir / f"{ds}.csv")
        r = analyze_col('sintetico', ds, values)
        if r:
            all_results.append(r)

    # Adult Census
    print(">> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = analyze_col(f"adult-{vol}", cname, vals)
            if r:
                all_results.append(r)
    reader.close()

    # TPC-H
    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = analyze_col(f"tpch.{table}-5k", cname, vals)
            if r:
                all_results.append(r)
    reader.close()

    # ---- Analise suffix comum (#8 arredondamento) ----
    print(f"\n=== Padroes #8 — suffix comum (>= 80% das strings) ===\n")
    with_suffix = [r for r in all_results
                   if r.get('common_suffix') and r.get('suffix_frac', 0) >= 0.8]
    print(f"Colunas com suffix comum: {len(with_suffix)}/{len(all_results)}")
    if with_suffix:
        print(f"\n{'source':<18} {'col':<22} {'suffix':<10} {'frac':>5} "
              f"{'m10':>7} {'enc':>7} {'gain':>7}")
        for r in sorted(with_suffix, key=lambda x: -(x.get('gain_suffix_pct', 0))):
            gain = r.get('gain_suffix_pct', 0)
            enc = r.get('bytes_enc_suffix', 0)
            print(f"{r['source']:<18} {r['col']:<22} {r['common_suffix']!r:<10} "
                  f"{r['suffix_frac']:.2f} {r['bytes_m10']:>7,} "
                  f"{enc:>7,} {gain:>+6.2f}%")

    # ---- Analise range narrow (#5 range) ----
    print(f"\n=== Padroes #5 — range narrow numerico ===\n")
    with_range = [r for r in all_results
                  if r.get('range_info', {}).get('narrow', False)
                  and r.get('bytes_enc_range') is not None]
    print(f"Colunas com range narrow + encoder estimativel: {len(with_range)}")
    if with_range:
        print(f"\n{'source':<18} {'col':<22} {'min':>8} {'max':>8} "
              f"{'m10':>7} {'enc':>7} {'gain':>7}")
        for r in sorted(with_range, key=lambda x: -(x.get('gain_range_pct', 0))):
            gain = r.get('gain_range_pct', 0)
            enc = r.get('bytes_enc_range', 0)
            info = r['range_info']
            print(f"{r['source']:<18} {r['col']:<22} "
                  f"{info['min']:>8.0f} {info['max']:>8.0f} "
                  f"{r['bytes_m10']:>7,} {enc:>7,} {gain:>+6.2f}%")

    # ---- Veredito ----
    print(f"\n=== Veredito ===\n")
    # Real-world only (excl sintetico)
    rw = [r for r in all_results if r['source'] != 'sintetico']
    rw_m10_total = sum(r['bytes_m10'] for r in rw)

    # Suffix gains real-world
    rw_suffix = [r for r in with_suffix if r['source'] != 'sintetico']
    rw_suffix_savings = sum(r['bytes_m10'] - r['bytes_enc_suffix']
                            for r in rw_suffix if r.get('bytes_enc_suffix'))
    rw_suffix_pct = rw_suffix_savings / rw_m10_total * 100 if rw_m10_total else 0

    # Range gains real-world
    rw_range = [r for r in with_range if r['source'] != 'sintetico']
    rw_range_savings = sum(r['bytes_m10'] - r['bytes_enc_range']
                           for r in rw_range if r.get('bytes_enc_range'))
    rw_range_pct = rw_range_savings / rw_m10_total * 100 if rw_m10_total else 0

    print(f"Real-world total M10: {rw_m10_total:,}B")
    print(f"#8 Suffix encoder potential: {rw_suffix_savings:+,}B "
          f"({rw_suffix_pct:+.2f}% weighted)")
    print(f"#5 Range encoder potential: {rw_range_savings:+,}B "
          f"({rw_range_pct:+.2f}% weighted)")

    if rw_suffix_pct >= 5 or rw_range_pct >= 5:
        veredito = "GO: pelo menos uma natureza >= 5% weighted potential"
        status = "go-prototype"
    elif rw_suffix_pct >= 2 or rw_range_pct >= 2:
        veredito = "MARGINAL: 2-5% potential. Decisao pelo dono."
        status = "marginal"
    else:
        veredito = "NO-GO: ambas naturezas < 2% weighted (M10 ja' captura bem ou padroes raros)"
        status = "no-go"

    print(f"\n{veredito}")
    print(f"Status: {status}")

    # Report
    report = [
        "# Sub-exp 01 — caracterizar naturezas raras #5 (range) e #8 (suffix)",
        "",
        "## Setup",
        "",
        "Caracterizacao observacional de padroes em Adult+TPC-H + D1-D9 controle.",
        "",
        f"Total colunas analisadas: {len(all_results)}",
        f"Real-world (excl sintetico): {len(rw)}",
        "",
        "## Padroes #8 — Suffix comum",
        "",
        f"Colunas com suffix comum (>= 80%): {len(with_suffix)}",
        "",
    ]
    if with_suffix:
        report.append("| Source | Col | Suffix | Frac | M10 | Enc | Gain |")
        report.append("|---|---|---|---:|---:|---:|---:|")
        for r in sorted(with_suffix, key=lambda x: -(x.get('gain_suffix_pct', 0))):
            gain = r.get('gain_suffix_pct', 0)
            enc = r.get('bytes_enc_suffix', 0)
            report.append(f"| {r['source']} | {r['col']} | `{r['common_suffix']}` | "
                          f"{r['suffix_frac']:.2f} | {r['bytes_m10']:,} | "
                          f"{enc:,} | {gain:+.2f}% |")

    report.extend([
        "",
        "## Padroes #5 — Range narrow numerico",
        "",
        f"Colunas com range narrow: {len(with_range)}",
        "",
    ])
    if with_range:
        report.append("| Source | Col | Min | Max | M10 | Enc | Gain |")
        report.append("|---|---|---:|---:|---:|---:|---:|")
        for r in sorted(with_range, key=lambda x: -(x.get('gain_range_pct', 0))):
            gain = r.get('gain_range_pct', 0)
            enc = r.get('bytes_enc_range', 0)
            info = r['range_info']
            report.append(f"| {r['source']} | {r['col']} | "
                          f"{info['min']:.0f} | {info['max']:.0f} | "
                          f"{r['bytes_m10']:,} | {enc:,} | {gain:+.2f}% |")

    report.extend([
        "",
        "## Agregado real-world",
        "",
        f"- Total M10: {rw_m10_total:,}B",
        f"- **#8 Suffix potential**: {rw_suffix_savings:+,}B "
        f"({rw_suffix_pct:+.2f}% weighted)",
        f"- **#5 Range potential**: {rw_range_savings:+,}B "
        f"({rw_range_pct:+.2f}% weighted)",
        "",
        "## Veredito",
        "",
        f"**{veredito}**",
        "",
        f"**Status**: `{status}`",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()
