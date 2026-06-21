"""Minimiza o bug de RT do core M10 em nome_fantasia (receita-estab).

1. Confirma que o fallback (raw) RT-passa (V2-A contorna o bug).
2. Localiza valores envolvidos (corrompido + spliced + metacaractere).
3. Delta-debug (ddmin) ate' um reproducer minimo de _encode/_decode_column.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.encoder import _encode_column  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

PATH = Path("Z:/tcf-data/external/receita-cnpj/estabelecimentos.csv")
LIMIT = 20000


def load_col(name):
    for enc in ("utf-8", "latin-1"):
        try:
            with PATH.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                idx = header.index(name)
                vals = []
                for i, row in enumerate(r):
                    if i >= LIMIT:
                        break
                    if len(row) != len(header):
                        continue
                    vals.append(row[idx])
            return vals
        except UnicodeDecodeError:
            continue
    raise RuntimeError("decode fail")


def rt_fails(vals):
    """True se _decode_column(_encode_column(vals)) != vals."""
    try:
        body = _encode_column(vals, header="c")
        back = _decode_column(body)
        return back != vals
    except Exception:
        return True


def raw_rt_ok(vals):
    """V2-A raw path: join/split por \\n (sem valores com \\n)."""
    if any("\n" in v for v in vals):
        return None  # nao aplicavel
    body = "\n".join(vals)
    return body.split("\n") == vals


def ddmin(vals):
    """Delta-debug: menor sublista contigua-ish que ainda falha."""
    # Fase 1: shrink por janela contigua (rapido, preserva contexto HCC)
    lo, hi = 0, len(vals)
    # encolhe a direita
    step = hi // 2
    while step >= 1:
        while hi - step > lo and rt_fails(vals[lo:hi - step]):
            hi -= step
        step //= 2
    # encolhe a esquerda
    step = (hi - lo) // 2
    while step >= 1:
        while lo + step < hi and rt_fails(vals[lo + step:hi]):
            lo += step
        step //= 2
    sub = vals[lo:hi]
    # Fase 2: remocao individual gulosa
    changed = True
    while changed and len(sub) > 1:
        changed = False
        for i in range(len(sub)):
            cand = sub[:i] + sub[i + 1:]
            if cand and rt_fails(cand):
                sub = cand
                changed = True
                break
    return sub


def main():
    vals = load_col("nome_fantasia")
    print(f"nome_fantasia: {len(vals)} valores")
    print(f"m10 col RT falha?  {rt_fails(vals)}")
    print(f"raw (V2-A) RT ok?  {raw_rt_ok(vals)}")

    # valores com metacaractere
    print("\nvalores com '*':")
    for i, v in enumerate(vals):
        if "*" in v:
            print(f"  [{i}] {v!r}")
    print("valores com ',' (primeiros 5):")
    shown = 0
    for i, v in enumerate(vals):
        if "," in v:
            print(f"  [{i}] {v!r}")
            shown += 1
            if shown >= 5:
                break

    print("\n=== minimizando ===")
    sub = ddmin(vals)
    print(f"reproducer minimo: {len(sub)} valores")
    for v in sub:
        print(f"  {v!r}")
    body = _encode_column(sub, header="c")
    back = _decode_column(body)
    print(f"\nbody TCF:\n{body!r}")
    print(f"\nin : {sub}")
    print(f"out: {back}")
    print(f"raw V2-A RT ok neste sub? {raw_rt_ok(sub)}")


if __name__ == "__main__":
    main()
