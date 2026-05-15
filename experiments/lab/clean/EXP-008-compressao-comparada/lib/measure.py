"""Medicao: bytes + roundtrip + latencia (mediana us)."""

from __future__ import annotations

import statistics
import time
from typing import Callable


def time_median_us(fn: Callable, reps: int) -> float:
    """Mediana de tempo (microssegundos) sobre `reps` execucoes."""
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        samples.append((t1 - t0) / 1000.0)
    return statistics.median(samples)


def measure_dataset(
    linhas: list[str],
    formats: dict[str, dict],
    compressors: dict[str, dict],
    reps_serialize: int,
    reps_compress: int,
) -> dict:
    """Mede um dataset.

    Retorna dict aninhado:
    ```
    {
      "raw_lines": int,
      "formats": {
        "<fmt>": {
          "bytes": int,
          "rt": bool,
          "t_serialize_us": float,
          "t_parse_us": float,
          "compressors": {
            "<comp>": {
              "bytes": int,
              "rt_compressor": bool,
              "rt_full": bool,
              "t_compress_us": float,
              "t_decompress_us": float,
            },
            ...
          }
        },
        ...
      }
    }
    ```
    """
    result: dict = {"raw_lines": len(linhas), "formats": {}}

    for fmt_name, fmt in formats.items():
        ser = fmt["serialize"]
        prs = fmt["parse"]
        text = ser(linhas)
        bytes_ = text.encode("utf-8")
        parsed = prs(text)
        rt = parsed == linhas

        t_s = time_median_us(lambda: ser(linhas), reps_serialize)
        t_p = time_median_us(lambda: prs(text), reps_serialize)

        fmt_result: dict = {
            "bytes":          len(bytes_),
            "rt":             rt,
            "t_serialize_us": round(t_s, 1),
            "t_parse_us":     round(t_p, 1),
            "compressors":    {},
        }

        for comp_name, comp in compressors.items():
            cfn = comp["compress"]
            dfn = comp["decompress"]
            c = cfn(bytes_)
            d = dfn(c)
            rt_c = d == bytes_
            rt_full = prs(d.decode("utf-8")) == linhas

            t_c = time_median_us(lambda: cfn(bytes_), reps_compress)
            t_d = time_median_us(lambda: dfn(c), reps_compress)

            fmt_result["compressors"][comp_name] = {
                "bytes":            len(c),
                "rt_compressor":    rt_c,
                "rt_full":          rt_full,
                "t_compress_us":    round(t_c, 1),
                "t_decompress_us":  round(t_d, 1),
            }

        result["formats"][fmt_name] = fmt_result

    return result


def write_outputs(
    out_dir,
    ds: str,
    linhas: list[str],
    formats: dict,
    compressors: dict,
) -> None:
    """Escreve outputs hierarquizados:

    - `outputs/raw/<fmt>/<ds>.<ext>`
    - `outputs/compressed/<fmt>/<comp>/<ds>.<ext>.<comp_ext>`
    """
    from pathlib import Path

    out_dir = Path(out_dir)

    for fmt_name, fmt in formats.items():
        text = fmt["serialize"](linhas)
        bytes_ = text.encode("utf-8")
        raw_dir = out_dir / "raw" / fmt_name
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{ds}.{fmt['ext']}").write_bytes(bytes_)

        for comp_name, comp in compressors.items():
            c = comp["compress"](bytes_)
            comp_dir = out_dir / "compressed" / fmt_name / comp_name
            comp_dir.mkdir(parents=True, exist_ok=True)
            (
                comp_dir / f"{ds}.{fmt['ext']}.{comp['ext']}"
            ).write_bytes(c)
