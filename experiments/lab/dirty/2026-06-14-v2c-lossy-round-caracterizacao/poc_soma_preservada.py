"""PoC — arredondamento com SOMA PRESERVADA (maior-resto), a ideia-chave do owner.

Loss por-linha, lossless no AGREGADO (soma). Metodo do maior resto (Hamilton
apportionment / distribuicao de centavos): arredonda cada valor pra baixo (floor
na precisao d) e adiciona +1 step aos itens de maior residuo ate' a soma bater o
total exato. Cada valor erra <= 1 step; a SOMA fica exata.

Mostra: (1) o exemplo canonico de parcelamento (100/3); (2) numa coluna decimal
real, que a soma e' preservada e os bytes caem (vs round ingenuo que pode driftar).

FORK exploratorio — NAO toca src/tcf. Usa Decimal (exatidao, sem ruido float).
"""

from __future__ import annotations

import csv
import sys
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode  # noqa: E402

EXT = Path("Z:/tcf-data/external")


def lr_round(vals, d):
    """Arredonda vals (list[Decimal]) a d casas preservando a SOMA (maior resto)."""
    q = Decimal(1).scaleb(-d)               # passo = 10^-d
    scaled = [v / q for v in vals]          # em unidades inteiras de passo
    floors = [s.to_integral_value(rounding=ROUND_FLOOR) for s in scaled]
    target = (sum(vals) / q).to_integral_value()   # total em unidades de passo (round)
    deficit = int(target - sum(floors))
    order = sorted(range(len(vals)), key=lambda i: scaled[i] - floors[i], reverse=True)
    add = set(order[:deficit]) if deficit > 0 else set()
    return [ (floors[i] + (1 if i in add else 0)) * q for i in range(len(vals)) ]


def fmt(x, d):
    return f"{x:.{d}f}"


def nbytes(s):
    return len(s.encode("utf-8"))


print("=== (1) Exemplo canonico: parcelar 100.00 em 3 ===")
parcela = Decimal("100.00") / 3                       # 33.3333...
naive = [parcela.quantize(Decimal("0.01")) for _ in range(3)]
lr = lr_round([parcela] * 3, 2)
print(f"  valor real por parcela: {parcela}")
print(f"  round ingenuo: {[str(x) for x in naive]}  soma={sum(naive)}  (drift!)")
print(f"  maior-resto:   {[str(x) for x in lr]}  soma={sum(lr)}  (soma EXATA)")

print("\n=== (2) Coluna decimal real (wine density, alta precisao) ===")
path = EXT / "wine-quality" / "wine.csv"
if path.exists():
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        h = next(r)
        col = h.index("density")
        vals = []
        for n, row in enumerate(r):
            if n >= 5000:
                break
            try:
                vals.append(Decimal(row[col]))
            except Exception:
                pass
    orig_txt = [str(v) for v in vals]
    for d in (3, 2):
        naive = [fmt(v.quantize(Decimal(1).scaleb(-d)), d) for v in vals]
        lr = lr_round(vals, d)
        lr_txt = [fmt(x, d) for x in lr]
        soma_orig = sum(vals)
        soma_naive = sum(Decimal(x) for x in naive)
        soma_lr = sum(lr)
        b_orig = nbytes(encode(orig_txt))
        b_lr = nbytes(encode(lr_txt))
        max_err = max(abs(vals[i] - lr[i]) for i in range(len(vals)))
        print(f"\n  d={d}:")
        print(f"    soma original        = {soma_orig}")
        print(f"    soma round ingenuo   = {soma_naive}   drift={soma_naive - soma_orig.quantize(soma_naive)}")
        print(f"    soma maior-resto     = {soma_lr}   (== soma orig arredondada a d)")
        print(f"    erro maximo por-linha= {max_err}  (<= passo 10^-{d})")
        print(f"    bytes: original={b_orig}  maior-resto={b_lr}  ({100*(b_orig-b_lr)/b_orig:.1f}% menor)")
else:
    print("  SKIP (wine nao encontrado)")

print("\nLeitura: a soma e' recuperada EXATA (no agregado), cada linha erra <= 1 step,")
print("e os bytes caem porque os valores arredondados sao low-precision (caem no split+dict).")
print("Pra recuperar a soma na precisao ORIGINAL (nao so' a d), guarda-se 1 ancora (a soma exata).")
