"""Demonstração medida das intuições sobre CPF/CNPJ specs (T-SPEC-DEEPDIVE-08 §5.1).

O owner pediu VER os exemplos com amostras antes de implementar a "nature compete".
Este script MEDE e MOSTRA:
  1. a transformação de 1 valor (base-94 descarta máscara+DV) — placeholder público;
  2. CNPJ real (receita, não-PII): a estrutura que a nature DESTRÓI (filial quase-
     constante, base ordenada, DV derivável) + os bytes com/sem nature, ordenado vs
     embaralhado — a raiz do achado F4;
  3. CPF sintético (efêmero, §2.3): nature AJUDA em random, PIORA em clustered.

§2.3: CPF sempre efêmero (gerado, não salvo); valores exibidos = placeholders públicos
(dígitos repetidos, mod-11-válidos, não mapeiam pessoa) OU mascarados. CNPJ real da receita
é registro público não-PII; as amostras exibidas mascaram a base (só a ESTRUTURA importa).
"""
from __future__ import annotations

import io
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import SPEC_CNPJ, SPEC_CPF, encode  # noqa: E402
from tcf.natures.templated_checked import encode_value  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

OUT = []                                    # linhas do relatório (stdout + DEMO.md)


def p(s=""):
    OUT.append(s)
    print(s)


def col_bytes(values: list[str], spec=None) -> tuple[int, str]:
    """Bytes EMITIDOS + modo vencedor da coluna (via side_outputs.per_col, BUG-07).
    spec=None → sem nature; spec → nature_per_col forçada (comportamento atual)."""
    side = SideOutputs()
    kw = {"nature_per_col": {"c": spec}} if spec is not None else {}
    encode({"c": values}, side_outputs=side, **kw)
    pc = side.per_col["c"]
    return pc.emitted_bytes, pc.emitted_mode


def _cpf_dv(body9: str) -> str:
    """DV mod-11 do CPF (2 dígitos) — pra gerar CPFs válidos sequenciais/clustered."""
    ds = [int(c) for c in body9]
    d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
    ds2 = ds + [d1]
    d2 = (sum(d * w for d, w in zip(ds2, range(11, 1, -1))) * 10) % 11 % 10
    return f"{d1}{d2}"


def _fmt_cpf(body9: str) -> str:
    dv = _cpf_dv(body9)
    return f"{body9[:3]}.{body9[3:6]}.{body9[6:9]}-{dv}"


# ===========================================================================
def demo1_transform():
    p("## 1. A transformação de 1 valor (o que a nature faz)")
    p("")
    # placeholder público: dígitos repetidos, mod-11-VÁLIDO, não mapeia pessoa (README)
    for raw in ["111.111.111-11", "222.222.222-22"]:
        enc, status = encode_value(SPEC_CPF, raw)
        p(f"  CPF  {raw!r}  ({len(raw)}B)  →  {enc!r}  ({len(enc)}B, {status})")
    cnpj_ph = "11.222.333/0001-81"           # placeholder ilustrativo
    enc, status = encode_value(SPEC_CNPJ, cnpj_ph)
    p(f"  CNPJ {cnpj_ph!r} ({len(cnpj_ph)}B)  →  {enc!r}  ({len(enc)}B, {status})")
    p("")
    p("  A nature JOGA FORA a máscara (pontuação) + o DV (derivável) e empacota o CORPO")
    p("  num inteiro base-94. Em 1 valor isolado é ótimo (−64%). O PROBLEMA aparece em")
    p("  COLUNA, porque o inteiro base-94 apaga a estrutura ENTRE as linhas.")
    p("")


# ===========================================================================
def demo2_cnpj_real():
    p("## 2. CNPJ REAL (receita, não-PII): a estrutura que a nature destrói")
    p("")
    r = DatasetReader("receita-cnpj")
    try:
        rows = r.rows("estabelecimentos", limit=5000)
    finally:
        r.close()
    cnpj = [row["cnpj"] for row in rows]     # PK-sorted no hub

    # --- estrutura medida ---
    def parts(v):                            # NN.NNN.NNN/FFFF-DD
        digits = "".join(ch for ch in v if ch.isdigit())
        return digits[:8], digits[8:12], digits[12:]   # base8, filial, dv
    bases = [parts(v)[0] for v in cnpj]
    filiais = [parts(v)[1] for v in cnpj]
    fc = Counter(filiais)
    top_fil, top_n = fc.most_common(1)[0]
    non_decr = sum(1 for a, b in zip(bases, bases[1:]) if b >= a)
    deltas = Counter(int(b) - int(a) for a, b in zip(bases, bases[1:]))
    dv_ok = all(_cnpj_dv_ok(v) for v in cnpj[:500])

    p(f"  amostra: {len(cnpj)} CNPJs reais (primeiros, PK-sorted)")
    p(f"  FILIAL   : {len(fc)} distintos; '{top_fil}' domina {100*top_n/len(cnpj):.1f}% "
      f"(quase-constante → dict/RLE quase de graça)")
    p(f"  BASE-8   : {100*len(set(bases))/len(bases):.1f}% únicos, MAS "
      f"{100*non_decr/(len(bases)-1):.1f}% não-decrescente (ORDENADA)")
    top_d = deltas.most_common(4)
    p(f"  deltas base consecutivos concentrados: {', '.join(f'{d:+d}={100*n/(len(bases)-1):.0f}%' for d,n in top_d)}")
    p(f"  DV       : derivável (mod-11) — 0 bits de informação (checado {dv_ok})")
    p("")
    # amostras MASCARADAS (base ofuscada, estrutura visível)
    p("  amostras (base mascarada, filial+ordenação visíveis):")
    for v in cnpj[:5]:
        b, f, d = parts(v)
        p(f"    XX.XXX.X{b[-1]}/{f}-{d}   (base termina …{b[-2:]}, filial {f})")
    p("")

    # --- bytes com/sem nature, ordenado vs embaralhado ---
    p("  BYTES da coluna cnpj (emitted_bytes / modo vencedor):")
    for label, col in [("ORDENADA (como no hub)", cnpj),
                       ("EMBARALHADA", _shuffled(cnpj))]:
        no_b, no_m = col_bytes(col)
        na_b, na_m = col_bytes(col, SPEC_CNPJ)
        verdict = "nature PIORA" if na_b > no_b else "nature ajuda"
        p(f"    {label:24} sem nature {no_b:>6}B ({no_m:5})  |  "
          f"com nature {na_b:>6}B ({na_m:5})  →  {verdict} {na_b-no_b:+d}B")
    p("")
    p("  LEITURA: ordenada, o split explora a estrutura (matriz/filial/deltas) e a nature")
    p("  a DESTRÓI (cai pra raw) → +bytes. Embaralhada, não há estrutura → a nature ganha.")
    p("  A nature de hoje é FORÇADA (camada-0) — não deixa o split competir. É o que o fix corrige.")
    p("")


def _cnpj_dv_ok(v: str) -> bool:
    d = [int(c) for c in v if c.isdigit()]
    def dv(ds, ws):
        s = sum(x * w for x, w in zip(ds, ws)); r = s % 11
        return 0 if r < 2 else 11 - r
    w1 = [5,4,3,2,9,8,7,6,5,4,3,2]; w2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    return d[12] == dv(d[:12], w1) and d[13] == dv(d[:12] + [d[12]], w2)


def _shuffled(xs):
    ys = list(xs); random.Random(20260712).shuffle(ys); return ys


# ===========================================================================
def demo3_cpf_regimes():
    p("## 3. CPF sintético (efêmero, §2.3): nature ajuda RANDOM, piora CLUSTERED")
    p("")
    rng = random.Random(20260601)
    N = 500
    # random: corpos totalmente aleatórios
    rand = [_fmt_cpf(f"{rng.randint(0, 999999999):09d}") for _ in range(N)]
    # clustered administrativo: base sequencial a partir de um ponto (lote emitido junto)
    start = rng.randint(0, 999000000)
    clust = [_fmt_cpf(f"{start + i*3:09d}") for i in range(N)]
    p(f"  {N} CPFs sintéticos por regime (gerados, NÃO salvos — §2.3)")
    # §2.3: NUNCA exibir CPF DV-válido (mesmo sintético) — mostro só a ESTRUTURA
    def _mask(cpf):                          # prefixo visível, corpo-final+DV mascarados
        return cpf[:7] + "X.XXX-XX"
    p(f"  RANDOM   : corpos aleatórios (ex. {_mask(rand[0])} — mascarado §2.3)")
    p(f"  CLUSTERED: base sequencial (lote emitido junto): {_mask(clust[0])}, {_mask(clust[1])}, "
      f"{_mask(clust[2])} — prefixo '{clust[0][:7]}' compartilhado, base +3 por linha")
    p("")
    p("  BYTES da coluna cpf (emitted_bytes / modo):")
    for label, col in [("RANDOM", rand), ("CLUSTERED (sequencial)", clust)]:
        no_b, no_m = col_bytes(col)
        na_b, na_m = col_bytes(col, SPEC_CPF)
        verdict = "nature PIORA" if na_b > no_b else "nature AJUDA"
        p(f"    {label:24} sem nature {no_b:>6}B ({no_m:5})  |  "
          f"com nature {na_b:>6}B ({na_m:5})  →  {verdict} {na_b-no_b:+d}B")
    p("")
    p("  LEITURA: a MESMA intuição do CNPJ vale pro CPF. Onde há estrutura inter-linha")
    p("  (lote sequencial = clustering administrativo real, NUNCA testado standalone), a")
    p("  nature pode PIORAR. Onde não há (random), ela ganha. O gate real-world do CPF")
    p("  segue aberto (só sintético) — mas o mecanismo é o mesmo, agora demonstrado.")
    p("")


# ===========================================================================
def main() -> int:
    p("# DEMO — intuições CPF/CNPJ medidas (T-SPEC-DEEPDIVE-08 §5.1)")
    p("")
    p("Gerado por scripts/spec_demo.py. Todos os bytes MEDIDOS (emitted_bytes por coluna,")
    p("via SideOutputs BUG-07). CPF efêmero (§2.3); CNPJ real não-PII com base mascarada.")
    p("")
    demo1_transform()
    demo2_cnpj_real()
    demo3_cpf_regimes()
    out = ROOT / "experiments" / "results" / "evidencia-0.8" / "spec-demo" / "DEMO.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(OUT), encoding="utf-8", newline="\n")
    print(f"\n[DEMO.md -> {out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
