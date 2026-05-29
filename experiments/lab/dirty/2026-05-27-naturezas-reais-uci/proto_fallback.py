"""Prototipo: fallback identity por coluna (Passo 4.2).

FORK exploratorio (NAO toca src/tcf). Mede o ganho de:
  "se o TCF de uma coluna fica MAIOR que o raw, guarda raw".

Caracterizacao 4.1 mostrou 8+ colunas numericas com M10 > 100% (TCF
infla). Fallback identity capa cada coluna em 100% (nunca pior que raw).

Design do prototipo (multi-col):
- Header: #TCF.6 M + meta line com flag de modo por coluna
  `# <size>=<name>` (TCF) vs `# <size>=!<name>` (raw, '!' prefix)
- Body raw = '\\n'.join(values) (assume sem newline embutido — vale pros
  datasets numericos/curtos; impl real precisaria escape)
- Decode: se name comeca com '!', split por '\\n'; senao TCF decode

Mede: bytes totais com fallback vs M10 puro (all-TCF), por dataset.
Verifica round-trip em ambos.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402
from tcf.encoder import _encode_column  # interno: encoda 1 coluna  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

EXT = Path("Z:/tcf-data/external")
DATASETS = {
    "wine-quality": (EXT / "wine-quality" / "wine.csv", None),
    "beijing-pm25": (EXT / "beijing-pm25" / "beijing_pm25.csv", None),
    "online-retail": (EXT / "online-retail" / "online_retail.csv", 50000),
}


def load_cols(path: Path, limit=None) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for i, row in enumerate(r):
            if limit and i >= limit:
                break
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def encode_with_fallback(table: dict[str, list[str]]):
    """Retorna (full_bytes, per_col_modes). per_col_modes[name] = 'tcf'|'raw'."""
    col_bodies = []  # (name, body_bytes, mode)
    modes = {}
    for name, values in table.items():
        tcf_body = _encode_column(values, header=name).encode("utf-8")
        raw_body = "\n".join(values).encode("utf-8")
        if len(raw_body) < len(tcf_body):
            col_bodies.append((name, raw_body, "raw"))
            modes[name] = "raw"
        else:
            col_bodies.append((name, tcf_body, "tcf"))
            modes[name] = "tcf"
    # Header com flag
    meta_parts = []
    for name, body, mode in col_bodies:
        tag = "!" + name if mode == "raw" else name
        meta_parts.append(f"{len(body)}={tag}")
    header = ("#TCF.6 M\n# " + ",".join(meta_parts) + "\n").encode("utf-8")
    full = header + b"".join(b for _, b, _ in col_bodies)
    return full, modes


def decode_with_fallback(raw: bytes) -> dict[str, list[str]]:
    nl1 = raw.find(b"\n")
    nl2 = raw.find(b"\n", nl1 + 1)
    meta = raw[nl1 + 1:nl2].decode("utf-8")[2:]  # strip '# '
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
    print(f"{'dataset':16s} {'M10 bytes':>12s} {'fallback':>12s} {'ganho':>8s} "
          f"{'cols_raw':>9s} {'RT':>5s}")
    print("-" * 70)
    for ds, (path, lim) in DATASETS.items():
        if not path.exists():
            print(f"{ds}: skip (nao existe)")
            continue
        cols = load_cols(path, lim)

        # M10 puro (baseline atual)
        m10_text = encode(cols)
        m10_bytes = len(m10_text.encode("utf-8"))
        m10_rt = decode(m10_text) == cols

        # Fallback
        fb_full, modes = encode_with_fallback(cols)
        fb_bytes = len(fb_full)
        fb_rt = decode_with_fallback(fb_full) == cols

        n_raw = sum(1 for m in modes.values() if m == "raw")
        ganho = (1 - fb_bytes / m10_bytes) * 100
        rt_ok = "OK" if (m10_rt and fb_rt) else "FAIL"
        print(f"{ds:16s} {m10_bytes:12d} {fb_bytes:12d} {ganho:7.1f}% "
              f"{n_raw:3d}/{len(cols):<3d}  {rt_ok:>5s}")
        raw_cols = [n for n, m in modes.items() if m == "raw"]
        if raw_cols:
            print(f"                 cols que cairam pra raw: {raw_cols}")


if __name__ == "__main__":
    main()
