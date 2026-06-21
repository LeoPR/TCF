"""V2-A fallback identity — caracterizacao EXPANDIDA (Stage 1 da v2.0).

Contexto: ADR-0018 registra V2-A (fallback identity por coluna) como
prioridade #1 do roadmap v2.0. Proto original (2026-05-27-naturezas-reais-uci/
proto_fallback.py) mediu so' 3 datasets (wine/beijing/retail). O checklist
"antes de declarar confirmada-empirica" (CLAUDE.md) exige N>=5 fontes reais.

Este script estende a MESMA ideia (min(tcf, raw) por coluna, marcador !name)
a 9 tabelas reais de 6+ fontes distintas, pra responder:
  1. V2-A generaliza? (ganho consistente, nao so' beijing)
  2. Ganho weighted real-world >= 5%? (criterio de bytes absolutos)
  3. RT OK em todas? (single path + fallback path)
  4. Quantas/quais colunas caem pra raw? (onde o fallback morde)

FORK exploratorio — NAO toca src/tcf. Pure characterization.

Marcador de modo: meta line `<size>=<name>` (TCF) vs `<size>=!<name>` (raw).
Body raw = '\\n'.join(values) (assume sem newline embutido — caveat: impl
real precisa escape; aqui detectamos e pulamos colunas com '\\n' interno).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

EXT = Path("Z:/tcf-data/external")

# (label, path, row_limit) — fontes distintas, big files amostrados.
DATASETS = [
    ("adult-census",   EXT / "adult-census" / "adult.csv",              20000),
    ("beijing-pm25",   EXT / "beijing-pm25" / "beijing_pm25.csv",       20000),
    ("wine-quality",   EXT / "wine-quality" / "wine.csv",                None),
    ("ibge-municipios", EXT / "ibge-municipios" / "municipios.csv",      None),
    ("online-retail",  EXT / "online-retail" / "online_retail.csv",     20000),
    ("tpch-lineitem",  EXT / "tpch-sf001" / "lineitem.csv",             20000),
    ("tpch-orders",    EXT / "tpch-sf001" / "orders.csv",               20000),
    ("br-empresas",    EXT / "br-identidades" / "empresas.csv",         20000),
    ("receita-estab",  EXT / "receita-cnpj" / "estabelecimentos.csv",   20000),
]


def load_cols(path: Path, limit=None) -> dict[str, list[str]]:
    """Le CSV -> dict coluna->valores. utf-8 com fallback latin-1."""
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                cols = {h: [] for h in header}
                for i, row in enumerate(r):
                    if limit and i >= limit:
                        break
                    if len(row) != len(header):
                        continue  # linha malformada: pula (dado "feliz")
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"nao decodificou {path}")


def encode_with_fallback(table: dict[str, list[str]]):
    """min(tcf, raw) por coluna. Retorna (full_bytes, modes, per_col)."""
    col_bodies = []
    modes = {}
    per_col = []
    for name, values in table.items():
        # Caveat de escape: se algum valor tem '\n', raw body quebraria.
        has_nl = any("\n" in v for v in values)
        tcf_body = _encode_column(values, header=name).encode("utf-8")
        if has_nl:
            # forca TCF (raw nao e' seguro sem escape neste proto)
            col_bodies.append((name, tcf_body, "tcf"))
            modes[name] = "tcf"
            per_col.append((name, len(tcf_body), len(tcf_body), "tcf-forced-nl"))
            continue
        raw_body = "\n".join(values).encode("utf-8")
        if len(raw_body) < len(tcf_body):
            col_bodies.append((name, raw_body, "raw"))
            modes[name] = "raw"
            per_col.append((name, len(tcf_body), len(raw_body), "raw"))
        else:
            col_bodies.append((name, tcf_body, "tcf"))
            modes[name] = "tcf"
            per_col.append((name, len(tcf_body), len(raw_body), "tcf"))
    meta_parts = []
    for name, body, mode in col_bodies:
        tag = "!" + name if mode == "raw" else name
        meta_parts.append(f"{len(body)}={tag}")
    header = ("#TCF.6 M\n# " + ",".join(meta_parts) + "\n").encode("utf-8")
    full = header + b"".join(b for _, b, _ in col_bodies)
    return full, modes, per_col


def decode_with_fallback(raw: bytes) -> dict[str, list[str]]:
    nl1 = raw.find(b"\n")
    nl2 = raw.find(b"\n", nl1 + 1)
    meta = raw[nl1 + 1:nl2].decode("utf-8")[2:]
    pairs = []
    for p in meta.split(","):
        size_str, tag = p.split("=", 1)
        if tag.startswith("!"):
            pairs.append((int(size_str), tag[1:], "raw"))
        else:
            pairs.append((int(size_str), tag, "tcf"))
    cursor = nl2 + 1
    out = {}
    for size, name, mode in pairs:
        body = raw[cursor:cursor + size]
        cursor += size
        if mode == "raw":
            out[name] = body.decode("utf-8").split("\n")
        else:
            out[name] = _decode_column(body.decode("utf-8"))
    return out


def main():
    rows = []
    tot_m10 = 0
    tot_fb = 0
    print(f"{'dataset':16s} {'rows':>7s} {'cols':>5s} {'M10 B':>11s} "
          f"{'fallback':>11s} {'ganho':>7s} {'->raw':>7s} {'RT':>5s}")
    print("-" * 78)
    for label, path, lim in DATASETS:
        if not path.exists():
            print(f"{label:16s}  SKIP (nao existe: {path})")
            continue
        cols = load_cols(path, lim)
        n_rows = len(next(iter(cols.values()))) if cols else 0

        m10_text = encode(cols)
        m10_bytes = len(m10_text.encode("utf-8"))
        m10_rt = decode(m10_text) == cols

        fb_full, modes, per_col = encode_with_fallback(cols)
        fb_bytes = len(fb_full)
        fb_rt = decode_with_fallback(fb_full) == cols

        n_raw = sum(1 for m in modes.values() if m == "raw")
        ganho = (1 - fb_bytes / m10_bytes) * 100 if m10_bytes else 0.0
        rt_ok = "OK" if (m10_rt and fb_rt) else "FAIL"
        tot_m10 += m10_bytes
        tot_fb += fb_bytes
        print(f"{label:16s} {n_rows:7d} {len(cols):5d} {m10_bytes:11d} "
              f"{fb_bytes:11d} {ganho:6.2f}% {n_raw:3d}/{len(cols):<3d} {rt_ok:>5s}")
        raw_cols = [f"{n}({t}B<{c}B)" for n, c, t, m in per_col if m == "raw"]
        if raw_cols:
            print(f"   raw: {', '.join(raw_cols)}")
        rows.append((label, n_rows, len(cols), m10_bytes, fb_bytes, ganho,
                     n_raw, rt_ok))

    print("-" * 78)
    w = (1 - tot_fb / tot_m10) * 100 if tot_m10 else 0.0
    print(f"{'WEIGHTED':16s} {'':7s} {'':5s} {tot_m10:11d} {tot_fb:11d} "
          f"{w:6.2f}%")
    print(f"\nN datasets medidos: {len(rows)} (fontes distintas)")
    print(f"Ganho weighted real-world: {w:.2f}%")


if __name__ == "__main__":
    main()
