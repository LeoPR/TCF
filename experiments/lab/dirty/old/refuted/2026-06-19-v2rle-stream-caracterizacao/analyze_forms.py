"""V2-RLE-STREAM — follow-up do nicho "texto curto repetitivo / formulário"
(refinamento do owner 2026-06-19). Lab dirty, read-only, NAO toca src/tcf.

Pergunta refinada: o stream-RLE faz sentido em PAYLOAD MINUSCULO predominado por
uma coluna LOW-CARD de TEXTO CURTO (campo de formulario: estado civil, tipo,
resposta, status), onde a repeticao acontece mesmo em frases curtas — e mais
ainda se CLUSTERIZADO. Mede o nicho NARROW (a coluna domina o blob), natural vs
clusterizado (sort_by), textual vs brotli. Reusa o modelo RLE de analyze.py.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode                       # noqa: E402
from tcf_lazy.lazy import LazyTCF            # noqa: E402
from analyze import rle_len, DOWN, _down     # noqa: E402


def measure(label: str, col: list[str], *, clustered: bool) -> None:
    data = {"v": sorted(col)} if clustered else {"v": col}
    blob = encode(data)
    bb = blob.encode("utf-8")
    lz = LazyTCF(blob)
    mode = lz._mode.get("v")
    if mode != "dict":
        print(f"   {label:<34} N={len(col):<6} modo={mode} (nao-dict; stream-RLE NAO se aplica)")
        return
    unicas, w, stream = lz._dict_parts("v")
    cur = len(stream)
    rle, n_runs, n_rle = rle_len(stream, w)
    sav = cur - rle
    pct_blob = 100 * sav / len(bb) if bb else 0
    # downstream no BLOB inteiro (nicho real: paga-se o blob todo na transmissao)
    blob_rle_proxy = len(bb) - sav            # tamanho textual com stream-RLE
    d_cur = _down(bb)
    # aproxima o blob-rle: substitui o stream cru pelo rle no fim do corpo
    rle_bytes = _rle_stream(stream, w)
    bb_rle = bb[: len(bb) - cur] + rle_bytes
    d_rle = _down(bb_rle)
    print(f"   {label:<34} N={len(col):<6} K={len(unicas):<4} w={w} "
          f"blob {len(bb)}B  stream {cur}->{rle}B  saving {sav}B = {pct_blob:+.1f}% do blob"
          f"   brotli {d_cur}->{d_rle}B ({100*(d_cur-d_rle)/d_cur:+.1f}%)")


def _rle_stream(stream: bytes, w: int) -> bytes:
    from analyze import rle_stream_bytes
    return rle_stream_bytes(stream, w)


def real_text_cols():
    """Colunas LOW-CARD de TEXTO de datasets reais, isoladas (nicho narrow)."""
    try:
        from dataset_reader import DatasetReader
    except Exception as e:
        print(f"(dataset_reader indisponivel: {e})"); return
    picks = [
        ("adult-census", "adult", "workclass", 20000),
        ("adult-census", "adult", "education", 20000),
        ("adult-census", "adult", "marital-status", 20000),
        ("receita-cnpj", None, "situacao", 15000),
        ("tpch-sf001", "orders", "o_orderpriority", 15000),
        ("ibge-municipios", None, "mesorregiao", 6000),
    ]
    for ds, tab, colname, lim in picks:
        try:
            r = DatasetReader(ds)
            t = tab or (r.tables[0] if r.tables else None)
            cols = r.columns(t, limit=lim)
            if colname not in cols:
                continue
            col = [("" if v is None else str(v)) for v in cols[colname]]
        except Exception as e:
            print(f"   skip {ds}/{colname}: {e}"); continue
        measure(f"{ds}/{colname} [natural]", col, clustered=False)
        measure(f"{ds}/{colname} [clusterizado]", col, clustered=True)


def synthetic_forms():
    """[SINTETICO, vies declarado] formulario: ~8 respostas curtas, blocos
    clusterizados (submissoes agrupadas por lote/periodo)."""
    respostas = ["Sim", "Nao", "Talvez", "Nao se aplica", "Prefiro nao responder",
                 "Concordo", "Discordo", "Neutro"]
    # blocos: cada lote tem uma resposta dominante (forms agrupados)
    col = []
    import itertools
    cyc = itertools.cycle(respostas)
    for _ in range(2000):
        dom = next(cyc)
        col += [dom] * 9 + [respostas[(respostas.index(dom) + 3) % 8]]  # 90% dominante
    measure("SINTETICO forms [natural-clusterizado]", col, clustered=False)
    measure("SINTETICO forms [sort_by]", col, clustered=True)


def main():
    print(f"# V2-RLE-STREAM — nicho texto-curto/formulario (downstream={DOWN})")
    print("# (coluna low-card de TEXTO isolada = payload narrow; a coluna domina o blob)\n")
    print("## Colunas de texto reais (isoladas):")
    real_text_cols()
    print("\n## Sintetico forms (vies de design declarado):")
    synthetic_forms()
    print("\nNOTA: clusterizado/sort_by e' ORDER-FREE (perde a ordem original).")


if __name__ == "__main__":
    main()
