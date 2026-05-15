"""EXP-007 — Prototipo TCF-CORE.

Primeiro experimento clean v0.6: valida `from tcf import encode, decode`
em 9 datasets sinteticos de controle, contra o baseline byte-canonico
do dirty lab (M14).

Pergunta: `src/tcf` reproduz bytes byte-a-byte de M14?
Hipotese: sim (welding step 3 + contra-prova M14 ja' validados).

Saidas:
- outputs/<dataset>.tcf — TCF gerado pela API publica
- manifest.jsonl — 1 linha por execucao (timestamp + resultados)
- report.md — analise consolidada
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

THIS = Path(__file__).parent

# sys.path: src/ ao topo para `from tcf import` resolver.
SRC = THIS.parents[3] / "src"
sys.path.insert(0, str(SRC))

from tcf import encode, decode  # noqa: E402


def write_lf(path: Path, content: str) -> None:
    """Escreve content preservando LF (sem CRLF Windows)."""
    path.write_bytes(content.encode("utf-8"))


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def main() -> None:
    config_path = THIS / "config.json"
    with config_path.open(encoding="utf-8") as f:
        config = json.load(f)

    datasets_dir = (THIS / config["datasets_dir"]).resolve()
    out_dir = (THIS / config["out_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== EXP-007 — Prototipo TCF-CORE ===")
    print(f"src/tcf via: {SRC}")
    print(f"datasets: {datasets_dir}")
    print(f"out:      {out_dir}")
    print()

    per_dataset: list[dict] = []
    total_bytes = 0
    total_raw = 0
    rt_count = 0

    for ds in config["datasets"]:
        header, linhas = ler_csv(datasets_dir / f"{ds}.csv")
        raw_bytes = sum(len(l.encode("utf-8")) + 1 for l in linhas)

        tcf_text = encode(linhas)
        write_lf(out_dir / f"{ds}.tcf", tcf_text)
        n_bytes = len(tcf_text.encode("utf-8"))

        decoded = decode(tcf_text)
        rt_ok = decoded == linhas

        if rt_ok:
            rt_count += 1
        total_bytes += n_bytes
        total_raw += raw_bytes

        ratio = n_bytes / raw_bytes if raw_bytes else 0.0
        mark = "OK" if rt_ok else "FAIL"
        print(f"  {ds:<30} [{mark}]  {n_bytes:>4} bytes  ({ratio:.1%} raw)")

        per_dataset.append({
            "dataset": ds,
            "rt": rt_ok,
            "bytes": n_bytes,
            "raw_bytes": raw_bytes,
            "ratio": round(ratio, 4),
        })

    overall_ratio = total_bytes / total_raw if total_raw else 0.0
    expected = config["expected"]
    expected_total = expected["total_bytes"]
    expected_rt = expected["rt_count"]
    matches_expected = (
        total_bytes == expected_total and rt_count == expected_rt
    )

    print()
    print(f"TOTAL: {total_bytes} bytes em {total_raw} raw "
          f"({overall_ratio:.1%} ratio)")
    print(f"RT: {rt_count}/{len(config['datasets'])} OK")
    print(f"Match baseline: {matches_expected} "
          f"(esperado {expected_total} bytes, {expected_rt} RT)")

    # Manifest
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_id": config["experiment_id"],
        "tcf_source": config["tcf_source"],
        "total_bytes": total_bytes,
        "total_raw": total_raw,
        "ratio": round(overall_ratio, 4),
        "rt_count": rt_count,
        "expected_total_bytes": expected_total,
        "matches_expected": matches_expected,
        "per_dataset": per_dataset,
    }
    manifest_path = THIS / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\nManifest atualizado: {manifest_path}")

    return None


if __name__ == "__main__":
    main()
