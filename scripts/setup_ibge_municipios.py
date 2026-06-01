"""Download the IBGE municipalities dataset (Brazilian municipios).

Fetches the full list from the IBGE Localidades API and flattens the nested
hierarchy (municipio -> microrregiao -> mesorregiao -> UF -> regiao) into a
single flat table. Writes CSV to data_root/external/ibge-municipios/ and a
100-row sample in datasets/samples/ibge-municipios/ for git.

Brazilian real-world data: ~5571 rows, accented UTF-8 strings, high
categorical repetition (27 UFs, 5 regioes) -> exercises HCC composition on
repeated textual values.

Usage:
    python scripts/setup_ibge_municipios.py
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402


API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
TABLE = "municipios"

# Flat column order. The CSV header MUST match this order exactly, because
# csv_to_sqlite.py validates header == list(metadata columns).
COLUMNS = {
    "id":           {"type": "int", "nullable": False,
                     "note": "IBGE municipality code (7 digits)"},
    "municipio":    {"type": "string", "nullable": False,
                     "note": "Municipality name (UTF-8, accented)"},
    "microrregiao": {"type": "string", "nullable": False,
                     "note": "Microregion name (falls back to immediate region)"},
    "mesorregiao":  {"type": "string", "nullable": False,
                     "note": "Mesoregion name (falls back to intermediate region)"},
    "uf_sigla":     {"type": "string", "nullable": False,
                     "note": "State 2-letter code (e.g. SP)"},
    "uf_nome":      {"type": "string", "nullable": False,
                     "note": "State full name (e.g. Sao Paulo)"},
    "regiao_sigla": {"type": "string", "nullable": False,
                     "note": "Region 1-letter code (N/NE/SE/S/CO)"},
    "regiao_nome":  {"type": "string", "nullable": False,
                     "note": "Region full name (e.g. Sudeste)"},
}

SCHEMA = {
    TABLE: {
        "pk": ["id"],
        "fk": {},
        "columns": COLUMNS,
    }
}


def _fetch(url: str, verbose: bool = True) -> bytes:
    """Fetch a URL, transparently decompressing gzip responses.

    The IBGE API intermittently returns gzip even when not requested, so we
    detect the gzip magic bytes and decompress regardless of headers.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "tcf-dataset-setup/1.0",
            "Accept-Encoding": "identity",
        },
    )
    raw = urllib.request.urlopen(req, timeout=120).read()
    if raw[:2] == b"\x1f\x8b":
        if verbose:
            print("[ibge] gzip response detected -> decompressing")
        raw = gzip.decompress(raw)
    return raw


def _flatten(m: dict) -> dict:
    """Flatten one municipio record to the COLUMNS schema.

    Primary path: microrregiao -> mesorregiao -> UF -> regiao.
    Fallback (microrregiao is None for a few recent municipios):
    regiao-imediata -> regiao-intermediaria -> UF -> regiao.
    """
    micro = m.get("microrregiao")
    if micro is not None:
        meso = micro["mesorregiao"]
        uf = meso["UF"]
        micro_nome = micro["nome"]
        meso_nome = meso["nome"]
    else:
        ri = m["regiao-imediata"]
        rint = ri["regiao-intermediaria"]
        uf = rint["UF"]
        micro_nome = ri["nome"]
        meso_nome = rint["nome"]
    regiao = uf["regiao"]
    return {
        "id": m["id"],
        "municipio": m["nome"],
        "microrregiao": micro_nome,
        "mesorregiao": meso_nome,
        "uf_sigla": uf["sigla"],
        "uf_nome": uf["nome"],
        "regiao_sigla": regiao["sigla"],
        "regiao_nome": regiao["nome"],
    }


def download_ibge(verbose: bool = True) -> tuple[Path, list[dict]]:
    """Download + flatten IBGE municipios. Returns (output_dir, rows)."""
    ensure_dirs()
    output = external_dir("ibge-municipios")
    output.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[ibge] fetching {API_URL}")
    data = json.loads(_fetch(API_URL, verbose).decode("utf-8"))
    if verbose:
        print(f"[ibge] received {len(data)} municipios")

    rows = [_flatten(m) for m in data]
    # Deterministic order by IBGE code.
    rows.sort(key=lambda r: r["id"])

    csv_path = output / f"{TABLE}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(COLUMNS.keys()))
        w.writeheader()
        w.writerows(rows)

    size_kb = csv_path.stat().st_size / 1024
    if verbose:
        print(f"[ibge] saved: {csv_path} ({size_kb:.1f} KB, {len(rows)} rows)")
    return output, rows


def write_metadata(rows: list[dict]) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "ibge-municipios"
    meta_dir.mkdir(parents=True, exist_ok=True)

    n_uf = len({r["uf_sigla"] for r in rows})
    n_regiao = len({r["regiao_sigla"] for r in rows})

    meta = {
        "name": "ibge-municipios",
        "source": "IBGE Localidades API (servicodados.ibge.gov.br)",
        "origin": API_URL,
        "license": "Open data (IBGE) — see https://www.ibge.gov.br/",
        "citation": "IBGE. Divisao territorial brasileira. Instituto Brasileiro de Geografia e Estatistica.",
        "downloaded_via": "urllib (IBGE Localidades API v1)",
        "description": (
            "Brazilian municipalities flattened from the IBGE administrative "
            "hierarchy. Real-world UTF-8 text with high categorical repetition "
            f"({n_uf} UFs, {n_regiao} regioes)."
        ),
        "row_counts": {TABLE: len(rows)},
        "column_count": len(COLUMNS),
        "n_uf": n_uf,
        "n_regiao": n_regiao,
        "tables": SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[ibge] metadata: {meta_path}")


def generate_sample(external_path: Path, n_rows: int = 100) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "ibge-municipios"
    samples_dir.mkdir(parents=True, exist_ok=True)

    src = external_path / f"{TABLE}.csv"
    dst = samples_dir / "ibge-municipios-sample.csv"

    with src.open("r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i > n_rows:  # header + n_rows
                break
            lines.append(line)

    dst.write_text("".join(lines), encoding="utf-8")
    size_kb = dst.stat().st_size / 1024
    print(f"[ibge]   sample: ibge-municipios-sample.csv ({size_kb:.1f} KB, {n_rows} rows)")


def main():
    output, rows = download_ibge()
    write_metadata(rows)
    generate_sample(output, n_rows=100)

    print(f"\n[ibge] Done. {len(rows):,} rows x {len(COLUMNS)} columns.")
    print(f"[ibge] Raw data: {output}")
    print("[ibge] Metadata + sample: in git under datasets/canonical/ibge-municipios/")
    print("[ibge] Next: python scripts/csv_to_sqlite.py ibge-municipios")


if __name__ == "__main__":
    main()
