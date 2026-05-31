"""Profile HCC focado em _detect_compositions — lineitem 5000.

Roda cProfile no pipeline completo e extrai stats de syntax.py.
Tambem instrumenta _detect_compositions com contadores de escala
(via monkey-patch leve).
"""

from __future__ import annotations

import cProfile
import csv
import io
import pstats
import sys
import time
from collections import defaultdict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = ROOT / "experiments" / "lab" / "clean" / "EXP-011-multi-column-basic"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))

from dataset_reader import DatasetReader  # noqa: E402
from multi_col import encode_table  # noqa: E402

# Instrumentar _detect_compositions pra contar escala
from tcf.composicional import syntax as hcc_syntax  # noqa: E402

orig_detect = hcc_syntax.M8AVirtualRefsSyntax._detect_compositions
scale_log = []


def instrumented_detect(self, pieces_per_line, atom_count):
    # Conta tamanho do input antes
    n_lines = sum(1 for p in pieces_per_line if p is not None)
    n_refs_total = 0
    refs_max_len = 0
    for p in pieces_per_line:
        if p is None:
            continue
        for piece in p:
            if piece[0] == 'refs':
                refs = piece[1]
                n_refs_total += len(refs)
                if len(refs) > refs_max_len:
                    refs_max_len = len(refs)

    t0 = time.perf_counter()
    result = orig_detect(self, pieces_per_line, atom_count)
    t = time.perf_counter() - t0
    alias_to_sub, iter_traces = result
    scale_log.append({
        "n_lines": n_lines,
        "n_refs_total": n_refs_total,
        "refs_max_len": refs_max_len,
        "atom_count": atom_count,
        "n_iter_outer": len(iter_traces),
        "n_aliases_picked": len(alias_to_sub),
        "n_candidates_first_iter": iter_traces[0].get("n_candidates", 0) if iter_traces else 0,
        "n_pairs_first_iter": iter_traces[0].get("n_pairs", 0) if iter_traces else 0,
        "time_total_s": t,
    })
    return result


hcc_syntax.M8AVirtualRefsSyntax._detect_compositions = instrumented_detect


VOLUME = 5000
TABLE = "lineitem"


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def fmt_stats(profile_path, sort_by, top_n=30, restrict=None):
    buf = io.StringIO()
    p = pstats.Stats(str(profile_path), stream=buf)
    p.strip_dirs().sort_stats(sort_by)
    if restrict:
        p.print_stats(restrict, top_n)
    else:
        p.print_stats(top_n)
    return buf.getvalue()


def main():
    print(f"=== Profile HCC — {TABLE} {VOLUME} rows ===")

    print("Reading rows...")
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows(TABLE, limit=VOLUME)
    reader.close()
    cols = rows_to_cols(rows)
    print(f"  {len(rows)} rows × {len(cols)} cols")

    print("Profiling encode_table...")
    profile_path = THIS / "hcc_baseline.prof"
    profiler = cProfile.Profile()
    t1 = time.perf_counter()
    profiler.enable()
    tcf, info = encode_table(cols)
    profiler.disable()
    t_encode = time.perf_counter() - t1
    profiler.dump_stats(str(profile_path))
    print(f"  encode: {t_encode:.1f}s  bytes_tcf: {len(tcf):,}")

    # Reports
    cumulative_syntax = fmt_stats(profile_path, "cumulative", 30, "syntax.py")
    tottime_syntax = fmt_stats(profile_path, "tottime", 30, "syntax.py")
    cumulative_all = fmt_stats(profile_path, "cumulative", 20)
    callers = ""
    try:
        buf = io.StringIO()
        p = pstats.Stats(str(profile_path), stream=buf)
        p.strip_dirs().print_callers("_detect_compositions",
                                      "_estimate_baseline_chars")
        callers = buf.getvalue()
    except Exception as e:
        callers = f"(failed: {e})"

    # Scale log resumido
    scale_summary = ["", "## Scale por coluna (instrumented)", "",
                     "| col_idx | n_lines | n_refs_total | refs_max_len | "
                     "atom_count | n_iter | n_aliases | candidates_iter1 | pairs_iter1 | time(s) |",
                     "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for i, s in enumerate(scale_log):
        scale_summary.append(
            f"| {i+1} | {s['n_lines']} | {s['n_refs_total']} | "
            f"{s['refs_max_len']} | {s['atom_count']} | {s['n_iter_outer']} | "
            f"{s['n_aliases_picked']} | {s['n_candidates_first_iter']} | "
            f"{s['n_pairs_first_iter']} | {s['time_total_s']:.2f} |"
        )

    # Totals
    total_time_detect = sum(s["time_total_s"] for s in scale_log)
    total_iters = sum(s["n_iter_outer"] for s in scale_log)
    total_candidates = sum(s["n_candidates_first_iter"] for s in scale_log)
    total_pairs = sum(s["n_pairs_first_iter"] for s in scale_log)

    report = [
        "# Sub-exp 01 — profile HCC (resultado)",
        "",
        f"**Dataset**: {TABLE} {VOLUME} rows × {len(cols)} cols",
        f"**Encode time (com cProfile)**: {t_encode:.1f}s",
        f"**Bytes TCF**: {len(tcf):,}",
        f"**Total _detect_compositions time**: {total_time_detect:.2f}s "
        f"({total_time_detect/t_encode*100:.0f}% do encode)",
        f"**Total outer iterations**: {total_iters} (16 cols)",
        f"**Total candidates iter1**: {total_candidates}",
        f"**Total pairs (R>=2) iter1**: {total_pairs}",
        "",
        "## Top 30 cumulative — syntax.py",
        "",
        "```",
        cumulative_syntax.strip(),
        "```",
        "",
        "## Top 30 tottime (self) — syntax.py",
        "",
        "```",
        tottime_syntax.strip(),
        "```",
        "",
        "## Top 20 cumulative — geral",
        "",
        "```",
        cumulative_all.strip(),
        "```",
        "",
        "## Callers `_detect_compositions` + `_estimate_baseline_chars`",
        "",
        "```",
        callers.strip() if callers else "(no data)",
        "```",
    ]
    report.extend(scale_summary)
    report.append("")
    report.append("## Analise")
    report.append("")
    report.append("*(preencher manual apos rodar)*")
    report.append("")

    write_lf(THIS / "result.md", "\n".join(report) + "\n")
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
