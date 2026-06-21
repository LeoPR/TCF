"""V2-RLE-STREAM — caracterizacao (lab dirty, read-only, NAO toca src/tcf).

Hipotese: aplicar RLE no STREAM de indices do V2-B (modo @dict) reduz bytes
quando ha' runs adjacentes do mesmo indice (coluna naturalmente clusterizada ou
ordenada). Mede o ganho TEXTUAL (nicho explicavel do TCF) e se sobrevive ao brotli.

Modelo de tamanho RLE (upper-bound otimo, esquema textual com marcador reservado):
  stream atual = N * width bytes (token base-94 por linha, sem delimitador).
  RLE: por run maximal de m tokens identicos (token = width bytes):
    literal = m * width        (sem overhead; decoder le width bytes ate' o marcador)
    rle     = 1 + cnt + width  (marcador 0x01 reservado + count base-94 + 1 token)
    contribui min(literal, rle)  -> escolha otima por run.
  (marcador 0x01 nunca colide: tokens usam 0x21-0x7E.)

Gate (anti-incidente 2026-05-21): >=15% weighted em 2+ datasets REAIS, e checar
se some sob brotli. Sinteticos contam separado (vies de design declarado).
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode                       # noqa: E402
from tcf.multi import _v2b_width             # noqa: E402
from tcf_lazy.lazy import LazyTCF            # noqa: E402

try:
    import brotli
    def _down(b: bytes) -> int:
        return len(brotli.compress(b, quality=11))
    DOWN = "brotli-q11"
except ImportError:                          # pragma: no cover
    def _down(b: bytes) -> int:
        return len(gzip.compress(b, 9))
    DOWN = "gzip-9"


def rle_len(stream: bytes, w: int) -> tuple[int, int, int]:
    """(rle_bytes, n_runs, n_rle_runs) para o stream sob o modelo otimo."""
    n = len(stream) // w
    total = n_runs = n_rle = 0
    i = 0
    while i < n:
        tok = stream[i * w:(i + 1) * w]
        j = i + 1
        while j < n and stream[j * w:(j + 1) * w] == tok:
            j += 1
        m = j - i
        literal = m * w
        rle = 1 + _v2b_width(m) + w
        if rle < literal:
            total += rle; n_rle += 1
        else:
            total += literal
        n_runs += 1
        i = j
    return total, n_runs, n_rle


def rle_stream_bytes(stream: bytes, w: int) -> bytes:
    """Materializa o stream RLE (pro teste downstream)."""
    n = len(stream) // w
    out = bytearray()
    i = 0
    while i < n:
        tok = stream[i * w:(i + 1) * w]
        j = i + 1
        while j < n and stream[j * w:(j + 1) * w] == tok:
            j += 1
        m = j - i
        rle = 1 + _v2b_width(m) + w
        if rle < m * w:
            cnt = m
            digs = bytearray()
            for _ in range(_v2b_width(m)):
                digs.append(0x21 + cnt % 94); cnt //= 94
            out.append(0x01); out += bytes(reversed(digs)); out += tok
        else:
            out += tok * m
        i = j
    return bytes(out)


def analyze_table(name: str, cols: dict[str, list[str]], *, sortable=True) -> dict:
    blob = encode(cols)
    blob_b = blob.encode("utf-8")
    lz = LazyTCF(blob)
    dict_cols = [c for c in lz.columns if lz._mode[c] == "dict"]

    rows = []
    tot_cur = tot_rle = 0
    streams_cur = bytearray()
    streams_rle = bytearray()
    for c in dict_cols:
        unicas, w, stream = lz._dict_parts(c)
        cur = len(stream)
        rle, n_runs, n_rle = rle_len(stream, w)
        tot_cur += cur; tot_rle += rle
        streams_cur += stream
        streams_rle += rle_stream_bytes(stream, w)
        rows.append((c, len(unicas), w, cur, rle, cur - rle,
                     round(100 * (cur - rle) / cur, 1) if cur else 0.0, n_runs))

    saving = tot_cur - tot_rle
    pct_blob = round(100 * saving / len(blob_b), 2) if blob_b else 0.0

    # downstream: a economia textual sobrevive ao compressor a jusante?
    d_cur = _down(bytes(streams_cur)) if streams_cur else 0
    d_rle = _down(bytes(streams_rle)) if streams_rle else 0

    # upper bound sort_by: melhor chave (order-free; so' ilustrativo)
    best_sort = None
    if sortable and dict_cols:
        best = (-1, None)
        for key in dict_cols:
            try:
                bs = encode(cols, sort_by=key)
            except Exception:
                continue
            lzs = LazyTCF(bs); bs_b = bs.encode("utf-8")
            s = 0
            for c in [x for x in lzs.columns if lzs._mode[x] == "dict"]:
                _, w, st = lzs._dict_parts(c)
                s += len(st) - rle_len(st, w)[0]
            pct = 100 * s / len(bs_b) if bs_b else 0
            if pct > best[0]:
                best = (pct, key)
        best_sort = (best[1], round(best[0], 2))

    return {
        "name": name, "blob_bytes": len(blob_b), "n_cols": len(lz.columns),
        "n_dict": len(dict_cols), "stream_cur": tot_cur, "stream_rle": tot_rle,
        "saving": saving, "pct_blob": pct_blob, "rows": rows,
        "down": DOWN, "down_cur": d_cur, "down_rle": d_rle,
        "down_saving_pct": round(100 * (d_cur - d_rle) / d_cur, 2) if d_cur else 0.0,
        "best_sort": best_sort,
    }


def load_real(dataset: str, table: str, limit: int) -> dict[str, list[str]] | None:
    try:
        from dataset_reader import DatasetReader
        r = DatasetReader(dataset)
        if table not in r.tables:
            return None
        cols = r.columns(table, limit=limit)
        return {c: [("" if v is None else str(v)) for v in vals] for c, vals in cols.items()}
    except Exception as e:                    # pragma: no cover
        print(f"  ! skip {dataset}/{table}: {e}")
        return None


def main():
    print(f"# V2-RLE-STREAM — caracterizacao (downstream={DOWN})\n")
    REAL = [
        ("adult-census", "adult", 20000),
        ("tpch-sf001", "lineitem", 15000),
        ("tpch-sf001", "orders", 15000),
        ("tpch-sf001", "customer", 15000),
        ("br-identidades", None, 15000),
        ("receita-cnpj", None, 15000),
        ("ibge-municipios", None, 15000),
    ]
    results = []
    for dataset, table, lim in REAL:
        # descobrir tabela default se None
        tabs = []
        try:
            from dataset_reader import DatasetReader
            tabs = DatasetReader(dataset).tables
        except Exception as e:
            print(f"## {dataset}: indisponivel ({e})\n"); continue
        tgt = table or (tabs[0] if tabs else None)
        if not tgt:
            continue
        cols = load_real(dataset, tgt, lim)
        if not cols:
            print(f"## {dataset}/{tgt}: skip\n"); continue
        r = analyze_table(f"{dataset}/{tgt}", cols)
        results.append(r)
        print(f"## {r['name']}  ({r['n_dict']}/{r['n_cols']} cols @dict, blob {r['blob_bytes']}B)")
        for c, k, w, cur, rle, sav, pct, runs in sorted(r["rows"], key=lambda x: -x[5])[:8]:
            print(f"   @{c:<20} K={k:<5} w={w} stream {cur}B -> {rle}B  ({pct:+.1f}%, {runs} runs)")
        print(f"   STREAM total {r['stream_cur']}B -> {r['stream_rle']}B  "
              f"saving {r['saving']}B = {r['pct_blob']:+.2f}% do blob")
        print(f"   downstream({DOWN}) streams: {r['down_cur']}B -> {r['down_rle']}B "
              f"({r['down_saving_pct']:+.2f}%)   sort_by upper: {r['best_sort']}\n")

    reals = [r for r in results]
    if reals:
        tot_sav = sum(r["saving"] for r in reals)
        tot_blob = sum(r["blob_bytes"] for r in reals)
        n_ge15 = sum(1 for r in reals if r["pct_blob"] >= 15)
        print("=" * 60)
        print(f"WEIGHTED (textual, {len(reals)} reais): "
              f"{round(100*tot_sav/tot_blob,2)}%  (saving {tot_sav}B / {tot_blob}B)")
        print(f"datasets com >=15% do blob: {n_ge15}/{len(reals)}  -> "
              f"{'PASSA' if n_ge15>=2 else 'NAO passa'} o gate textual")
        dc = sum(r["down_cur"] for r in reals); dr = sum(r["down_rle"] for r in reals)
        print(f"downstream({DOWN}) agregado: {round(100*(dc-dr)/dc,2) if dc else 0}% "
              f"(a economia {'SOBREVIVE' if dc and (dc-dr)/dc>=0.05 else 'SOME'} sob compressor)")


if __name__ == "__main__":
    main()
