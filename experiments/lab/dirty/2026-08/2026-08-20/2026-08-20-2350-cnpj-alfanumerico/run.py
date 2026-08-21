"""O CNPJ alfanumerico (vigente desde jul/2026) quebra o mecanismo que hoje ganha?

O FATO EXTERNO
--------------
IN RFB no 2.229/2024: a partir de julho/2026 as novas inscricoes de CNPJ tem as
**12 primeiras posicoes ALFANUMERICAS** (0-9 e A-Z) e so' os **2 DV numericos**.
O DV segue modulo 11 com os MESMOS pesos; muda a conversao caractere->valor:
valor = ASCII(c) - 48  (digito -> ele mesmo; 'A' -> 17 ... 'Z' -> 42).
Os CNPJ numericos existentes NAO mudam e geram o MESMO DV — retrocompativel por
construcao, ja' que digito converte pra ele mesmo.

A PERGUNTA DO LAB
-----------------
Nao e' "a nature de CNPJ para de funcionar" — ela ja' NAO dispara em dado real
(o FLOOR prefere o split). A pergunta e':

  **o mecanismo que HOJE ganha no CNPJ real sobrevive ao alfanumerico?**

  G1  qual mecanismo o FLOOR escolhe hoje, no CNPJ numerico REAL (Shaper)?
  G2  o mesmo mecanismo dispara no alfanumerico com estrutura REALISTA?
  G3  quanto se perde — e o TCF chega a ficar MAIOR que o raw?
  G4  o conserto: decomposicao POSICIONAL (a mascara e' fixa) recupera o ganho?
  G5  integridade: o alfanumerico faz roundtrip hoje? (corrompe ou so' deixa de ganhar?)

Dado numerico: REAL, via Shaper (`receita-cnpj`). Alfanumerico: sintetico — nao
existe corpus real ainda —, em DUAS versoes, a realista e o pior caso declarado.
`src/tcf` INTOCADO.
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
from tcf.natures.templated_checked import _cnpj_check_fn                # noqa: E402

N = 2000
ALFA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_arquivos: set[Path] = set()


def val(c: str) -> int:
    """A conversao da IN 2.229/2024: ASCII menos 48."""
    return ord(c) - 48


def dv(corpo: str) -> str:
    return "".join(str(d) for d in _cnpj_check_fn([val(c) for c in corpo]))


def so_alnum(s: str) -> str:
    return "".join(ch for ch in str(s) if ch.isalnum()).upper()


def mascara(s: str) -> str:
    """Aplica a mascara aos 14 caracteres. NORMALIZA antes — o campo da fonte pode
    ja' vir formatado, e mascarar duas vezes produz string de 22 chars que ainda
    sobrevive a `replace` de separador (foi assim que o erro quase passou)."""
    s = so_alnum(s)
    assert len(s) == 14, f"CNPJ com {len(s)} caracteres: {s!r}"
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def grava(nome: str, texto: str) -> Path:
    p = (OUT if nome.endswith((".tcf", ".roundtrip.json")) else IN) / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())
    return p


def mede(cid: str, desc: str, valores: list[str]) -> dict:
    """Encoda a coluna, PROVA o roundtrip e grava a evidencia."""
    w = encode({"cnpj": valores})
    rt = decode(w)["cnpj"]
    assert rt == valores, f"{cid}: ROUNDTRIP QUEBROU"
    b = len(w.encode("utf-8"))
    raw = len("\n".join(valores).encode("utf-8"))
    # o discriminador vem LOGO DEPOIS de `#TCF.8M`; se nao for um dos tres, e' o core
    d = w[7] if len(w) > 7 else "?"
    mec = {"!": "raw", "@": "dict", "%": "split"}.get(d, "core")
    grava(f"{cid}.tcf", w)
    grava(f"{cid}.roundtrip.json", json.dumps(rt[:40], ensure_ascii=False, indent=1))
    grava(f"{cid}.json", json.dumps(valores[:40], ensure_ascii=False, indent=1))
    reg = {"caso": cid, "desc": desc, "n": len(valores), "bytes": b, "raw": raw,
           "vs_raw_pct": round((b / raw - 1) * 100, 2), "mecanismo": mec,
           "header": w[:28].split("\n")[0], "rt": True}
    print(f"  {cid:<26} {b:>8,} B  vs raw {reg['vs_raw_pct']:>+7.2f}%   "
          f'mec={mec:<6} {reg["header"]}')
    return reg


def main() -> int:
    print("=" * 104)
    print("CNPJ ALFANUMERICO (IN RFB 2.229/2024, vigente desde jul/2026) — o que quebra?")
    print("=" * 104)

    # ── a regra, verificada contra o exemplo publicado ────────────────────
    print("\n[0] A REGRA — o exemplo publicado contra o `check_fn` que src/tcf JA' TEM")
    assert dv("12ABC34501DE") == "35", "a regra nao fecha"
    print("     12.ABC.345/01DE-35  ->  DV calculado 35   CONFERE")
    print("     Os pesos e o modulo 11 NAO mudaram. So' a conversao caractere->valor.")

    # ── dado REAL via Shaper ─────────────────────────────────────────────
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj", volume=N, seed=11,
                                    stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    reais = [mascara(str(x["cnpj"])) for x in rows][:N]
    assert all(dv(so_alnum(s)[:12]) == so_alnum(s)[12:] for s in reais),         "CNPJ real invalido sob a regra nova"
    assert all(len(s) == 18 for s in reais), "mascara aplicada duas vezes"
    print(f"\n[1] RETROCOMPATIBILIDADE: {len(reais):,} CNPJ reais, 100% validos sob a regra NOVA")

    # ── alfanumerico: realista e pior caso ───────────────────────────────
    rng = random.Random(2026)

    def alfa_realista(n: int) -> list[str]:
        """Preserva a estrutura que o split explora: raiz por empresa + ordem '0001'
        dominante (matriz), como no cadastro real."""
        out = []
        for _ in range(n):
            raiz = "".join(rng.choice(ALFA) for _ in range(8))
            ordem = "0001" if rng.random() < 0.90 else f"{rng.randint(2, 25):04d}"
            corpo = raiz + ordem
            out.append(mascara(corpo + dv(corpo)))
        return out

    def alfa_caos(n: int) -> list[str]:
        out = []
        for _ in range(n):
            corpo = "".join(rng.choice(ALFA) for _ in range(12))
            out.append(mascara(corpo + dv(corpo)))
        return out

    # gera UMA VEZ e reusa — o §3 tem de medir a MESMA coluna do §2, nao outra
    COLUNAS = {
        "a-numerico-real": reais,
        "b-alfa-realista": alfa_realista(N),
        "c-alfa-caos": alfa_caos(N),
    }

    print("\n[2] O QUE O FLOOR ESCOLHE — o discriminador do header")
    print("     (logo apos '#TCF.8M': '%'=split · '@'=dict · '!'=raw · ausente=core)")
    res = [
        mede("a-numerico-real", "CNPJ numerico REAL (Shaper/receita-cnpj)",
             COLUNAS["a-numerico-real"]),
        mede("b-alfa-realista", "alfanumerico c/ raiz + ordem 0001 dominante",
             COLUNAS["b-alfa-realista"]),
        mede("c-alfa-caos", "alfanumerico uniforme (PIOR CASO declarado)",
             COLUNAS["c-alfa-caos"]),
    ]

    # ── o conserto candidato: decomposicao POSICIONAL ────────────────────
    print("\n[3] O CONSERTO — a mascara e' FIXA, entao a posicao nao depende do caractere")
    extra = []
    for cid in ("a-numerico-real", "b-alfa-realista", "c-alfa-caos"):
        col = COLUNAS[cid]                     # a MESMA coluna medida no §2
        # as 18 posicoes do valor FORMATADO — inclusive os separadores. Assim o wire
        # se auto-descreve e a comparacao com o `%` (que guarda o template) e' justa:
        # nada e' recomposto por conhecimento fora do arquivo.
        L = len(col[0])
        assert all(len(s) == L for s in col)
        posicional = {f"p{k:02d}": [s[k] for s in col] for k in range(L)}
        w = encode(posicional)
        volta = decode(w)
        remontado = ["".join(volta[f"p{k:02d}"][i] for k in range(L)) for i in range(N)]
        assert remontado == col, f"{cid}: remontagem posicional falhou"
        b = len(w.encode("utf-8"))
        base = next(x["bytes"] for x in res if x["caso"] == cid)
        raw = len("\n".join(col).encode("utf-8"))
        grava(f"d-posicional-{cid}.tcf", w)
        grava(f"d-posicional-{cid}.roundtrip.json",
              json.dumps([mascara(s) for s in remontado][:40], ensure_ascii=False, indent=1))
        grava(f"d-posicional-{cid}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        print(f"  posicional/{cid:<16} {b:>8,} B  vs raw {(b/raw-1)*100:>+7.2f}%   "
              f"vs coluna unica {(b/base-1)*100:>+7.2f}%")
        extra.append({"caso": f"d-posicional-{cid}", "bytes": b, "raw": raw,
                      "vs_raw_pct": round((b / raw - 1) * 100, 2),
                      "vs_coluna_unica_pct": round((b / base - 1) * 100, 2), "rt": True})

    # ── a MESMA causa, outro documento: a placa Mercosul ─────────────────
    print("\n[4] MESMA CAUSA — placa Mercosul (LLLNLNN) contra a antiga (LLLNNNN)")
    print("     Nao ha' corpus real de placa (busca em Z:/tcf-data: nenhum dataset tem a")
    print("     coluna). Sintetico serve aqui porque a pergunta e' do GATE, que e' logico.")
    L, D = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789"
    rp = random.Random(7)

    def placa_antiga(n):        # LLL NNNN
        return [f"{''.join(rp.choice(L) for _ in range(3))}"
                f"{''.join(rp.choice(D) for _ in range(4))}" for _ in range(n)]

    def placa_mercosul(n):      # LLL N L NN — a letra na 5a posicao e' a mudanca
        return [f"{''.join(rp.choice(L) for _ in range(3))}{rp.choice(D)}"
                f"{rp.choice(L)}{''.join(rp.choice(D) for _ in range(2))}"
                for _ in range(n)]

    placas = []
    for cid, col in (("e-placa-antiga", placa_antiga(N)),
                     ("f-placa-mercosul", placa_mercosul(N)),
                     ("g-placa-frota-mista", placa_antiga(N // 2) + placa_mercosul(N // 2))):
        w = encode({"placa": col})
        assert decode(w)["placa"] == col, f"{cid}: RT quebrou"
        b, raw = len(w.encode("utf-8")), len("\n".join(col).encode("utf-8"))
        d = w[7] if len(w) > 7 else "?"
        mec = {"!": "raw", "@": "dict", "%": "split"}.get(d, "core")
        pos = {f"p{k}": [s[k] for s in col] for k in range(7)}
        wp = encode(pos)
        vp = decode(wp)
        assert ["".join(vp[f"p{k}"][i] for k in range(7)) for i in range(len(col))] == col
        bp = len(wp.encode("utf-8"))
        grava(f"{cid}.tcf", w)
        grava(f"{cid}.roundtrip.json", json.dumps(decode(w)["placa"][:40], ensure_ascii=False, indent=1))
        grava(f"{cid}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        grava(f"d-posicional-{cid}.tcf", wp)
        grava(f"d-posicional-{cid}.roundtrip.json",
              json.dumps(["".join(vp[f"p{k}"][i] for k in range(7)) for i in range(40)],
                         ensure_ascii=False, indent=1))
        grava(f"d-posicional-{cid}.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
        print(f"  {cid:<22} {b:>8,} B  vs raw {(b/raw-1)*100:>+7.2f}%  mec={mec:<6}"
              f"   posicional {bp:,} B ({(bp/raw-1)*100:+.2f}% vs raw)")
        placas.append({"caso": cid, "bytes": b, "raw": raw, "mecanismo": mec,
                       "vs_raw_pct": round((b / raw - 1) * 100, 2),
                       "posicional_bytes": bp,
                       "posicional_vs_raw_pct": round((bp / raw - 1) * 100, 2), "rt": True})
    print("  A placa NAO tem separador na forma armazenada, entao o split nem se aplica —")
    print("  o gate exige >=2 grupos de digitos separados por nao-digito. E a Mercosul poe")
    print("  uma LETRA no meio dos digitos: a mesma colisao do CNPJ alfanumerico.")

    # ── veredito ─────────────────────────────────────────────────────────
    print("\n" + "=" * 104)
    print("VEREDITO")
    print("=" * 104)
    a, b_, c = res
    print(f"  G1 hoje, no REAL       : mecanismo '{a['mecanismo']}' · {a['vs_raw_pct']:+.2f}% vs raw")
    print(f"  G2 alfanum. realista   : mecanismo '{b_['mecanismo']}' · {b_['vs_raw_pct']:+.2f}% vs raw")
    print(f"  G3 alfanum. pior caso  : mecanismo '{c['mecanismo']}' · {c['vs_raw_pct']:+.2f}% vs raw")
    print(f"  G4 conserto posicional : " + " · ".join(
        f"{x['caso'].split('-',2)[-1]} {x['vs_raw_pct']:+.2f}% vs raw" for x in extra))
    print(f"  G5 integridade         : roundtrip OK em {len(res)+len(extra)}/{len(res)+len(extra)}"
          f" — o alfanumerico NAO corrompe, so' deixa de ganhar")

    (AQUI / "resultado.json").write_text(
        json.dumps({"casos": res, "conserto": extra, "placas": placas,
                    "regra": {"conversao": "ASCII - 48", "exemplo": "12.ABC.345/01DE-35 -> DV 35",
                              "pesos_inalterados": True,
                              "retrocompat_verificada_em": len(reais)}},
                   ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {p.resolve() for p in list(OUT.rglob("*")) + list(IN.rglob("*")) if p.is_file()}
    assert not (_arquivos - achados), f"EVIDENCIA FALTANDO: {_arquivos - achados}"
    assert not (achados - _arquivos), f"EVIDENCIA ORFA: {achados - _arquivos}"
    print(f"\n-> {len(achados)} arquivos (inputs + outputs), portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
