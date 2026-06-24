"""B1 Etapa 3 — o NICHO flag/survey: cross-dict ganha onde muitas colunas
compartilham um vocabulario pequeno?

READ-ONLY, src/tcf intocado. Sintetico DECLARADO, mas modela uma forma de tabela
REAL (questionario/survey/voting-records/feature-flags) — ecologicamente valida
(dataset de design, nao stress artificial).

Hipotese a testar: mesmo no nicho, a economia do cross-dict e' so' a TABELA
deduplicada (poucos bytes/coluna); o STREAM de indices (o grosso) e' identico em
V0 e V1 -> sob brotli (que ja' deduplica tabelas identicas) o ganho some em escala.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import brotli

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.encoder import _encode_column          # noqa: E402
from tcf.multi import _v2b_encode               # noqa: E402
from tcf.pipeline import PipelineConfig          # noqa: E402

CFG = PipelineConfig()
ALPHA = "".join(chr(c) for c in range(0x21, 0x7F))


def w94(k):
    w, c = 1, 94
    while k > c:
        w += 1; c *= 94
    return w


def idx(i, width):
    if width == 1:
        return ALPHA[i]
    o = []
    for _ in range(width):
        o.append(ALPHA[i % 94]); i //= 94
    return "".join(reversed(o))


def br(b):
    return len(brotli.compress(b, quality=11))


def measure(cols: dict[str, list[str]]):
    # V0 per-col @dict
    pc, pcc, dictcols = 0, b"", {}
    for n, vals in cols.items():
        b = _v2b_encode(vals, cfg=CFG, min_len=None)
        if b is None:
            continue
        pc += len(b); pcc += b; dictcols[n] = vals
    if not dictcols:
        return None
    # V1 global flat
    gseen, guni = {}, []
    for vals in dictcols.values():
        for v in vals:
            if v not in gseen:
                gseen[v] = len(guni); guni.append(v)
    K = len(guni); wg = w94(K)
    gt = _encode_column(guni, header="val", cfg=CFG, min_len=None).encode()
    streams = b"".join(
        "".join(idx(gseen[v], wg) for v in vals).encode() for vals in dictcols.values()
    )
    g = len(f"{len(gt)}\n".encode()) + len(gt) + len(streams)
    gc = f"{len(gt)}\n".encode() + gt + streams
    return {
        "ncols_dict": len(dictcols), "K": K, "w": wg,
        "v0_txt": pc, "v0_br": br(pcc),
        "v1_txt": g, "v1_br": br(gc),
    }


def survey(N, C, vocab, rng):
    """C colunas, cada uma sorteia de `vocab` com skew per-coluna aleatorio."""
    cols = {}
    for c in range(C):
        # skew: cada coluna com um valor dominante diferente
        weights = [rng.random() + 0.1 for _ in vocab]
        cols[f"q{c:02d}"] = rng.choices(vocab, weights=weights, k=N)
    return cols


def run(label, vocab):
    print(f"\n{'='*72}\n{label}  vocab={vocab}\n{'='*72}")
    print(f"{'C×N':>10} {'V0 txt':>8} {'V1 txt':>8} {'net%txt':>8} "
          f"{'V0 br':>8} {'V1 br':>8} {'net%br':>8}  veredito")
    rng = random.Random(1234)
    for C in (8, 16, 32):
        for N in (200, 2000):
            m = measure(survey(N, C, vocab, rng))
            if m is None:
                print(f"{C}x{N:>6}  (sem col dict)"); continue
            nt = 100 * (m["v1_txt"] - m["v0_txt"]) / m["v0_txt"]
            nb = 100 * (m["v1_br"] - m["v0_br"]) / m["v0_br"]
            verd = "cross-dict GANHA" if nb < -0.5 else ("~empate" if abs(nb) <= 0.5 else "cross-dict PERDE")
            print(f"{C}x{N:>6} {m['v0_txt']:>8} {m['v1_txt']:>8} {nt:>+7.1f}% "
                  f"{m['v0_br']:>8} {m['v1_br']:>8} {nb:>+7.1f}%  {verd} (K={m['K']},w={m['w']})")


if __name__ == "__main__":
    run("SIM/NAO (2 valores, estilo feature-flags)", ["SIM", "NAO"])
    run("y/n/? (3 valores, estilo UCI voting-records)", ["y", "n", "?"])
