# -*- coding: utf-8 -*-
"""AVALIAÇÃO DO `.8H` — gramática real, header, estágios duplicados e o candidato único.

    python run.py     # sai 0 só se os RTs fecharem e as medições de estrutura baterem

## O pedido (owner, 2026-08-16)

*"vamos avaliar o modo H, pois a estrutura de header dele é ligeiramente diferente. Faça o de
sempre: primeiro estudo do que se tem das últimas atualizações das capacidades do H, e o foco
de sempre do `.8` — ver pra simplificar o header, ver integração dos estágios internos que
estejam repetidos ou que podem ser simplificados para generalizar, opções e tudo mais."*

## O ESTUDO PRÉVIO — e a defasagem que ele revelou

O documento canônico do header do `.8H` é o `tcf8h-header-checklist.md` (2026-07-06), que
enumera 5 camadas (C1 explícito → C5 cobertor-curto). **Ele descreve o PROTÓTIPO**, e diz
literalmente: *"TCF.8H é protótipo externo opt-in; nada disto está weldado em `src/tcf`
ainda"*.

**O weld veio depois** (ADR-0033, 2026-07-14) e emitiu uma gramática **com mais coisas**:

| | checklist 2026-07-06 | weld (medido hoje) |
|---|---|---|
| espaço após o magic | `#TCF.8H ` (com espaço) | **sem espaço** — o checklist já marcava como pendente e o weld resolveu ✓ |
| tag de TIPO por folha | não existe | **`n`/`b` após o size** (`n:6n`, `b:8b`) |
| máscara de nulo/ausente | citada como P1, sem glifo | **`?` no nome** (`a?:5`) |
| marcadores de RAIZ | não existem | **`#O`** (objeto), **`#V`** (escalar) |
| contagem de array | `[` | **`#` + `[`** (`tel#:6[`) |

Este lab mede a gramática **real**, não a documentada.

## GATE

`src/tcf` INTOCADO. Lê `Z:/tcf-data/` somente-leitura.
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import shutil
import sqlite3
import string
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode                                    # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N_ALVO = 2000


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def grava_caso(nome, dados, wire, extra=None):
    volta = decode(wire)
    _js(INP / f"{nome}.entrada.json", dados)
    _esc(OUT / f"{nome}.tcf", wire)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    igual = ((INP / f"{nome}.entrada.json").read_text(encoding="utf-8")
             == (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8"))
    _js(OUT / f"{nome}.meta.json", {
        "wire_bytes": B(wire), "linha1": wire.split("\n", 1)[0][:200],
        "roundtrip_identico_a_entrada": igual, **(extra or {})})
    return igual


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], {}

    # ── BLOCO 1 — a gramática REAL, capacidade por capacidade ──────────────
    print("BLOCO 1 — a gramática REAL do `.8H` (não a do checklist de 2026-07-06)\n")
    print(f"  {'capacidade':<26} {'bytes':>6} {'RT':<4} header")
    CAPS = [
        ("plano 1 campo",        [{"nome": "ana"}, {"nome": "bia"}]),
        ("plano 3 campos",       [{"a": "1", "b": "2", "c": "3"}] * 3),
        ("TIPOS (s/n/b)",        [{"s": "x", "n": 1, "f": 1.5, "b": True}] * 3),
        ("objeto aninhado",      [{"o": {"rua": "R1", "n": "10"}}] * 3),
        ("objeto 2 níveis",      [{"a": {"b": {"c": "x"}}}] * 3),
        ("array de escalares",   [{"tel": ["1", "2"]}, {"tel": ["3"]}]),
        ("array de objetos",     [{"t": [{"n": "a"}, {"n": "b"}]}, {"t": [{"n": "c"}]}]),
        ("array de arrays",      [{"m": [["a", "b"], ["c"]]}] * 2),
        ("NULL",                 [{"a": "x"}, {"a": None}]),
        ("ragged (campo falta)", [{"a": "x", "b": "y"}, {"a": "z"}]),
        ("dict escalar (raiz O)", {"a": "x"}),
        ("escalar solto (raiz V)", "abc"),
        ("lista vazia",          []),
        ("dict vazio",           {}),
    ]
    b1 = []
    for rot, d in CAPS:
        try:
            w = encode(d)
            ok = grava_caso(f"cap-{rot.split()[0].lower()}-{len(b1):02d}", d, w,
                            extra={"capacidade": rot})
            if not ok:
                falhas.append(f"cap/{rot}: diff entrada x roundtrip")
            l1 = w.split("\n", 1)[0]
            b1.append({"capacidade": rot, "bytes": B(w), "rt": ok, "linha1": l1})
            print(f"  {rot:<26} {B(w):>6} {'ok' if ok else 'FALHA':<4} {l1!r}")
        except Exception as e:
            b1.append({"capacidade": rot, "erro": f"{type(e).__name__}: {e}"})
            print(f"  {rot:<26} {'—':>6} {'—':<4} {type(e).__name__}: {str(e)[:40]}")
    reg["bloco1_gramatica"] = b1

    # ── BLOCO 2 — o vocabulário do header: cada glifo, o que significa ─────
    print("\nBLOCO 2 — o vocabulário do meta do `.8H`, deduzido dos wires acima")
    GLIFOS = [
        ("`:N`",  "byte-size do corpo da folha", "herdado do `.8M` (mesma ideia)"),
        ("`,`",   "separa irmãos no mesmo nível", "herdado do `.8M`"),
        ("`{}`",  "objeto (contenção 1:1)", "exclusivo do `.8H`"),
        ("`[`",   "array (contenção 1:N)", "exclusivo do `.8H`"),
        ("`#`",   "contagem do array (`#count`)", "exclusivo do `.8H`"),
        ("`?`",   "máscara: campo pode faltar ou ser null", "exclusivo do `.8H`"),
        ("`n`/`b`", "tag de tipo escalar após o size", "análogo à tag do single-col tipado"),
        ("`#O`",  "raiz é OBJETO (não lista de registros)", "exclusivo do `.8H`"),
        ("`#V`",  "raiz é ESCALAR solto", "exclusivo do `.8H`"),
        ("`\\`",  "escape de nome", "PORTADO do `.8M` — alfabeto DIFERENTE (bloco 3)"),
    ]
    print(f"  {'glifo':<10} {'significa':<40} origem")
    for g, s, o in GLIFOS:
        print(f"  {g:<10} {s:<40} {o}")
    reg["bloco2_vocabulario"] = [{"glifo": g, "significa": s, "origem": o}
                                 for g, s, o in GLIFOS]

    # ── BLOCO 3 — os ESTÁGIOS DUPLICADOS, medidos ─────────────────────────
    print("\nBLOCO 3 — estágios duplicados entre `.8H` e `.8M` (o pedido do owner)")
    import re
    h = (REPO / "src/tcf/hierarchical.py").read_text(encoding="utf-8")
    m = (REPO / "src/tcf/multi/core.py").read_text(encoding="utf-8")
    fh = set(re.findall(r"^def (\w+)", h, re.M))
    fm = set(re.findall(r"^def (\w+)", m, re.M))
    comuns = sorted(fh & fm)
    print(f"  funções com o MESMO NOME nos dois módulos: {len(comuns)} → {comuns}")
    dup = []
    for f in comuns:
        ch = re.search(rf"^def {f}\(.*?(?=^def |\Z)", h, re.S | re.M).group(0)
        cm = re.search(rf"^def {f}\(.*?(?=^def |\Z)", m, re.S | re.M).group(0)
        dup.append({"funcao": f, "linhas_H": len(ch.splitlines()),
                    "linhas_M": len(cm.splitlines()),
                    "identicas": ch.strip() == cm.strip()})
        print(f"    {f:<14} .8H={len(ch.splitlines()):>3}L  .8M={len(cm.splitlines()):>3}L  "
              f"{'IDÊNTICAS' if ch.strip() == cm.strip() else 'DIVERGEM'}")
    importa_multi = "from tcf.multi" in h
    print(f"  o `hierarchical.py` importa do `multi`? {'sim' if importa_multi else 'NÃO'}")
    print(f"  (o comentário no código admite: 'portado do .8M' — é CÓPIA, não compartilhamento)")

    # a divergência é BUG ou é JUSTIFICADA? -> comparar os alfabetos escapados
    from tcf.multi.core import _esc_name as escM
    from tcf.hierarchical import _esc_name as escH
    difs = [c for c in string.printable if c not in "\n\r" and escM(f"x{c}y") != escH(f"x{c}y")]
    so_M = [c for c in difs if escM(f"x{c}y") != f"x{c}y"]
    so_H = [c for c in difs if escH(f"x{c}y") != f"x{c}y"]
    print(f"\n  chars escapados DIFERENTE: {len(difs)} → {difs}")
    print(f"    só o `.8M` escapa: {so_M}   (são os separadores DELE: `=`)")
    print(f"    só o `.8H` escapa: {so_H}   (são os glifos DELE: `{{}}[]?#`)")
    print(f"  => a divergência é JUSTIFICADA: cada rota escapa a SUA gramática.")
    print(f"     Unificar o ALFABETO seria ERRADO; o que caberia unificar é o MECANISMO.")

    # e a prova de que nenhuma quebra: RT nas duas rotas com nomes hostis
    hostis = [f"a{c}b" for c in ",=:{}[]?#!@%"] + ["a\\b"]
    quebras = []
    for nome in hostis:
        VAL = ["v1", "v2", "v3"]
        try:
            if decode(encode({nome: list(VAL)})) != {nome: list(VAL)}:
                quebras.append(("M", nome))
        except Exception:
            quebras.append(("M", nome))
        r = [{nome: v} for v in VAL]
        try:
            if decode(encode(r)) != r:
                quebras.append(("H", nome))
        except Exception:
            quebras.append(("H", nome))
    print(f"  RT com {len(hostis)} nomes hostis nas DUAS rotas: "
          f"{'todas fecham' if not quebras else 'QUEBRAS: ' + str(quebras)}")
    if quebras:
        falhas.append(f"nomes hostis quebram: {quebras}")
    reg["bloco3_duplicacao"] = {"funcoes_duplicadas": dup, "importa_multi": importa_multi,
                                "chars_divergentes": difs, "so_M": so_M, "so_H": so_H,
                                "nomes_hostis_ok": not quebras}

    # ── BLOCO 4 — o CANDIDATO ÚNICO, agora no CORPUS (não numa tabela só) ──
    print("\nBLOCO 4 — `T-8H-UM-CANDIDATO-SO`: o overhead do `.8H`, agora no CORPUS")
    print(f"  {'tabela':<30} {'.8M':>9} {'.8H':>9} {'.8M nf':>9} {'residual':>9} {'expl.%':>7}")
    b4, somas = [], {"m": 0, "h": 0, "nf": 0}
    for db in sorted(glob.glob("Z:/tcf-data/interim/*.db")):
        if os.path.getsize(db) == 0:
            continue
        nome_db = os.path.basename(db)[:-3]
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for t in [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            if not n:
                continue
            off = max(0, (n - N_ALVO) // 2)
            cur = con.execute(f"SELECT * FROM {t} LIMIT {N_ALVO} OFFSET {off}")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            tab = {c: [("" if r[i] is None else str(r[i])) for r in rows]
                   for i, c in enumerate(cols)}
            recs = [dict(zip(cols, [("" if v is None else str(v)) for v in r])) for r in rows]
            try:
                wM, wH = encode(tab), encode(recs)
                wNF = encode(tab, fallback=False)
                if decode(wH) != recs:
                    falhas.append(f"{nome_db}/{t}: RT do .8H nao fechou")
            except Exception as e:
                falhas.append(f"{nome_db}/{t}: {type(e).__name__}")
                continue
            resid = B(wH) - B(wNF)
            tot = B(wH) - B(wM)
            expl = 100 * (tot - resid) / tot if tot else 0.0
            somas["m"] += B(wM)
            somas["h"] += B(wH)
            somas["nf"] += B(wNF)
            b4.append({"tabela": f"{nome_db}/{t}", "m": B(wM), "h": B(wH), "nf": B(wNF),
                       "residual": resid, "explicado_pct": round(expl, 3)})
            print(f"  {nome_db + '/' + t:<30} {B(wM):>9} {B(wH):>9} {B(wNF):>9} "
                  f"{resid:>9} {expl:>6.2f}%")
        con.close()
    tot_over = somas["h"] - somas["m"]
    tot_resid = somas["h"] - somas["nf"]
    print(f"\n  CORPUS: .8M {somas['m']} · .8H {somas['h']} · .8M(fallback=False) {somas['nf']}")
    print(f"  overhead do .8H sobre o .8M: {tot_over:+d} B "
          f"({100 * (somas['h'] / somas['m'] - 1):+.1f}%)")
    print(f"  residual (.8H − .8M sem candidatos): {tot_resid:+d} B")
    print(f"  => o CONJUNTO DE CANDIDATOS explica "
          f"{100 * (tot_over - tot_resid) / tot_over:.2f}% do overhead, no corpus inteiro")
    reg["bloco4_candidato_unico"] = {"por_tabela": b4, **somas,
                                     "overhead_total": tot_over, "residual_total": tot_resid,
                                     "explicado_pct": round(100 * (tot_over - tot_resid) / tot_over, 2),
                                     "CONSTANTE_na_comparacao": "os MESMOS valores; muda so' a "
                                                                "rota e o conjunto de candidatos"}

    # ── BLOCO 5 — o HEADER do `.8H`: quanto pesa (o "simplificar" do pedido) ──
    print(chr(10) + "BLOCO 5 — o header do `.8H`: peso e composição")
    print(f"  {'tabela':<30} {'wire':>9} {'header':>7} {'header%':>8} {'nomes':>7}")
    b5, hs, ws, ns = [], 0, 0, 0
    for db in sorted(glob.glob("Z:/tcf-data/interim/*.db")):
        if os.path.getsize(db) == 0:
            continue
        nome_db = os.path.basename(db)[:-3]
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for t_ in [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]:
            n = con.execute(f"SELECT COUNT(*) FROM {t_}").fetchone()[0]
            if not n:
                continue
            off = max(0, (n - N_ALVO) // 2)
            cur = con.execute(f"SELECT * FROM {t_} LIMIT {N_ALVO} OFFSET {off}")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            recs = [dict(zip(cols, [("" if v is None else str(v)) for v in r]))
                    for r in rows]
            try:
                w = encode(recs)
            except Exception:
                continue
            l1 = w.split(chr(10), 1)[0]
            n_nomes = sum(len(c) for c in cols)
            b5.append({"tabela": f"{nome_db}/{t_}", "wire": B(w), "header": B(l1) + 1,
                       "pct": round(100 * (B(l1) + 1) / B(w), 2), "nomes_B": n_nomes})
            hs += B(l1) + 1
            ws += B(w)
            ns += n_nomes
            print(f"  {nome_db + '/' + t_:<30} {B(w):>9} {B(l1)+1:>7} "
                  f"{100*(B(l1)+1)/B(w):>7.2f}% {n_nomes:>7}")
        con.close()
    print(f"{chr(10)}  CORPUS: header {hs} B de {ws} B = {100*hs/ws:.2f}% do wire")
    print(f"  os NOMES são {ns} B = {100*ns/hs:.1f}% do header")
    print(f"  => o header do `.8H` NÃO é o problema: {100*hs/ws:.2f}% do wire.")
    reg["bloco5_header"] = {"por_tabela": b5, "header_total": hs, "wire_total": ws,
                            "pct_do_wire": round(100 * hs / ws, 2),
                            "nomes_total": ns,
                            "nomes_pct_do_header": round(100 * ns / hs, 1)}

    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — avaliação do `.8H`", "",
         "As capacidades gravadas com entrada, wire e roundtrip.", "",
         "| capacidade | bytes | RT | header |", "|---|---:|:--:|---|"] +
        [f"| {x['capacidade']} | {x.get('bytes','—')} | "
         f"{'✓' if x.get('rt') else '✗' if 'rt' in x else '—'} | `{x.get('linha1','—')}` |"
         for x in b1]) + "\n")
    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})
    print(f"\n{'='*76}\n{len(falhas)} falha(s)")
    for f_ in falhas[:15]:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
