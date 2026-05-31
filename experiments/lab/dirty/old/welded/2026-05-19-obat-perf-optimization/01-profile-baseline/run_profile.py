"""Profile OBAT baseline em lineitem 5000 rows.

Roda cProfile em encode_table (pipeline EXP-011 + ADR-0008) e dumpa
stats em result.md.
"""

from __future__ import annotations

import cProfile
import csv
import io
import pstats
import sys
import time
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


def fmt_stats(profile_path: Path, sort_by: str, top_n: int = 30) -> str:
    """Retorna string com top_n linhas formatadas."""
    buf = io.StringIO()
    p = pstats.Stats(str(profile_path), stream=buf)
    p.strip_dirs().sort_stats(sort_by).print_stats(top_n)
    return buf.getvalue()


def fmt_callers(profile_path: Path, func_names: list[str]) -> str:
    """Retorna callers das funcoes especificadas."""
    buf = io.StringIO()
    p = pstats.Stats(str(profile_path), stream=buf)
    p.strip_dirs().print_callers(*func_names)
    return buf.getvalue()


def main():
    print(f"=== Profile baseline — {TABLE} {VOLUME} rows ===")

    print("Reading rows...")
    t0 = time.perf_counter()
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows(TABLE, limit=VOLUME)
    reader.close()
    cols = rows_to_cols(rows)
    t_read = time.perf_counter() - t0
    print(f"  {len(rows)} rows × {len(cols)} cols read in {t_read:.1f}s")

    profile_path = THIS / "baseline.prof"

    print("Profiling encode_table...")
    profiler = cProfile.Profile()
    t1 = time.perf_counter()
    profiler.enable()
    tcf, info = encode_table(cols)
    profiler.disable()
    t_encode = time.perf_counter() - t1

    profiler.dump_stats(str(profile_path))
    print(f"  encode: {t_encode:.1f}s  bytes_tcf: {len(tcf):,}")
    print(f"  profile dumped: {profile_path}")

    bytes_tcf = len(tcf.encode("utf-8"))

    # Stats
    print("\nGenerating report...")
    cumulative = fmt_stats(profile_path, "cumulative", 30)
    tottime = fmt_stats(profile_path, "tottime", 30)
    callers = fmt_callers(profile_path, ["_melhor_pref", "_melhor_suf",
                                          "_escolher_par", "lcp_len", "lcs_len"])

    # Conta colunas com cadence detectada (impacta no fork seq-RLE do HCC)
    cad = sum(1 for ci in info["col_info"].values() if ci.get("cadence_detected"))

    report = [
        "# Sub-exp 01 — profile baseline (resultado)",
        "",
        f"**Dataset**: {TABLE} {VOLUME} rows × {len(cols)} colunas",
        f"**Encode time**: {t_encode:.1f}s",
        f"**Bytes TCF**: {bytes_tcf:,}",
        f"**Cadence detected**: {cad}/{len(cols)} colunas",
        "",
        "## Top 30 por cumulative time",
        "",
        "```",
        cumulative.strip(),
        "```",
        "",
        "## Top 30 por tottime (self time)",
        "",
        "```",
        tottime.strip(),
        "```",
        "",
        "## Callers das funcoes OBAT-core",
        "",
        "```",
        callers.strip(),
        "```",
        "",
        "## Analise",
        "",
        "*(preencher manual apos rodar)*",
        "",
    ]
    write_lf(THIS / "result.md", "\n".join(report) + "\n")
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()
