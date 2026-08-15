# -*- coding: utf-8 -*-
"""FLOAT e HORA nas vertentes que o fechamento NÃO passou — latência, memória,
velocidade, compressão-de-transporte, multi-col e view.

    python run.py

## A cobrança (owner, 2026-08-14)

> *"o .8 preza tanto pela funcionalidade, fechar gaps e possibilidades extras de comprimir
> tipos, ver se o wire interno fecha tudo, desde o spec até após a saída de forma geral…
> lembrando também da vertente de latência, memória, velocidade, compressão etc."*

## O gap que este lab fecha

Os fechamentos de float (`…-1616`) e hora (`…-2230`) passaram os **5 eixos estruturais**
(dispatch, candidatos, API, wire, RT). **Nenhum fechamento de tipo — nem int, nem data — passou
as vertentes de execução**: quanto custa fatiar (latência), quanto custa rodar (CPU/memória),
e quanto o ganho sobrevive ao recompressor (terminal × transporte). Este lab as mede para
float e hora, com int e string como réguas.

## As 6 vertentes medidas

| vertente | pergunta | método |
|---|---|---|
| **A multi-col** | o tipo fecha no `.8M` como fecha no single? | encode dict de 3 colunas + RT |
| **B view** | a saída lazy abre o tipo? | `view()` no single e no multi |
| **C latência** | quanto custa fatiar em p pedaços? | a régua do lab de data (`1740`), agora p/ float e hora |
| **D granularidade** | quantos pontos de entrega o wire pronto tem? | análise estrutural do corpo (linhas × classe do candidato) |
| **E velocidade+memória** | µs/valor e pico de alocação | `perf_counter` + `tracemalloc` — **dev-run declarado** |
| **F transporte** | o ganho sobrevive ao gzip? | wire × gzip(wire) × gzip(JSON) |

## Ressalva de honestidade sobre a vertente E

É **dev-run** em máquina não quiescente — o mesmo status que o `bench_perf` chama de
não-probatório. Valem as **razões entre tipos** (mesmo n, mesma máquina, mesmo instante),
não os absolutos.
"""
from __future__ import annotations

import gzip
import json
import pathlib
import shutil
import sqlite3
import sys
import time
import tracemalloc

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode, view  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def GZ(t):
    return len(gzip.compress(t.encode("utf-8"), 9))


def _hh(seg):
    return f"{seg//3600:02d}:{(seg%3600)//60:02d}:{seg%60:02d}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas = []

    # ── as colunas: float e hora + as réguas int e string ────────────────────
    N = 2000
    x = 99991
    horas = []
    for _ in range(N):
        x = (x * 1103515245 + 12345) % 2147483648
        horas.append(_hh(8 * 3600 + x % (10 * 3600)))
    COLS = {
        "float-sint": [round(1.0 + (i % 97) * 0.25, 2) for i in range(N)],
        "hora-sint": horas,
        "int-regua": [1000 + (i % 97) for i in range(N)],
        "str-regua": [f"item-{i % 97:03d}" for i in range(N)],
    }
    try:
        con = sqlite3.connect("file:Z:/tcf-data/interim/wine-quality.db?mode=ro", uri=True)
        v = [r[0] for r in con.execute("SELECT density FROM wine WHERE density IS NOT NULL")]
        con.close()
        passo = max(1, len(v) // N)
        COLS["float-real"] = v[::passo][:N]
        con = sqlite3.connect("file:Z:/tcf-data/interim/online-retail.db?mode=ro", uri=True)
        v = [str(r[0]).split(" ")[1] for r in con.execute(
            "SELECT InvoiceDate FROM online_retail WHERE InvoiceDate LIKE '% %'")]
        con.close()
        passo = max(1, len(v) // N)
        COLS["hora-real"] = v[::passo][:N]
    except Exception:
        print("(sem Z: — só sintéticos)")
    for nome, vals in COLS.items():
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json", {
            "gerador": "run.py" if "real" not in nome else "Z:/tcf-data (passo espalhado)",
            "n": len(vals), "pin": "sintético determinístico (LCG/módulo), sem random"
                                   if "real" not in nome else "corpus Z: — não versionado"})

    # ── A) TABELA: onde float e hora caem quando entram numa tabela ──────────
    #
    # DESCOBERTA DA 1ª RODADA (eu rotulava isto de ".8M" — errado): o dispatch é
    # type-coherent — dict de SÓ strings sai `#TCF.8M`; dict com QUALQUER tipo (float,
    # int, bool) sai `#TCF.8H`. O `.8M` é a rota flat de strings; a tabela TIPADA é `.8H`.
    print("A) TABELA — float e hora dentro de um dict (dispatch type-coherent)")
    tab = {"f": COLS["float-sint"], "h": COLS["hora-sint"], "s": COLS["str-regua"]}
    wm = encode(tab)
    back = decode(wm)
    ok = back == tab
    if not ok:
        falhas.append("tabela tipada: RT não fechou")
    _esc(OUT / "tabela-tipada.tcf", wm)
    _js(OUT / "tabela-tipada.roundtrip.json", back)
    tab_s = {"a": COLS["str-regua"], "b": [str(v) for v in COLS["int-regua"]]}
    wms = encode(tab_s)
    a_reg = {"header_tipado": wm.split("\n")[0][:60], "rota_tipada": "8H",
             "bytes": B(wm), "rt_com_tipo": ok,
             "header_so_strings": wms.split("\n")[0][:40],
             "rota_so_strings": "8M" if wms.startswith("#TCF.8M") else "?",
             "soma_singles": sum(B(encode(c)) for c in tab.values())}
    print(f"  dict TIPADO  -> {wm.split(chr(10))[0][:40]!r}  ({B(wm)} B, RT c/ tipo={ok})")
    print(f"  dict strings -> {wms.split(chr(10))[0][:40]!r}")

    # ── B) VIEW: a ponta lazy abre o que a API emite para tipos? ─────────────
    print("\nB) VIEW — a ponta de leitura lazy")
    from tcf.multi.core import _encode_multi
    b_reg = {}
    ensaios = [("single-float (#TCF.8n…)", encode(COLS["float-sint"])),
               ("single-hora (#TCF.8…)", encode(COLS["hora-sint"])),
               ("tabela tipada (.8H)", wm),
               ("tabela só-strings (.8M)", wms)]
    for rot, wire in ensaios:
        try:
            vw = view(wire)
            nr = vw.nrows() if callable(vw.nrows) else vw.nrows
            b_reg[rot] = f"abre (nrows={nr})"
        except ValueError as e:
            b_reg[rot] = f"NAO ABRE: ValueError: {str(e)[:56]}"
        print(f"  view({rot}): {b_reg[rot]}")
    # e o único caminho "lazy p/ float" que existiria: o .8M interno — perde o tipo
    w_int = _encode_multi({"f": COLS["float-sint"][:50]})
    volta_int = decode(w_int)["f"]
    b_reg["_8M_interno_com_float"] = {
        "decode_devolve": repr(volta_int[0]),
        "tipo_preservado": isinstance(volta_int[0], float),
        "nota": "a rota interna aceita float mas devolve STRING — o tipo nao viaja no .8M"}
    print(f"  (.8M interno c/ float: decode devolve {volta_int[0]!r} — tipo perdido)")

    # ── C) LATÊNCIA: a régua de fatias (o lab 1740, agora p/ float e hora) ──
    print("\nC) LATÊNCIA — o custo de fatiar em p pedaços (wire somado, p wires independentes)")
    print(f"  {'coluna':>12} {'p=1':>8} {'p=2':>8} {'p=4':>8} {'p=8':>8} {'mult p=8':>9}")
    c_reg = {}
    for nome in ("float-sint", "float-real", "hora-sint", "hora-real",
                 "int-regua", "str-regua"):
        if nome not in COLS:
            continue
        vals = COLS[nome]
        linha = {}
        for p in (1, 2, 4, 8):
            tam = len(vals) // p
            fat = [vals[i * tam:(i + 1) * tam] for i in range(p)]
            wires = [encode(f) for f in fat]
            for wi, f in zip(wires, fat):
                if decode(wi) != f:
                    falhas.append(f"{nome} p={p}: RT da fatia falhou")
            linha[f"p{p}"] = sum(map(B, wires))
            if p == 8:
                _esc(OUT / f"{nome}.fatia8-exemplo.tcf", wires[0])
        linha["mult_p8"] = round(linha["p8"] / linha["p1"], 2)
        c_reg[nome] = linha
        print(f"  {nome:>12} {linha['p1']:>8} {linha['p2']:>8} {linha['p4']:>8} "
              f"{linha['p8']:>8} {linha['mult_p8']:>8}x")

    # ── D) GRANULARIDADE: pontos de entrega do wire pronto ──────────────────
    print("\nD) GRANULARIDADE — a estrutura do corpo (classe do vencedor x linhas)")
    d_reg = {}
    for nome, vals in COLS.items():
        w = encode(vals)
        corpo = [l for l in w.split("\n")[1:] if l]
        disc = w.split("\n")[0][6:]
        # 1ª rodada tinha um bug aqui: o disc TIPADO (`nB77d0`) não casava com
        # startswith("B") e o bN saía rotulado "linha-a-linha". A classe certa do bN
        # modo B: domínio streamável linha-a-linha + payload em UM bloco base64.
        eh_bn = "B" in disc[:2] and any(l.startswith("=") for l in corpo)
        if eh_bn:
            dom = sum(1 for l in corpo if not l.startswith("="))
            classe = f"bN-B: dominio streamavel ({dom} linhas) + payload em 1 bloco"
        else:
            classe = f"linha-a-linha ({len(corpo)} linhas = ate' {len(corpo)} pontos)"
        d_reg[nome] = {"disc": disc or "(vazio)", "linhas_corpo": len(corpo),
                       "classe": classe}
        print(f"  {nome:>12} disc={disc or '(vazio)':>8} linhas={len(corpo):>5}  {classe}")

    # ── E) VELOCIDADE + MEMÓRIA (dev-run declarado) ─────────────────────────
    print("\nE) VELOCIDADE + MEMÓRIA — dev-run: valem as RAZÕES, não os absolutos")
    print(f"  {'coluna':>12} {'enc µs/val':>11} {'dec µs/val':>11} {'pico enc KB':>12}")
    e_reg = {}
    for nome, vals in COLS.items():
        w = encode(vals)                     # aquece
        t0 = time.perf_counter()
        for _ in range(3):
            w = encode(vals)
        enc_us = (time.perf_counter() - t0) / 3 / len(vals) * 1e6
        t0 = time.perf_counter()
        for _ in range(3):
            r = decode(w)
        dec_us = (time.perf_counter() - t0) / 3 / len(vals) * 1e6
        if r != vals:
            falhas.append(f"{nome}: RT na medição E")
        tracemalloc.start()
        encode(vals)
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        e_reg[nome] = {"enc_us_por_valor": round(enc_us, 2),
                       "dec_us_por_valor": round(dec_us, 2),
                       "pico_encode_KB": round(pico / 1024, 1),
                       "AVISO": "dev-run, maquina nao quiescente — razoes, nao absolutos"}
        print(f"  {nome:>12} {enc_us:>11.2f} {dec_us:>11.2f} {pico/1024:>12.1f}")

    # ── F) TRANSPORTE: o ganho sobrevive ao gzip? ───────────────────────────
    print("\nF) TERMINAL × TRANSPORTE — wire × gzip(wire) × gzip(JSON)")
    print(f"  {'coluna':>12} {'json':>8} {'wire':>8} {'term%':>7} "
          f"{'gz(json)':>9} {'gz(wire)':>9} {'transp%':>8}")
    f_reg = {}
    for nome, vals in COLS.items():
        j = json.dumps(vals, ensure_ascii=False)
        w = encode(vals)
        term = round(100 * (1 - B(w) / B(j)), 1)
        transp = round(100 * (1 - GZ(w) / GZ(j)), 1)
        f_reg[nome] = {"json_B": B(j), "wire_B": B(w), "terminal_pct": term,
                       "gzip_json_B": GZ(j), "gzip_wire_B": GZ(w),
                       "transporte_pct": transp}
        print(f"  {nome:>12} {B(j):>8} {B(w):>8} {term:>6.1f}% "
              f"{GZ(j):>9} {GZ(w):>9} {transp:>7.1f}%")

    reg = {"A_multicol": a_reg, "B_view": b_reg, "C_latencia_fatias": c_reg,
           "D_granularidade": d_reg, "E_perf_devrun": e_reg, "F_transporte": f_reg}
    _js(INT / "vertentes.json", reg)
    _js(RAIZ / "resultado.json", {"vertentes": reg, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — float e hora nas vertentes restantes", "",
         "| vertente | o que mediu | onde |", "|---|---|---|",
         "| A | multi-col fecha? | `multi-3cols.tcf` + roundtrip |",
         "| B | view abre? | `../intermediates/vertentes.json` |",
         "| C | custo de fatiar (latência) | `<col>.fatia8-exemplo.tcf` |",
         "| D | pontos de entrega | `../intermediates/vertentes.json` |",
         "| E | µs/valor + pico KB (dev-run) | idem |",
         "| F | terminal × transporte | idem |", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
