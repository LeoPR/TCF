"""EXP-008 — Compressao comparada (raw vs TCF).

Compara TCF contra compressores de fluxo geral (gzip, brotli, zstd,
lzma, bz2), tanto stand-alone quanto como pre-tx (`tcf → C`),
medindo bytes + RT + latencia (mediana).

Saidas:
- outputs/<ds>.tcf
- outputs/<ds>.raw.{gz,br,zst,xz,bz2}
- outputs/<ds>.tcf.{gz,br,zst,xz,bz2}
- manifest.jsonl (linha por execucao)
- report.md (consolidado, gerado por write_report())
"""

from __future__ import annotations

import bz2
import csv
import gzip
import json
import lzma
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import brotli
import zstandard

THIS = Path(__file__).parent
SRC = THIS.parents[3] / "src"
sys.path.insert(0, str(SRC))

from tcf import decode, encode  # noqa: E402


# ---- Compressores: (compress_fn, decompress_fn, ext) ----
_ZSTD_C = zstandard.ZstdCompressor(level=22)
_ZSTD_D = zstandard.ZstdDecompressor()


def _gz_c(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9, mtime=0)


def _gz_d(b: bytes) -> bytes:
    return gzip.decompress(b)


def _br_c(b: bytes) -> bytes:
    return brotli.compress(b, quality=11)


def _br_d(b: bytes) -> bytes:
    return brotli.decompress(b)


def _zst_c(b: bytes) -> bytes:
    return _ZSTD_C.compress(b)


def _zst_d(b: bytes) -> bytes:
    return _ZSTD_D.decompress(b)


def _xz_c(b: bytes) -> bytes:
    return lzma.compress(b, preset=9)


def _xz_d(b: bytes) -> bytes:
    return lzma.decompress(b)


def _bz_c(b: bytes) -> bytes:
    return bz2.compress(b, compresslevel=9)


def _bz_d(b: bytes) -> bytes:
    return bz2.decompress(b)


COMPRESSORS: dict[str, tuple[Callable, Callable, str]] = {
    "gzip":   (_gz_c, _gz_d, "gz"),
    "brotli": (_br_c, _br_d, "br"),
    "zstd":   (_zst_c, _zst_d, "zst"),
    "lzma":   (_xz_c, _xz_d, "xz"),
    "bz2":    (_bz_c, _bz_d, "bz2"),
}


def time_median_us(fn: Callable, reps: int) -> float:
    """Mediana de tempo (microssegundos) sobre `reps` execucoes."""
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        samples.append((t1 - t0) / 1000.0)
    return statistics.median(samples)


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def medir_dataset(
    ds: str,
    linhas: list[str],
    out_dir: Path,
    reps_tcf: int,
    reps_comp: int,
) -> dict:
    raw_text = "\n".join(linhas) + "\n"
    raw_b = raw_text.encode("utf-8")

    # TCF
    tcf_text = encode(linhas)
    tcf_b = tcf_text.encode("utf-8")
    decoded = decode(tcf_text)
    rt_tcf = decoded == linhas

    t_enc = time_median_us(lambda: encode(linhas), reps_tcf)
    t_dec = time_median_us(lambda: decode(tcf_text), reps_tcf)

    (out_dir / f"{ds}.tcf").write_bytes(tcf_b)

    row: dict = {
        "dataset": ds,
        "linhas": len(linhas),
        "raw": len(raw_b),
        "tcf": len(tcf_b),
        "ratio_tcf": round(len(tcf_b) / len(raw_b), 4),
        "rt_tcf": rt_tcf,
        "t_encode_us": round(t_enc, 1),
        "t_decode_us": round(t_dec, 1),
        "compressors": {},
    }

    for name, (cfn, dfn, ext) in COMPRESSORS.items():
        c_raw = cfn(raw_b)
        c_tcf = cfn(tcf_b)
        rt_c_raw = dfn(c_raw) == raw_b
        rt_c_tcf = dfn(c_tcf) == tcf_b
        rt_full = decode(dfn(c_tcf).decode("utf-8")) == linhas

        t_c_raw = time_median_us(lambda: cfn(raw_b), reps_comp)
        t_c_tcf = time_median_us(lambda: cfn(tcf_b), reps_comp)
        t_d_raw = time_median_us(lambda: dfn(c_raw), reps_comp)
        t_d_tcf = time_median_us(lambda: dfn(c_tcf), reps_comp)

        (out_dir / f"{ds}.raw.{ext}").write_bytes(c_raw)
        (out_dir / f"{ds}.tcf.{ext}").write_bytes(c_tcf)

        row["compressors"][name] = {
            "raw_bytes": len(c_raw),
            "tcf_bytes": len(c_tcf),
            "ratio_raw": round(len(c_raw) / len(raw_b), 4),
            "ratio_tcf_pipeline": round(len(c_tcf) / len(raw_b), 4),
            "tcf_complement": (
                round(len(c_tcf) / len(c_raw), 4) if c_raw else None
            ),
            "rt_compressor_raw": rt_c_raw,
            "rt_compressor_tcf": rt_c_tcf,
            "rt_full": rt_full,
            "t_compress_raw_us": round(t_c_raw, 1),
            "t_compress_tcf_us": round(t_c_tcf, 1),
            "t_decompress_raw_us": round(t_d_raw, 1),
            "t_decompress_tcf_us": round(t_d_tcf, 1),
        }

    return row


def write_report(
    path: Path,
    rows: list[dict],
    timestamp: str,
    config: dict,
) -> None:
    comp_names = list(COMPRESSORS.keys())

    out: list[str] = []
    out.append("# EXP-008 — Compressao comparada (relatorio)")
    out.append("")
    out.append(f"**Data execucao**: {timestamp}")
    out.append(f"**TCF source**: `{config['tcf_source']}`")
    out.append(f"**Datasets**: {len(rows)}")
    out.append(f"**Compressores**: {', '.join(comp_names)} (niveis maximos)")
    out.append(
        f"**Reps**: tcf={config['reps_tcf']}, "
        f"compressores={config['reps_comp']}"
    )
    out.append("")

    # Sumario global
    total_raw = sum(r["raw"] for r in rows)
    total_tcf = sum(r["tcf"] for r in rows)
    rt_tcf_count = sum(1 for r in rows if r["rt_tcf"])

    out.append("## Sumario global")
    out.append("")
    out.append(
        f"- **Raw total**: {total_raw} bytes em {len(rows)} datasets"
    )
    out.append(
        f"- **TCF total**: {total_tcf} bytes "
        f"({total_tcf/total_raw*100:.1f}% raw)"
    )
    out.append(f"- **RT TCF**: {rt_tcf_count}/{len(rows)} OK")
    out.append("")
    out.append("Compressores aplicados a raw e a tcf:")
    out.append("")
    out.append("| compressor | total raw | total tcf | tcf vs raw |")
    out.append("|---|---:|---:|---:|")
    for c in comp_names:
        cr = sum(r["compressors"][c]["raw_bytes"] for r in rows)
        ct = sum(r["compressors"][c]["tcf_bytes"] for r in rows)
        delta = ct / cr if cr else 0.0
        out.append(f"| {c} | {cr} | {ct} | {delta:.2f}x |")
    out.append("")

    # Bytes por dataset
    out.append("## Bytes por dataset")
    out.append("")
    header = ["dataset", "raw", "tcf"]
    for c in comp_names:
        header.append(f"{c}/raw")
        header.append(f"{c}/tcf")
    out.append("| " + " | ".join(header) + " |")
    out.append("|" + "---|" * len(header))
    for r in rows:
        cells = [r["dataset"], str(r["raw"]), str(r["tcf"])]
        for c in comp_names:
            cells.append(str(r["compressors"][c]["raw_bytes"]))
            cells.append(str(r["compressors"][c]["tcf_bytes"]))
        out.append("| " + " | ".join(cells) + " |")
    cells = ["**TOTAL**", f"**{total_raw}**", f"**{total_tcf}**"]
    for c in comp_names:
        cr = sum(r["compressors"][c]["raw_bytes"] for r in rows)
        ct = sum(r["compressors"][c]["tcf_bytes"] for r in rows)
        cells.append(f"**{cr}**")
        cells.append(f"**{ct}**")
    out.append("| " + " | ".join(cells) + " |")
    out.append("")

    # Ratio C(raw)/raw vs C(tcf)/raw
    out.append("## Ratio versus raw")
    out.append("")
    out.append(
        "`tcf/raw` e `C(*)/raw` — quanto cada saida ocupa em relacao "
        "ao raw original do dataset."
    )
    out.append("")
    header2 = ["dataset", "tcf"]
    for c in comp_names:
        header2.append(f"{c}(raw)")
        header2.append(f"{c}(tcf)")
    out.append("| " + " | ".join(header2) + " |")
    out.append("|" + "---|" * len(header2))
    for r in rows:
        cells = [r["dataset"], f"{r['ratio_tcf']*100:.0f}%"]
        for c in comp_names:
            cells.append(f"{r['compressors'][c]['ratio_raw']*100:.0f}%")
            cells.append(
                f"{r['compressors'][c]['ratio_tcf_pipeline']*100:.0f}%"
            )
        out.append("| " + " | ".join(cells) + " |")
    out.append("")

    # TCF como pre-tx
    out.append("## TCF como pre-tx: C(tcf) / C(raw)")
    out.append("")
    out.append(
        "Valor **<1** = TCF reduz tamanho final do pipeline. "
        "**~1** = ortogonal. **>1** = TCF aumenta tamanho final "
        "(redundancia ja' explorada pelo compressor, ou overhead "
        "TCF supera a reducao)."
    )
    out.append("")
    header3 = ["dataset"] + comp_names
    out.append("| " + " | ".join(header3) + " |")
    out.append("|" + "---|" * len(header3))
    for r in rows:
        cells = [r["dataset"]]
        for c in comp_names:
            v = r["compressors"][c]["tcf_complement"]
            cells.append(f"{v:.2f}" if v is not None else "-")
        out.append("| " + " | ".join(cells) + " |")
    out.append("")

    # Menor bytes por dataset
    out.append("## Menor bytes por dataset (campeao global)")
    out.append("")
    out.append("| dataset | raw | menor | metodo | reducao |")
    out.append("|---|---:|---:|---|---:|")
    for r in rows:
        candidates = [("raw", r["raw"]), ("tcf", r["tcf"])]
        for c in comp_names:
            candidates.append(
                (f"{c}(raw)", r["compressors"][c]["raw_bytes"])
            )
            candidates.append(
                (f"{c}(tcf)", r["compressors"][c]["tcf_bytes"])
            )
        best_name, best_bytes = min(candidates, key=lambda x: x[1])
        red = best_bytes / r["raw"]
        out.append(
            f"| {r['dataset']} | {r['raw']} | {best_bytes} "
            f"| {best_name} | {red*100:.0f}% |"
        )
    out.append("")

    # Roundtrip
    rt_full_all = all(
        r["compressors"][c]["rt_full"] for r in rows for c in comp_names
    )
    out.append("## Roundtrip")
    out.append("")
    out.append(
        "- **RT TCF**: `decode(encode(D)) == D`"
    )
    out.append(
        "- **RT full**: `decode(C.decompress(C.compress(encode(D))))"
        ".decode == D` (stack completo)"
    )
    out.append("")
    out.append(f"RT TCF: {rt_tcf_count}/{len(rows)}")
    out.append(
        f"RT full (todos compressores × todos datasets): "
        f"{'OK' if rt_full_all else 'FAIL'}"
    )
    out.append("")

    # Tempo
    out.append("## Tempo (mediana, microssegundos)")
    out.append("")
    out.append(
        "Compressao em nivel maximo. Medianas sobre "
        f"{config['reps_tcf']} reps (TCF) e {config['reps_comp']} "
        "reps (compressores). Resolucao do clock = ~100ns no "
        "Windows; operacoes <10us tem ruido significativo."
    )
    out.append("")
    out.append("### TCF encode/decode")
    out.append("")
    out.append("| dataset | encode | decode |")
    out.append("|---|---:|---:|")
    for r in rows:
        out.append(
            f"| {r['dataset']} | {r['t_encode_us']:.1f} "
            f"| {r['t_decode_us']:.1f} |"
        )
    out.append("")
    out.append("### Compressor sobre raw")
    out.append("")
    out.append(
        "| dataset | " + " | ".join(comp_names) + " |"
    )
    out.append("|" + "---|" * (1 + len(comp_names)))
    for r in rows:
        cells = [r["dataset"]]
        for c in comp_names:
            cells.append(
                f"{r['compressors'][c]['t_compress_raw_us']:.1f}"
            )
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    out.append("### Compressor sobre tcf")
    out.append("")
    out.append(
        "| dataset | " + " | ".join(comp_names) + " |"
    )
    out.append("|" + "---|" * (1 + len(comp_names)))
    for r in rows:
        cells = [r["dataset"]]
        for c in comp_names:
            cells.append(
                f"{r['compressors'][c]['t_compress_tcf_us']:.1f}"
            )
        out.append("| " + " | ".join(cells) + " |")
    out.append("")

    # Observacoes (computadas, sem narrativa)
    out.append("## Observacoes (computadas)")
    out.append("")

    # TCF stand-alone
    n_tcf_helps = sum(1 for r in rows if r["tcf"] < r["raw"])
    best_tcf = min(rows, key=lambda r: r["ratio_tcf"])
    worst_tcf = max(rows, key=lambda r: r["ratio_tcf"])
    out.append(
        f"- **TCF stand-alone reduz bytes**: {n_tcf_helps}/{len(rows)} "
        f"datasets. Melhor caso: `{best_tcf['dataset']}` = "
        f"{best_tcf['ratio_tcf']*100:.0f}% raw. Pior caso: "
        f"`{worst_tcf['dataset']}` = {worst_tcf['ratio_tcf']*100:.0f}% raw."
    )

    # TCF complement <1 por compressor
    n_helps = {
        c: sum(
            1 for r in rows
            if (r["compressors"][c]["tcf_complement"] or 1) < 1.0
        )
        for c in comp_names
    }
    helps_str = ", ".join(f"{c}={n}/{len(rows)}" for c, n in n_helps.items())
    out.append(
        f"- **TCF como pre-tx (C(tcf) < C(raw))**: {helps_str}."
    )

    # Campeao global por dataset
    champ_count: dict[str, int] = {}
    for r in rows:
        candidates = [("raw", r["raw"]), ("tcf", r["tcf"])]
        for c in comp_names:
            candidates.append(
                (f"{c}(raw)", r["compressors"][c]["raw_bytes"])
            )
            candidates.append(
                (f"{c}(tcf)", r["compressors"][c]["tcf_bytes"])
            )
        best, _ = min(candidates, key=lambda x: x[1])
        champ_count[best] = champ_count.get(best, 0) + 1
    champ_str = ", ".join(
        f"{k}={v}" for k, v in sorted(
            champ_count.items(), key=lambda x: -x[1]
        )
    )
    out.append(f"- **Campeao bytes por dataset**: {champ_str}.")

    # Total reducao do campeao por dataset
    total_best = 0
    for r in rows:
        candidates = [r["raw"], r["tcf"]]
        for c in comp_names:
            candidates.append(r["compressors"][c]["raw_bytes"])
            candidates.append(r["compressors"][c]["tcf_bytes"])
        total_best += min(candidates)
    out.append(
        f"- **Soma dos melhores por dataset**: {total_best} bytes "
        f"({total_best/total_raw*100:.1f}% do raw total). "
        f"Limite inferior empirico sobre esse conjunto de compressores."
    )

    # Latencia: encoders mais caros
    t_encode_avg = statistics.mean(r["t_encode_us"] for r in rows)
    t_decode_avg = statistics.mean(r["t_decode_us"] for r in rows)
    t_comp_avg = {
        c: statistics.mean(
            r["compressors"][c]["t_compress_raw_us"] for r in rows
        )
        for c in comp_names
    }
    comp_t_str = ", ".join(
        f"{c}={t:.0f}us" for c, t in sorted(
            t_comp_avg.items(), key=lambda x: x[1]
        )
    )
    out.append(
        f"- **Latencia media (us)**: tcf encode={t_encode_avg:.0f}, "
        f"tcf decode={t_decode_avg:.0f}; compressores={comp_t_str}."
    )
    out.append("")

    # Notas
    out.append("## Notas metodologicas")
    out.append("")
    out.append(
        "- **D10-D15** sao variety datasets (poucas repeticoes "
        "por tipo); TCF-CORE atual nao tem type encoders (Estrategia "
        "1.A do roadmap), entao baixa redundancia interna. Comportamento "
        "esperado: compressores gerais relativamente melhores."
    )
    out.append(
        "- **Escala**: raw 100-500 bytes/dataset. Overhead fixo de "
        "gzip/brotli/zstd (~20-40 bytes header) e' significativo aqui. "
        "Inversoes de tendencia podem ocorrer em escalas maiores."
    )
    out.append(
        "- **Niveis maximos**: gzip=9, brotli=11, zstd=22, lzma "
        "preset=9, bz2=9. Foco em bytes; latencia caracterizada como "
        "custo associado, nao otimizada."
    )
    out.append(
        "- **gzip ≠ TCF** (ver feedback `gzip_e_compressao_externa`): "
        "comparacao e' qualitativa, nao criterio de descarte/aprovacao."
    )
    out.append("")

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


def main() -> None:
    config_path = THIS / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    datasets_dir = (THIS / config["datasets_dir"]).resolve()
    out_dir = (THIS / config["out_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    reps_tcf = config.get("reps_tcf", 20)
    reps_comp = config.get("reps_comp", 100)

    print("=== EXP-008 — Compressao comparada ===")
    print(f"src/tcf via: {SRC}")
    print(f"datasets:    {datasets_dir}")
    print(f"out:         {out_dir}")
    print(f"reps:        tcf={reps_tcf}, compressores={reps_comp}")
    print(f"compressores: {', '.join(COMPRESSORS.keys())}")
    print()

    rows: list[dict] = []
    for ds in config["datasets"]:
        _, linhas = ler_csv(datasets_dir / f"{ds}.csv")
        row = medir_dataset(ds, linhas, out_dir, reps_tcf, reps_comp)
        rows.append(row)

        rt_mark = "OK" if row["rt_tcf"] else "FAIL"
        rt_full_all = all(
            row["compressors"][c]["rt_full"] for c in COMPRESSORS
        )
        rt_full_mark = "OK" if rt_full_all else "FAIL"
        print(
            f"  {ds:<28}  raw={row['raw']:>4}  tcf={row['tcf']:>4}  "
            f"({row['ratio_tcf']*100:>5.1f}%)  "
            f"RT_tcf={rt_mark}  RT_full={rt_full_mark}"
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_entry = {
        "timestamp": timestamp,
        "experiment_id": config["experiment_id"],
        "tcf_source": config["tcf_source"],
        "compressors": list(COMPRESSORS.keys()),
        "reps_tcf": reps_tcf,
        "reps_comp": reps_comp,
        "datasets": len(rows),
        "rt_tcf_all": all(r["rt_tcf"] for r in rows),
        "rt_full_all": all(
            r["compressors"][c]["rt_full"]
            for r in rows for c in COMPRESSORS
        ),
        "rows": rows,
    }
    manifest_path = THIS / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
    print(f"\nManifest atualizado: {manifest_path}")

    write_report(THIS / "report.md", rows, timestamp, config)
    print(f"Report gerado: {THIS / 'report.md'}")


if __name__ == "__main__":
    main()
