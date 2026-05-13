import os
import json
from typing import Dict, Any
import numpy as np
import pandas as pd
from .schema import infer_column_type

UNK_TOKEN = 0


def fit_artifacts(tables: Dict[str, pd.DataFrame], n_bins: int = 16) -> Dict[str, Any]:
    """Fit categorical vocabularies and numeric binning parameters per table.column."""
    vocab: Dict[str, Dict[str, int]] = {}
    bins: Dict[str, Dict[str, float]] = {}

    for tname, df in tables.items():
        for col in df.columns:
            key = f"{tname}.{col}"
            col_type = infer_column_type(df[col])
            if col_type == "categorical":
                # frequency order for stability
                counts = df[col].astype(str).value_counts()
                mapping: Dict[str, int] = {"__unk__": UNK_TOKEN}
                idx = 1
                for val in counts.index:
                    v = str(val)
                    if v == "":
                        continue
                    mapping[v] = idx
                    idx += 1
                vocab[key] = mapping
            else:
                # numeric: compute min/max for uniform quantization
                vals = pd.to_numeric(df[col], errors='coerce')
                vmin = float(np.nanmin(vals.values)) if vals.notna().any() else 0.0
                vmax = float(np.nanmax(vals.values)) if vals.notna().any() else 0.0
                if vmax < vmin:
                    vmax = vmin
                bins[key] = {"min": vmin, "max": vmax, "n_bins": int(n_bins)}

    return {"vocab": vocab, "bins": bins}


def save_artifacts(artifacts: Dict[str, Any], artifacts_dir: str) -> None:
    os.makedirs(artifacts_dir, exist_ok=True)
    with open(os.path.join(artifacts_dir, "vocab.json"), "w", encoding="utf-8") as f:
        json.dump(artifacts.get("vocab", {}), f, ensure_ascii=False)
    with open(os.path.join(artifacts_dir, "bins.json"), "w", encoding="utf-8") as f:
        json.dump(artifacts.get("bins", {}), f, ensure_ascii=False)


def load_artifacts(artifacts_dir: str) -> Dict[str, Any]:
    with open(os.path.join(artifacts_dir, "vocab.json"), encoding="utf-8") as f:
        vocab = json.load(f)
    with open(os.path.join(artifacts_dir, "bins.json"), encoding="utf-8") as f:
        bins = json.load(f)
    return {"vocab": vocab, "bins": bins}
