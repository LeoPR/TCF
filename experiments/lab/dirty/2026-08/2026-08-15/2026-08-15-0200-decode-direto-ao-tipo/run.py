# -*- coding: utf-8 -*-
"""DECODE DIRETO AO TIPO — a proposta do owner, medida.

    python run.py

## A proposta (owner, 2026-08-15)

> *"no decode, ele sai de string e vai passar por uma função de date/datetime de qualquer
> forma. Fazer isso num formato para depois o dev pegar esse resultado e passar novamente para
> um segundo formato… é mais barato se fizer isso já na primeira vez e economiza o processo:*
>
> *o que acontece hoje:  `datetime comprimido` → decode → date-padrão → date que o cliente quer*
> *o que proponho:       `datetime comprimido` → decode(alguns formatos) → date que o cliente quer*
>
> *Obviamente o tcf não é pra ficar importando várias libs caras — use o barato/nativo. Mas a
> ideia é padronizar antes; não quero que ele vire um datatransform portátil. Se o tcf for
> feito em outra linguagem, cuidado pra não inflar o núcleo com tratamento de data demais."*

## O fato de código que sustenta a proposta

O decode do `data_iso` **constrói o objeto e o joga fora**:

    data_iso.py:107   return _FROM_ORD(int(payload)).isoformat()
                             └────── objeto `date` ──────┘└─ serializa ─┘

O cliente então re-parseia a string que saiu. A proposta corta as duas pontas: para de
serializar, e o cliente para de re-parsear.

## O precedente que JÁ faz isso (a resposta a "o encode já tem algo assim?")

**A rota tipada.** `decoder.py::_cast_tipo` — *"os literais do core viram o tipo TIPADO"* —
já transforma string→`int`/`float`/`bool` DENTRO do decode, hoje, soldado. O que se mede aqui
é estender a mesma lógica aos specs de grafia (date/datetime), opt-in.

## As três rotas medidas

| rota | o que faz | quem paga o quê |
|---|---|---|
| **hoje** | `decode → str` e o cliente re-parseia | isoformat (dentro) + fromisoformat (cliente) |
| **direta** | `decode_value` devolve o **objeto** | só fromordinal — nada se serializa |
| *(baseline)* | `decode → str`, cliente NÃO converte | para calibrar o custo do decode em si |

## O que fica FORA (a linha vermelha do owner)

O parâmetro escolheria o **TIPO** de saída (o objeto da lib nativa), nunca uma **GRAFIA**
arbitrária. `ordinal → "31/01/2026"` seria transformação nova — o "datatransform portátil"
que o owner não quer. Isso não se mede porque não se propõe.

## GATE

Protótipo em lab, `src/tcf` intocado. O spec-objeto usa um `wire_id` próprio (`dtobj`/`dmobj`)
**só como veículo do protótipo** — num weld real a saída seria kwarg da API do host
(`decode(w, nature=SPEC, saida="date")`), com o wire IDÊNTICO ao de hoje. O wire não muda nada.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import shutil
import sys
import time

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode                                     # noqa: E402
from tcf.natures import MARKER_LITERAL                             # noqa: E402
from tcf.natures.data_iso import DataIsoSpec                       # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── os specs do protótipo ────────────────────────────────────────────────────
class DataIsoStr(DataIsoSpec):
    """O `data_iso` com id de protótipo — a rota de HOJE, isolada para comparação justa."""
    name: str = "data-iso-str-proto"
    wire_id: str = "dtobj"

    def __init__(self):
        object.__setattr__(self, "name", "data-iso-str-proto")
        object.__setattr__(self, "wire_id", "dtobj")


class DataIsoObjeto(DataIsoStr):
    """A rota DIRETA: o decode devolve o OBJETO `date` — nada se serializa.

    O literal (`_...`) continua string: a saída é a UNIÃO `date|str|None` — o mesmo
    CONTRATO UNIÃO que o ADR-0039 já decidiu para o lazy bool (`[bool|None|str]`).
    """

    def decode_value(self, payload):
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        return _dt.date.fromordinal(int(payload))


def cronometra(fn, rep=5):
    fn()                                       # aquece
    melhor = None
    for _ in range(rep):
        t0 = time.perf_counter()
        fn()
        dt_ = time.perf_counter() - t0
        melhor = dt_ if melhor is None else min(melhor, dt_)
    return melhor


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, reg = [], []

    base = _dt.date(2024, 1, 1)
    CASOS = [
        ("diaria-200", [(base + _dt.timedelta(days=i)).isoformat() for i in range(200)],
         "200 diárias — o caso pequeno"),
        ("diaria-2000", [(base + _dt.timedelta(days=i)).isoformat() for i in range(2000)],
         "2000 diárias — o caso do gabarito"),
        ("diaria-com-literal",
         [(base + _dt.timedelta(days=i)).isoformat() for i in range(500)],
         "1 não-canônica no meio → a saída vira UNIÃO date|str (contrato ADR-0039)"),
    ]
    CASOS[2][1][250] = "2024-9-7"              # a não-canônica

    spec_str, spec_obj = DataIsoStr(), DataIsoObjeto()

    print(f"{'caso':>20} {'wire':>7} {'rt-str':>7} {'volta-obj':>10} "
          f"{'hoje ns/val':>12} {'direta ns/val':>14} {'economia':>9}")
    for nome, vals, ideia in CASOS:
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "run.py", "ideia": ideia, "n": len(vals),
             "pin": "sintético determinístico (progressão diária)"})
        w = encode(vals, nature=spec_str)
        if ":dtobj" not in w.split("\n")[0]:
            falhas.append(f"{nome}: o spec não venceu o FLOOR — o teste não vale")
            continue
        _esc(OUT / f"{nome}.tcf", w)

        # rota de HOJE: decode → str, e o cliente re-parseia
        saida_str = decode(w, nature=spec_str)
        rt = saida_str == vals
        if not rt:
            falhas.append(f"{nome}: RT string quebrou")
        _js(OUT / f"{nome}.roundtrip.json", saida_str)

        def rota_hoje():
            out = decode(w, nature=spec_str)
            return [_dt.date.fromisoformat(s) if len(s) == 10 and s[4] == "-" else s
                    for s in out]

        # rota DIRETA: decode devolve objetos
        def rota_direta():
            return decode(w, nature=spec_obj)

        saida_obj = rota_direta()
        tipos = sorted({type(x).__name__ for x in saida_obj})
        volta_ok = all((x.isoformat() if isinstance(x, _dt.date) else x) == s
                       for x, s in zip(saida_obj, vals))
        if not volta_ok:
            falhas.append(f"{nome}: a volta do objeto não bate a entrada")
        _js(OUT / f"{nome}.saida-objeto.json",
            [x.isoformat() if isinstance(x, _dt.date) else x for x in saida_obj])

        t_hoje = cronometra(rota_hoje) / len(vals) * 1e9
        t_dir = cronometra(rota_direta) / len(vals) * 1e9
        t_base = cronometra(lambda: decode(w, nature=spec_str)) / len(vals) * 1e9
        eco = 100 * (1 - t_dir / t_hoje)
        linha = {"caso": nome, "ideia": ideia, "n": len(vals), "wire_bytes": B(w),
                 "header": w.split("\n")[0], "rt_string": rt,
                 "tipos_na_saida_objeto": tipos, "volta_objeto_ok": volta_ok,
                 "ns_por_valor_rota_hoje": round(t_hoje, 1),
                 "ns_por_valor_rota_direta": round(t_dir, 1),
                 "ns_por_valor_decode_puro": round(t_base, 1),
                 "economia_pct": round(eco, 1),
                 "AVISO": "dev-run, maquina nao quiescente — razoes, nao absolutos",
                 "CONSTANTE_na_comparacao": "o MESMO wire e a MESMA saida final (objetos "
                                            "date); so' muda ONDE a conversao acontece"}
        reg.append(linha)
        _js(OUT / f"{nome}.meta.json", linha)
        print(f"{nome:>20} {B(w):>7} {str(rt):>7} {str(volta_ok):>10} "
              f"{t_hoje:>12.0f} {t_dir:>14.0f} {eco:>8.1f}%")

    # o contrato união, mostrado
    caso3 = next(r for r in reg if r["caso"] == "diaria-com-literal")
    print(f"\n  união na saída do caso com literal: {caso3['tipos_na_saida_objeto']}"
          f"  (precedente: CONTRATO UNIÃO do ADR-0039, lazy bool)")

    _js(INT / "medicoes.json", reg)
    _js(RAIZ / "resultado.json", {"medicoes": reg, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — decode direto ao tipo", "",
         "| caso | wire | RT str | volta obj | hoje ns/val | direta ns/val | economia |",
         "|---|---|---|---|---|---|---|"] +
        [f"| [`{r['caso']}`](./{r['caso']}.tcf) | {r['wire_bytes']} | {r['rt_string']} | "
         f"{r['volta_objeto_ok']} | {r['ns_por_valor_rota_hoje']} | "
         f"{r['ns_por_valor_rota_direta']} | **{r['economia_pct']}%** |" for r in reg] +
        ["", "A saída-objeto de cada caso está em `<caso>.saida-objeto.json` (re-serializada",
         "para o diff; os tipos reais estão em `meta.json`).", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
