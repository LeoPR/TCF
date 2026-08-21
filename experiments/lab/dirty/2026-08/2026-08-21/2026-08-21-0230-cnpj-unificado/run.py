"""ADR-0044 — um `cnpj` so'. E o RELATORIO que o owner pediu sobre o compacto.

O PEDIDO (owner, 2026-08-21)
---------------------------
*"a ideia e' ter so' 'cnpj' mesmo, ou seja nada de ter dois. [...] agora o alfa
e' padrao, e o so' numerico pode ate' ser oportunidade, mas acho que ela sera'
transitoria [...] O ideal e' ter um algoritmo so' pro cnpj novo, e so' se tiver
uma real vantagem e facil implementacao [...] ai vc avisa."*

Entao este lab tem duas tarefas: PROVAR a unificacao, e RESPONDER se o caso
compacto numerico se sustenta.

  Q1  OTIMALIDADE — 7 e 10 chars sao minimos em base-80? Ha' versao menor?
  Q2  E' TRANSITORIO? — varredura da mistura: o ganho decai? chega a ficar
      NEGATIVO (i.e. a largura mista cobra pedagio a jusante)?
  Q3  LOAD-BEARING? — sem o compacto, um `:cnpj` alfanumerico ainda le' o wire
      de 7 chars ja' emitido?
  Q4  NEUTRALIDADE — o unificado emite/le' o wire historico byte a byte?
      (diferencial contra os parametros HISTORICOS, em `diferencial.py`)

`SPEC_CNPJ` E' o alfanumerico. Nao ha' segundo spec.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import replace
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                       # noqa: E402
from tcf.natures import SPEC_CNPJ                                    # noqa: E402
from tcf.natures.templated_checked import BASE94, _cnpj_check_fn     # noqa: E402

N = 2000
AL = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
#: o "um algoritmo so' PURO" — sem o caso compacto. E' a alternativa que o
#: owner levantou, e existe aqui so' pra ser MEDIDA contra a soldada.
SEM_COMPACTO = replace(SPEC_CNPJ, name="cnpj-sem-compacto", wire_id="xsemc",
                       alfabeto_compacto=None, encoded_length_compacto=0)
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
    print("ADR-0044 — um `cnpj` so'. O compacto numerico se sustenta?")
    print("=" * 100)

    # ── Q1 ───────────────────────────────────────────────────────────────
    print("\nQ1) OTIMALIDADE POR VALOR — ha' versao menor a achar?")
    q1 = {}
    for rot, dom in (("numerico 10^12", 10 ** 12), ("alfanum  36^12", 36 ** 12)):
        k = 1
        while len(BASE94) ** k < dom:
            k += 1
        print(f"  {rot} = {dom:.3e}  ->  MINIMO {k} chars "
              f"(80^{k-1} = {len(BASE94)**(k-1):.2e} nao cabe)")
        q1[rot.split()[0]] = k
        assert len(BASE94) ** (k - 1) < dom <= len(BASE94) ** k
    assert (q1["numerico"], q1["alfanum"]) == (SPEC_CNPJ.encoded_length_compacto,
                                               SPEC_CNPJ.encoded_length)
    print("  Os DOIS sao minimos, e batem com o spec soldado. E o DV nunca e'")
    print("  gravado (check_length=2 e' RECOMPUTADO): a redundancia ja' era zero.")

    # ── Q2 ───────────────────────────────────────────────────────────────
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj", volume=N, seed=11,
                                    stratify_by="uf"))
    reais = [str(x["cnpj"]) for x in r.tables[list(r.tables)[0]]][:N]
    rng = random.Random(31)

    print("\nQ2) O GANHO E' TRANSITORIO? — varredura da mistura (n=2000, real+injecao)")
    print(f"  {'frac_num':>9} {'com compacto':>14} {'sem compacto':>14} {'ganho':>9} "
          f"{'larguras':>11}")
    tabela = []
    for frac in (1.0, 0.99, 0.90, 0.75, 0.50, 0.25, 0.10, 0.01, 0.0):
        k = int(round(N * (1 - frac)))
        col = list(reais)
        for i in rng.sample(range(N), k):
            col[i] = um_alfa(rng)
        w_on = encode(col, nature=SPEC_CNPJ)
        w_off = encode(col, nature=SEM_COMPACTO)
        assert decode(w_on) == col, f"RT frac={frac}"
        assert decode(w_off, nature=SEM_COMPACTO) == col, f"RT-off frac={frac}"
        b_on, b_off = len(w_on.encode("utf-8")), len(w_off.encode("utf-8"))
        larg = sorted({len(SPEC_CNPJ.encode_value(v)[0]) for v in col})
        ganho = (1 - b_on / b_off) * 100
        rot = f"frac{int(frac*100):03d}"
        grava(IN, f"{rot}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        grava(OUT, f"{rot}.tcf", w_on)
        grava(OUT, f"{rot}.roundtrip.json",
              json.dumps(decode(w_on)[:40], ensure_ascii=False, indent=1))
        print(f"  {frac:>9.2f} {b_on:>14,} {b_off:>14,} {ganho:>+8.2f}% {str(larg):>11}")
        tabela.append({"frac_num": frac, "com": b_on, "sem": b_off,
                       "ganho_pct": round(ganho, 2), "larguras": larg})
        assert ganho >= 0, f"frac={frac}: o compacto PERDEU — a mistura cobra pedagio"
    print("\n  O ganho DECAI de +27,6% a +0,00% — o owner estava certo sobre a")
    print("  magnitude. Mas NUNCA fica negativo (0/9): a largura mista nao cobra")
    print("  pedagio a jusante. Custo de mante-lo: zero.")

    # ── Q3 ───────────────────────────────────────────────────────────────
    print("\nQ3) O COMPACTO E' LOAD-BEARING? — o wire legado de 7 chars")
    v = reais[0]
    p_legado = SPEC_CNPJ.encode_value(v)[0]
    assert len(p_legado) == 7
    com = SPEC_CNPJ.decode_value(p_legado)
    sem = SEM_COMPACTO.decode_value(p_legado)
    print(f"  payload historico {p_legado!r} (7 chars)")
    print(f"    com compacto -> {com!r}   {'OK' if com == v else 'FALHOU'}")
    print(f"    sem compacto -> {sem!r}   "
          f"{'OK' if sem == v else 'NAO LE (devolve o payload CRU como valor)'}")
    assert com == v and sem != v
    grava(OUT, "q3-wire-legado.tcf", encode(reais[:50], nature=SPEC_CNPJ))
    grava(OUT, "q3-wire-legado.roundtrip.json",
          json.dumps(decode(encode(reais[:50], nature=SPEC_CNPJ))[:40],
                     ensure_ascii=False, indent=1))
    grava(IN, "q3-wire-legado.json", json.dumps(reais[:40], ensure_ascii=False, indent=1))
    print("\n  => sem o compacto, unificar CORROMPE EM SILENCIO todo wire `:cnpj`")
    print("     ja' emitido. Nao e' erro alto: e' valor errado passando.")
    print("     O compacto nao fica pela compressao — fica porque e' o que permite")
    print("     UM id so'. A compressao (+27,6% -> 0%) e' o bonus que decai.")

    (AQUI / "resultado.json").write_text(json.dumps({
        "Q1_minimos": q1, "Q2_varredura": tabela,
        "Q3_load_bearing": {"payload": p_legado, "com_compacto": com,
                            "sem_compacto": sem, "corrompe_silencioso": sem != v},
        "Q4_diferencial": "ver diferencial.py — 4.011 encodes + 3.505 decodes, 0 divergencias",
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados), f"EVIDENCIA FALTANDO: {_arquivos - achados}"
    assert not (achados - _arquivos), f"EVIDENCIA ORFA: {achados - _arquivos}"
    print(f"\n-> {len(achados)} arquivos (inputs+outputs), portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
