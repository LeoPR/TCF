import os
import json
import pandas as pd
from typing import Dict, Any, Tuple

# Utilities to read metadata and load tables consistently

def load_metadata(metadata_path: str) -> Dict[str, Any]:
    if not os.path.isfile(metadata_path):
        raise FileNotFoundError(f"metadata.json não encontrado em {metadata_path}")
    with open(metadata_path, encoding="utf-8") as f:
        meta_raw = json.load(f)
    meta = {}
    for tname, spec in meta_raw.items():
        file_part, pk, fks = None, None, {}
        v = str(spec).strip()
        if "#" in v:
            file_part, tail = v.split("#", 1)
            file_part = file_part.strip()
            if "=" in tail:
                for pair in tail.split(","):
                    if "=" in pair:
                        k, col = pair.strip().split("=", 1)
                        fks[k.strip()] = col.strip()
            else:
                pk = tail.strip()
        else:
            file_part = v
        meta[tname] = {"file": file_part, "pk": pk, "fks": fks}
    return meta


def resolve_file_path(cwd: str, file_part: str) -> str:
    cand = os.path.join(cwd, file_part)
    if os.path.isfile(cand):
        return cand
    for ext in (".csv", ".json"):
        cand2 = os.path.join(cwd, file_part + ext)
        if os.path.isfile(cand2):
            return cand2
    # fallback search in CWD without join
    if os.path.isfile(file_part):
        return file_part
    for ext in (".csv", ".json"):
        if os.path.isfile(file_part + ext):
            return file_part + ext
    raise FileNotFoundError(f"Arquivo para '{file_part}' não encontrado a partir de {cwd}")


def load_tables(cwd: str, meta: Dict[str, Any]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    tables, meta_info = {}, {}
    for tname, spec in meta.items():
        fpath = resolve_file_path(cwd, spec["file"])
        if fpath.lower().endswith(".csv"):
            df = pd.read_csv(fpath, dtype=str, keep_default_na=False)
        elif fpath.lower().endswith(".json"):
            with open(fpath, encoding="utf-8") as fj:
                raw = json.load(fj)
                if isinstance(raw, list):
                    df = pd.DataFrame(raw)
                elif isinstance(raw, dict) and "rows" in raw:
                    df = pd.DataFrame(raw["rows"])
                else:
                    raise ValueError(f"{fpath} inválido. Deve ser lista ou dict com 'rows'.")
            # ensure str dtype consistently
            df = df.applymap(lambda x: "" if x is None else str(x))
        else:
            raise ValueError(f"Extensão de arquivo não suportada: {fpath}")
        tables[tname] = df
        meta_info[tname] = {"file": fpath, "pk": spec.get("pk"), "fks": spec.get("fks", {})}
    return tables, meta_info


def infer_column_type(series: pd.Series, thresh_numeric: float = 0.95) -> str:
    """Return 'numeric' or 'categorical' based on cast success rate."""
    s = series.astype(str)
    ok = 0
    total = len(s)
    for v in s:
        v2 = v.strip()
        if v2 == "":
            continue
        try:
            float(v2)
            ok += 1
        except Exception:
            pass
    ratio = ok / max(total, 1)
    return "numeric" if ratio >= thresh_numeric else "categorical"
