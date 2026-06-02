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

# Receita migrated the open-data repository to a Nextcloud public share served
# over WebDAV (discovered 2026-06-02 from the actively-maintained
# rictom/cnpj-sqlite downloader). The flat /dados/cnpj/... HTTP paths 404; the
# REAL API is a WebDAV PROPFIND on /public.php/webdav with HTTP Basic auth
# (user = share token, empty password), and downloads via /public.php/dav/files.
# Verified 2026-06-02: PROPFIND root -> 207, months up to 2026-05;
# Estabelecimentos0.zip is ~1.99 GB (NOT the ~290 MB earlier estimate).
WEBDAV_HOST = "https://arquivos.receitafederal.gov.br"
SHARE_TOKEN = "YggdBLfdninEJX9"
WEBDAV_ROOT = f"{WEBDAV_HOST}/public.php/webdav"          # PROPFIND listing
DAV_FILES = f"{WEBDAV_HOST}/public.php/dav/files/{SHARE_TOKEN}"  # GET downloads

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


def _basic_auth() -> str:
    import base64
    return "Basic " + base64.b64encode((SHARE_TOKEN + ":").encode()).decode()


def _propfind(url: str, timeout: int = 60) -> str:
    """WebDAV PROPFIND (Depth 1). Returns the XML multistatus body."""
    req = urllib.request.Request(
        url, method="PROPFIND",
        headers={**_UA, "Depth": "1", "Authorization": _basic_auth()},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _list_months(verbose: bool = True) -> list[str]:
    import re
    body = _propfind(WEBDAV_ROOT + "/")
    months = sorted(set(re.findall(r"(20\d\d-\d\d)", body)))
    if not months:
        raise RuntimeError("WebDAV PROPFIND returned no YYYY-MM folders")
    if verbose:
        print(f"[receita] months available: {months[-6:]} (latest {months[-1]})")
    return months


def _list_files(period: str) -> list[str]:
    import re
    import urllib.parse
    body = _propfind(WEBDAV_ROOT + "/" + period + "/")
    hrefs = re.findall(r"<[dD]:href>([^<]+)</[dD]:href>", body)
    return sorted({urllib.parse.unquote(h.split("/")[-1])
                   for h in hrefs if h.lower().endswith(".zip")})


def _estabelecimento_name(period: str, part: int, verbose: bool = True) -> str:
    """Find the real Estabelecimentos filename for a part inside a period."""
    files = _list_files(period)
    estab = [f for f in files if "estabelec" in f.lower()]
    if verbose:
        print(f"[receita] establishments files in {period}: {estab[:3]}{' ...' if len(estab) > 3 else ''}")
    if not estab:
        raise RuntimeError(f"No Estabelecimentos*.zip in {period}. Files: {files[:8]}")
    for f in estab:
        if f"{part}.zip" in f or f"_{part}.zip" in f or f"-{part}.zip" in f:
            return f
    return estab[part] if part < len(estab) else estab[0]


def list_remote(verbose: bool = True) -> None:
    """--list mode: print the real WebDAV tree (months -> files of latest)."""
    months = _list_months(verbose=True)
    print(f"\nWEBDAV ROOT: {WEBDAV_ROOT}")
    print(f"MONTHS ({len(months)}): {months}")
    latest = months[-1]
    files = _list_files(latest)
    print(f"\nFILES in {latest} ({len(files)}):")
    for f in files:
        print(f"  {f}")


def file_url(period: str, name: str) -> str:
    """Build the WebDAV download URL for a file in a period folder."""
    return f"{DAV_FILES}/{period}/{name}"


def download_zip(part: int, period: str | None, verbose: bool = True) -> Path:
    """Download the full Estabelecimentos part to disk (fallback path).

    NOTE: each part is ~2 GB. Prefer stream_rows() which downloads only as far
    as needed to collect n_rows. This full download exists for callers that want
    the raw zip retained (e.g. to re-slice later).
    """
    out = external_dir(DATASET)
    out.mkdir(parents=True, exist_ok=True)
    if period is None:
        period = _list_months(verbose)[-1]
    name = _estabelecimento_name(period, part, verbose)
    url = file_url(period, name)
    dst = out / name
    if dst.exists() and dst.stat().st_size > 1_000_000:
        if verbose:
            print(f"[receita] zip already present: {dst} ({dst.stat().st_size/1024/1024:.1f} MB)")
        return dst
    if verbose:
        print(f"[receita] downloading (full) {url}")
    req = urllib.request.Request(url, headers={**_UA, "Authorization": _basic_auth()})
    with urllib.request.urlopen(req, timeout=300) as r, dst.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if verbose and total % (100 << 20) < (1 << 20):
                print(f"[receita]   downloaded {total/1024/1024:.0f} MB ...")
    if verbose:
        print(f"[receita] saved {dst} ({dst.stat().st_size/1024/1024:.1f} MB)")
    return dst


def _project_row(raw_row: list[str]):
    """Map one 30-col raw establishments row -> (out_row, is_compressible) or None."""
    if len(raw_row) < len(RAW_COLUMNS):
        return None
    cnpj = _format_cnpj(raw_row[_IDX["cnpj_basico"]],
                        raw_row[_IDX["cnpj_ordem"]],
                        raw_row[_IDX["cnpj_dv"]])
    if cnpj is None:
        return None
    out_row = [
        cnpj,
        raw_row[_IDX["identificador_matriz_filial"]].strip(),
        raw_row[_IDX["nome_fantasia"]].strip(),
        raw_row[_IDX["situacao_cadastral"]].strip(),
        raw_row[_IDX["data_inicio_atividade"]].strip(),
        raw_row[_IDX["cnae_fiscal"]].strip(),
        raw_row[_IDX["uf"]].strip(),
        raw_row[_IDX["municipio"]].strip(),
    ]
    return out_row, (SPEC_CNPJ.classify_value(cnpj) == "compressible")


def _consume_csv(text_stream, n_rows: int, verbose: bool):
    """Read a semicolon CSV text stream, project rows, write the dataset CSV.

    Returns (csv_path, n_written, n_compressible). Stops after n_rows.
    Raises _StopEnough internally is avoided; caller may break the producer.
    """
    out = external_dir(DATASET)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{TABLE}.csv"
    n_written = n_compressible = n_bad = 0
    reader = csv.reader(text_stream, delimiter=";", quotechar='"')
    with csv_path.open("w", encoding="utf-8", newline="") as fout:
        w = csv.writer(fout)
        w.writerow(list(COLUMNS.keys()))
        for raw in reader:
            res = _project_row(raw)
            if res is None:
                n_bad += 1
                continue
            out_row, comp = res
            w.writerow(out_row)
            n_written += 1
            if comp:
                n_compressible += 1
            if n_written >= n_rows:
                break
    if verbose:
        pct = (100 * n_compressible / n_written) if n_written else 0
        print(f"[receita] wrote {n_written:,} rows -> {csv_path} ({csv_path.stat().st_size/1024/1024:.1f} MB)")
        print(f"[receita] compressible under SPEC_CNPJ: {n_compressible:,}/{n_written:,} ({pct:.1f}%)")
        print(f"[receita] skipped malformed cnpj rows: {n_bad:,}")
    return csv_path, n_written, n_compressible


def process_zip(zip_path: Path, n_rows: int, verbose: bool = True):
    """Process an ALREADY-DOWNLOADED zip on disk (used by --zip)."""
    with zipfile.ZipFile(zip_path) as z:
        inner = z.namelist()[0]
        if verbose:
            print(f"[receita] inner file: {inner}")
        with z.open(inner) as rawf:
            text = io.TextIOWrapper(rawf, encoding="latin-1", newline="")
            return _consume_csv(text, n_rows, verbose)


def _stream_inflate_lines(resp, cap_bytes: int):
    """Yield decoded text lines from a streamed ZIP without seeking.

    ZipFile needs to seek to the end-of-central-directory to open an archive, so
    it cannot read a 2 GB zip from a socket. Instead we parse the first member's
    LOCAL FILE HEADER (which sits at the very start, right after the PK\\x03\\x04
    signature) and feed the following compressed bytes straight into a streaming
    zlib raw-inflate. We stop downloading after cap_bytes of COMPRESSED data.
    """
    import struct
    import zlib

    head = b""
    while len(head) < 30:
        more = resp.read(30 - len(head))
        if not more:
            raise RuntimeError("stream ended before local file header")
        head += more
    if head[:4] != b"PK\x03\x04":
        raise RuntimeError(f"not a zip local header: {head[:4]!r}")
    method = struct.unpack("<H", head[8:10])[0]
    fnlen = struct.unpack("<H", head[26:28])[0]
    exlen = struct.unpack("<H", head[28:30])[0]
    # skip filename + extra to reach the compressed data
    to_skip = fnlen + exlen
    while to_skip > 0:
        s = resp.read(to_skip)
        if not s:
            break
        to_skip -= len(s)

    if method == 8:
        dec = zlib.decompressobj(-15)  # raw deflate
    elif method == 0:
        dec = None  # stored
    else:
        raise RuntimeError(f"unsupported zip method {method}")

    consumed = 0
    pending = b""
    while consumed < cap_bytes:
        chunk = resp.read(1 << 20)
        if not chunk:
            break
        consumed += len(chunk)
        data = dec.decompress(chunk) if dec else chunk
        if not data:
            continue
        pending += data
        parts = pending.split(b"\n")
        pending = parts.pop()
        for ln in parts:
            yield ln.decode("latin-1")
    if dec is not None:
        try:
            pending += dec.flush()
        except Exception:
            pass
    if pending:
        yield pending.decode("latin-1")


def stream_rows(period: str, part: int, n_rows: int, cap_mb: int, verbose: bool = True):
    """Download the Estabelecimentos zip ONLY as far as needed, extract n_rows.

    Avoids pulling the full ~2 GB part: opens the WebDAV stream, parses the zip
    local header, raw-inflates on the fly, and stops after n_rows (or cap_mb of
    compressed bytes). Raises if the cap is too small to reach n_rows.
    """
    name = _estabelecimento_name(period, part, verbose)
    url = file_url(period, name)
    if verbose:
        print(f"[receita] streaming {url}  (cap {cap_mb} MB, target {n_rows:,} rows)")
    req = urllib.request.Request(url, headers={**_UA, "Authorization": _basic_auth()})
    resp = urllib.request.urlopen(req, timeout=300)
    try:
        line_iter = _stream_inflate_lines(resp, cap_mb << 20)
        csv_path, nw, nc = _consume_csv(line_iter, n_rows, verbose)
    finally:
        resp.close()
    if nw < n_rows:
        raise RuntimeError(
            f"Stream cap {cap_mb} MB yielded only {nw:,}/{n_rows:,} rows. "
            f"Retry with a larger --cap-mb (or use --full to download the whole part)."
        )
    return csv_path, nw, nc


def write_metadata(n_rows: int, n_compressible: int, period: str | None) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / DATASET
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": DATASET,
        "synthetic": False,
        "source": "Receita Federal — Dados Publicos CNPJ (Estabelecimentos)",
        "origin": "WebDAV public share: arquivos.receitafederal.gov.br/public.php/dav/files/<token>/<YYYY-MM>/ (monthly)",
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
    ap.add_argument("--part", type=int, default=0, help="Estabelecimentos part 0..9 (default 0)")
    ap.add_argument("--rows", type=int, default=200_000, help="rows to slice (default 200000)")
    ap.add_argument("--zip", dest="zip_path", help="process an already-downloaded zip (skip download)")
    ap.add_argument("--list", action="store_true",
                    help="just discover + print the remote WebDAV tree (no download)")
    ap.add_argument("--full", action="store_true",
                    help="download the whole ~2GB part to disk instead of streaming")
    ap.add_argument("--cap-mb", type=int, default=120,
                    help="streaming download cap in MB (default 120; raise if rows fall short)")
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
        csv_path, n_rows, n_compressible = process_zip(zip_path, args.rows)
    elif args.full:
        zip_path = download_zip(args.part, args.period)
        period = args.period or _list_months()[-1]
        csv_path, n_rows, n_compressible = process_zip(zip_path, args.rows)
    else:
        period = args.period or _list_months()[-1]
        csv_path, n_rows, n_compressible = stream_rows(
            period, args.part, args.rows, args.cap_mb)
    write_metadata(n_rows, n_compressible, period)
    generate_samples(csv_path)
    print(f"\n[receita] Done. {n_rows:,} rows.")
    print(f"[receita] Raw data: {csv_path.parent}")
    print("[receita] Next: python scripts/csv_to_sqlite.py receita-cnpj")


if __name__ == "__main__":
    main()
