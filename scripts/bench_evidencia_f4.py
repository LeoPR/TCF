"""F4-mínimo — públicos nos hubs PRONTOS (T-QA-8 F4; T-REL-08 R1/2d).

Escopo MÍNIMO (fila ROI 2026-07-12): os hubs já prontos, com AMOSTRAS
determinísticas ("primeiros N", precedente das fixtures real-world) — a
população total (tpch-sf01 600k, tabelas cheias de 500k) fica pra janela
dedicada pós-release (decisão F3, T-REL-08).

Casos: adult · tpch-sf001 (lineitem + customer) · ibge (FULL) · br-identidades
(pessoas/empresas, com e sem natures) · receita-cnpj (REAL, nature cnpj — a
fonte confirmada-empirica). Natures: valores DV-válidos ficam no hub Z:/ e nos
registros só CONTAGENS (§2.3) — NENHUM blob salvo no f4.

Sinal de compressão externa (§2.8, qualitativo): zlib/gzip (stdlib) sempre;
brotli só se importável (sonda graciosa — F0-3). Nunca é gate.

Saída: experiments/results/evidencia-0.8/f4-minimo/ (JSONL + RESULT.md gerado).
"""
from __future__ import annotations

import csv
import io
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_evidencia import RESULTS_DIR, run_case, validate_pins, write_jsonl  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from tcf import SPEC_CNPJ, SPEC_CPF  # noqa: E402

F4 = RESULTS_DIR / "f4-minimo"
SAMPLE = 5000            # "primeiros N" determinístico (precedente fixtures 2k)

try:
    import brotli  # type: ignore
    _BR = lambda b: len(brotli.compress(b, quality=11))   # noqa: E731
    _BR_NAME = "brotli-q11"
except ImportError:
    _BR, _BR_NAME = None, None

_summary: list[dict] = []


def _cols_from_hub(ds: str, table: str, limit: int | None) -> dict[str, list[str]]:
    """Colunas do hub -> dict[str, list[str]] (mesma conversão do encode:
    str(v), None->''). Amostra = primeiros `limit` (determinístico)."""
    r = DatasetReader(ds)
    try:
        rows = r.rows(table, limit=limit)
    finally:
        r.close()
    if not rows:
        raise RuntimeError(f"{ds}.{table}: 0 linhas")
    cols: dict[str, list[str]] = {k: [] for k in rows[0].keys()}
    for row in rows:
        for k, v in row.items():
            cols[k].append("" if v is None else str(v))
    return cols


def _csv_bytes(cols: dict[str, list[str]]) -> int:
    """Baseline CSV honesto (csv.writer, quoting mínimo, LF)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(list(cols))
    for row in zip(*cols.values()):
        w.writerow(row)
    return len(buf.getvalue().encode("utf-8"))


def case(cid: str, ds: str, table: str, *, limit: int | None, n: int,
         kw: dict | None = None, note: str = "",
         apply_rate_gate: float | None = None) -> None:
    cols = _cols_from_hub(ds, table, limit)
    rec = run_case(cid, cols, kw, n=n, warmup=1 if n > 1 else 0,
                   source=f"hub:{ds}/{table} (primeiros {limit or 'TODOS'})")
    assert rec.get("rt_ok"), f"{cid}: RT quebrado — investigar ANTES de reportar"
    if apply_rate_gate is not None:
        na = rec["side"].get("nature_apply") or {}
        rates = [v.get("apply_rate") for v in na.values() if isinstance(v, dict)]
        assert rates and all(r == apply_rate_gate for r in rates), (
            f"{cid}: apply_rate {rates} != {apply_rate_gate} (gate §2.3)")
    # sinal de compressão externa (qualitativo, §2.8) — sobre o MESMO conteúdo
    csv_b = _csv_bytes(cols)
    blob_b = rec["bytes"]["total"]
    from tcf import encode
    blob = encode(cols, **(kw or {})).encode("utf-8")
    csv_raw = None  # csv reconstruído só pra compressão
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(list(cols))
    for row in zip(*cols.values()):
        w.writerow(row)
    csv_raw = buf.getvalue().encode("utf-8")
    signal = {"csv_bytes": csv_b,
              "zlib9": {"csv": len(zlib.compress(csv_raw, 9)),
                        "tcf": len(zlib.compress(blob, 9))}}
    if _BR is not None:
        signal[_BR_NAME] = {"csv": _BR(csv_raw), "tcf": _BR(blob)}
    rec["compression_signal"] = signal
    write_jsonl([rec], F4 / f"{cid}.jsonl")
    na = rec["side"].get("nature_apply") or {}
    rates = [round(v.get("apply_rate", 0), 3) for v in na.values()
             if isinstance(v, dict)]
    _summary.append({
        "id": cid, "rows": rec["dataset"]["n_rows"], "cols": rec["dataset"]["n_cols"],
        "tcf": blob_b, "csv": csv_b, "delta": round(100 * (1 - blob_b / csv_b), 1),
        "enc_ms": rec["timing"]["encode"]["median_ns"] / 1e6, "n": n,
        "modes": "".join({"tcf": "t", "raw": "!", "dict": "@", "split": "%"}[m]
                         for m in (rec["side"].get("multi_info") or {})
                         .get("col_modes", {}).values()),
        "apply": rates or "-", "signal": signal, "note": note,
    })


def emit_result() -> Path:
    L = ["# F4-mínimo — públicos nos hubs prontos (gerado por scripts/bench_evidencia_f4.py)",
         "",
         f"Amostras determinísticas (primeiros N; SAMPLE={SAMPLE}); população total = janela",
         "dedicada pós-release (decisão F3/ROI). RT validado em TODOS os casos antes de",
         "qualquer número. Natures: só contagens nos registros (§2.3); nenhum blob salvo.",
         f"Sinal de compressão externa: zlib9 (stdlib) {'+ ' + _BR_NAME if _BR_NAME else '(brotli indisponível no venv)'} — qualitativo, nunca gate.",
         "", "## Casos", "",
         "| caso | linhas×cols | TCF B | CSV B | Δ vs CSV | modos | apply_rate | enc mediana ms (n) | nota |",
         "|---|---|---:|---:|---:|---|---|---:|---|"]
    for r in _summary:
        L.append(f"| {r['id']} | {r['rows']}×{r['cols']} | {r['tcf']} | {r['csv']} "
                 f"| {r['delta']}% | {r['modes']} | {r['apply']} "
                 f"| {r['enc_ms']:.0f} ({r['n']}) | {r['note']} |")
    L += ["", "## Sinal de compressão externa (mesmo conteúdo, qualitativo §2.8)", "",
          "| caso | zlib9(csv) | zlib9(tcf) |" + (f" {_BR_NAME}(csv) | {_BR_NAME}(tcf) |" if _BR_NAME else ""),
          "|---|---:|---:|" + ("---:|---:|" if _BR_NAME else "")]
    for r in _summary:
        s = r["signal"]
        row = f"| {r['id']} | {s['zlib9']['csv']} | {s['zlib9']['tcf']} |"
        if _BR_NAME and _BR_NAME in s:
            row += f" {s[_BR_NAME]['csv']} | {s[_BR_NAME]['tcf']} |"
        L.append(row)
    L += ["", "Notas: tpch-sf01 (600k) e tabelas cheias (500k) = janela dedicada;",
          "n=3 nos casos grandes -> latência INDICATIVA (claims de latência exigem n>=9).", ""]
    out = F4 / "RESULT.md"
    out.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return out


def main() -> int:
    assert validate_pins(verbose=False), "régua divergiu — NÃO produza material (F1-4)"
    if F4.exists():
        import shutil
        shutil.rmtree(F4)
    F4.mkdir(parents=True, exist_ok=True)

    case("adult-5k", "adult-census", "adult", limit=SAMPLE, n=3,
         note="census 15 cols, mix num/categ")
    case("tpch-lineitem-5k", "tpch-sf001", "lineitem", limit=SAMPLE, n=3,
         note="16 cols, free-text l_comment (regime do gate real-world)")
    case("tpch-customer-full", "tpch-sf001", "customer", limit=None, n=9,
         note="1500 linhas FULL, 8 cols")
    case("ibge-municipios-full", "ibge-municipios", "municipios", limit=None, n=9,
         note="5571 linhas FULL (real, geografia BR)")
    case("br-pessoas-5k", "br-identidades", "pessoas", limit=SAMPLE, n=3,
         note="sintético DV-válido (declared-bias), SEM natures")
    case("br-pessoas-5k-natures", "br-identidades", "pessoas", limit=SAMPLE, n=3,
         kw={"nature_per_col": {"cpf": SPEC_CPF}}, apply_rate_gate=1.0,
         note="idem + :cpf (delta natures em volume; §2.3 só contagens)")
    case("br-empresas-5k-natures", "br-identidades", "empresas", limit=SAMPLE, n=3,
         kw={"nature_per_col": {"cnpj": SPEC_CNPJ}}, apply_rate_gate=1.0,
         note="+ :cnpj sintético DV-válido")
    case("receita-5k", "receita-cnpj", "estabelecimentos", limit=SAMPLE, n=3,
         note="REAL non-PII, SEM natures")
    case("receita-5k-natures", "receita-cnpj", "estabelecimentos", limit=SAMPLE, n=3,
         kw={"nature_per_col": {"cnpj": SPEC_CNPJ}},
         note="+ :cnpj em dado REAL (fonte confirmada-empirica; apply_rate reportado, sem gate)")

    out = emit_result()
    print(f"F4-mínimo completo: {len(_summary)} casos -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
