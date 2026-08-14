"""FECHAMENTO do tipo FLOAT — os 5 eixos + as peculiaridades. `python run.py`

## O critério (corrigido pelo owner em 2026-08-14)

> *"seria interessante fechar todos os tipos primeiro até pra ver se o fluxo de spec está
> padronizado e cada um tem suas peculiaridades declaradas, quanto mais coisa em comum
> melhor."*

**Um tipo não fecha porque compensa — fecha porque foi verificado.** Este lab não mede ganho
(já medido: 8% agregado em 30 colunas reais). Ele verifica os 5 eixos de conformidade e
**declara as peculiaridades** do float — o que ele tem de irredutivelmente diferente.

## O RT que vale para float

`==` **não basta**, e por duas razões distintas:

- `type()` — em Python `1 == 1.0` e `True == 1`; comparar valor mascara troca de tipo;
- **sinal do zero** — `-0.0 == 0.0` é `True`. Só `math.copysign` distingue. Um float que
  entra `-0.0` e volta `0.0` passaria num teste ingênuo.

Ambos estão no `igual_float` abaixo.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import shutil
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_CPF, int_pad_para  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def igual_float(a, b) -> bool:
    """RT de float: tipo E valor E **sinal do zero**. Ver docstring do módulo."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if type(x) is not type(y):
            return False
        if x is None:
            continue
        if isinstance(x, float) and x == 0.0 and y == 0.0:
            if math.copysign(1.0, x) != math.copysign(1.0, y):
                return False        # -0.0 virou 0.0 (ou vice-versa) — `==` nao pega
        elif x != y:
            return False
    return True


# ── EIXO 5 + peculiaridades: as BORDAS ────────────────────────────────────────
BORDAS = [
    ("float-exato", [3.0, 4.0, 5.0], "int em roupa de float — o `1.` do owner", True),
    ("zero-negativo", [-0.0, 0.0, 1.0], "`-0.0` != `0.0` no sinal; `==` NAO detecta", True),
    ("cientifica-pequena", [1e-5, 2e-5, 3e-5], "grafia `1e-05` vem do proprio Python", True),
    ("cientifica-grande", [1e20, 2e20, 3e20], "grafia `1e+20`", True),
    ("max-float", [1.7976931348623157e308, 1e308], "o maior float representavel", True),
    ("subnormal", [5e-324, 1e-323], "o menor subnormal — borda inferior do IEEE-754", True),
    ("precisao-suja", [0.1 + 0.2, 1 / 3, 2 / 3], "0.30000000000000004 — 17 digitos", True),
    ("misto-int-float", [1, 2.5, 3], "a UNIAO `int|float` na mesma tag `n`", True),
    ("com-nulo", [1.5, None, 2.5], "o slot 0 atravessa qualquer tag", True),
    ("nan", [float("nan"), 1.0], "fora do JSON (RFC 8259) -> FAIL-LOUD", False),
    ("infinito", [float("inf"), 1.0], "idem", False),
    ("menos-infinito", [float("-inf"), 1.0], "idem", False),
]


def eixos_conformidade(vals):
    """Eixos 1-4 para uma coluna float: dispatch, candidatos, API, wire."""
    w = encode(vals)
    l0 = w.split("\n")[0]
    out = {"wire_header": l0, "disc": l0[6:] if l0.startswith("#TCF.8") else "?",
           "bytes": B(w)}
    # EIXO 3 — API: nature= e min_len= sao aceitos? (a porta que o weld de hoje abriu)
    try:
        so = SideOutputs()
        w2 = encode(vals, nature=SPEC_CPF, side_outputs=so)
        out["api_nature"] = ("processado, FLOOR recusou" if w2 == w and so.nature_apply
                             else "ACEITO e aplicado" if w2 != w else "sem efeito e SEM AVISO")
    except Exception as e:
        out["api_nature"] = f"recusa fail-loud: {type(e).__name__}"
    try:
        w3 = encode(vals, min_len=8)
        out["api_min_len"] = "aceito" if isinstance(w3, str) else "?"
    except Exception as e:
        out["api_min_len"] = f"recusa fail-loud: {type(e).__name__}"
    # EIXO 2 — candidatos: o IntPadSpec serve? (a peculiaridade medida)
    out["int_pad_serve"] = int_pad_para(vals) is not None
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, linhas = [], []

    print("EIXO 5 + BORDAS — o que atravessa, o que e' recusado")
    for nome, vals, ideia, deve_passar in BORDAS:
        _js(INP / f"borda-{nome}.entrada.json", [None if v is None else
                                                 (repr(v) if isinstance(v, float) and
                                                  (math.isnan(v) or math.isinf(v)) else v)
                                                 for v in vals])
        try:
            w = encode(vals)
            back = decode(w)
            ok = igual_float(back, vals)
            estado = "RT ok" if ok else "RT DIVERGIU"
            if not deve_passar:
                falhas.append(f"borda {nome}: deveria ser RECUSADA e passou")
            elif not ok:
                falhas.append(f"borda {nome}: RT nao preservou (tipo/valor/sinal)")
            _esc(OUT / f"borda-{nome}.tcf", w)
            _js(OUT / f"borda-{nome}.roundtrip.json", back)
            corpo = w.split("\n")[1][:22] if "\n" in w else ""
            print(f"  {nome:20s} {estado:12s} {w.split(chr(10))[0]:11s} {corpo!r}")
            linhas.append({"borda": nome, "ideia": ideia, "resultado": estado,
                           "wire": w.split("\n")[0], "bytes": B(w)})
        except Exception as e:
            estado = f"RECUSA {type(e).__name__}"
            if deve_passar:
                falhas.append(f"borda {nome}: deveria PASSAR e foi recusada: {e}")
            print(f"  {nome:20s} {estado:12s} {str(e)[:44]}")
            linhas.append({"borda": nome, "ideia": ideia, "resultado": estado,
                           "mensagem": str(e)[:90]})

    # ── EIXOS 1-4 em colunas REAIS ────────────────────────────────────────────
    print("\nEIXOS 1-4 — dispatch, candidatos, API, wire (colunas REAIS)")
    REAIS = [
        ("wine.density", "wine-quality", "SELECT density FROM wine LIMIT 2000"),
        ("wine.alcohol", "wine-quality", "SELECT alcohol FROM wine LIMIT 2000"),
        ("tpch.l_discount", "tpch-sf001", "SELECT l_discount FROM lineitem LIMIT 2000"),
        ("tpch.l_quantity", "tpch-sf001", "SELECT l_quantity FROM lineitem LIMIT 2000"),
        ("retail.UnitPrice", "online-retail",
         "SELECT UnitPrice FROM online_retail WHERE UnitPrice IS NOT NULL LIMIT 2000"),
    ]
    eixos = {}
    for rot, db, sql in REAIS:
        try:
            con = sqlite3.connect(f"file:Z:/tcf-data/interim/{db}.db?mode=ro", uri=True)
            v = [r[0] for r in con.execute(sql)]
            con.close()
        except Exception:
            print(f"  {rot:20s} (sem Z: — pulado)")
            continue
        v = [x for x in v if x is not None]
        _js(INP / f"real-{rot.replace('.', '-')}.entrada.json", v)
        e = eixos_conformidade(v)
        back = decode(encode(v))
        e["rt_tipo_sinal"] = igual_float(back, v)
        if not e["rt_tipo_sinal"]:
            falhas.append(f"{rot}: RT nao preservou tipo/valor/sinal")
        eixos[rot] = e
        _esc(OUT / f"real-{rot.replace('.', '-')}.tcf", encode(v))
        _js(OUT / f"real-{rot.replace('.', '-')}.roundtrip.json", back)
        print(f"  {rot:20s} disc={e['disc']:6s} nature:{e['api_nature'][:26]:28s} "
              f"min_len:{e['api_min_len']:8s} IntPad={e['int_pad_serve']}  RT={e['rt_tipo_sinal']}")

    _js(INT / "bordas.json", linhas)
    _js(INT / "eixos-reais.json", eixos)
    _js(RAIZ / "resultado.json", {"bordas": linhas, "eixos": eixos, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — fechamento do float", "",
         "| borda | ideia | resultado |", "|---|---|---|"] +
        [f"| [`{x['borda']}`](./borda-{x['borda']}.tcf) | {x['ideia']} | {x['resultado']} |"
         for x in linhas] +
        ["", "Colunas reais em `real-*.tcf` com contra-prova `.roundtrip.json`.",
         "Eixos 1-4 medidos em `../intermediates/eixos-reais.json`.", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
