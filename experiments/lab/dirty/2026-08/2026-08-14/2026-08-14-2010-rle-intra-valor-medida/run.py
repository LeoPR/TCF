# -*- coding: utf-8 -*-
"""RLE INTRA-VALOR — a primeira medição da H-INTRA (aberta desde 2026-06-16).

    python run.py

## A pergunta (uma só)

> O núcleo já aproveita repetição de caractere **dentro** de um valor? Se não, quanto sobra na
> mesa — e onde isso existe em dado real?

Ideia do owner (2026-08-14, reabrindo a dele mesmo de 2026-06-16):

> *"itens repetidos no meio do texto… `0.30000000000000004` poderia ser `0.3(14x0)4`… ou ainda
> pra aproveitar o fluxo: `14x0` / `\\0.3 <ref-01> 4` — um 'RLE fantasma' que descomprime só
> pra preencher dicionário, não coloca no conteúdo de fato."*

**Distinção que organiza tudo** (é a da `rle-familia-estudo.md`):

| | o quê | estado |
|---|---|---|
| **A** | RLE de LINHA (`*N\\|`, `*N+delta\\|`) | **soldado** |
| **B** | RLE no stream de índices do dict | caracterizado, closed |
| **C** | **RLE intra-valor** — substring dentro de UMA célula | **é este lab** |

## O que este lab NÃO faz

Não propõe weld, não toca `src/tcf/`, não implementa o mecanismo. Mede **o que existe hoje**,
**o teto** de um mecanismo idealizado (de graça, sem custo de marcador) e a **contra-prova** de
custo. O teto é limite superior, não promessa.

## As duas famílias que a varredura separou

Elas têm destinos OPOSTOS, e por isso o lab mede as duas:

- **padding de ID** (`Clerk#000000004`) — o run é prefixo compartilhado; o OBAT já o come. Aqui
  um RLE intra-valor deve **custar** bytes. É a contra-prova.
- **cauda de float** (`wine.alcohol`) — run no meio, sem afixo comum; sobrevive verbatim. É o
  único lugar onde pagaria.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
RUN = re.compile(r"(.)\1{3,}")          # >=4 caracteres identicos consecutivos


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def grava(nome, vals, ideia, fonte):
    """Encoda, valida o RT e grava o trio input/wire/roundtrip + meta."""
    _js(INP / f"{nome}.entrada.json", vals)
    _js(INP / f"{nome}.fonte.json", fonte)
    w = encode(vals)
    volta = decode(w)
    ok = volta == vals
    _esc(OUT / f"{nome}.tcf", w)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    _js(OUT / f"{nome}.meta.json", {
        "input": f"inputs/{nome}.entrada.json", "ideia": ideia, "fonte": fonte,
        "n": len(vals), "chars_entrada": sum(len(str(v)) for v in vals),
        "bytes_wire": B(w), "header": w.split("\n")[0], "roundtrip_ok": ok})
    return w, ok


def marcador_livre(graf):
    """Um char ASCII de 1 BYTE que NAO ocorre na coluna \u2014 a ideia da H-REF-03.

    DEFEITO ACHADO NA 1a RODADA DESTE LAB: eu usava `\\u00a4`, que sao **2 bytes em UTF-8**.
    O "teto de 5 chars" custava 10 B e o teto saia pessimista. Escolher por COMPLEMENTO
    resolve e ainda e' o mecanismo que o repo ja' propoe (alfabeto livre-de-conflito).
    """
    usados = set("".join(graf))
    for c in map(chr, range(33, 127)):
        if c not in usados:
            return c
    return None


def colapsa(s, marc, custo=5):
    """TETO idealizado: cada run >=4 vira `custo` chars de 1 byte. Limite SUPERIOR."""
    return RUN.sub(lambda m: marc * custo, s)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, reg = [], {}

    # ── BLOCO 1 — o run e' aproveitado? (mesmo comprimento, com e sem) ───────
    print("BLOCO 1 — MESMO comprimento, MESMO alfabeto; so' muda se ha' repeticao")
    par = []
    for nome, v, ideia in (
        ("b1-com-run", ["0.30000000000000004"], "14 zeros no meio — o caso do owner"),
        ("b1-sem-run", ["0.31415926535894704"], "MESMO comprimento, digitos sem repeticao"),
    ):
        w, ok = grava(nome, v, ideia,
                      {"gerador": "run.py::BLOCO1", "params": {"len": len(v[0])},
                       "ideia": ideia, "pin": "par de contra-prova; o CONSTANTE e' o comprimento"})
        falhas += [] if ok else [f"{nome}: RT falhou"]
        par.append((nome, B(w), w.split("\n")[1]))
        print(f"  {nome:14s} wire={B(w):>4} B   corpo={w.split(chr(10))[1]!r}")
    reg["bloco1_par"] = {"CONSTANTE_na_comparacao": "comprimento (19), alfabeto (digitos + '.')",
                         "com_run_bytes": par[0][1], "sem_run_bytes": par[1][1],
                         "diferenca": par[0][1] - par[1][1],
                         "veredito": ("o nucleo NAO aproveita o run" if par[0][1] == par[1][1]
                                      else "o nucleo aproveita o run")}
    print(f"  -> diferenca: {par[0][1] - par[1][1]} B — "
          f"{reg['bloco1_par']['veredito']}")

    # ── BLOCO 2 — a curva: bytes vs tamanho do run ──────────────────────────
    print("\nBLOCO 2 — a curva `a` + N x `0` + `b`")
    curva = []
    for n in (4, 8, 16, 32, 64, 128, 256):
        v1 = ["a" + "0" * n + "b"]
        vd = [c + "0" * n + c.upper() for c in "abcdefghijklmnopqrst"]   # 20 DISTINTOS
        w1, ok1 = grava(f"b2-1valor-n{n:03d}", v1, f"1 valor, run de {n}",
                        {"gerador": "run.py::BLOCO2", "params": {"n": n, "linhas": 1},
                         "ideia": "curva de 1 valor", "pin": "sintetico"})
        wd, okd = grava(f"b2-20distintos-n{n:03d}", vd, f"20 valores distintos, run de {n}",
                        {"gerador": "run.py::BLOCO2", "params": {"n": n, "linhas": 20},
                         "ideia": "o run se amortiza entre valores?", "pin": "sintetico"})
        falhas += [f"b2-n{n}: RT falhou"] if not (ok1 and okd) else []
        curva.append({"n": n, "um_valor": B(w1), "vinte_distintos": B(wd)})
        print(f"  n={n:>3}  1 valor={B(w1):>5} B   20 distintos={B(wd):>6} B")
    d1 = [(curva[i + 1]["um_valor"] - curva[i]["um_valor"]) / (curva[i + 1]["n"] - curva[i]["n"])
          for i in range(len(curva) - 1)]
    dd = [(curva[i + 1]["vinte_distintos"] - curva[i]["vinte_distintos"])
          / (curva[i + 1]["n"] - curva[i]["n"]) for i in range(len(curva) - 1)]
    reg["bloco2_curva"] = {"CONSTANTE_na_comparacao": "as bordas ('a','b'); so' N varia",
                           "pontos": curva, "d_bytes_d_n_1valor": d1,
                           "d_bytes_d_n_20distintos": dd,
                           "veredito": "1 B por char repetido por linha; zero amortizacao"
                           if all(abs(x - 1.0) < 1e-9 for x in d1) else "ha' amortizacao"}
    print(f"  -> d(bytes)/d(n): 1 valor = {set(d1)}, 20 distintos = {set(dd)}")

    # ── BLOCO 3 — o `*0|` FANTASMA. Aqui o WIRE e' a ENTRADA. ───────────────
    #
    # Inversao deliberada do fluxo: estes wires NAO sao produzidos pelo encoder — sao
    # escritos a mao para perguntar se o DECODER os aceita. Por isso vivem em inputs/.
    print("\nBLOCO 3 — o `*0|` (o 'RLE fantasma' do owner) ja' e' aceito?")
    fantasmas = [
        ("f1-declara-e-referencia", "#TCF.8\n*0|abc\ndef\n^1\n",
         "declara `abc` sem emitir, e depois referencia por ^1", ["def", "abc"]),
        ("f2-so-fantasma", "#TCF.8\n*0|abc\n", "1 linha no corpo, 0 elementos", []),
        ("f3-count-negativo", "#TCF.8\n*-1|abc\ndef\n", "count NEGATIVO", ["def"]),
        ("f4-fantasma-ignorado", "#TCF.8\n*0|zzz\nx\ny\n", "fantasma nunca referenciado",
         ["x", "y"]),
    ]
    res_f = []
    for nome, wire, ideia, esperado in fantasmas:
        _esc(INP / f"{nome}.wire-de-entrada.tcf", wire)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "ESCRITO A MAO — o encoder canonico nunca emite isto",
             "wire": wire, "ideia": ideia, "esperado_se_aceito": esperado,
             "pin": "fluxo INVERTIDO: o wire e' a entrada, o JSON e' a saida"})
        try:
            saida = decode(wire)
            aceito, detalhe = True, saida
        except Exception as e:
            aceito, detalhe = False, f"{type(e).__name__}: {str(e)[:70]}"
        _js(OUT / f"{nome}.decodificado.json", detalhe)
        res_f.append({"caso": nome, "wire": wire, "ideia": ideia,
                      "aceito_pelo_decoder": aceito, "saida": detalhe})
        print(f"  {nome:24s} aceito={str(aceito):5s}  -> {detalhe}")

    # o encoder canonico produz isso alguma vez?
    formas = ([], ["a"], ["a", "a"], ["a"] * 5, ["a", "b", "a"], [None], ["a", None, "a"],
              ["a"] * 50, list("abcdefghij"))
    emitiu = [repr(encode(v)) for v in formas if "*0|" in encode(v) or "*-" in encode(v)]
    reg["bloco3_fantasma"] = {
        "CONSTANTE_na_comparacao": "o mesmo decoder publico, arvore limpa, src/ intocado",
        "casos": res_f, "encoder_emite": emitiu or None,
        "formas_testadas_no_encoder": len(formas),
        "veredito": ("o `*0|` E' ACEITO e o encoder NUNCA o emite -> wire aceito-em-silencio"
                     if all(c["aceito_pelo_decoder"] for c in res_f) and not emitiu
                     else "ver casos")}
    print(f"  -> o encoder emitiu `*0|` em {len(formas)} formas? {emitiu or 'nao'}")

    # ── BLOCO 4 — dado REAL: o teto e a CONTRA-PROVA ────────────────────────
    print("\nBLOCO 4 — dado REAL: onde pagaria, e onde CUSTA")
    REAIS = [
        ("r1-wine-alcohol", "wine-quality", "SELECT alcohol FROM wine WHERE alcohol IS NOT NULL",
         "cauda de float: a UNICA coluna do corpus com run no MEIO do valor", 6497),
        ("r2-tpch-o-clerk", "tpch-sf001", "SELECT o_clerk FROM orders",
         "padding de ID: o run e' PREFIXO compartilhado — a CONTRA-PROVA", 15000),
        ("r3-tpch-c-name", "tpch-sf001", "SELECT c_name FROM customer",
         "idem: `Customer#000000001`", 1500),
    ]
    reais = []
    for nome, db, sql, ideia, lim in REAIS:
        try:
            con = sqlite3.connect(f"file:Z:/tcf-data/interim/{db}.db?mode=ro", uri=True)
            vals = [r[0] for r in con.execute(sql)]
            con.close()
        except Exception:
            print(f"  {nome:18s} (sem Z: — pulado)")
            continue
        vals = [v for v in vals if v is not None][:lim]
        graf = [str(v) for v in vals]
        w, ok = grava(nome, vals, ideia,
                      {"gerador": "run.py::BLOCO4", "db": db, "sql": sql, "ideia": ideia,
                       "pin": "corpus local Z:/tcf-data/interim — nao versionado"})
        falhas += [] if ok else [f"{nome}: RT falhou"]
        com_run = sum(1 for g in graf if RUN.search(g))
        chars_run = sum(len(m.group(0)) for g in graf for m in RUN.finditer(g))
        marc = marcador_livre(graf)
        linha = {"caso": nome, "n": len(vals), "com_run": com_run,
                 "pct_com_run": round(100 * com_run / len(vals), 2),
                 "chars_totais": sum(map(len, graf)), "chars_em_run": chars_run,
                 "bytes_hoje": B(w), "header": w.split("\n")[0],
                 "marcador_por_complemento": marc, "tetos": {}}
        for custo in (3, 5):
            ideal = [colapsa(g, marc, custo) for g in graf]
            wi = encode(ideal)
            _esc(OUT / f"{nome}.teto-marcador{custo}.tcf", wi)
            linha["tetos"][f"marcador_{custo}ch"] = {
                "bytes": B(wi), "delta": B(wi) - B(w),
                "pct": round(100 * (B(wi) - B(w)) / B(w), 2)}
        t5 = linha["tetos"]["marcador_5ch"]
        print(f"  {nome:18s} n={len(vals):>5} run={linha['pct_com_run']:>6.2f}%  "
              f"hoje={B(w):>6} B  teto(5ch)={t5['bytes']:>6} B  {t5['pct']:>+6.2f}%"
              f"   {'<- CUSTA' if t5['delta'] > 0 else ''}")
        reais.append(linha)
    reg["bloco4_real"] = {
        "CONSTANTE_na_comparacao": "a MESMA coluna, o MESMO encode; so' os runs sao colapsados",
        "AVISO": "o 'teto' colapsa o run DE GRACA (sem marcador real, sem escape) — "
                 "e' limite SUPERIOR, nao promessa",
        "colunas": reais}

    # ── saidas ──────────────────────────────────────────────────────────────
    _js(INT / "medicoes.json", reg)
    _js(RAIZ / "resultado.json", {"registros": reg, "falhas": falhas})
    linhas = ["# INDEX — RLE intra-valor, primeira medição", "",
              "Wires em `<caso>.tcf`; contra-prova em `<caso>.roundtrip.json`; procedência em",
              "`<caso>.meta.json`. **Bloco 3 inverte o fluxo**: o wire é a ENTRADA",
              "(`inputs/<caso>.wire-de-entrada.tcf`) e o JSON é a saída.", "",
              "| bloco | caso | ideia | resultado |", "|---|---|---|---|"]
    linhas += [f"| 1 | [`{n}`](./{n}.tcf) | par de contra-prova | {b} B |"
               for n, b, _ in par]
    linhas += [f"| 2 | `b2-*-n{c['n']:03d}` | curva | 1 valor {c['um_valor']} B · "
               f"20 distintos {c['vinte_distintos']} B |" for c in curva]
    linhas += [f"| 3 | [`{c['caso']}`](./{c['caso']}.decodificado.json) | {c['ideia']} | "
               f"aceito={c['aceito_pelo_decoder']} → `{c['saida']}` |" for c in res_f]
    linhas += [f"| 4 | [`{r['caso']}`](./{r['caso']}.tcf) | run em {r['pct_com_run']}% | "
               f"hoje {r['bytes_hoje']} B · teto(5ch) "
               f"{r['tetos']['marcador_5ch']['pct']:+}% |" for r in reais]
    _esc(OUT / "INDEX.md", "\n".join(linhas) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
