"""EXP-010 — valida prototype em 20 datasets sinteticos.

Verifica:
1. Bytes ~= sub-exp 09 (delta < 5 por dataset)
2. RT 20/20 OK
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(THIS))

from delta_aware import encode_column, decode_column  # noqa: E402


DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
    "D11a-datas-dia",
    "D11b-datas-borda",
    "D11c-datas-mensal",
    "D11d-datetime-min",
    "D11e-datetime-mensal",
    "D11f-datetime-ms",
    "D11g-datetime-us",
    "D11h-datetime-ns",
    "D16a-ids-3digits",
    "D16b-ids-4digits",
    "D16c-ids-prefixados",
]

REFERENCE_DIR = (ROOT / "experiments" / "lab" / "dirty"
                 / "2026-05-17-OBAT-delta-aware"
                 / "09-auto-detect-cadence-heuristic" / "outputs")


def write_lf(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def load_rows(ds):
    p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with p.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def load_reference_body(ds):
    """Carrega body auto-detect do sub-exp 09 pra comparativo."""
    p = REFERENCE_DIR / ds / "body-auto.tcf"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def process(ds):
    rows = load_rows(ds)
    body, info = encode_column(rows)
    bytes_proto = len(body.encode("utf-8"))

    decoded = decode_column(body)
    rt_ok = (decoded == rows)
    rt = "OK" if rt_ok else "FAIL"

    # Reference (dirty lab sub-exp 09)
    ref_body = load_reference_body(ds)
    if ref_body is not None:
        bytes_ref = len(ref_body.encode("utf-8"))
        body_match = (body == ref_body)
    else:
        bytes_ref = None
        body_match = None

    out = THIS / "outputs" / f"{ds}.tcf"
    write_lf(out, body)

    return {
        "dataset": ds,
        "rows": len(rows),
        "unicas": info["n_unicas"],
        "cadence_detected": info["cadence_detected"],
        "hint_used": info["hint_used"],
        "n_seq_runs": info["n_seq_runs"],
        "bytes_proto": bytes_proto,
        "bytes_ref": bytes_ref,
        "body_match": body_match,
        "delta_bytes": (bytes_proto - bytes_ref) if bytes_ref else None,
        "rt": rt,
    }


def main():
    print("=== EXP-010 — TCF delta-aware prototype ===\n")
    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        det = "[on]" if r['cadence_detected'] else "[off]"
        match = "match" if r['body_match'] else "DIFF" if r['body_match'] is not None else "noref"
        d_str = f"{r['delta_bytes']:+d}" if r['delta_bytes'] is not None else "---"
        print(f"  {ds:24} {det:5}  bytes={r['bytes_proto']:4}  "
              f"ref={r['bytes_ref'] or '---':>4}  d={d_str:>4}  "
              f"{match:5}  runs={r['n_seq_runs']}  RT={r['rt']}")

    total_proto = sum(r['bytes_proto'] for r in results)
    total_ref = sum(r['bytes_ref'] for r in results if r['bytes_ref'])
    rt_pass = sum(1 for r in results if r['rt'] == 'OK')
    body_match_count = sum(1 for r in results if r['body_match'])
    cadence_detected = sum(1 for r in results if r['cadence_detected'])

    # Manifest
    manifest = []
    for r in results:
        m = {k: v for k, v in r.items() if k != 'detect_info'}
        manifest.append(m)
    write_lf(THIS / "manifest.jsonl",
             "\n".join(json.dumps(m) for m in manifest) + "\n")

    # Report
    out = [
        "# EXP-010 — Prototype TCF delta-aware (report)",
        "",
        f"**Total bytes prototype**: {total_proto}",
        f"**Total bytes reference (sub-exp 09 dirty)**: {total_ref}",
        f"**Diff**: {total_proto - total_ref:+d} bytes",
        f"**RT**: {rt_pass}/{len(results)}",
        f"**Body byte-match com referencia**: {body_match_count}/{len(results)}",
        f"**Cadence detected**: {cadence_detected}/{len(results)}",
        "",
        "## Tabela",
        "",
        "| Dataset | det? | runs | bytes proto | bytes ref | Δ | body match | RT |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        det = "yes" if r['cadence_detected'] else "no"
        match = "✓" if r['body_match'] else "✗" if r['body_match'] is False else "?"
        d_str = f"{r['delta_bytes']:+d}" if r['delta_bytes'] is not None else "---"
        out.append(f"| {r['dataset']} | {det} | {r['n_seq_runs']} | "
                   f"{r['bytes_proto']} | {r['bytes_ref'] or '---'} | "
                   f"{d_str} | {match} | {r['rt']} |")
    out.append("")
    out.append("## Validacao")
    out.append("")
    if total_proto == total_ref and rt_pass == len(results) and body_match_count == len(results):
        out.append("✓ **WELDED OK**: bytes identicos a referencia, RT 100%, "
                   "byte-match em todos datasets.")
    elif rt_pass == len(results):
        out.append("⚠ **RT OK mas bytes diferem**: investigar divergencia "
                   "vs dirty lab.")
    else:
        out.append("✗ **WELDING FALHOU**: RT failures ou bugs.")
    out.append("")
    out.append("## Pipeline")
    out.append("")
    out.append("Pipeline single-column:")
    out.append("```")
    out.append("rows = load")
    out.append("unicas = dedup_preserve_order(rows)")
    out.append("detected, _ = detect_cadence(unicas, threshold=0.7)")
    out.append("if detected:")
    out.append("    tokens = processar_with_hint(unicas, "
               "prefer_shape_consistency=True)")
    out.append("else:")
    out.append("    tokens = processar(unicas)  # canonical")
    out.append("body = HCCSeqRLE().encode(rows, unicas, tokens)")
    out.append("```")
    out.append("")
    out.append("## Limitacoes")
    out.append("")
    out.append("- Single-column. Multi-column expansao futura.")
    out.append("- Datasets sao **sinteticos**. Real-world (TPC-H, "
               "Adult Census) NAO testado.")
    out.append("- Threshold 0.7 do auto-detect e' arbitrario.")
    out.append("")
    write_lf(THIS / "report.md", "\n".join(out) + "\n")
    print()
    print(f"Totais: proto={total_proto}, ref={total_ref}, "
          f"diff={total_proto - total_ref:+d}")
    print(f"RT: {rt_pass}/{len(results)} | body-match: {body_match_count}/{len(results)}")
    print(f"\nreport.md: {THIS / 'report.md'}")


if __name__ == "__main__":
    main()
