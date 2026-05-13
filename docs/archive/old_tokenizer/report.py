import os
import json
from typing import Dict, Any
import numpy as np
import pandas as pd

from .schema import load_metadata, load_tables
from .vocab import load_artifacts


def compute_stats(tables: Dict[str, pd.DataFrame], artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """Compute statistics: vocab size, coverage, OOV, bin distribution, etc."""
    vocab = artifacts.get("vocab", {})
    bins = artifacts.get("bins", {})
    
    stats: Dict[str, Any] = {
        "vocab_stats": {},
        "bins_stats": {},
        "global": {
            "total_vocab_size": sum(len(v) for v in vocab.values()),
            "total_categorical_cols": len(vocab),
            "total_numeric_cols": len(bins),
        }
    }
    
    # Categorical stats
    for tname, df in tables.items():
        for col in df.columns:
            key = f"{tname}.{col}"
            if key in vocab:
                mapping = vocab[key]
                vals = df[col].astype(str)
                unique_vals = set(vals.unique())
                vocab_keys = set(mapping.keys()) - {"__unk__"}
                
                # Coverage and OOV
                covered = unique_vals & vocab_keys
                oov = unique_vals - vocab_keys - {""}
                
                # Frequency distribution
                counts = vals.value_counts()
                freq_dist = {str(k): int(v) for k, v in counts.head(10).items()}
                
                stats["vocab_stats"][key] = {
                    "vocab_size": len(mapping),
                    "unique_values": len(unique_vals),
                    "covered": len(covered),
                    "oov_count": len(oov),
                    "coverage_ratio": len(covered) / max(len(unique_vals), 1),
                    "top_10_freq": freq_dist,
                    "total_rows": len(vals)
                }
    
    # Numeric stats
    for tname, df in tables.items():
        for col in df.columns:
            key = f"{tname}.{col}"
            if key in bins:
                bn = bins[key]
                vals = pd.to_numeric(df[col], errors='coerce')
                valid = vals.dropna()
                
                # Compute bin distribution
                min_val, max_val, n_bins = bn["min"], bn["max"], bn["n_bins"]
                if len(valid) > 0:
                    rng = max(max_val - min_val, 1e-12)
                    scaled = (valid - min_val) / rng
                    inds = np.floor(scaled * n_bins).clip(0, n_bins - 1).astype(int)
                    bin_counts = np.bincount(inds, minlength=n_bins)
                    bin_dist = {f"bin_{i}": int(c) for i, c in enumerate(bin_counts)}
                else:
                    bin_dist = {}
                
                stats["bins_stats"][key] = {
                    "min": float(min_val),
                    "max": float(max_val),
                    "n_bins": int(n_bins),
                    "total_rows": len(df),
                    "valid_values": len(valid),
                    "na_count": len(vals) - len(valid),
                    "bin_distribution": bin_dist
                }
    
    return stats


def save_report(stats: Dict[str, Any], output_path: str) -> None:
    """Save stats report as JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def print_summary(stats: Dict[str, Any]) -> None:
    """Print human-readable summary to console."""
    print("\n=== Resumo do Tokenizador ===\n")
    g = stats["global"]
    print(f"Total de colunas categóricas: {g['total_categorical_cols']}")
    print(f"Total de colunas numéricas: {g['total_numeric_cols']}")
    print(f"Tamanho total do vocabulário: {g['total_vocab_size']}")
    
    print("\n--- Colunas Categóricas ---")
    for key, info in stats["vocab_stats"].items():
        cov_pct = info["coverage_ratio"] * 100
        print(f"{key}:")
        print(f"  Vocab: {info['vocab_size']} | Únicos: {info['unique_values']} | "
              f"Cobertura: {cov_pct:.1f}% | OOV: {info['oov_count']}")
    
    print("\n--- Colunas Numéricas ---")
    for key, info in stats["bins_stats"].items():
        na_pct = info["na_count"] / max(info["total_rows"], 1) * 100
        print(f"{key}:")
        print(f"  Range: [{info['min']:.2f}, {info['max']:.2f}] | Bins: {info['n_bins']} | "
              f"Valid: {info['valid_values']} | NA: {info['na_count']} ({na_pct:.1f}%)")
