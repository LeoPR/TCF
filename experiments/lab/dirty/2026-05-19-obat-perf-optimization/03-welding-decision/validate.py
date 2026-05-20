"""Validacao isolada: v3 monkey-patched no pipeline completo.

Roda:
1. D1-D9 single-column via `tcf.encode` → comparar bytes (esperar 1615)
2. lineitem 5000 via `multi_col.encode_table` → comparar bytes vs
   baseline EXP-014 (498,271) + tempo

Output: result.md (preenchido) com OK/FAIL por etapa.
"""

from __future__ import annotations

import csv
import io
import sys
import time
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
PROTO_DIR = THIS.parent / "02-index-prototypes"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = ROOT / "experiments" / "lab" / "clean" / "EXP-011-multi-column-basic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(PROTO_DIR))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))

import obat_v3_hash_pref_suf as v3  # noqa: E402

# Importa tcf modules (cacheia `from tcf.core.online import processar`)
import tcf.core.online as online_mod  # noqa: E402
import tcf.encoder as encoder_mod  # noqa: E402

# IMPORTANTE: v3 herdou TokLit/TokRefPref/TokRefSuf de obat_v0_baseline.
# HCC (syntax.py) usa isinstance contra tcf.core.online.TokLit etc.
# Substitui classes no namespace do v3 pra usar canonical.
v3.TokLit = online_mod.TokLit
v3.TokRefPref = online_mod.TokRefPref
v3.TokRefSuf = online_mod.TokRefSuf

# MONKEY-PATCH: substitui processar em todos os namespaces que ja
# capturaram a referencia
online_mod.processar = v3.processar
encoder_mod.processar = v3.processar

# Importa pipeline downstream APOS patch
import delta_aware  # noqa: E402
delta_aware.processar = v3.processar

from tcf import encode, decode  # noqa: E402
from multi_col import encode_table, decode_table  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402


D1_D9 = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
]
D1_D9_EXPECTED = 1615  # M9 baseline


def ler_csv(path: Path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # header
        return [row[0] for row in r if row]


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def table_to_csv_bytes(cols):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    cs = list(cols.keys())
    w.writerow(cs)
    n = len(next(iter(cols.values())))
    for i in range(n):
        w.writerow([cols[c][i] for c in cs])
    return buf.getvalue().encode("utf-8")


def validate_d1_d9():
    print("=== Validacao D1-D9 (single-col) ===")
    datasets_dir = ROOT / "datasets" / "synthetic"
    total = 0
    rt_ok = 0
    rows = []
    for name in D1_D9:
        linhas = ler_csv(datasets_dir / f"{name}.csv")
        tcf_text = encode(linhas)
        bytes_n = len(tcf_text.encode("utf-8"))
        decoded = decode(tcf_text)
        rt = (decoded == linhas)
        rt_ok += int(rt)
        total += bytes_n
        print(f"  {name}: {bytes_n}B, RT={'OK' if rt else 'FAIL'}")
        rows.append({"ds": name, "bytes": bytes_n, "rt": rt})
    print(f"  TOTAL: {total}B (esperado {D1_D9_EXPECTED}B) — "
          f"{'OK' if total == D1_D9_EXPECTED else 'DIVERGENCIA'}")
    print(f"  RT: {rt_ok}/9")
    return {"total": total, "rt": rt_ok, "rows": rows,
            "expected": D1_D9_EXPECTED,
            "match": total == D1_D9_EXPECTED}


def validate_lineitem(volume):
    print(f"\n=== Validacao lineitem {volume} rows (multi-col) ===")
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=volume)
    reader.close()
    cols = rows_to_cols(rows)

    raw_bytes = len(table_to_csv_bytes(cols))

    t0 = time.perf_counter()
    tcf, info = encode_table(cols)
    t_encode = time.perf_counter() - t0

    bytes_tcf = len(tcf.encode("utf-8"))
    t1 = time.perf_counter()
    decoded = decode_table(tcf)
    t_decode = time.perf_counter() - t1
    rt = (decoded == cols)

    print(f"  raw: {raw_bytes:,}B")
    print(f"  TCF: {bytes_tcf:,}B (ratio {bytes_tcf/raw_bytes*100:.1f}%)")
    print(f"  encode: {t_encode:.2f}s")
    print(f"  decode: {t_decode:.3f}s")
    print(f"  RT: {'OK' if rt else 'FAIL'}")

    return {"volume": volume, "raw": raw_bytes, "tcf": bytes_tcf,
            "t_encode": t_encode, "t_decode": t_decode, "rt": rt}


def main():
    print("Monkey-patched: tcf.core.online.processar = obat_v3_hash_pref_suf")
    print(f"Confirma: {online_mod.processar.__module__}.{online_mod.processar.__name__}")
    print()

    d1_d9 = validate_d1_d9()
    li1k = validate_lineitem(1000)
    li5k = validate_lineitem(5000)

    # Baseline EXP-014: 1000=10.2s/102,366B, 5000=71.5s/498,271B
    BASELINE = {
        1000: {"bytes": 102366, "encode": 10.2},
        5000: {"bytes": 498271, "encode": 71.5},
    }

    print("\n=== Resumo ===")
    print(f"D1-D9: {d1_d9['total']}B == {D1_D9_EXPECTED}B "
          f"({'OK' if d1_d9['match'] else 'FAIL'})")
    print(f"D1-D9 RT: {d1_d9['rt']}/9")
    for r in [li1k, li5k]:
        v = r["volume"]
        bs = BASELINE[v]
        bytes_ok = (r["tcf"] == bs["bytes"])
        speedup = bs["encode"] / r["t_encode"] if r["t_encode"] > 0 else 0
        baseline_str = f"{bs['bytes']:,}"
        diff_str = "OK" if bytes_ok else f"DIV vs {baseline_str}"
        rt_str = "OK" if r['rt'] else "FAIL"
        print(f"lineitem {v}: bytes={r['tcf']:,}B "
              f"({diff_str}), "
              f"encode={r['t_encode']:.2f}s "
              f"(speedup vs baseline {speedup:.1f}x), "
              f"RT={rt_str}")

    # Write result.md
    report = [
        "# Sub-exp 03 — validate (resultado)",
        "",
        f"**Setup**: monkey-patch v3 → `tcf.core.online.processar`",
        f"**Encoder usado**: `{online_mod.processar.__module__}.{online_mod.processar.__name__}`",
        "",
        "## D1-D9 (byte-canonical M9 = 1615B)",
        "",
        f"**Total**: {d1_d9['total']}B "
        f"({'OK' if d1_d9['match'] else 'DIVERGENCIA'})",
        f"**RT**: {d1_d9['rt']}/9",
        "",
        "| dataset | bytes | RT |",
        "|---|---:|---|",
    ]
    for r in d1_d9["rows"]:
        report.append(f"| {r['ds']} | {r['bytes']} | {'OK' if r['rt'] else 'FAIL'} |")

    report.extend([
        "",
        "## lineitem multi-col (vs baseline EXP-014)",
        "",
        "| volume | raw (B) | TCF (B) | baseline | match | encode (s) | baseline | speedup | decode (s) | RT |",
        "|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ])
    for r in [li1k, li5k]:
        v = r["volume"]
        bs = BASELINE[v]
        match = "OK" if r["tcf"] == bs["bytes"] else "DIV"
        speedup = bs["encode"] / r["t_encode"] if r["t_encode"] > 0 else 0
        report.append(
            f"| {v} | {r['raw']:,} | {r['tcf']:,} | {bs['bytes']:,} | {match} | "
            f"{r['t_encode']:.2f} | {bs['encode']:.1f} | {speedup:.1f}x | "
            f"{r['t_decode']:.3f} | {'OK' if r['rt'] else 'FAIL'} |"
        )

    overall_ok = (d1_d9["match"] and d1_d9["rt"] == 9
                  and li1k["rt"] and li5k["rt"]
                  and li1k["tcf"] == BASELINE[1000]["bytes"]
                  and li5k["tcf"] == BASELINE[5000]["bytes"])
    report.append("")
    report.append(f"## Verdict")
    report.append("")
    report.append(f"**{'PROCEDER COM WELDING' if overall_ok else 'NAO PROCEDER — investigar'}**")
    if overall_ok:
        report.append("")
        report.append("Bytes IDENTICOS em D1-D9 + lineitem 1k/5k. RT 100%.")
        report.append("v3 e' substituto byte-canonical seguro.")
        report.append("")
        report.append("Proximo: editar `src/tcf/core/online.py` aplicando v3.")

    write_lf(THIS / "result.md", "\n".join(report) + "\n")
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
