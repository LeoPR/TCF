"""Generate the br-identidades SYNTHETIC dataset (Brazilian CPF/CNPJ).

DECLARED BIAS — this is a SYNTHETIC / "built-to-test" dataset (Brunswik 1956
ecological-validity convention; CLAUDE.md anti-incident checklist Q4). It is
generated to exercise the ADR-0015 opt-in natures (SPEC_CPF / SPEC_CNPJ) and
the n_compressible>=~50% activation gate. It validates lossless round-trip and
the opt-in path, but per the project methodology it CANNOT alone justify a
'confirmada-empirica' claim — only a real source (e.g. Receita CNPJ open data,
see ticket T-DATA-2-RECEITA-CNPJ) can close the generalization gate.

What is REAL: geography (municipio/UF) reuses the canonical ibge-municipios
codes, so município/UF distribution is grounded. What is SYNTHETIC: the
identifiers (random mod-11-valid bodies, no regional 9th-digit encoding, not
issued documents), names, dates, emails.

Two related tables in one hub:
  - pessoas  (CPF, nature='cpf')   — primary high-volume table
  - empresas (CNPJ, nature='cnpj') — empresas.socio_cpf is a real cross-table
    FK into pessoas.cpf for ~30% of rows (exercises FK-candidate detection)

Identifiers are stored as STRINGS (leading zeros significant), all VALID and
MASKED (happy data). Check digits are computed by TCF's OWN welded specs
(src/tcf/natures), so every value satisfies classify_value()=='compressible'.

NOTE on volume: pessoas=500000 exceeds the shaper's validated <=100k regime
(T-SHAPER-CODE-HARDENING). Use this dataset via direct encode() on columns,
NOT via shaper sampling.

Usage (requires ibge-municipios already set up):
    python scripts/setup_ibge_municipios.py   # prerequisite (geography)
    python scripts/setup_br_identidades.py
    python scripts/csv_to_sqlite.py br-identidades
"""

from __future__ import annotations

import csv
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402

# Import TCF's OWN welded check-digit specs so generated identifiers are
# byte-identical to what the nature encoder expects (no reimplementation).
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf.natures import SPEC_CPF, SPEC_CNPJ  # noqa: E402

SEED = 20260601
N_PESSOAS = 500_000
N_EMPRESAS = 100_000
SOCIO_FRACTION = 0.30      # ~30% of empresas reference a real pessoas.cpf
EMAIL_EMPTY_FRACTION = 0.08  # ~8% of pessoas have no email (realistic, healthy)

# ---------------------------------------------------------------------------
# Schema (column order MUST match the CSV header — csv_to_sqlite requirement)
# ---------------------------------------------------------------------------
COLS_PESSOAS = {
    "cpf":           {"type": "string", "nullable": False,
                      "note": "Masked NNN.NNN.NNN-DD, valid mod-11, nature='cpf' target"},
    "nome":          {"type": "string", "nullable": False,
                      "note": "Synthetic BR full name (accented UTF-8)"},
    "municipio_id":  {"type": "int", "nullable": False,
                      "note": "7-digit IBGE code; soft ref into ibge-municipios.id (cross-hub, not a SQL FK)"},
    "uf_sigla":      {"type": "string", "nullable": False,
                      "note": "UF code denormalized from ibge-municipios (27 values)"},
    "data_cadastro": {"type": "date", "nullable": False,
                      "note": "ISO YYYY-MM-DD, 2010..2025, recency-weighted"},
    "email":         {"type": "string", "nullable": True,
                      "note": "Derived from nome + domain pool; empty for ~8%"},
}

COLS_EMPRESAS = {
    "cnpj":          {"type": "string", "nullable": False,
                      "note": "Masked NN.NNN.NNN/NNNN-DD, valid mod-11, nature='cnpj' target"},
    "razao_social":  {"type": "string", "nullable": False,
                      "note": "Synthetic company name with shared suffixes (Ltda/ME/SA/EIRELI/EPP)"},
    "municipio_id":  {"type": "int", "nullable": False,
                      "note": "7-digit IBGE code; soft ref into ibge-municipios.id (cross-hub)"},
    "uf_sigla":      {"type": "string", "nullable": False,
                      "note": "UF code denormalized from ibge-municipios"},
    "data_abertura": {"type": "date", "nullable": False,
                      "note": "ISO YYYY-MM-DD, 2005..2025"},
    "socio_cpf":     {"type": "string", "nullable": True,
                      "note": "References pessoas.cpf for ~30% of rows (real FK); empty otherwise"},
}

SCHEMA = {
    "pessoas":  {"pk": ["cpf"],  "fk": {}, "columns": COLS_PESSOAS},
    "empresas": {"pk": ["cnpj"], "fk": {"socio_cpf": "pessoas.cpf"}, "columns": COLS_EMPRESAS},
}
TABLE_ORDER = ["pessoas", "empresas"]

# ---------------------------------------------------------------------------
# Seeded value pools (kept small on purpose -> realistic repetition that
# exercises HCC dedup + OBAT affix sharing; declared simplification)
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Maria", "José", "Ana", "João", "Antônio", "Francisco", "Carlos", "Paulo",
    "Pedro", "Lucas", "Luiz", "Marcos", "Gabriel", "Rafael", "Daniel", "Marcelo",
    "Bruno", "Eduardo", "Felipe", "Rodrigo", "Juliana", "Fernanda", "Patrícia",
    "Aline", "Camila", "Amanda", "Bruna", "Jéssica", "Letícia", "Conceição",
]
SURNAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa", "Rocha",
    "Dias", "Nunes", "Mendes", "Araújo", "Cardoso", "Teixeira", "Moraes",
]
EMAIL_DOMAINS = ["gmail.com", "gmail.com", "hotmail.com", "outlook.com",
                 "yahoo.com.br", "uol.com.br", "bol.com.br"]
COMPANY_HEADS = [
    "Comércio de Alimentos", "Indústria", "Transportes", "Serviços", "Construções",
    "Tecnologia", "Distribuidora", "Consultoria", "Materiais", "Logística",
]
COMPANY_SUFFIXES = ["Ltda", "ME", "EIRELI", "S.A.", "EPP"]


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _gen_date(rng, y0: int, y1: int) -> str:
    years = list(range(y0, y1 + 1))
    weights = [(y - y0 + 1) for y in years]  # recency-weighted
    y = rng.choices(years, weights=weights, k=1)[0]
    m = rng.randint(1, 12)
    dmax = _DAYS[m - 1] + (1 if (m == 2 and _is_leap(y)) else 0)
    d = rng.randint(1, dmax)
    return f"{y:04d}-{m:02d}-{d:02d}"


def _gen_cpf(rng, seen: set) -> str:
    while True:
        body = [rng.randint(0, 9) for _ in range(9)]
        if len(set(body)) == 1:        # all-same digit: mod-11 passes but invalid
            continue
        digits = body + SPEC_CPF.check_fn(body)
        cpf = SPEC_CPF.formatter(digits)
        if cpf in seen:
            continue
        seen.add(cpf)
        return cpf


def _gen_cnpj(rng, seen: set) -> str:
    while True:
        base = [rng.randint(0, 9) for _ in range(8)]
        if len(set(base)) == 1:
            continue
        # branch slot: ~90% matriz /0001, else /0002../000N (low-cardinality)
        branch_n = 1 if rng.random() < 0.90 else rng.randint(2, 9)
        branch = [int(c) for c in f"{branch_n:04d}"]
        body = base + branch
        digits = body + SPEC_CNPJ.check_fn(body)
        cnpj = SPEC_CNPJ.formatter(digits)
        if cnpj in seen:
            continue
        seen.add(cnpj)
        return cnpj


def _gen_nome(rng) -> str:
    first = rng.choice(FIRST_NAMES)
    n_sur = rng.choices([1, 2], weights=[3, 2], k=1)[0]
    sur = " ".join(rng.choice(SURNAMES) for _ in range(n_sur))
    return f"{first} {sur}"


def _gen_email(rng, nome: str, idx: int) -> str:
    if (idx * 2654435761) % 100 < int(EMAIL_EMPTY_FRACTION * 100):
        return ""  # healthy missing value (sentinel empty -> NULL in SQLite)
    local = _strip_accents(nome).lower().replace(" ", ".")
    return f"{local}@{rng.choice(EMAIL_DOMAINS)}"


def _gen_razao(rng) -> str:
    head = rng.choice(COMPANY_HEADS)
    sur = rng.choice(SURNAMES)
    suffix = rng.choice(COMPANY_SUFFIXES)
    return f"{head} {sur} {suffix}"


def _load_geography() -> list[tuple[int, str]]:
    """Load (id, uf_sigla) from the ibge-municipios external CSV (full 5571)."""
    ibge_csv = external_dir("ibge-municipios") / "municipios.csv"
    if not ibge_csv.exists():
        sys.exit(
            f"ibge-municipios data not found at {ibge_csv}\n"
            "Run first:  python scripts/setup_ibge_municipios.py"
        )
    geo: list[tuple[int, str]] = []
    with ibge_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            geo.append((int(row["id"]), row["uf_sigla"]))
    return geo


def generate(verbose: bool = True):
    import random
    rng = random.Random(SEED)

    ensure_dirs()
    out = external_dir("br-identidades")
    out.mkdir(parents=True, exist_ok=True)
    geo = _load_geography()
    if verbose:
        print(f"[br-id] geography: {len(geo)} municipios loaded from ibge-municipios")

    # --- pessoas (streamed; keep only cpf list for FK referencing) ---
    cpf_seen: set = set()
    cpfs: list[str] = []
    pessoas_csv = out / "pessoas.csv"
    with pessoas_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(COLS_PESSOAS.keys()))
        for i in range(N_PESSOAS):
            cpf = _gen_cpf(rng, cpf_seen)
            mid, uf = rng.choice(geo)
            nome = _gen_nome(rng)
            email = _gen_email(rng, nome, i)
            data = _gen_date(rng, 2010, 2025)
            w.writerow([cpf, nome, mid, uf, data, email])
            cpfs.append(cpf)
            if verbose and (i + 1) % 100_000 == 0:
                print(f"[br-id]   pessoas {i + 1:,}/{N_PESSOAS:,}")
    if verbose:
        print(f"[br-id] pessoas: {pessoas_csv} ({pessoas_csv.stat().st_size/1024/1024:.1f} MB)")

    # --- empresas (streamed; socio_cpf references real pessoas.cpf) ---
    cnpj_seen: set = set()
    empresas_csv = out / "empresas.csv"
    n_socio = 0
    with empresas_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(COLS_EMPRESAS.keys()))
        for i in range(N_EMPRESAS):
            cnpj = _gen_cnpj(rng, cnpj_seen)
            mid, uf = rng.choice(geo)
            razao = _gen_razao(rng)
            data = _gen_date(rng, 2005, 2025)
            if rng.random() < SOCIO_FRACTION:
                socio = cpfs[rng.randrange(len(cpfs))]
                n_socio += 1
            else:
                socio = ""
            w.writerow([cnpj, razao, mid, uf, data, socio])
            if verbose and (i + 1) % 50_000 == 0:
                print(f"[br-id]   empresas {i + 1:,}/{N_EMPRESAS:,}")
    if verbose:
        print(f"[br-id] empresas: {empresas_csv} ({empresas_csv.stat().st_size/1024/1024:.1f} MB)")
        print(f"[br-id] socio_cpf populated: {n_socio:,}/{N_EMPRESAS:,} (~{100*n_socio/N_EMPRESAS:.0f}%)")

    # --- self-check: every id must be 'compressible' under the welded spec ---
    bad_cpf = sum(1 for c in cpfs[:5000] if SPEC_CPF.classify_value(c) != "compressible")
    assert bad_cpf == 0, f"{bad_cpf} generated CPFs not compressible — generator/spec mismatch"
    if verbose:
        print("[br-id] self-check: first 5000 CPFs all classify as 'compressible' OK")

    return out, n_socio


def write_metadata(n_socio: int) -> None:
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / "br-identidades"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": "br-identidades",
        "synthetic": True,
        "declared_bias": (
            "SYNTHETIC / built-to-test dataset (Brunswik 1956). Generated to "
            "exercise ADR-0015 CPF/CNPJ natures + activation gate. Identifiers "
            "are random mod-11-valid bodies (no regional encoding, not issued "
            "documents). Cannot alone justify 'confirmada-empirica' — see "
            "ticket T-DATA-2-RECEITA-CNPJ for the real-data path."
        ),
        "source": "Synthetic generator (scripts/setup_br_identidades.py), seed=%d" % SEED,
        "geography_source": "Real IBGE codes reused from canonical ibge-municipios",
        "license": "Synthetic — no license restriction; contains no PII",
        "citation": "Synthetic, generated for TCF nature testing (ADR-0015).",
        "downloaded_via": "deterministic generation (Python stdlib random)",
        "shaper_note": (
            "pessoas (500k) exceeds the shaper's validated <=100k regime "
            "(T-SHAPER-CODE-HARDENING). Use direct encode() on columns, not "
            "shaper sampling."
        ),
        "row_counts": {"pessoas": N_PESSOAS, "empresas": N_EMPRESAS},
        "socio_cpf_fk_rows": n_socio,
        "table_order": TABLE_ORDER,
        "tables": SCHEMA,
    }
    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(f"[br-id] metadata: {meta_path}")


def generate_samples(out: Path, n_rows: int = 100) -> None:
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / "br-identidades"
    samples_dir.mkdir(parents=True, exist_ok=True)
    for table in TABLE_ORDER:
        src = out / f"{table}.csv"
        dst = samples_dir / f"{table}-sample.csv"
        with src.open("r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i > n_rows:
                    break
                lines.append(line)
        dst.write_text("".join(lines), encoding="utf-8")
        print(f"[br-id]   sample: {table}-sample.csv ({dst.stat().st_size/1024:.1f} KB, {n_rows} rows)")


def main():
    out, n_socio = generate()
    write_metadata(n_socio)
    generate_samples(out, n_rows=100)
    print(f"\n[br-id] Done. pessoas={N_PESSOAS:,} + empresas={N_EMPRESAS:,}.")
    print(f"[br-id] Raw data: {out}")
    print("[br-id] Metadata + samples: in git under datasets/canonical/br-identidades/")
    print("[br-id] Next: python scripts/csv_to_sqlite.py br-identidades")


if __name__ == "__main__":
    main()
