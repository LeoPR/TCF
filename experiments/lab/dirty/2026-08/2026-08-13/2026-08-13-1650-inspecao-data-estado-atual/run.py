"""Inspecao do tipo DATA — estado de 2026-08-13. `python run.py`

Lab de INSPECAO (pedido do owner): nao decide nada, MOSTRA o que as 4 modificacoes
acumuladas no tipo data fazem, com o wire aberto e explicado. Regenera `inputs/`,
`intermediates/`, `outputs/` e `result.md`.

    inputs/<c>.entrada.json         o que entrou (sintetico MATERIALIZADO tambem)
    inputs/<c>.fonte.json           procedencia: gerador, ideia, n/k, hash
    intermediates/<c>.anatomia.txt  o WIRE DECOMPOSTO e explicado  <- a peca de inspecao
    intermediates/<c>.trace.txt     telemetria do encode (SideOutputs)
    outputs/<c>.tcf                 o wire
    outputs/<c>.roundtrip.json      decode(wire) — DIFF contra a entrada = a contra-prova
    outputs/INDEX.md                nome -> ideia -> input -> wire -> bytes -> RT

`inputs/<c>.entrada.json` e `outputs/<c>.roundtrip.json` sao escritos com a MESMA
formatacao: a contra-prova e' `diff` dar vazio, e o run.py faz esse assert.

`src/tcf` NAO e' tocado — o lab so' chama a API publica.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
# parents: [0]=<dia> [1]=<mes> [2]=dirty [3]=lab [4]=experiments [5]=repo
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from anatomia import anatomia  # noqa: E402
from casos import CASOS  # noqa: E402
from tcf import decode, encode, view  # noqa: E402
from tcf.natures import SPEC_DATA_ISO as S  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def _h(v):
    return hashlib.sha256(json.dumps(v, **JSON_KW).encode()).hexdigest()[:12]


def _B(t):
    return len(t.encode("utf-8"))


def _limpa():
    """Artefato orfao e' indistinguivel de resultado atual — some antes de gerar."""
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def _trace(so, vals):
    L = [f"n={len(vals)}  k={len(set(map(str, vals)))}"]
    if so.nature_apply:
        st = so.nature_apply.get("val") or next(iter(so.nature_apply.values()))
        L.append(f"nature spec={st['spec']!r}  (o NAME legivel — ADR-0041: o wire leva `dt`)")
        L.append(f"  apply-rate: {st['compressible']}/{st['total']} = {st['apply_rate']:.1%}")
        L.append(f"  por status: {st['by_status']}")
        L.append(f"  venceu o FLOOR: {st.get('used')}")
    if so.cadence_info:
        L.append(f"cadence: {so.cadence_info}")
    if so.seq_rle_runs:
        L.append(f"seq_rle_runs ({len(so.seq_rle_runs)}): {so.seq_rle_runs[:3]}")
    if so.body_bytes is not None:
        L.append(f"body_bytes (candidato tcf da coluna): {so.body_bytes}")
    if so.multi_info:
        L.append(f"multi_info: { {k: v for k, v in so.multi_info.items() if 'nature' in k} }")
    if so.hcc_trace:
        L.append("\n-- hcc_trace --\n" + so.hcc_trace[:1500])
    if so.obat_log:
        L.append("\n-- obat_log --\n" + so.obat_log[:1200])
    return "\n".join(L)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    linhas, pulados, falhas = [], [], []

    for nome, familia, gen, ideia in CASOS:
        vals = gen()
        if vals is None:
            pulados.append(nome)
            continue

        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json", {
            "caso": nome, "familia": familia, "ideia": ideia,
            "n": len(vals), "k_unicos": len(set(map(str, vals))),
            "primeiros": vals[:5], "hash_entrada": _h(vals),
            "gerador": "casos.py", "corpus_real": familia == "real",
        })

        so = SideOutputs()
        wire = encode(vals, nature=S, side_outputs=so)
        wire_core = encode(vals)                      # o baseline que o FLOOR enfrentou
        volta = decode(wire)

        _esc(OUT / f"{nome}.tcf", wire)
        _js(OUT / f"{nome}.roundtrip.json", volta)
        _esc(INT / f"{nome}.anatomia.txt",
             anatomia(wire, titulo=f"{nome} — {ideia}") + "\n\n"
             + f"ENTRADA (5 primeiros): {vals[:5]}\n"
             + f"BASELINE do FLOOR (encode sem nature): {_B(wire_core)} B — "
               f"{'a nature VENCEU' if _B(wire) < _B(wire_core) else 'o CORE venceu (nature recusada)'}\n")
        _esc(INT / f"{nome}.trace.txt", _trace(so, vals))

        rt_ok = volta == vals
        arq_ok = (INP / f"{nome}.entrada.json").read_text(encoding="utf-8") == \
                 (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8")
        if not (rt_ok and arq_ok):
            falhas.append(f"{nome}: RT={rt_ok} arquivo-diffavel={arq_ok}")
        linhas.append({
            "caso": nome, "familia": familia, "ideia": ideia, "n": len(vals),
            "bytes_com_spec": _B(wire), "bytes_core": _B(wire_core),
            "spec_venceu": wire.startswith("#TCF.8 :dt"),
            "header": wire.split("\n", 1)[0][:40], "rt": rt_ok and arq_ok,
        })
        print(f"  {nome:26s} {_B(wire):7d} B (core {_B(wire_core):7d}) "
              f"{'spec' if wire.startswith('#TCF.8 :dt') else 'core'}  RT={'ok' if rt_ok else 'FALHOU'}")

    # ── D/E: estrutura e migracao (casos que nao sao "uma coluna") ──
    from casos import diaria, uteis
    extras = []

    # D1 multi-col + o fix do view (2026-08-12)
    datas = [d for d in diaria(400)]
    datas = [datas[i % 50] for i in range(400)]           # k=50 -> regime que emite modo dict
    tab = {"quando": datas, "valor": [str(i % 7) for i in range(400)]}
    w = encode(tab, nature_per_col={"quando": S})
    v = view(w)
    alvo = datas[0]
    onde = v.where("quando", alvo).count()
    grupos = list(view(w).group_count("quando"))[:3]
    _esc(OUT / "d1-multicol.tcf", w)
    _js(INP / "d1-multicol.entrada.json", tab)
    _js(OUT / "d1-multicol.roundtrip.json", decode(w))
    _esc(INT / "d1-multicol.anatomia.txt", anatomia(w, titulo="d1 — data em MULTI-COLUNA")
         + f"\n\nVIEW (lazy, sem materializar a tabela):\n"
           f"  where('quando', {alvo!r}).count() = {onde}   (verdade: {datas.count(alvo)})\n"
           f"  group_count('quando') -> primeiras chaves: {grupos}\n"
           f"  as chaves voltam como DATA, nao como ordinal — e' o fix de 2026-08-12\n")
    extras.append(("d1-multicol", "estrutura", "data em multi-col + o view lazy respondendo por VALOR",
                   _B(w), decode(w) == tab, onde == datas.count(alvo)
                   and all(str(g).startswith("20") for g in grupos)))

    # D2 hierarquico .8H
    recs = [{"quando": d, "n": str(i)} for i, d in enumerate(uteis(300))]
    w8 = encode(recs, nature_per_col={"quando": S})
    _esc(OUT / "d2-hierarquico.tcf", w8)
    _js(INP / "d2-hierarquico.entrada.json", recs)
    _js(OUT / "d2-hierarquico.roundtrip.json", decode(w8))
    _esc(INT / "d2-hierarquico.anatomia.txt", anatomia(w8, titulo="d2 — data em dataset .8H"))
    extras.append(("d2-hierarquico", "estrutura", "data como folha de dataset (.8H)",
                   _B(w8), decode(w8) == recs, True))

    # E1 migracao: o wire historico `:data-iso`
    import dataclasses
    wd = encode(uteis(600), nature=S)
    velho = wd.replace("#TCF.8 :dt\n", "#TCF.8 :data-iso\n", 1)
    _esc(OUT / "e1-wire-historico.tcf", velho)
    try:
        decode(velho)
        erro = "NAO FALHOU (era pra falhar)"
        ok_falha = False
    except ValueError as e:
        erro = str(e)
        ok_falha = True
    valvula = dataclasses.replace(S, wire_id="data-iso")
    lido = decode(velho, nature=valvula)
    _js(OUT / "e1-wire-historico.roundtrip.json", lido)
    _js(INP / "e1-wire-historico.entrada.json", uteis(600))
    _esc(INT / "e1-wire-historico.anatomia.txt",
         anatomia(velho, titulo="e1 — wire ANTIGO, gravado antes do rename de hoje")
         + f"\n\nDECODE SEM AJUDA (o que acontece hoje):\n  ValueError: {erro}\n"
           f"\nDECODE COM A VALVULA out-of-band:\n"
           f"  decode(w, nature=dataclasses.replace(SPEC_DATA_ISO, wire_id='data-iso'))\n"
           f"  -> {len(lido)} valores, iguais a' entrada: {lido == uteis(600)}\n"
           f"\nE' a decisao 3 do ADR-0041 (resolucao ESTRITA): o passado se le' pelo git,\n"
           f"nao por bagagem no codigo. Os 14 wires historicos do repo sao TODOS single-col,\n"
           f"logo TODOS alcancaveis por esta valvula.\n")
    extras.append(("e1-wire-historico", "migracao",
                   "wire gravado com `:data-iso` — falha alto e le' pela valvula",
                   _B(velho), lido == uteis(600), ok_falha))

    for nome, fam, ideia, b, rt, ok in extras:
        print(f"  {nome:26s} {b:7d} B  {fam:10s} RT={'ok' if rt else 'FALHOU'} check={'ok' if ok else 'FALHOU'}")
        if not (rt and ok):
            falhas.append(f"{nome}: rt={rt} check={ok}")

    # ── INDEX + result ──
    idx = ["# INDEX — o que cada arquivo e'", "",
           "| caso | ideia | input | wire | bytes (core) | quem venceu | RT |",
           "|---|---|---|---|---:|---|:--:|"]
    for r in linhas:
        idx.append(f"| `{r['caso']}` | {r['ideia']} | [entrada](../inputs/{r['caso']}.entrada.json) "
                   f"| [.tcf](./{r['caso']}.tcf) | {r['bytes_com_spec']} ({r['bytes_core']}) "
                   f"| {'spec `:dt`' if r['spec_venceu'] else 'core'} | {'ok' if r['rt'] else 'FALHOU'} |")
    for nome, fam, ideia, b, rt, ok in extras:
        idx.append(f"| `{nome}` | {ideia} | [entrada](../inputs/{nome}.entrada.json) "
                   f"| [.tcf](./{nome}.tcf) | {b} | {fam} | {'ok' if rt else 'FALHOU'} |")
    idx += ["", "A anatomia de cada wire (header e marcadores explicados) esta' em "
                "`../intermediates/<caso>.anatomia.txt`; a telemetria do encode em `<caso>.trace.txt`.",
            "", "**Contra-prova**: `outputs/<c>.roundtrip.json` e `inputs/<c>.entrada.json` sao "
                "gravados com a MESMA formatacao — `diff` entre os dois tem de dar VAZIO."]
    _esc(OUT / "INDEX.md", "\n".join(idx) + "\n")

    print()
    print(f"{len(linhas)} casos de coluna + {len(extras)} de estrutura; "
          f"{len(pulados)} pulados; {len(falhas)} falha(s)")
    if pulados:
        print(f"  pulados (fonte ausente): {', '.join(pulados)}")
    for f in falhas:
        print(f"  FALHA: {f}")
    _js(RAIZ / "resultado.json", {"casos": linhas, "extras": [
        {"caso": n, "familia": f, "ideia": i, "bytes": b, "rt": rt, "check": ok}
        for n, f, i, b, rt, ok in extras], "pulados": pulados, "falhas": falhas})
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
