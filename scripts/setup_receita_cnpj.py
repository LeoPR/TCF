"""Set up the receita-cnpj canonical dataset (REAL Brazilian CNPJ, non-PII).

Real-data counterpart to the synthetic `br-identidades`. Companies (pessoa
juridica) are public, non-PII data, so a CNPJ slice CAN be sourced — and a
real CNPJ column is the only path that can move the ADR-0015 CNPJ nature
toward 'confirmada-empirica' (see ticket T-DATA-2-RECEITA-CNPJ).

Source: Receita Federal Dados Publicos CNPJ (monthly), file "Estabelecimentos"
(10 parts, Estabelecimentos0.zip .. Estabelecimentos9.zip). Each unzips to a
semicolon-separated, NO-HEADER, ISO-8859-1 (Latin-1) CSV with 30 columns. The
CNPJ is split across 3 columns: cnpj_basico(8) + cnpj_ordem(4) + cnpj_dv(2),
which we re-assemble into the masked form NN.NNN.NNN/NNNN-DD.

This script downloads ONE part (~290 MB), unzips, takes the first N rows
(default 200k), assembles + validates the CNPJ against TCF's own SPEC_CNPJ,
projects a small set of columns, and writes the canonical light reference +
a 2000-row frozen fixture for a real-world snapshot gate.

NETWORK NOTE: the official host (dadosabertos.rfb.gov.br) may be unreachable
from some networks. Pass --zip <path> to process an ALREADY-DOWNLOADED zip
(drop it in Z:/tcf-data/external/receita-cnpj/ or anywhere) and skip the
download entirely.

Usage:
    # autodetect period + download part 0, slice 200k:
    python scripts/setup_receita_cnpj.py
    # specify period / part / volume:
    python scripts/setup_receita_cnpj.py --period 2025-05 --part 0 --rows 200000
    # process an already-downloaded zip (no network):
    python scripts/setup_receita_cnpj.py --zip Z:/tcf-data/external/receita-cnpj/Estabelecimentos0.zip
    # then:
    python scripts/csv_to_sqlite.py receita-cnpj
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf.natures import SPEC_CNPJ  # noqa: E402

DATASET = "receita-cnpj"
TABLE = "estabelecimentos"

# Candidate directory roots that expose an autoindex of period subfolders
# (YYYY-MM/). The exact filename inside each period varies over time, so we
# DISCOVER it from the directory listing instead of guessing — earlier guesses
# (Estabelecimentos0.zip) 404'd even on a reachable host. Tried in order.
# --zip bypasses all network entirely.
INDEX_BASES = [
    "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/",
    "https://arquivos.receitafederal.gov.br/CNPJ/dados_abertos_cnpj/",
    "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/",
    "https://dadosabertos.rfb.gov.br/CNPJ/",
]

# Estabelecimentos layout — 30 columns, fixed order (Receita "novo layout";
# cross-checked against okfn-brasil/receita startdb.sql).
RAW_COLUMNS = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
    "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
    "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
    "data_inicio_atividade", "cnae_fiscal", "cnae_fiscal_secundario",
    "tipo_logradouro", "logradouro", "numero", "complemento", "bairro",
    "cep", "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2",
    "ddd_fax", "telefone_fax", "correio_eletronico", "situacao_especial",
    "data_situacao_especial",
]
_IDX = {name: i for i, name in enumerate(RAW_COLUMNS)}

# Projected columns we keep (the dataset we actually publish).
COLUMNS = {
    "cnpj":             {"type": "string", "nullable": False,
                         "note": "Masked NN.NNN.NNN/NNNN-DD assembled from basico+ordem+dv; nature='cnpj' target"},
    "matriz_filial":    {"type": "string", "nullable": False,
                         "note": "1=matriz, 2=filial"},
    "nome_fantasia":    {"type": "string", "nullable": True,
                         "note": "Trade name (real free text); empty for many rows"},
    "situacao":         {"type": "string", "nullable": False,
                         "note": "Situacao cadastral code (01..08), low-card"},
    "data_inicio":      {"type": "string", "nullable": True,
                         "note": "Activity start date, raw YYYYMMDD (0 means missing)"},
    "cnae_principal":   {"type": "string", "nullable": True,
                         "note": "Primary CNAE code (7 digits)"},
    "uf":               {"type": "string", "nullable": True,
                         "note": "State 2-letter code"},
    "municipio_cod":    {"type": "string", "nullable": True,
                         "note": "Receita municipality code (NOT the IBGE code)"},
}
SCHEMA = {TABLE: {"pk": ["cnpj"], "fk": {}, "columns": COLUMNS}}


def _format_cnpj(basico: str, ordem: str, dv: str) -> str | None:
    """Assemble masked CNPJ NN.NNN.NNN/NNNN-DD. Returns None if not 8/4/2 digits."""
    basico = basico.strip().zfill(8)
    ordem = ordem.strip().zfill(4)
    dv = dv.strip().zfill(2)
    if not (len(basico) == 8 and basico.isdigit()
            and len(ordem) == 4 and ordem.isdigit()
            and len(dv) == 2 and dv.isdigit()):
        return None
    return f"{basico[:2]}.{basico[2:5]}.{basico[5:8]}/{ordem}-{dv}"


_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tcf-dataset-setup/1.0"}


def _fetch_index(url: str, timeout: int = 40) -> list[str]:
    """Fetch an autoindex page and return the list of href entries (raw)."""
    import re
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
    return re.findall(r'href=["\']([^"\']+)["\']', body)


def _find_index_base(verbose: bool = True) -> str:
    """Return the first INDEX_BASES that responds with a usable directory page."""
    import re
    last = None
    for base in INDEX_BASES:
        try:
            hrefs = _fetch_index(base)
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:70]}"
            if verbose:
                print(f"[receita]   index {base} -> {last}")
            continue
        has_period = any(re.search(r"20\d\d-\d\d", h) for h in hrefs)
        has_zip = any(h.lower().endswith(".zip") for h in hrefs)
        if has_period or has_zip:
            if verbose:
                print(f"[receita] using index base: {base}")
            return base
        if verbose:
            print(f"[receita]   index {base} -> reachable but no period/zip links")
    raise RuntimeError(
        f"No usable index base found (last: {last}). Use --zip <path> with a "
        "manually downloaded file, or --period + --base."
    )


def _latest_period(base: str, verbose: bool = True) -> str:
    """List period subfolders (YYYY-MM/) under base and return the newest."""
    import re
    hrefs = _fetch_index(base)
    periods = sorted(set(re.findall(r"(20\d\d-\d\d)", " ".join(hrefs))))
    if not periods:
        raise RuntimeError(f"No YYYY-MM period folders found under {base}")
    if verbose:
        print(f"[receita] periods available: {periods[-6:]} (using {periods[-1]})")
    return periods[-1]


def _estabelecimento_urls(base: str, period: str, verbose: bool = True) -> list[str]:
    """Discover the REAL Estabelecimentos file URLs inside a period folder.

    The filename has varied over time (Estabelecimentos0.zip, Estabelecimentos_0.zip,
    K3241.K03200Y0...ESTABELE...zip). We read the listing and match anything
    that looks like an establishments file, rather than guessing.
    """
    import re
    purl = base.rstrip("/") + "/" + period + "/"
    hrefs = _fetch_index(purl)
    cands = []
    for h in hrefs:
        name = h.split("/")[-1]
        if not name.lower().endswith(".zip"):
            continue
        if "estabelec" in name.lower() or "ESTABELE" in name:
            full = h if h.startswith("http") else purl + name
            cands.append(full)
    cands.sort()
    if verbose:
        print(f"[receita] establishments files in {period}: {len(cands)} found")
        for c in cands[:3]:
            print(f"           {c}")
    if not cands:
        raise RuntimeError(
            f"No Estabelecimentos*.zip found under {purl}. Inspect with --list."
        )
    return cands


def list_remote(verbose: bool = True) -> None:
    """--list mode: print the discoverable index tree (base -> periods -> files)."""
    base = _find_index_base(verbose=True)
    import re
    hrefs = _fetch_index(base)
    periods = sorted(set(re.findall(r"(20\d\d-\d\d)", " ".join(hrefs))))
    print(f"\nINDEX BASE: {base}")
    print(f"PERIODS ({len(periods)}): {periods}")
    if periods:
        latest = periods[-1]
        purl = base.rstrip("/") + "/" + latest + "/"
        files = [h.split("/")[-1] for h in _fetch_index(purl) if h.lower().endswith(".zip")]
        print(f"\nFILES in {latest} ({len(files)}):")
        for f in sorted(files):
            print(f"  {f}")


def download_zip(part: int, period: str | None, base: str | None, verbose: bool = True) -> Path:
    out = external_dir(DATASET)
    out.mkdir(parents=True, exist_ok=True)

    if base is None:
        base = _find_index_base(verbose)
    if period is None:
        period = _latest_period(base, verbose)

    urls = _estabelecimento_urls(base, period, verbose)
    # pick the requested part if the filenames carry an index; else the part-th
    url = None
    for u in urls:
        tail = u.rsplit("/", 1)[-1]
        if f"{part}.zip" in tail or f"_{part}.zip" in tail or f"-{part}.zip" in tail:
            url = u
            break
    if url is None:
        url = urls[part] if part < len(urls) else urls[0]

    dst = out / url.rsplit("/", 1)[-1]
    if dst.exists() and dst.stat().st_size > 1_000_000:
        if verbose:
            print(f"[receita] zip already present: {dst} ({dst.stat().st_size/1024/1024:.1f} MB)")
        return dst

    if verbose:
        print(f"[receita] downloading {url}")
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=180) as r, dst.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if verbose and total % (50 << 20) < (1 << 20):
                print(f"[receita]   downloaded {total/1024/1024:.0f} MB ...")
    if verbose:
        print(f"[receita] saved {dst} ({dst.stat().st_size/1024/1024:.1f} MB)")
    return dst


def process_zip(zip_path: Path, n_rows: int, verbose: bool = True):
    """Stream the inner CSV, project + validate, write the dataset CSV."""
    out = external_dir(DATASET)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{TABLE}.csv"

    n_written = 0
    n_compressible = 0
    n_bad_format = 0
    with zipfile.ZipFile(zip_path) as z:
        inner = z.namelist()[0]
        if verbose:
            print(f"[receita] inner file: {inner}")
        with z.open(inner) as raw, csv_path.open("w", encoding="utf-8", newline="") as fout:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            reader = csv.reader(text, delimiter=";", quotechar='"')
            w = csv.writer(fout)
            w.writerow(list(COLUMNS.keys()))
            for row in reader:
                if len(row) < len(RAW_COLUMNS):
                    continue
                cnpj = _format_cnpj(row[_IDX["cnpj_basico"]],
                                    row[_IDX["cnpj_ordem"]],
                                    row[_IDX["cnpj_dv"]])
                if cnpj is None:
                    n_bad_format += 1
                    continue
                status = SPEC_CNPJ.classify_value(cnpj)
                if status == "compressible":
                    n_compressible += 1
                w.writerow([
                    cnpj,
                    row[_IDX["identificador_matriz_filial"]].strip(),
                    row[_IDX["nome_fantasia"]].strip(),
                    row[_IDX["situacao_cadastral"]].strip(),
                    row[_IDX["data_inicio_atividade"]].strip(),
                    row[_IDX["cnae_fiscal"]].strip(),
                    row[_IDX["uf"]].strip(),
                    row[_IDX["municipio"]].strip(),
                ])
                n_written += 1
                if n_written >= n_rows:
                    break
    if verbose:
        pct = (100 * n_compressible / n_written) if n_written else 0
        print(f"[receita] wrote {n_written:,} rows -> {csv_path} ({csv_path.stat().st_size/1024/1024:.1f} MB)")
        print(f"[receita] compressible under SPEC_CNPJ: {n_compressible:,}/{n_written:,} ({pct:.1f}%)")
        print(f"[receita] skipped malformed cnpj rows: {n_bad_format:,}")
    return csv_path, n_written, n_compressible


def write_metadata(n_rows: int, n_compressible: int, period: str | None) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / DATASET
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": DATASET,
        "synthetic": False,
        "source": "Receita Federal — Dados Publicos CNPJ (Estabelecimentos)",
        "origin": "https://dadosabertos.rfb.gov.br/CNPJ/ (monthly); mirror arquivos.receitafederal.gov.br",
        "period": period,
        "license": "Dados abertos (Receita Federal). Pessoa juridica = nao-PII.",
        "license_note": "Confirmar termos de uso antes de redistribuir o dado bruto.",
        "citation": "Receita Federal do Brasil. Dados Publicos CNPJ.",
        "downloaded_via": "scripts/setup_receita_cnpj.py (1 part Estabelecimentos, slice)",
        "note": (
            "REAL CNPJ slice (non-PII). Counterpart to synthetic br-identidades. "
            "Volume %d rows exceeds shaper <=100k regime -> use direct encode()."
            % n_rows
        ),
        "cnpj_compressible_count": n_compressible,
        "cnpj_compressible_pct": round(100 * n_compressible / n_rows, 2) if n_rows else 0,
        "row_counts": {TABLE: n_rows},
        "column_count": len(COLUMNS),
        "tables": SCHEMA,
    }
    (meta_dir / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[receita] metadata: {meta_dir / 'metadata.json'}")


def generate_samples(csv_path: Path) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / DATASET
    samples_dir.mkdir(parents=True, exist_ok=True)
    # 100-row sample + 2000-row frozen fixture for a real-world snapshot gate
    for name, n in [("estabelecimentos-sample.csv", 100), ("cnpj-2k.csv", 2000)]:
        dst = samples_dir / name
        with csv_path.open("r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i > n:
                    break
                lines.append(line)
        dst.write_text("".join(lines), encoding="utf-8")
        print(f"[receita]   sample: {name} ({dst.stat().st_size/1024:.1f} KB, {n} rows)")


def main():
    ap = argparse.ArgumentParser(description="Set up receita-cnpj (real CNPJ slice)")
    ap.add_argument("--period", help="YYYY-MM (default: latest discovered)")
    ap.add_argument("--base", help="override index base URL (a dir listing of YYYY-MM/ folders)")
    ap.add_argument("--part", type=int, default=0, help="Estabelecimentos part 0..9 (default 0)")
    ap.add_argument("--rows", type=int, default=200_000, help="rows to slice (default 200000)")
    ap.add_argument("--zip", dest="zip_path", help="process an already-downloaded zip (skip download)")
    ap.add_argument("--list", action="store_true",
                    help="just discover + print the remote index tree (no download)")
    args = ap.parse_args()

    ensure_dirs()
    if args.list:
        list_remote()
        return

    if args.zip_path:
        zip_path = Path(args.zip_path)
        period = args.period
        if not zip_path.exists():
            sys.exit(f"--zip not found: {zip_path}")
    else:
        zip_path = download_zip(args.part, args.period, args.base)
        period = args.period

    csv_path, n_rows, n_compressible = process_zip(zip_path, args.rows)
    write_metadata(n_rows, n_compressible, period)
    generate_samples(csv_path)
    print(f"\n[receita] Done. {n_rows:,} rows.")
    print(f"[receita] Raw data: {csv_path.parent}")
    print("[receita] Next: python scripts/csv_to_sqlite.py receita-cnpj")


if __name__ == "__main__":
    main()
