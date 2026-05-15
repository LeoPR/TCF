"""EXP-008 — Compressao comparada (raw vs TCF) com 5 compressores.

Template: comparativo multi-axis (META-EXP-FORMAT).

Estrutura:
- lib/ codigo modular (formats, compressors, measure, reporting)
- results/manifest.jsonl + results/per-dataset/*.json
- reports/00..05-*.md gerados ao fim
- outputs/raw/<fmt>/<ds>.<ext> + outputs/compressed/<fmt>/<comp>/<ds>.<ext>.<comp_ext>
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

THIS = Path(__file__).parent
SRC = THIS.parents[3] / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(THIS))

from tcf import decode, encode  # noqa: E402
from lib.compressors import CLASSES, COMPRESSORS  # noqa: E402
from lib.formats import build_formats  # noqa: E402
from lib.measure import measure_dataset, write_outputs  # noqa: E402
from lib.reporting import (  # noqa: E402
    write_bytes_por_classe,
    write_bytes_por_formato,
    write_campeao,
    write_latencia,
    write_resumo,
    write_roundtrip,
)


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def main() -> None:
    config = json.loads((THIS / "config.json").read_text(encoding="utf-8"))

    datasets_dir = (THIS / config["datasets_dir"]).resolve()
    out_dir = (THIS / "outputs").resolve()
    results_dir = THIS / "results"
    per_dataset_dir = results_dir / "per-dataset"
    reports_dir = THIS / "reports"
    for d in (out_dir, results_dir, per_dataset_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    formats = build_formats(encode, decode)
    fmt_names = list(formats.keys())
    comp_names = list(COMPRESSORS.keys())

    reps_serialize = config.get("reps_serialize", 20)
    reps_compress = config.get("reps_compress", 30)

    print("=== EXP-008 — Compressao comparada ===")
    print(f"src/tcf via:  {SRC}")
    print(f"datasets:     {datasets_dir}")
    print(f"out:          {out_dir}")
    print(f"results:      {results_dir}")
    print(f"reports:      {reports_dir}")
    print(f"formatos:     {', '.join(fmt_names)}")
    print(f"compressores: {', '.join(comp_names)}")
    print(f"reps:         serialize={reps_serialize}, compress={reps_compress}")
    print()

    per_dataset: dict[str, dict] = {}
    ds_list = config["datasets"]

    for ds in ds_list:
        _, linhas = ler_csv(datasets_dir / f"{ds}.csv")
        result = measure_dataset(
            linhas, formats, COMPRESSORS,
            reps_serialize=reps_serialize,
            reps_compress=reps_compress,
        )
        per_dataset[ds] = result

        write_outputs(out_dir, ds, linhas, formats, COMPRESSORS)

        # Per-dataset JSON
        (per_dataset_dir / f"{ds}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8", newline="\n",
        )

        # Print resumo
        tcf_bytes = result["formats"]["tcf"]["bytes"]
        csv_bytes = result["formats"]["csv"]["bytes"]
        rt_all = all(
            result["formats"][f]["compressors"][c]["rt_full"]
            for f in fmt_names for c in comp_names
        )
        rt_mark = "OK" if rt_all else "FAIL"
        print(
            f"  {ds:<28}  csv={csv_bytes:>4}  tcf={tcf_bytes:>4} "
            f"({tcf_bytes/csv_bytes*100:>5.1f}% csv)  RT_full={rt_mark}"
        )

    timestamp = datetime.now(timezone.utc).isoformat()

    # Manifest run-level
    manifest_entry = {
        "timestamp":       timestamp,
        "experiment_id":   config["experiment_id"],
        "schema_version":  2,
        "tcf_source":      config["tcf_source"],
        "formats":         fmt_names,
        "compressors":     comp_names,
        "compressor_meta": {
            c: {k: v for k, v in meta.items()
                if k not in ("compress", "decompress")}
            for c, meta in COMPRESSORS.items()
        },
        "reps_serialize":  reps_serialize,
        "reps_compress":   reps_compress,
        "datasets":        ds_list,
        "rt_format_all":   all(
            per_dataset[d]["formats"][f]["rt"]
            for d in ds_list for f in fmt_names
        ),
        "rt_full_all":     all(
            per_dataset[d]["formats"][f]["compressors"][c]["rt_full"]
            for d in ds_list for f in fmt_names for c in comp_names
        ),
        "totals_raw":     {
            f: sum(per_dataset[d]["formats"][f]["bytes"] for d in ds_list)
            for f in fmt_names
        },
        "totals_compressed": {
            f: {
                c: sum(
                    per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                    for d in ds_list
                )
                for c in comp_names
            }
            for f in fmt_names
        },
    }
    manifest_path = results_dir / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
    print(f"\nManifest atualizado: {manifest_path}")

    # Reports
    write_resumo(
        reports_dir / "00-resumo.md",
        per_dataset, ds_list, fmt_names, comp_names, config, timestamp,
    )
    write_bytes_por_formato(
        reports_dir / "01-bytes-por-formato.md",
        per_dataset, ds_list, fmt_names,
    )
    write_bytes_por_classe(
        reports_dir / "02-bytes-por-classe.md",
        per_dataset, ds_list, fmt_names, COMPRESSORS, CLASSES,
    )
    write_latencia(
        reports_dir / "03-latencia.md",
        per_dataset, ds_list, fmt_names, comp_names, config,
    )
    write_roundtrip(
        reports_dir / "04-roundtrip.md",
        per_dataset, ds_list, fmt_names, comp_names,
    )
    write_campeao(
        reports_dir / "05-campeao-por-dataset.md",
        per_dataset, ds_list, fmt_names, comp_names,
    )
    print(f"Reports gerados: {reports_dir}/")


if __name__ == "__main__":
    main()
