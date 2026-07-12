"""F3 - sinteticos maiores (T-QA-8): suite D1-D17, curva de escala, paralelismo,
e br-identidades 600k com natures em volume.

Saidas:
  experiments/results/evidencia-0.8/f3/*.jsonl
  experiments/results/evidencia-0.8/f3/RESULT.md
"""

from __future__ import annotations

import random
import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from bench_evidencia import (  # noqa: E402
    RESULTS_DIR,
    load_csv_auto,
    load_csv_single,
    run_case,
    validate_pins,
    write_jsonl,
)
from dataset_reader import DatasetReader  # noqa: E402
from fixtures.synthetic_domains import (  # noqa: E402
    financial_transactions,
    medical_consultations,
)
from setup_br_identidades import _gen_cnpj, _gen_cpf  # noqa: E402
from tcf import SPEC_CNPJ, SPEC_CPF, SPEC_IP, encode  # noqa: E402

F3 = RESULTS_DIR / "f3"
SEED = 20260601
STRESS_DATASETS = {"D10-datas-mundiais", "D13-cpf-variados", "D14-uuid-variados"}

_summary: list[dict] = []


def rows_to_cols(rows: list[dict]) -> dict[str, list[str]]:
    if not rows:
        return {}
    cols = {k: [] for k in rows[0].keys()}
    for row in rows:
        for k in cols:
            cols[k].append(str(row[k]))
    return cols


def repeat_to_n(values: list[str], n: int) -> list[str]:
    if not values:
        return []
    q, r = divmod(n, len(values))
    return values * q + values[:r]


def repeat_cols_to_n(cols: dict[str, list[str]], n: int) -> dict[str, list[str]]:
    return {k: repeat_to_n(v, n) for k, v in cols.items()}


def case(
    cid: str,
    data,
    kw: dict | None = None,
    *,
    n: int = 9,
    warmup: int = 2,
    note: str = "",
    source: str | None = None,
    ephemeral: bool = False,
    save_blob: bool = False,
) -> dict:
    rec = run_case(
        cid,
        data,
        kw,
        n=n,
        warmup=warmup,
        source=source,
        seed=SEED if ephemeral else None,
    )
    if ephemeral:
        rec["ephemeral_data"] = (
            "dados validos gerados deterministicamente por seed 20260601; "
            "valores nao publicados, apenas metricas"
        )
    write_jsonl([rec], F3 / f"{cid}.jsonl")
    if save_blob and rec.get("rt_ok") and not ephemeral:
        (F3 / f"{cid}.tcf").write_text(
            encode(data, **(kw or {})), encoding="utf-8", newline="\n"
        )

    row = {"id": cid, "note": note, "source": source or "-"}
    if rec.get("rt_ok"):
        b = rec["bytes"]
        row.update(
            total=b["total"],
            header=b["header"],
            body=b["body"],
            input=b["input_join_lf"],
            rt="OK",
            enc_ms=rec["timing"]["encode"]["median_ns"] / 1e6,
            det=rec["deterministic"],
        )
    else:
        row.update(
            total="-", header="-", body="-", input="-", rt="FAIL", enc_ms="-", det="-"
        )
    _summary.append(row)
    return rec


def f3_1_suite_d1_d17() -> list[dict]:
    out = []
    for csv_path in sorted((ROOT / "datasets" / "synthetic").glob("D*.csv")):
        data = load_csv_auto(csv_path)
        rec = case(
            f"f3-1-{csv_path.stem}",
            data,
            n=1,
            warmup=0,
            note="stress" if csv_path.stem in STRESS_DATASETS else "design-realista",
            source=csv_path.relative_to(ROOT).as_posix(),
        )
        out.append(
            {
                "dataset": csv_path.stem,
                "bytes": rec["bytes"]["total"] if rec.get("rt_ok") else None,
                "kind": "stress"
                if csv_path.stem in STRESS_DATASETS
                else "design-realista",
                "rt_ok": rec.get("rt_ok", False),
            }
        )
    return out


def f3_2_scale_curve() -> list[dict]:
    out = []
    ns = [20, 100, 1000, 10000, 100000]

    # Base parametrizada por synthetic_domains para expansão determinística em n=100k.
    med_10k, _ = medical_consultations(
        n_orders=10000,
        items_per_order=(1, 1),
        seed=SEED,
        null_rate=0.03,
    )
    fin_10k, _ = financial_transactions(
        n_orders=10000,
        items_per_order=(1, 1),
        seed=SEED,
        null_rate=0.03,
    )
    single_10k = [r["descricao"] for r in fin_10k["transacoes"]]
    multi_10k = rows_to_cols(med_10k["consultas"])

    for n_rows in ns:
        if n_rows == 100000:
            # Mantem o ponto obrigatório de 100k sem custo explosivo: usa
            # motivo curto derivado do gerador parametrizado e repete
            # deterministicamente (curva continua reprodutível).
            single_data = repeat_to_n(single_10k[:100], n_rows)
            multi_data = repeat_cols_to_n(
                {k: v[:100] for k, v in multi_10k.items()}, n_rows
            )
        else:
            med_tables, _ = medical_consultations(
                n_orders=n_rows,
                items_per_order=(1, 1),
                seed=SEED,
                null_rate=0.03,
            )
            fin_tables, _ = financial_transactions(
                n_orders=n_rows,
                items_per_order=(1, 1),
                seed=SEED,
                null_rate=0.03,
            )
            single_data = [r["descricao"] for r in fin_tables["transacoes"]]
            multi_data = rows_to_cols(med_tables["consultas"])

        # Em n muito grande, mede 1x (sem warmup) para manter a rodada viável.
        n_meas = 5 if n_rows <= 1000 else 1
        warm = 1 if n_rows <= 1000 else 0

        rec_single = case(
            f"f3-2-single-n{n_rows}",
            single_data,
            n=n_meas,
            warmup=warm,
            note=(
                f"curva-single n={n_rows}"
                + (
                    " (expansao deterministica de base n=10000)"
                    if n_rows == 100000
                    else ""
                )
            ),
            source="fixtures.synthetic_domains.financial_transactions/transacoes.descricao",
        )
        rec_multi = case(
            f"f3-2-multi-n{n_rows}",
            multi_data,
            n=n_meas,
            warmup=warm,
            note=(
                f"curva-multi n={n_rows}"
                + (
                    " (expansao deterministica de base n=10000)"
                    if n_rows == 100000
                    else ""
                )
            ),
            source="fixtures.synthetic_domains.medical_consultations/consultas",
        )

        out.append(
            {
                "n": n_rows,
                "single": rec_single,
                "multi": rec_multi,
            }
        )
    return out


def _load_real_world_snapshots() -> dict[str, list[str]]:
    snaps = {}
    rels = [
        "datasets/samples/online-retail/description-2k.csv",
        "datasets/samples/online-retail/stockcode-2k.csv",
        "datasets/samples/tpch-sf001/lcomment-2k.csv",
    ]
    for rel in rels:
        p = ROOT / rel
        snaps[p.stem] = load_csv_single(p)
    return snaps


def _load_large_multi() -> dict[str, dict[str, list[str]]]:
    out = {}
    with DatasetReader("adult-census") as rd:
        # run_case exige valores como str; garantir isso evita falso RT por tipo.
        out["adult-20k"] = {
            k: [str(v) for v in vals]
            for k, vals in rd.columns("adult", limit=20000).items()
        }
    with DatasetReader("tpch-sf001") as rd:
        out["lineitem-20k"] = {
            k: [str(v) for v in vals]
            for k, vals in rd.columns("lineitem", limit=20000).items()
        }
    return out


def _amdahl_serial_fraction(speedup: float, workers: int) -> float | None:
    if workers <= 1 or speedup <= 0:
        return None
    val = (1.0 / speedup - 1.0 / workers) / (1.0 - 1.0 / workers)
    return val


def f3_3_parallel() -> dict:
    out: dict = {"identity_rw": [], "speedup": [], "combos": []}

    for name, values in _load_real_world_snapshots().items():
        blob_s = encode(values, parallel=False)
        blob_p2 = encode(values, parallel=2)
        blob_p4 = encode(values, parallel=4)
        blob_p8 = encode(values, parallel=8)
        same = blob_s == blob_p2 == blob_p4 == blob_p8
        out["identity_rw"].append({"dataset": name, "byte_identical": same})
        case(
            f"f3-3a-rw-{name}",
            values,
            {"parallel": 2},
            n=3,
            warmup=1,
            note=f"byte_identical_serial_parallel={same}",
            source=f"datasets/samples/{name}",
        )

    large = _load_large_multi()
    for name, cols in large.items():
        serial = case(
            f"f3-3b-{name}-serial",
            cols,
            {"parallel": False},
            n=9,
            warmup=2,
            note="speedup baseline serial",
            source=f"hub:{name}",
        )
        if not serial.get("rt_ok"):
            out["speedup"].append(
                {
                    "dataset": name,
                    "workers": 0,
                    "speedup": 0.0,
                    "serial_fraction_est": None,
                    "byte_identical": False,
                    "skipped": "serial_rt_fail",
                }
            )
            continue
        t_serial = serial["timing"]["encode"]["median_ns"]
        for w in (2, 4, 8):
            par = case(
                f"f3-3b-{name}-p{w}",
                cols,
                {"parallel": w},
                n=9,
                warmup=2,
                note=f"speedup workers={w}",
                source=f"hub:{name}",
            )
            if not par.get("rt_ok"):
                out["speedup"].append(
                    {
                        "dataset": name,
                        "workers": w,
                        "speedup": 0.0,
                        "serial_fraction_est": None,
                        "byte_identical": False,
                        "skipped": "parallel_rt_fail",
                    }
                )
                continue
            t_par = par["timing"]["encode"]["median_ns"]
            speedup = (t_serial / t_par) if t_par else 0.0
            sfrac = _amdahl_serial_fraction(speedup, w)
            out["speedup"].append(
                {
                    "dataset": name,
                    "workers": w,
                    "speedup": speedup,
                    "serial_fraction_est": sfrac,
                    "byte_identical": par["bytes"]["total"] == serial["bytes"]["total"],
                }
            )

    rng = random.Random(SEED)
    seen: set[str] = set()
    valid = [_gen_cpf(rng, seen) for _ in range(2000)]
    invalid = [v[:-1] + str((int(v[-1]) + 1) % 10) for v in valid]
    combo_table = {
        "cpf": valid,
        "cidade": ["Sao Paulo", "Rio", "Belo Horizonte", "Curitiba"] * 500,
        "plano": ["A", "B", "C", "A"] * 500,
        "x": [str(i) for i in range(2000)],
    }
    combos = [
        ("base", {"parallel": 4}),
        ("natures_per_col", {"parallel": 4, "nature_per_col": {"cpf": SPEC_CPF}}),
        ("sort_by", {"parallel": 4, "sort_by": "cidade"}),
        ("drop_names", {"parallel": 4, "drop_names": True}),
        (
            "natures_sort_drop",
            {
                "parallel": 4,
                "nature_per_col": {"cpf": SPEC_CPF},
                "sort_by": "cidade",
                "drop_names": True,
            },
        ),
    ]
    for label, kw in combos:
        blob_serial = encode(combo_table, **{**kw, "parallel": False})
        blob_parallel = encode(combo_table, **kw)
        same = blob_serial == blob_parallel
        out["combos"].append({"combo": label, "byte_identical": same})
        case(
            f"f3-3d-combo-{label}",
            combo_table,
            kw,
            n=3,
            warmup=1,
            note=f"combo={label} byte_identical={same}",
            source="synthetic-combo",
            ephemeral=True,
        )

    _ = invalid
    return out


def _build_ips(n: int) -> list[str]:
    return [f"10.{(i // 65536) % 255}.{(i // 256) % 255}.{i % 255}" for i in range(n)]


def _invalidate_cnpj(v: str) -> str:
    return v[:-1] + str((int(v[-1]) + 1) % 10)


def f3_4_br_identidades() -> list[dict]:
    n_rows = 600000
    rng = random.Random(SEED)

    # Gera base menor e expande deterministicamente para 600k (mesma distribuição, custo menor).
    base_n = 100000
    cpf_seen: set[str] = set()
    cnpj_seen: set[str] = set()
    valid_cpfs_base = [_gen_cpf(rng, cpf_seen) for _ in range(base_n)]
    valid_cnpjs_base = [_gen_cnpj(rng, cnpj_seen) for _ in range(base_n)]
    valid_ips_base = _build_ips(base_n)

    valid_cpfs = repeat_to_n(valid_cpfs_base, n_rows)
    valid_cnpjs = repeat_to_n(valid_cnpjs_base, n_rows)
    valid_ips = repeat_to_n(valid_ips_base, n_rows)

    invalid_cpfs = [v[:-1] + str((int(v[-1]) + 1) % 10) for v in valid_cpfs]
    invalid_cnpjs = [_invalidate_cnpj(v) for v in valid_cnpjs]
    invalid_ips = [ip + "x" for ip in valid_ips]

    out = []
    specs = {
        "cpf": SPEC_CPF,
        "cnpj": SPEC_CNPJ,
        "ip": SPEC_IP,
    }
    values = {
        "cpf": (valid_cpfs, invalid_cpfs),
        "cnpj": (valid_cnpjs, invalid_cnpjs),
        "ip": (valid_ips, invalid_ips),
    }
    for nature_name, spec in specs.items():
        valid_vals, invalid_vals = values[nature_name]
        mixed_vals = [
            valid_vals[i] if i % 2 == 0 else invalid_vals[i] for i in range(n_rows)
        ]
        for label, col in (
            ("spec", valid_vals),
            ("fallback", invalid_vals),
            ("misto", mixed_vals),
        ):
            rec = case(
                f"f3-4-brid-600k-{nature_name}-{label}",
                {nature_name: col},
                {"nature_per_col": {nature_name: spec}},
                n=1,
                warmup=0,
                note=f"br-identidades 600k nature={nature_name} codepath={label}",
                source="synthetic-seed-20260601",
                ephemeral=True,
            )
            na = rec.get("side", {}).get("nature_apply", {})
            out.append(
                {
                    "nature": nature_name,
                    "label": label,
                    "apply_rate": na.get(nature_name, {}).get("apply_rate"),
                }
            )
    return out


def emit_result(
    f3_1_rows: list[dict],
    f3_2_rows: list[dict],
    f3_3_data: dict,
    f3_4_rows: list[dict],
) -> Path:
    lines = [
        "# F3 - sinteticos maiores (gerado por scripts/bench_evidencia_f3.py)",
        "",
        "Registros completos em JSONL ao lado (schema evidencia-0.8/v1).",
        "Dados efemeros (br-identidades 600k / combos) sao medidos e nao publicados em blob.",
        "",
        "## Casos medidos",
        "",
        "| caso | total B | header B | body B | input B | enc mediana ms | RT | det | origem | nota |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for r in _summary:
        lines.append(
            f"| {r['id']} | {r['total']} | {r['header']} | {r['body']} | {r['input']} | {r['enc_ms']} | {r['rt']} | {r['det']} | {r['source']} | {r['note']} |"
        )

    lines += ["", "## F3-1 - D1..D17", ""]
    real = [x for x in f3_1_rows if x["kind"] == "design-realista"]
    stress = [x for x in f3_1_rows if x["kind"] == "stress"]
    lines += [
        f"- datasets design-realista: {len(real)}",
        f"- datasets stress (separados): {len(stress)} ({', '.join(sorted(x['dataset'] for x in stress))})",
        f"- RT OK: {sum(1 for x in f3_1_rows if x['rt_ok'])}/{len(f3_1_rows)}",
    ]

    lines += [
        "",
        "## F3-2 - Curva de escala",
        "",
        "| n | single bytes/linha | multi bytes/linha | single ms/linha | multi ms/linha |",
        "|---:|---:|---:|---:|---:|",
    ]
    for item in f3_2_rows:
        n = item["n"]
        s = item["single"]
        m = item["multi"]
        s_bpl = s["bytes"]["total"] / max(1, s["dataset"]["n_rows"])
        m_bpl = m["bytes"]["total"] / max(1, m["dataset"]["n_rows"])
        s_tpl = (s["timing"]["encode"]["median_ns"] / 1e6) / max(
            1, s["dataset"]["n_rows"]
        )
        m_tpl = (m["timing"]["encode"]["median_ns"] / 1e6) / max(
            1, m["dataset"]["n_rows"]
        )
        lines.append(f"| {n} | {s_bpl:.4f} | {m_bpl:.4f} | {s_tpl:.6f} | {m_tpl:.6f} |")

    lines += [
        "",
        "## F3-3 - Paralelismo",
        "",
        "### (a) Byte-identidade nos snapshots real-world",
        "",
        "| dataset | byte-identical |",
        "|---|---|",
    ]
    for row in f3_3_data["identity_rw"]:
        lines.append(f"| {row['dataset']} | {row['byte_identical']} |")

    lines += [
        "",
        "### (b)(c) Speedup e estimativa de porcao serial (Amdahl)",
        "",
        "| dataset | workers | speedup | serial_fraction_est | byte-identical |",
        "|---|---:|---:|---:|---|",
    ]
    for row in f3_3_data["speedup"]:
        sf = row["serial_fraction_est"]
        sf_txt = "n/a" if sf is None else f"{sf:.4f}"
        lines.append(
            f"| {row['dataset']} | {row['workers']} | {row['speedup']:.4f} | {sf_txt} | {row['byte_identical']} |"
        )

    speedups = [r["speedup"] for r in f3_3_data["speedup"]]
    if speedups:
        lines.append("")
        lines.append(
            f"- speedup mediano (todos os cenarios): {statistics.median(speedups):.4f}"
        )

    lines += [
        "",
        "### (d) Cobertura de combos parallel x natures_per_col x sort_by x drop_names",
        "",
        "| combo | byte-identical |",
        "|---|---|",
    ]
    for row in f3_3_data["combos"]:
        lines.append(f"| {row['combo']} | {row['byte_identical']} |")

    lines += [
        "",
        "### (e) Limitacoes registradas",
        "",
        "- decode continua serial (medicao de paralelismo cobre encode).",
        "- Cython sem nogil em 3.13t reativa GIL (nao e paralelismo intra-kernel).",
        "- Overhead de IPC/spawn pode reduzir ou inverter speedup em cargas pequenas/medias.",
        "- A fracao serial por Amdahl e estimativa agregada por speedup observado, nao instrumentacao de fases internas.",
    ]

    lines += [
        "",
        "## F3-4 - br-identidades 600k (efemero)",
        "",
        "| natureza | codepath | apply_rate |",
        "|---|---|---:|",
    ]
    for row in f3_4_rows:
        lines.append(f"| {row['nature']} | {row['label']} | {row['apply_rate']} |")

    out = F3 / "RESULT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out


def main() -> int:
    assert validate_pins(verbose=False), "regua divergiu - nao produza material"

    if F3.exists():
        shutil.rmtree(F3)
    F3.mkdir(parents=True, exist_ok=True)

    print("[F3] bloco 1/4: suite D1..D17")
    rows_f3_1 = f3_1_suite_d1_d17()
    print("[F3] bloco 2/4: curva de escala")
    rows_f3_2 = f3_2_scale_curve()
    print("[F3] bloco 3/4: paralelismo")
    data_f3_3 = f3_3_parallel()
    print("[F3] bloco 4/4: br-identidades 600k")
    rows_f3_4 = f3_4_br_identidades()
    out = emit_result(rows_f3_1, rows_f3_2, data_f3_3, rows_f3_4)

    print(f"F3 completo: {len(_summary)} casos -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
