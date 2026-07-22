"""run.py — spec por largura de bits (b/b2/b4/b8): densidade, RT, e PESAR vs HCC-nativo (owner 2026-07-07).

(1) tabela k→w→linhas/byte.
(2) RT em domínios sintéticos k=2,3,4,8,16.
(3) colunas REAIS (adult enum 2..16, tpch enum-2/3): bit-packed vs raw HCC → escolhe o menor (pesa).

`python run.py` regenera artifacts/. Dados: Z:/tcf-data/interim/*.db. Não toca src/tcf.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import bitpack as BP                                   # noqa: E402
from tcf import encode                                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
INTERIM = Path("Z:/tcf-data/interim")


def nb(s): return len(s.encode("utf-8"))
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def thread_tabela():
    L = ["# TABELA — k valores → w bits → linhas por byte (o spec primitivo de tipo)", "",
         "| k (distintos) | spec | w bits | linhas/byte |", "|---|---|---|---|"]
    for k in (2, 3, 4, 5, 8, 16, 17, 256):
        wd = BP.width_for(k)
        L.append(f"| {k} | {BP.spec_name(wd)} | {wd} | {BP.rows_per_byte(wd)} |")
    L += ["", "A lista do domínio (embutida no spec) É a referência (índice↔valor). Corpo = índices a w bits."]
    w("01-tabela-larguras.txt", "\n".join(L) + "\n")


def thread_sintetico(n=64):
    L = ["# RT sintético — domínios k=2..16, N=64 (densidade real do empacotamento)", ""]
    for k in (2, 3, 4, 8, 16):
        dom = [f"v{i}" for i in range(k)]
        col = [dom[i % k] for i in range(n)]
        enc = BP.encode_col(col)
        ok = BP.decode_col(enc) == col
        L.append(f"  k={k:2d} spec={BP.spec_name(enc['w']):3s} w={enc['w']}  "
                 f"idx-bytes={len(enc['data'])} (={n}×{enc['w']}/8)  linhas/byte={BP.rows_per_byte(enc['w'])}  RT={'OK' if ok else 'FAIL'}")
    w("02-sintetico-rt.txt", "\n".join(L) + "\n")


REAIS = [
    ("adult-census.db", "adult", "sex"), ("adult-census.db", "adult", "class"),
    ("adult-census.db", "adult", "race"), ("adult-census.db", "adult", "relationship"),
    ("adult-census.db", "adult", "marital-status"), ("adult-census.db", "adult", "workclass"),
    ("adult-census.db", "adult", "occupation"), ("adult-census.db", "adult", "education"),
    ("tpch-sf001.db", "lineitem", "l_returnflag"), ("tpch-sf001.db", "orders", "o_orderstatus"),
    ("tpch-sf001.db", "lineitem", "l_linestatus"),
    ("receita-cnpj.db", "estabelecimentos", "matriz_filial"),
]


def thread_reais():
    L = ["# COLUNAS REAIS — bit-packed (b/b2/b4) vs raw HCC → PESA e escolhe o menor", "",
         "| coluna | N | k | spec | raw HCC | packed(dom+idx) | vencedor |", "|---|---|---|---|---|---|---|"]
    for db, tbl, coln in REAIS:
        dbp = INTERIM / db
        if not dbp.exists():
            continue
        con = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
        try:
            vals = [str(r[0]) for r in con.execute(f'SELECT "{coln}" FROM "{tbl}"').fetchall()]
        except Exception as e:
            L.append(f"| {tbl}.{coln} | erro {str(e)[:20]} | | | | | |"); con.close(); continue
        con.close()
        enc = BP.encode_col(vals)
        ok = BP.decode_col(enc) == vals
        raw = nb(encode(vals))
        packed = BP.packed_total(enc)
        win = "packed" if packed < raw else "HCC"
        L.append(f"| {tbl}.{coln} | {len(vals)} | {len(enc['dom'])} | {BP.spec_name(enc['w'])} | "
                 f"{raw}B | {packed}B | **{win}**{'' if ok else ' RT-FAIL'} |")
    L += ["",
          "raw HCC = tcf.encode nativo (RLE de refs, textual). packed = domínio embutido + índices a w bits (V2-L).",
          "PESAR (owner): o HCC já empacota repetições (RLE); o bit-pack ganha quando o dado é espalhado. O motor",
          "escolhe o menor. Em dado real (espalhado) o bit-pack tende a vencer; header textual `col:b<w>` roteia."]
    w("03-reais-pesa-vs-hcc.txt", "\n".join(L) + "\n")


def main():
    thread_tabela(); thread_sintetico(); thread_reais()

    R = ["# Spec por largura de bits (b/b2/b4/b8) [resumo]", "",
         "## O spec primitivo de tipo (owner)",
         "- k distintos → w bits → 8/w linhas/byte: k≤2→**b**(8/byte) · k≤4→**b2**(4/byte) · k≤16→**b4**(2/byte)",
         "  · k≤256→**b8**(1/byte). Header `col:b<w>` + **lista do domínio embutida = a referência** (índice↔valor).",
         "- Generaliza o spec_bin: enum-3 (A/N/R, F/O/P)→b2; enum-5..16 (race, education…)→b4. Tudo RT.",
         "- **Pesar vs HCC-nativo**: o HCC já empacota repetições (RLE de refs); o bit-pack ganha no espalhado.",
         "  O motor escolhe o menor; header textual roteia (o pack é V2-L, binário interno).",
         "",
         "## Resultado",
         "- tabela de densidade (01); RT sintético k=2..16 (02); colunas reais pesadas vs HCC (03).",
         "- o spec_bin vira caso particular (b, k=2). A referência embutida no spec = 'até a referência está",
         "  embutida' (owner). Próximo: pack pós-HCC lendo *N|^k; welding V2-L."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
