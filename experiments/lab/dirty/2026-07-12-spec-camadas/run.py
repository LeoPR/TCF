"""Lab spec-camadas — as 3 FORMAS / 6 CAMADAS do spec, medidas (T-SPEC-DEEPDIVE-08 §4-ter).

Hipótese do owner (2026-07-12): o spec pode ser tratado em 3 formas —
  A) ENTRADA total: transforma antes, o núcleo nem trabalha (= nature HOJE);
  B) PARALELA: o núcleo trabalha no dado (limpo), e DEPOIS troca-se a base-94
     ao menos nas REFERÊNCIAS/resíduos;
  C) MISTO: limpa na entrada (pra o núcleo achar padrões) + troca na saída.
Decompondo em ~6 camadas: limpeza (máscara) · derivação (DV) · pré-forma
(ordem/delta) · núcleo · troca nas referências · saída/header.

Este lab MEDE a escada de composições pra CPF e CNPJ nos regimes que temos,
SEM tocar o core (cada degrau é uma transformação de coluna reversível por
construção — a nota de máquina diz o que cada um exigiria de spec).

Degraus (todos passam pelo pipeline REAL via encode(); bytes = emitted_bytes):
  S1  masked           — valor original mascarado (baseline; split acha estrutura)
  S2  clean            — L1+L2: dígitos do corpo (máscara+DV removidos, rederiváveis)
  S3  clean+delta      — L3 pré-forma: corpo como delta do anterior (1º absoluto)
  S4  base94 absoluto  — forma A (nature HOJE): corpo→base-94 por linha
  S5  delta→base94     — forma C medível: pré-forma delta + densificação base-94
                         (quando o modo vence por dict, é ≡ trocar a TABELA de
                         referências — a "troca nas referências" da forma B)

Decode de cada degrau (lossless por construção): expande base-94 → desfaz delta
→ zfill(body) → rederiva DV → re-aplica máscara. Exatamente a visão do owner:
"a expansão do base-94 e depois leva as chaves".
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode  # noqa: E402
from tcf.natures.templated_checked import BASE94  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

HERE = Path(__file__).parent
B = len(BASE94)
OUT: list[str] = []


def p(s=""):
    OUT.append(s)
    print(s)


def col_bytes(values: list[str]) -> tuple[int, str]:
    side = SideOutputs()
    encode({"c": list(values)}, side_outputs=side)
    pc = side.per_col["c"]
    return pc.emitted_bytes, pc.emitted_mode


def b94(n: int) -> str:
    """int → base-94 variável (alfabeto do spec; sinal '-' pra delta negativo)."""
    if n == 0:
        return BASE94[0]
    neg, n = n < 0, abs(n)
    out = []
    while n:
        n, r = divmod(n, B)
        out.append(BASE94[r])
    return ("-" if neg else "") + "".join(reversed(out))


def ladder(name: str, masked: list[str], body_digits: list[str]) -> list[tuple]:
    """Mede os 5 degraus de uma coluna. body_digits = corpo SEM máscara/DV."""
    ints = [int(d) for d in body_digits]
    deltas = [str(ints[0])] + [str(b - a) for a, b in zip(ints, ints[1:])]
    rows = [
        ("S1 masked (baseline)", masked),
        ("S2 clean (mask+DV out)", body_digits),
        ("S3 clean+delta", deltas),
        ("S4 base94 absoluto (=hoje)", [b94(i) for i in ints]),
        ("S5 delta->base94 (misto)", [b94(ints[0])] + [b94(b - a) for a, b in zip(ints, ints[1:])]),
    ]
    out = []
    for label, col in rows:
        by, mode = col_bytes(col)
        out.append((label, by, mode))
    base = out[0][1]
    p(f"### {name}  (n={len(masked)}; S1 baseline = {base}B)")
    p("")
    p("| degrau | bytes | modo | vs S1 |")
    p("|---|---:|---|---:|")
    for label, by, mode in out:
        p(f"| {label} | {by} | {mode} | {100*(by-base)/base:+.1f}% |")
    p("")
    return out


def cnpj_digits(v: str) -> str:
    d = "".join(c for c in v if c.isdigit())
    return d[:12]                            # corpo base8+filial (DV fora)


def cpf_dv(body9: str) -> str:
    ds = [int(c) for c in body9]
    d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(d * w for d, w in zip(ds + [d1], range(11, 1, -1))) * 10) % 11 % 10
    return f"{d1}{d2}"


def fmt_cpf(body9: str) -> str:
    return f"{body9[:3]}.{body9[3:6]}.{body9[6:9]}-{cpf_dv(body9)}"


def main() -> int:
    p("# spec-camadas — a escada medida (formas A/B/C do owner)")
    p("")
    p("Gerado por run.py. Bytes = emitted_bytes da coluna pelo pipeline REAL.")
    p("Cada degrau é lossless por construção (decode: base94 -> delta -> zfill ->")
    p("DV -> máscara). S5 vencendo por dict ≡ 'troca nas referências' (forma B).")
    p("")

    # --- CNPJ real (receita), ordenado e embaralhado ---
    r = DatasetReader("receita-cnpj")
    try:
        rows = r.rows("estabelecimentos", limit=5000)
    finally:
        r.close()
    cnpj = [x["cnpj"] for x in rows]
    shuf = list(cnpj)
    random.Random(20260712).shuffle(shuf)
    p("## CNPJ real (receita, 5000)")
    p("")
    lad_ord = ladder("CNPJ ordenado (PK do hub)", cnpj, [cnpj_digits(v) for v in cnpj])
    lad_shf = ladder("CNPJ embaralhado", shuf, [cnpj_digits(v) for v in shuf])

    # --- CPF sintético (efêmero §2.3), random e clustered ---
    rng = random.Random(20260601)
    N = 500
    rand_bodies = [f"{rng.randint(0, 999999999):09d}" for _ in range(N)]
    start = rng.randint(0, 999000000)
    clust_bodies = [f"{start + i*3:09d}" for i in range(N)]
    p("## CPF sintético (efêmero §2.3, 500)")
    p("")
    lad_rand = ladder("CPF RANDOM", [fmt_cpf(b) for b in rand_bodies], rand_bodies)
    lad_clus = ladder("CPF CLUSTERED (lote +3)", [fmt_cpf(b) for b in clust_bodies], clust_bodies)

    # --- leitura por camada ---
    p("## Leitura por camada (em que grau cada uma dá vantagem)")
    p("")
    def g(lad, i):  # bytes do degrau i
        return lad[i][1]
    p("| camada isolada | CNPJ ord | CNPJ shuf | CPF rand | CPF clust |")
    p("|---|---:|---:|---:|---:|")
    p(f"| L1+L2 limpeza+DV (S1→S2) | {g(lad_ord,1)-g(lad_ord,0):+d} | {g(lad_shf,1)-g(lad_shf,0):+d} "
      f"| {g(lad_rand,1)-g(lad_rand,0):+d} | {g(lad_clus,1)-g(lad_clus,0):+d} |")
    p(f"| L3 pré-forma delta (S2→S3) | {g(lad_ord,2)-g(lad_ord,1):+d} | {g(lad_shf,2)-g(lad_shf,1):+d} "
      f"| {g(lad_rand,2)-g(lad_rand,1):+d} | {g(lad_clus,2)-g(lad_clus,1):+d} |")
    p(f"| L5 base94 nos resíduos (S3→S5) | {g(lad_ord,4)-g(lad_ord,2):+d} | {g(lad_shf,4)-g(lad_shf,2):+d} "
      f"| {g(lad_rand,4)-g(lad_rand,2):+d} | {g(lad_clus,4)-g(lad_clus,2):+d} |")
    p(f"| forma A hoje (S1→S4) | {g(lad_ord,3)-g(lad_ord,0):+d} | {g(lad_shf,3)-g(lad_shf,0):+d} "
      f"| {g(lad_rand,3)-g(lad_rand,0):+d} | {g(lad_clus,3)-g(lad_clus,0):+d} |")
    p(f"| forma C misto (S1→S5) | {g(lad_ord,4)-g(lad_ord,0):+d} | {g(lad_shf,4)-g(lad_shf,0):+d} "
      f"| {g(lad_rand,4)-g(lad_rand,0):+d} | {g(lad_clus,4)-g(lad_clus,0):+d} |")
    p("")
    p("Nota de máquina: S3/S5 exigem spec ESTATAL por coluna (delta depende da linha")
    p("anterior) — encode_value per-value de hoje não expressa; é a capacidade nova")
    p("('column-wise nature') a registrar. S5≡troca-nas-referências quando dict vence.")
    (HERE / "result.md").write_text("\n".join(OUT), encoding="utf-8", newline="\n")
    print(f"\n[result.md -> {HERE/'result.md'}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
