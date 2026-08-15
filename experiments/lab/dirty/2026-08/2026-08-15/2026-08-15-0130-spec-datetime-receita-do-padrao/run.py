# -*- coding: utf-8 -*-
"""SPEC de datetime — a receita do padrão, e qual payload emitir.

    python run.py

## O pedido (owner, 2026-08-15)

> *"o datetime pode entrar no mesmo esquema do date e do time… pré-formatados ou padronizados
> para entrar no tcf, aí formatos variantes podem ser tratados como string… só seguir a receita
> de padrão. Isso ajuda a focar num estilo de compressão que é melhor pro datetime."*

## As três perguntas deste lab

1. **Qual payload?** Um spec mapeia um valor a UM payload — não pode splitar. Três candidatos:
   `ordinal` (dia·86400+seg), `epoch` (desde 1970) e `par` (`dia:seg`, dois grupos).
2. **Qual separador canônico?** `" "` (SQL, e o do corpus) ou `"T"` (ISO/JSON). A outra vira
   `length_wrong` → literal. O lab mede o custo da escolha errada.
3. **O spec ganha do núcleo, e onde perde?** Sob o FLOOR (nunca-pior), em 8 regimes.

## O que NÃO se testa aqui

Robustez a grafia misturada. A decisão do owner é explícita: a coluna vem **pré-formatada** de
um banco; mistura seria corrupção de transmissão, não regime. O lab tem **um** caso de grafia
estrangeira, e só para verificar que ela cai em literal sem quebrar o RT.

## GATE

Protótipo em lab. `src/tcf` intocado — o spec é uma classe local que o `encode(nature=)` aceita
por duck-typing.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ.parent / "2026-08-15-0020-datetime-grafias-regimes-mecanismos"))

from tcf import decode, encode                                     # noqa: E402
from tcf.side_outputs import SideOutputs                           # noqa: E402
import casos as C                                                  # noqa: E402
from spec_datetime import VARIANTES, DatetimeIsoSpec               # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 2000


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def com_spec(vals, spec):
    """encode com a nature + o RT pela porta pública, e a telemetria."""
    so = SideOutputs()
    w = encode(vals, nature=spec, side_outputs=so)
    volta = decode(w, nature=spec)
    st = (so.nature_apply or {}).get("val", so.nature_apply) or {}
    return w, volta == vals, {
        "bytes": B(w), "header": w.split("\n")[0],
        "apply_rate": st.get("apply_rate"), "by_status": st.get("by_status"),
        "used": st.get("used")}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas = []

    # ── BLOCO 1 — qual PAYLOAD? (separador fixo no do corpus) ───────────────
    print("BLOCO 1 — qual PAYLOAD emitir (separador fixo = espaço, o do corpus)")
    print(f"  {'regime':>26} {'k':>5} {'núcleo':>8} {'ordinal':>9} {'epoch':>8} "
          f"{'par':>8} {'melhor':>10} {'ganho':>8}")
    b1, specs_esp = [], [(p, DatetimeIsoSpec(sep=" ", payload=p))
                         for p in ("ordinal", "epoch", "par")]
    for nome, fn, ideia, par in C.REGIMES:
        vals = [C.g_sql_espaco(d) for d in fn(N)]
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "casos.py (lab …-0020) :: REGIMES x g_sql_espaco",
             "regime": nome, "grafia": "YYYY-MM-DD HH:MM:SS (canônica candidata)",
             "n": N, "par": par, "ideia": ideia,
             "seed": "LCG determinístico, sem random",
             "pin": "sintético; coluna PRÉ-FORMATADA, como um banco emite"})
        base = encode(vals)
        assert decode(base) == vals
        _esc(OUT / f"{nome}.nucleo.tcf", base)
        _js(OUT / f"{nome}.nucleo.roundtrip.json", decode(base))
        linha = {"regime": nome, "ideia": ideia, "n": N, "distintos": len(set(vals)),
                 "nucleo": B(base),
                 "CONSTANTE_na_comparacao": "a MESMA coluna e o MESMO encode; só muda o PAYLOAD"}
        for rot, spec in specs_esp:
            w, rt, info = com_spec(vals, spec)
            if not rt:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            linha[rot] = info["bytes"]
            linha[f"{rot}_apply"] = info["apply_rate"]
            linha[f"{rot}_hdr"] = info["header"]
            _esc(OUT / f"{nome}.spec-{rot}.tcf", w)
            _js(OUT / f"{nome}.spec-{rot}.roundtrip.json", decode(w, nature=spec))
        cands = {r: linha[r] for r, _ in specs_esp}
        melhor = min(cands, key=cands.get)
        linha["melhor_payload"] = melhor
        linha["ganho_vs_nucleo_pct"] = round(100 * (1 - cands[melhor] / linha["nucleo"]), 1)
        b1.append(linha)
        print(f"  {nome:>26} {linha['distintos']:>5} {linha['nucleo']:>8} "
              f"{linha['ordinal']:>9} {linha['epoch']:>8} {linha['par']:>8} "
              f"{melhor:>10} {linha['ganho_vs_nucleo_pct']:>7.1f}%")

    # ── BLOCO 2 — qual SEPARADOR canônico, e o custo de errar ──────────────
    print("\nBLOCO 2 — o custo de escolher o separador ERRADO (spec vê a outra grafia)")
    print(f"  {'coluna emitida por':>22} {'spec espaço':>12} {'spec T':>10} "
          f"{'apply(esp)':>11} {'apply(T)':>9}")
    b2 = []
    for rot_g, gfn in (("espaço (SQL)", C.g_sql_espaco), ("T (ISO/JSON)", C.g_iso_t)):
        vals = [gfn(d) for d in C.r_comercial(N)]
        nome = f"grafia-{'espaco' if 'SQL' in rot_g else 'T'}"
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "casos.py :: r_comercial", "grafia_emitida": rot_g, "n": N,
             "ideia": "medir o custo de o spec ser configurado no separador ERRADO",
             "pin": "sintético"})
        linha = {"grafia_emitida": rot_g, "nucleo": B(encode(vals))}
        for rot_s, sep in (("espaco", " "), ("T", "T")):
            spec = DatetimeIsoSpec(sep=sep, payload="ordinal")
            w, rt, info = com_spec(vals, spec)
            if not rt:
                falhas.append(f"{nome}/spec-{rot_s}: RT não fechou")
            linha[f"spec_{rot_s}"] = info["bytes"]
            linha[f"apply_{rot_s}"] = info["apply_rate"]
            linha[f"status_{rot_s}"] = info["by_status"]
            _esc(OUT / f"{nome}.spec-{rot_s}.tcf", w)
            _js(OUT / f"{nome}.spec-{rot_s}.roundtrip.json", decode(w, nature=spec))
        b2.append(linha)
        print(f"  {rot_g:>22} {linha['spec_espaco']:>12} {linha['spec_T']:>10} "
              f"{str(linha['apply_espaco']):>11} {str(linha['apply_T']):>9}")

    # ── BLOCO 3 — as BORDAS de canonicidade (a receita protege?) ───────────
    print("\nBLOCO 3 — bordas: a receita recusa o que deve, sem quebrar o RT?")
    spec = DatetimeIsoSpec(sep=" ", payload="ordinal")
    BORDAS = [
        ("b-canonica", ["2026-03-02 08:26:00", "2026-03-02 08:27:00"],
         "a grafia canônica — deve comprimir"),
        ("b-com-T", ["2026-03-02T08:26:00", "2026-03-02T08:27:00"],
         "a irmã com `T` — 19 chars, passa a largura e morre na RE-EMISSÃO"),
        ("b-sem-segundo", ["2026-03-02 08:26", "2026-03-02 08:27"],
         "16 chars — morre no gate de largura"),
        ("b-com-fracao", ["2026-03-02 08:26:00.500000"], "26 chars — largura"),
        ("b-com-timezone", ["2026-03-02 08:26:00+00:00"], "25 chars — largura"),
        ("b-compacta", ["20260302082600"], "14 chars — largura"),
        ("b-epoch", ["1772439960"], "10 chars — largura"),
        ("b-br", ["02/03/2026 08:26:00"], "**19 chars** — passa a largura, morre no PARSE"),
        ("b-mes-invalido", ["2026-13-02 08:26:00"], "19 chars — parse inválido"),
        ("b-24h", ["2026-03-02 24:00:00"], "ISO permite, Python recusa"),
        ("b-nao-canonica", ["2026-03-02 08:26:00 "], "espaço à direita — 20 chars"),
        ("b-com-nulo", ["2026-03-02 08:26:00", None, "2026-03-02 08:27:00"],
         "o slot nulo atravessa"),
        ("b-mista", ["2026-03-02 08:26:00", "02/03/2026 08:27:00"],
         "**corrupção de transmissão** (o owner: seria raro) — metade cai em literal"),
    ]
    b3 = []
    for nome, vals, ideia in BORDAS:
        _js(INP / f"{nome}.entrada.json", vals)
        try:
            w, rt, info = com_spec(vals, spec)
            if not rt:
                falhas.append(f"{nome}: RT não fechou com o spec")
            _esc(OUT / f"{nome}.tcf", w)
            _js(OUT / f"{nome}.roundtrip.json", decode(w, nature=spec))
            st = info["by_status"] or {}
            linha = {"borda": nome, "ideia": ideia, "bytes": info["bytes"],
                     "apply_rate": info["apply_rate"], "by_status": st, "rt": rt,
                     "header": info["header"]}
            print(f"  {nome:>16} apply={str(info['apply_rate']):>5} "
                  f"status={str(dict(st))[:44]:<46} RT={rt}")
        except Exception as e:
            linha = {"borda": nome, "ideia": ideia,
                     "recusa": f"{type(e).__name__}: {str(e)[:60]}"}
            print(f"  {nome:>16} RECUSA {type(e).__name__}: {str(e)[:44]}")
        b3.append(linha)

    _js(INT / "bloco1-payloads.json", b1)
    _js(INT / "bloco2-separador.json", b2)
    _js(INT / "bloco3-bordas.json", b3)
    _js(RAIZ / "resultado.json", {"payloads": b1, "separador": b2, "bordas": b3,
                                  "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — spec de datetime", "",
         "| regime | k | núcleo | ordinal | epoch | par | melhor | ganho |",
         "|---|---|---|---|---|---|---|---|"] +
        [f"| [`{x['regime']}`](./{x['regime']}.nucleo.tcf) | {x['distintos']} | {x['nucleo']} | "
         f"{x['ordinal']} | {x['epoch']} | {x['par']} | **{x['melhor_payload']}** | "
         f"{x['ganho_vs_nucleo_pct']}% |" for x in b1] +
        ["", "Bordas em `b-*.tcf`; separador em `grafia-*.spec-*.tcf`.", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:15]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
