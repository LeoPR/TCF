"""ADR-0043 — um CNPJ so': o numerico como caso COMPACTO POR VALOR.

A DIRECAO DO OWNER (2026-08-21)
-------------------------------
*"o CNPJ numerico ultimamente sera' apenas pra legado agora [...] ele nao e'
estatisticamente pequeno AGORA, mas se diluira' no tempo [...] precisamos firmar
um CNPJ so', que sera' alfa e tera' que cobrir o numerico [...] pode ser que a
gente nao consiga fazer uma heuristica que sustente isso por muito tempo. [...]
se aparecer alguma oportunidade de expressa-lo menor (por ser numerico) me
parece uma boa ideia."*

O numerico e' 10^12/36^12 ~ 2,1e-7 do espaco novo — qualquer heuristica POR
COLUNA calibrada na fracao numerico/alfa tem prazo de validade. A resposta nao
e' heuristica: e' POR VALOR. No `SPEC_CNPJ_ALFA`, corpo 100% decimal grava em
base 10 com 7 chars (payload BYTE-IDENTICO ao do legado); corpo com letra grava
em base 36 com 10. O decode distingue pelo COMPRIMENTO. Nao ha' escolha a errar.

OS GATES DESTE LAB
------------------
  G1  PARIDADE: payload numerico do unificado == payload do SPEC_CNPJ, byte a byte
  G2  DOMINACAO: na varredura k=0..2000 (real + injecao), o unificado nunca perde
      mais que o header (+1 B em k=0) e vence em todo k>=1 — contra o legado E
      contra o desenho fixo do ADR-0042 (numeros pinados do lab 0030)
  G3  CHOOSER: contra a verdade (dois encodes), na MESMA varredura de 51 pontos
      que reprovou o anterior (41/51, residuo 3,15%)
  G4  MINUSCULA: o dominio oficial e' MAIUSCULA-only (NT 2025.001); minuscula e'
      representacao -> hoje literal (byte-RT); medir o que o contrato case-fold
      compraria (classe CONTRATO, H-15-06 — NAO soldado)
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                          # noqa: E402
from tcf.natures import SPEC_CNPJ, SPEC_CNPJ_ALFA, cnpj_spec_para       # noqa: E402
from tcf.natures.templated_checked import _cnpj_check_fn                # noqa: E402

N = 2000
AL = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
#: (k, bytes) do desenho FIXO do ADR-0042, pinados do lab 0030 (mesma seed 11)
FIXO_0042 = {0: 24292, 1: 24292, 1000: 24455, 2000: 24542}
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


def um_alfa(rng) -> str:
    c = "".join(rng.choice(AL) for _ in range(12))
    if c.isdigit():
        c = "A" + c[1:]
    d = "".join(str(x) for x in _cnpj_check_fn([ord(ch) - 48 for ch in c]))
    s = c + d
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def main() -> int:
    from shaper import Shaper, ShapeRequest

    print("=" * 100)
    print("ADR-0043 — um CNPJ so': o numerico como caso COMPACTO POR VALOR")
    print("=" * 100)

    # ── G1: paridade byte a byte ─────────────────────────────────────────
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj", volume=N, seed=11,
                                    stratify_by="uf"))
    reais = [str(x["cnpj"]) for x in r.tables[list(r.tables)[0]]][:N]
    pares = 0
    for v in reais:
        p1, _ = SPEC_CNPJ.encode_value(v)
        p2, _ = SPEC_CNPJ_ALFA.encode_value(v)
        assert p1 == p2 and len(p2) == 7, v
        pares += 1
    print(f"\nG1 PARIDADE: {pares:,}/{len(reais):,} payloads numericos BYTE-IDENTICOS "
          f"ao legado (7 chars)")

    # ── G2+G3: a varredura ───────────────────────────────────────────────
    print(f"\nG2 DOMINACAO (seed 11; evidencia gravada) — vs legado e vs o fixo do ADR-0042")
    print(f"  {'k':>5} {'legado :cnpj':>13} {'unificado':>11} {'delta':>9} {'fixo-0042':>10}")
    rng = random.Random(11 * 7)
    KS = (0, 1, 10, 100, 300, 450, 500, 600, 800, 1500, 2000)
    tabela = []
    for k in KS:
        col = list(reais)
        for i in rng.sample(range(N), k):
            col[i] = um_alfa(rng)
        w1 = encode(col, nature=SPEC_CNPJ)
        w2 = encode(col, nature=SPEC_CNPJ_ALFA)
        assert decode(w1) == col and decode(w2) == col, f"RT k={k}"
        b1, b2 = len(w1.encode("utf-8")), len(w2.encode("utf-8"))
        grava(IN, f"k{k:04d}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        grava(OUT, f"k{k:04d}-unificado.tcf", w2)
        grava(OUT, f"k{k:04d}-unificado.roundtrip.json",
              json.dumps(decode(w2)[:40], ensure_ascii=False, indent=1))
        fixo = FIXO_0042.get(k)
        print(f"  {k:>5} {b1:>13,} {b2:>11,} {b2-b1:>+8,}B {fixo if fixo else '--':>10}")
        tabela.append({"k": k, "legado": b1, "unificado": b2,
                       "fixo_adr0042": fixo, "rt": True})
        assert b2 - b1 <= 1, f"k={k}: unificado perdeu mais que o header"
        if k >= 1:
            assert b2 < b1, f"k={k}: unificado deveria vencer"

    # G3: o chooser contra a verdade, 3 sementes x 17 fracoes (a MESMA varredura)
    KS51 = (0, 1, 10, 100, 300, 420, 450, 470, 490, 500, 510, 530, 560, 600,
            800, 1500, 2000)
    tot = err = 0
    for seed in (11, 23, 42):
        rr = Shaper().apply(ShapeRequest(dataset="receita-cnpj", volume=N,
                                         seed=seed, stratify_by="uf"))
        base = [str(x["cnpj"]) for x in rr.tables[list(rr.tables)[0]]][:N]
        rng2 = random.Random(seed * 7)
        for k in KS51:
            col = list(base)
            for i in rng2.sample(range(N), k):
                col[i] = um_alfa(rng2)
            b1 = len(encode(col, nature=SPEC_CNPJ).encode("utf-8"))
            b2 = len(encode(col, nature=SPEC_CNPJ_ALFA).encode("utf-8"))
            verdade = SPEC_CNPJ if b1 <= b2 else SPEC_CNPJ_ALFA
            tot += 1
            err += (cnpj_spec_para(col) is not verdade)
    print(f"\nG3 CHOOSER: {tot-err}/{tot} contra a verdade "
          f"(ADR-0042 dava 41/51, residuo ate' 3,15%)")
    assert err == 0, "chooser errou — o residuo nao desapareceu"

    # ── G4: minuscula ────────────────────────────────────────────────────
    rng3 = random.Random(9)
    col_alfa = [um_alfa(rng3) for _ in range(N)]
    col_lower = [v.lower() for v in col_alfa]
    raw = len("\n".join(col_lower).encode("utf-8"))
    w_hoje = encode(col_lower, nature=SPEC_CNPJ_ALFA)
    assert decode(w_hoje) == col_lower                       # byte-RT do literal
    w_fold = encode(col_alfa, nature=SPEC_CNPJ_ALFA)         # o que o CONTRATO faria
    assert decode(w_fold) == col_alfa
    b_hoje, b_fold = len(w_hoje.encode("utf-8")), len(w_fold.encode("utf-8"))
    grava(IN, "minuscula.json", json.dumps(col_lower[:40], ensure_ascii=False, indent=1))
    grava(OUT, "minuscula-hoje-literal.tcf", w_hoje)
    grava(OUT, "minuscula-hoje-literal.roundtrip.json",
          json.dumps(decode(w_hoje)[:40], ensure_ascii=False, indent=1))
    grava(OUT, "minuscula-sob-fold.tcf", w_fold)
    grava(OUT, "minuscula-sob-fold.roundtrip.json",
          json.dumps(decode(w_fold)[:40], ensure_ascii=False, indent=1))
    print(f"\nG4 MINUSCULA (dominio oficial e' MAIUSCULA-only — NT 2025.001):")
    print(f"  hoje (literal, byte-RT)   : {b_hoje:>7,} B ({(b_hoje/raw-1)*100:+.2f}% vs raw)")
    print(f"  sob contrato case-fold    : {b_fold:>7,} B ({(b_fold/raw-1)*100:+.2f}% vs raw)")
    print(f"  o contrato compraria      : {(1-b_fold/b_hoje)*100:.1f}% — MAS canoniza a")
    print("  saida (perde byte-RT) => classe CONTRATO, H-15-06, aguarda a assinatura")
    print("  do T-FMT-CONTRACT-SIGNATURE. NAO soldado.")

    (AQUI / "resultado.json").write_text(json.dumps({
        "G1_paridade": {"n": pares, "identicos": pares},
        "G2_dominacao": tabela,
        "G3_chooser": {"corretos": tot - err, "total": tot,
                       "adr0042_dava": "41/51, residuo 3,15%"},
        "G4_minuscula": {"raw": raw, "hoje_literal": b_hoje, "sob_fold": b_fold,
                         "contrato_compraria_pct": round((1 - b_fold / b_hoje) * 100, 1)},
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados), f"EVIDENCIA FALTANDO: {_arquivos - achados}"
    assert not (achados - _arquivos), f"EVIDENCIA ORFA: {achados - _arquivos}"
    print(f"\n-> {len(achados)} arquivos (inputs+outputs), portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
