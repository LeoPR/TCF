"""Experimento: TCF vs compressores de HTTP e de Parquet (2026-07-13).

Pergunta (filosofia CLAUDE.md): TCF NAO compete com compressores binarios
(gzip/brotli/zstd/snappy/lz4) — ocupa area textual/inspecionavel. Este lab
MEDE tres coisas em datasets reais:

  1. TCF sozinho vs cada compressor sozinho (sobre o mesmo dado cru).
  2. COMPOSICAO: compressor(TCF) vs compressor(raw) — TCF ajuda a camada
     de transporte HTTP (Content-Encoding) ou de pagina Parquet?
  3. O trade-off de legibilidade: TCF continua texto ASCII; os demais nao.

Familias medidas:
  - HTTP Content-Encoding: gzip, br (brotli), zstd  (o que trafega online)
  - Parquet column chunks:  snappy, zstd, lz4, gzip  (o que existe em .parquet)
  (zstd/gzip aparecem nos dois mundos.)

Datasets: as 3 colunas free-text reais do gate byte-canonical
(datasets/samples/{online-retail,tpch-sf001}) + 1 tabela multi-col sintetica
realista pra exercitar #TCF.8M.

Artefatos: escreve amostras de input, output TCF, e a contra-prova de RT
em artifacts/. RESULTADO em result.md (gerado por gen_result.py a partir do
JSON aqui).
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import brotli
import lz4.frame
import snappy
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

SAMPLES = ROOT / "datasets" / "samples"
ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(exist_ok=True)

# ---- compressores (nivel = default "web-realistic", nao o maximo teorico) ----
_zc = zstd.ZstdCompressor(level=19)  # zstd HTTP/parquet costuma girar 3..19


def c_gzip(b):   return gzip.compress(b, 6)          # HTTP gzip default ~6
def c_brotli(b): return brotli.compress(b, quality=11)  # HTTP br default alto
def c_zstd(b):   return _zc.compress(b)
def c_snappy(b): return snappy.compress(b)           # parquet snappy (rapido)
def c_lz4(b):    return lz4.frame.compress(b)        # parquet lz4

HTTP = [("gzip", c_gzip), ("brotli", c_brotli), ("zstd", c_zstd)]
PARQUET = [("snappy", c_snappy), ("zstd", c_zstd), ("lz4", c_lz4), ("gzip", c_gzip)]
ALL = {name: fn for name, fn in HTTP + PARQUET}


def load_col(rel: str) -> list[str]:
    path = SAMPLES / rel
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def synth_multi() -> dict:
    """Tabela multi-col realista (cadastro) — exercita #TCF.8M."""
    import random
    rnd = random.Random(20260713)
    cidades = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Recife"]
    planos = ["Premium", "Basic", "Enterprise", "Free"]
    dominios = ["acme.com.br", "example.org", "mail.com"]
    n = 2000
    nomes = [f"Cliente {i:04d}" for i in range(n)]
    return {
        "cliente": nomes,
        "email":   [f"user{i:04d}@{rnd.choice(dominios)}" for i in range(n)],
        "cidade":  [rnd.choice(cidades) for _ in range(n)],
        "plano":   [rnd.choice(planos) for _ in range(n)],
        "valor":   [str(rnd.randint(50, 500)) for _ in range(n)],
    }


def measure(name: str, values, is_multi: bool):
    """Mede raw, TCF, e composicao. Contra-prova de RT obrigatoria."""
    if is_multi:
        raw_text = "\n".join(
            ",".join(values[c][i] for c in values) for i in range(len(next(iter(values.values()))))
        )
        tcf_text = encode(values)
        rt_ok = decode(tcf_text) == values
    else:
        raw_text = "\n".join(values)
        tcf_text = encode(values)
        rt_ok = decode(tcf_text) == values

    raw_b = raw_text.encode("utf-8")
    tcf_b = tcf_text.encode("utf-8")

    n_rows = len(next(iter(values.values()))) if is_multi else len(values)
    n_cols = len(values) if is_multi else 1
    row = {
        "dataset": name,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "raw_bytes": len(raw_b),
        "tcf_bytes": len(tcf_b),
        "tcf_vs_raw_pct": round(100 * (1 - len(tcf_b) / len(raw_b)), 2),
        "rt_ok": rt_ok,
        "comp": {},
    }
    for cname, fn in ALL.items():
        on_raw = len(fn(raw_b))
        on_tcf = len(fn(tcf_b))
        row["comp"][cname] = {
            "on_raw": on_raw,
            "on_tcf": on_tcf,
            # TCF ajudou a camada? negativo = TCF+comp menor que comp(raw)
            "tcf_helps_pct": round(100 * (1 - on_tcf / on_raw), 2),
        }
    return row, raw_text, tcf_text, rt_ok


def main():
    datasets = [
        ("retail-description-2k", load_col("online-retail/description-2k.csv"), False),
        ("retail-stockcode-2k",   load_col("online-retail/stockcode-2k.csv"),   False),
        ("lineitem-comment-2k",   load_col("tpch-sf001/lcomment-2k.csv"),       False),
        ("cadastro-multi-2k",     synth_multi(),                                 True),
    ]
    results = []
    for name, vals, is_multi in datasets:
        row, raw_text, tcf_text, rt_ok = measure(name, vals, is_multi)
        results.append(row)
        # ---- ARTEFATOS: input (amostra), output TCF (amostra), RT ----
        (ART / f"{name}.01-input-sample.txt").write_text(
            "\n".join(raw_text.splitlines()[:12]), encoding="utf-8"
        )
        (ART / f"{name}.02-tcf-output-sample.txt").write_text(
            "\n".join(tcf_text.splitlines()[:14]), encoding="utf-8"
        )
        (ART / f"{name}.03-rt-counterproof.txt").write_text(
            f"dataset={name}\nRT decode(encode(x))==x: {rt_ok}\n"
            f"raw={row['raw_bytes']}B  tcf={row['tcf_bytes']}B  "
            f"tcf_vs_raw={row['tcf_vs_raw_pct']}%\n",
            encoding="utf-8",
        )
        assert rt_ok, f"RT QUEBRADO em {name} — resultado invalido (contra-prova)"

    out = {"results": results}
    (ART / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
