# -*- coding: utf-8 -*-
"""FECHAMENTO do tipo HORA — os 5 eixos + os sintéticos + a ciclicidade medida.

    python run.py

## O critério (o mesmo do float)

> Owner: *"seria interessante fechar todos os tipos primeiro até pra ver se o fluxo de spec
> está padronizado e cada um tem suas peculiaridades declaradas, quanto mais coisa em comum
> melhor."*

**Um tipo não fecha porque compensa — fecha porque foi verificado.** A hora já foi avaliada em
2026-08-14 (1,03× no único dado real; hora pura não existe no corpus). O que faltava, e o owner
nomeou: **os sintéticos** (*"campos com hora existem"*) e **os 5 eixos de conformidade**.

## Onde a hora difere estruturalmente da data

O ordinal do `data-iso` é **absoluto e monotônico** — dias desde a época, cresce sem voltar. A
hora é **cíclica**: volta a zero toda meia-noite. Este lab **mede** o que isso custa, em vez de
só declarar: o mesmo batimento por 1 dia e por 2 dias, e a mesma sequência como ordinal cíclico
e como ordinal absoluto.

## O que este lab NÃO faz

Não propõe spec nem weld, não toca `src/tcf/`. Verifica conformidade e **declara as
peculiaridades**.
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

from tcf import decode, encode                                    # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_DATA_ISO                   # noqa: E402
from tcf.side_outputs import SideOutputs                          # noqa: E402
import casos as C                                                 # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def igual_estrito(a, b) -> bool:
    """RT de hora: ela chega como STRING, então tipo E valor, sem normalização."""
    if a is None or len(a) != len(b):
        return False
    return all(type(x) is type(y) and x == y for x, y in zip(a, b))


# ── OS 5 EIXOS (os mesmos do fechamento do float) ────────────────────────────
def eixos(vals):
    """1 dispatch · 2 candidatos · 3 API · 4 wire · 5 RT."""
    w = encode(vals)
    l0 = w.split("\n")[0]
    r = {"bytes": B(w), "wire_header": l0,
         # EIXO 1+4 — dispatch e wire: hora chega como STRING, então NÃO tem tag
         "eixo1_dispatch": ("string (sem tag) — a hora não é tipo nativo do Python no wire"
                            if l0 == "#TCF.8" else f"disc={l0[6:]!r}"),
         "eixo4_wire_disc": l0[6:] or "(vazio — string default)"}

    # EIXO 3 — API: `nature=` e `min_len=` são aceitos, recusados ou silenciosos?
    for rot, spec in (("cpf", SPEC_CPF), ("data_iso", SPEC_DATA_ISO)):
        try:
            so = SideOutputs()
            w2 = encode(vals, nature=spec, side_outputs=so)
            r[f"eixo3_nature_{rot}"] = (
                "processado, FLOOR recusou" if w2 == w and so.nature_apply
                else "ACEITO e aplicado" if w2 != w
                else "sem efeito e SEM AVISO")
            if so.nature_apply:
                st = so.nature_apply.get("val", so.nature_apply)
                r[f"eixo3_nature_{rot}_status"] = st.get("by_status") if isinstance(st, dict) else None
        except Exception as e:
            r[f"eixo3_nature_{rot}"] = f"recusa fail-loud: {type(e).__name__}"
    try:
        encode(vals, min_len=6)
        r["eixo3_min_len"] = "aceito"
    except Exception as e:
        r["eixo3_min_len"] = f"recusa fail-loud: {type(e).__name__}"

    # EIXO 2 — candidatos: quais o núcleo constrói? (lido pelo discriminador emitido)
    r["eixo2_candidato_vencedor"] = {
        "": "core/OBAT literal", "!": "polaridade", "!!": "polaridade dupla",
    }.get(l0[6:], f"outro: {l0[6:]!r}")

    # EIXO 5 — RT
    volta = decode(w)
    r["eixo5_rt"] = igual_estrito(volta, vals)
    return r, w, volta


def roda(nome, vals, ideia, fonte, falhas):
    _js(INP / f"{nome}.entrada.json", vals)
    _js(INP / f"{nome}.fonte.json", fonte)
    try:
        r, w, volta = eixos(vals)
    except Exception as e:
        r = {"recusa": f"{type(e).__name__}: {str(e)[:80]}"}
        _js(OUT / f"{nome}.meta.json", {"input": f"inputs/{nome}.entrada.json",
                                        "ideia": ideia, "recusa": r["recusa"]})
        print(f"  {nome:32s} RECUSA {r['recusa'][:46]}")
        return {"caso": nome, "ideia": ideia, **r}
    if not r["eixo5_rt"]:
        falhas.append(f"{nome}: RT não fechou")
    _esc(OUT / f"{nome}.tcf", w)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    _js(OUT / f"{nome}.meta.json", {
        "input": f"inputs/{nome}.entrada.json", "ideia": ideia, "fonte": fonte,
        "n": len(vals), "chars_entrada": sum(len(str(v)) for v in vals if v is not None),
        "bytes": r["bytes"], "header": r["wire_header"], "rt": r["eixo5_rt"]})
    print(f"  {nome:32s} n={len(vals):>4} {r['bytes']:>6} B  disc={r['eixo4_wire_disc']:>16} "
          f"nature(cpf)={r.get('eixo3_nature_cpf','?')[:24]:>24} RT={r['eixo5_rt']}")
    return {"caso": nome, "ideia": ideia, "n": len(vals), **r}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, reg = [], []

    print("SINTÉTICOS por REGIME — o que o corpus não tem (pedido do owner)")
    for nome, vals, ideia, par in C.SINTETICOS:
        reg.append(roda(nome, vals, ideia,
                        {"gerador": "casos.py::SINTETICOS", "params": {"par": par},
                         "seed": "LCG determinístico (sem random)", "ideia": ideia,
                         "pin": "sintético viesado por construção"}, falhas))

    print("\nBORDAS — a norma permite, o Python aceita, o formato preserva?")
    for nome, vals, ideia in C.BORDAS:
        reg.append(roda(nome, vals, ideia,
                        {"gerador": "casos.py::BORDAS", "ideia": ideia,
                         "pin": "grafias de norma (ISO 8601 / RFC 3339)"}, falhas))

    print("\nREAL — a única hora do corpus (dentro de um datetime)")
    horas = C.carrega_hora_real()
    if horas:
        reg.append(roda("real-retail-hora", horas,
                        "a parte de hora do `online-retail.InvoiceDate`",
                        {"gerador": "casos.py::carrega_hora_real", "db": "online-retail",
                         "coluna": "InvoiceDate (parte de hora)",
                         "ideia": "a única hora do corpus", "pin": "Z: não versionado"},
                        falhas))
    else:
        print("  (sem Z: — pulado)")

    # ── A CICLICIDADE, MEDIDA (a peculiaridade declarada, agora com número) ──
    print("\nA CICLICIDADE — o mesmo batimento, cíclico contra absoluto")
    cic = []
    for dias, n in ((1, 96), (2, 192), (3, 288), (7, 672)):
        ciclico = C.batimento(900, n, ciclico=True)      # volta a zero à meia-noite
        absoluto = C.batimento(900, n, ciclico=False)    # cresce sem voltar (inválido como hora)
        wc, wa = encode(ciclico), encode(absoluto)
        assert decode(wc) == ciclico and decode(wa) == absoluto
        _esc(OUT / f"ciclicidade-{dias}dias.ciclico.tcf", wc)
        _esc(OUT / f"ciclicidade-{dias}dias.absoluto.tcf", wa)
        _js(OUT / f"ciclicidade-{dias}dias.ciclico.roundtrip.json", decode(wc))
        linha = {"dias": dias, "n": n, "bytes_ciclico": B(wc), "bytes_absoluto": B(wa),
                 "custo_da_ciclicidade_B": B(wc) - B(wa),
                 "custo_pct": round(100 * (B(wc) - B(wa)) / B(wa), 1),
                 "disc_ciclico": wc.split("\n")[0][6:] or "(vazio)",
                 "disc_absoluto": wa.split("\n")[0][6:] or "(vazio)",
                 "CONSTANTE_na_comparacao": "o MESMO passo (900 s) e o MESMO n; só muda se a "
                                            "sequência VOLTA à meia-noite"}
        cic.append(linha)
        print(f"  {dias} dia(s), n={n:>3}: cíclico={B(wc):>6} B  absoluto={B(wa):>6} B  "
              f"custo={B(wc)-B(wa):>+6} B ({linha['custo_pct']:>+6.1f}%)")

    # o ordinal: hora como segundos-desde-meia-noite (o desenho irmão do data-iso)
    print("\n  o ORDINAL (segundos desde meia-noite) — o desenho irmão do `data-iso`")
    ord_cic = []
    for dias, n in ((1, 96), (2, 192), (7, 672)):
        hs = C.batimento(900, n, ciclico=True)
        segs = [str(int(h[:2]) * 3600 + int(h[3:5]) * 60 + int(h[6:8])) for h in hs]
        w_txt, w_ord = encode(hs), encode(segs)
        assert decode(w_ord) == segs
        _esc(OUT / f"ordinal-{dias}dias.tcf", w_ord)
        _js(OUT / f"ordinal-{dias}dias.roundtrip.json", decode(w_ord))
        ord_cic.append({"dias": dias, "n": n, "bytes_texto": B(w_txt),
                        "bytes_ordinal": B(w_ord),
                        "ganho_pct": round(100 * (1 - B(w_ord) / B(w_txt)), 1),
                        "disc_ordinal": w_ord.split("\n")[0][6:] or "(vazio)"})
        print(f"    {dias} dia(s): texto={B(w_txt):>6} B  ordinal={B(w_ord):>6} B  "
              f"ganho={100*(1-B(w_ord)/B(w_txt)):>5.1f}%  disc={w_ord.split(chr(10))[0][6:]!r}")

    _js(INT / "eixos.json", reg)
    _js(INT / "ciclicidade.json", {"texto": cic, "ordinal": ord_cic})
    _js(RAIZ / "resultado.json", {"eixos": reg, "ciclicidade": cic, "ordinal": ord_cic,
                                  "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — fechamento da HORA", "",
         "| caso | ideia | bytes | disc | RT |", "|---|---|---|---|---|"] +
        [f"| [`{x['caso']}`](./{x['caso']}.tcf) | {x['ideia'][:66]} | "
         f"{x.get('bytes', '—')} | `{x.get('eixo4_wire_disc', '—')}` | {x.get('eixo5_rt', '—')} |"
         for x in reg] +
        ["", "Ciclicidade em `ciclicidade-*dias.{ciclico,absoluto}.tcf`;",
         "ordinal em `ordinal-*dias.tcf`.", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:12]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
