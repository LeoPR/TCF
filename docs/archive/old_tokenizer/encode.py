import os
import json
from typing import Dict, Any
import numpy as np
import pandas as pd

from .vocab import UNK_TOKEN


def _encode_categorical(series: pd.Series, mapping: Dict[str, int]) -> np.ndarray:
    vals = series.astype(str).values
    out = np.empty(len(vals), dtype=np.int32)
    unk = mapping.get("__unk__", UNK_TOKEN)
    for i, v in enumerate(vals):
        out[i] = mapping.get(v, unk)
    return out


def _encode_numeric(series: pd.Series, min_val: float, max_val: float, n_bins: int) -> np.ndarray:
    vals = pd.to_numeric(series, errors='coerce').values.astype(np.float64)
    out = np.full(len(vals), -1, dtype=np.int32)  # -1 para NA/invalid
    rng = max(max_val - min_val, 1e-12)
    scaled = (vals - min_val) / rng
    inds = np.floor(scaled * n_bins)
    inds = np.clip(inds, 0, n_bins - 1)
    mask = ~np.isnan(vals)
    out[mask] = inds[mask].astype(np.int32)
    return out


def encode_tables(tables: Dict[str, pd.DataFrame], artifacts: Dict[str, Any]) -> Dict[str, Dict[str, np.ndarray]]:
    vocab = artifacts.get("vocab", {})
    bins = artifacts.get("bins", {})
    encoded: Dict[str, Dict[str, np.ndarray]] = {}

    for tname, df in tables.items():
        table_tokens: Dict[str, np.ndarray] = {}
        for col in df.columns:
            key = f"{tname}.{col}"
            if key in vocab:
                arr = _encode_categorical(df[col], vocab[key])
            elif key in bins:
                bn = bins[key]
                arr = _encode_numeric(df[col], float(bn["min"]), float(bn["max"]), int(bn["n_bins"]))
            else:
                # default: categorical fallback
                mapping = {"__unk__": UNK_TOKEN}
                for i, v in enumerate(sorted(df[col].astype(str).unique())):
                    if v == "":
                        continue
                    mapping[v] = i + 1
                arr = _encode_categorical(df[col], mapping)
            table_tokens[col] = arr
        encoded[tname] = table_tokens
    return encoded


def save_tokens_jsonl(encoded: Dict[str, Dict[str, np.ndarray]], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for tname, cols in encoded.items():
        # align rows
        n = 0
        for arr in cols.values():
            n = max(n, len(arr))
        path = os.path.join(out_dir, f"{tname}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for i in range(n):
                row = {c: int(cols[c][i]) for c in cols}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
