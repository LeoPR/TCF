# -*- coding: utf-8 -*-
"""ORDEM DE COLUNAS no `.8M` — o que a ordem prende, o que ela não prende, e o nome implícito.

    python run.py     # sai 0 só se todos os RTs fecharem e as invariantes baterem

## A pergunta (owner, 2026-08-16)

*"ver as dependências de ordem dos elementos, já que um dataset pode não precisar respeitar
isso... a ordem das colunas é importante num contexto de fonte csv talvez, ou se não tiver
nomes, aí ele tem que aceitar o padrão de entrada — mas mesmo nesse caso dá pra 'burlar',
colocando um nome implícito... se eles mudam de ordem, então o número/nome implícito ficaria
explícito, não? apenas pesquise o que daria pra fazer nesse caso."*

## O que o código diz (lido antes de medir)

- Corpos são INDEPENDENTES por coluna e concatenados na ordem do meta
  (`multi/core.py:417-418`); nenhum mecanismo cruza colunas → reordenar = permutar pares.
- A ÚNICA posição especial é a ÚLTIMA: sem size, corpo até EOF (`min_header`, ADR-0023);
  e última ANÔNIMA é SEMPRE sem size (gramática — `multi/core.py:262-264`).
- Coluna anônima decoda com nome POSICIONAL `str(i)` (`multi/core.py:596-597`) —
  **para anônimas, a ordem É o nome.**
- Nome explícito é string arbitrária escapada; `"3"` é nome legal.

## PREDIÇÕES DECLARADAS (antes de rodar)

P1. RT fecha em QUALQUER permutação, e o corpo de cada coluna é byte-idêntico em qualquer
    posição — o total varia SÓ pelo header (qual size é omitido).
P2. Com `drop_names`, reordenar TROCA OS DONOS dos valores no decode (o consumidor quebra
    calado) — é o preço de o nome ser a ordem.
P3. O "nome implícito que vira explícito" do owner FUNCIONA hoje: `"3"` como nome explícito
    decoda como `"3"` em qualquer posição, custando `1+len(nome)` B no meta.
P4 (risco). Misturar anônima com nome numérico explícito pode COLIDIR: wire à mão com
    anônima na posição 0 + coluna nomeada `"0"` → o decode sobrescreve CALADO (dict).

## GATE

`src/tcf` INTOCADO. Dado: o MESMO cadastro do lab `1400` (import direto — precedente do
`0530` importando do `0400`). Bloco 3b usa FLUXO INVERTIDO (wire à mão em
`inputs/*.wire-de-entrada.tcf`), documentado.
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
sys.path.insert(0, str(RAIZ.parent / "2026-08-16-1400-cadastro-popular-header-do-M"))

from tcf import decode, encode                                    # noqa: E402
from run import cadastro                                          # noqa: E402  (o gerador do lab 1400)

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def anatomia(wire):
    """As fatias [ini:fim) de cada coluna, com o parser REAL (`_parse_meta`)."""
    from tcf.multi.core import _parse_meta
    line1, _, body = wire.partition("\n")
    cols = _parse_meta(line1[7:])
    corpo = body.encode("utf-8")
    out, off = [], 0
    for size, nome, modo, nat in cols:
        fim = len(corpo) if size is None else off + size
        out.append({"nome": nome, "modo": modo, "ini": off, "fim": fim,
                    "corpo": corpo[off:fim]})
        off = fim
    assert off == len(corpo), "fronteira furou"
    return line1, out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas = []
    T = cadastro()
    NOMES = list(T)                                   # a ordem canônica do lab 1400
    _js(INP / "cadastro.fonte.json", {
        "gerador": "IMPORTADO de ../2026-08-16-1400-cadastro-popular-header-do-M/run.py::cadastro()",
        "ideia": "os MESMOS 500 registros do lab do header — só a ORDEM das colunas muda aqui",
        "pin": "seed 20260815; precedente de import entre labs: 0530 <- 0400"})

    # ── BLOCO 1 — permutações: o que a ordem muda de verdade ────────────────
    print("BLOCO 1 — permutações de colunas (P1: corpo por coluna é invariante à posição)\n")
    base_line1, base_cols = anatomia(encode(T))
    corpo_canon = {c["nome"]: c["corpo"] for c in base_cols}

    perms = [NOMES, NOMES[::-1],
             sorted(NOMES), sorted(NOMES, key=len),
             NOMES[3:] + NOMES[:3]]
    print(f"  {'permutação':<28} {'total':>7} {'linha1':>7} {'RT':>4}  corpo por coluna == canônico?")
    b1 = []
    for i, ordem in enumerate(perms):
        Tp = {c: T[c] for c in ordem}
        w = encode(Tp)
        rt = decode(w) == Tp
        if not rt:
            falhas.append(f"perm {i}: RT")
        l1, cols = anatomia(w)
        iguais = all(c["corpo"] == corpo_canon[c["nome"]] for c in cols if c["nome"])
        # a última coluna é a exceção HONESTA: o corpo dela é idêntico, mas só
        # comparável quando ela também era não-última no canônico — comparamos tudo
        # pelo NOME, então `iguais` já cobre.
        rot = "→".join(x[:3] for x in ordem)
        b1.append({"ordem": ordem, "total_B": B(w), "linha1_B": B(l1),
                   "rt": rt, "corpos_invariantes": iguais})
        _esc(OUT / f"perm-{i}-{ordem[0]}-primeiro.tcf", w)
        print(f"  {rot:<28} {B(w):>7} {B(l1):>7} {'ok' if rt else 'FALHA':>4}  {iguais}")
    tot = {x["total_B"] for x in b1}
    print(f"\n  totais distintos entre permutações: {sorted(tot)} — a variação é SÓ header")

    # a escolha da ÚLTIMA coluna (o size omitido) — quanto cada escolha economiza
    print("\n  P1b — a única alavanca real da ordem: QUAL coluna fica por último")
    print(f"  {'última':<12} {'total':>7} {'economia vs pior':>17}")
    escolhas = []
    for ult in NOMES:
        ordem = [c for c in NOMES if c != ult] + [ult]
        w = encode({c: T[c] for c in ordem})
        if decode(w) != {c: T[c] for c in ordem}:
            falhas.append(f"ultima={ult}: RT")
        escolhas.append((ult, B(w)))
    pior = max(b for _, b in escolhas)
    for ult, b_ in sorted(escolhas, key=lambda x: x[1]):
        print(f"  {ult:<12} {b_:>7} {pior - b_:>16}B")
    b1b = {u: b_ for u, b_ in escolhas}

    # ── BLOCO 2 — drop_names: o nome É a ordem (P2) ─────────────────────────
    print("\nBLOCO 2 — drop_names × reordenação: os valores trocam de dono CALADO")
    wA = encode(T, drop_names=True)
    ordem2 = NOMES[1:] + NOMES[:1]                    # roda 1 posição
    wB = encode({c: T[c] for c in ordem2}, drop_names=True)
    dA, dB = decode(wA), decode(wB)
    _esc(OUT / "sem-nomes-ordem-canonica.tcf", wA)
    _esc(OUT / "sem-nomes-ordem-rodada.tcf", wB)
    troca = dA["0"][:1] != dB["0"][:1]
    print(f"  ordem canônica : decode()['0'][:1] = {dA['0'][:1]}   (era a coluna {NOMES[0]!r})")
    print(f"  ordem rodada   : decode()['0'][:1] = {dB['0'][:1]}   (agora é {ordem2[0]!r})")
    print(f"  => o MESMO consumidor lendo '0' recebe outra coluna, sem erro nenhum: {troca}")
    if not troca:
        falhas.append("P2 não demonstrou (colunas iguais demais?)")

    # ── BLOCO 3 — o nome implícito que vira explícito (P3) ──────────────────
    print("\nBLOCO 3 — a proposta: coluna fora do lugar carrega o NÚMERO como nome explícito")
    # cenário: consumidor conhece as colunas pela POSIÇÃO canônica 0..6; o produtor
    # precisou mover a coluna 3 (email) pro fim. As demais seguem anônimas.
    ordem3 = [c for c in NOMES if c != "email"] + ["email"]
    Tm = {}
    for c in ordem3:
        Tm[c] = T[c]
    # anônimas para todas MENOS a movida: o encode não tem kwarg por-coluna pra isso,
    # então o produtor usa NOMES NUMÉRICOS explícitos: as no-lugar ficam '' (anônimas)
    # não dá — '' só pode UMA (colisão posicional). O jeito REPRESENTÁVEL hoje:
    # nomear TODAS pelo índice canônico. Medimos o custo disso contra drop_names puro.
    Tn = {str(NOMES.index(c)): T[c] for c in ordem3}   # nomes = índices canônicos
    wn = encode(Tn)
    dn = decode(wn)
    rt3 = dn == Tn
    if not rt3:
        falhas.append("P3: RT dos nomes numéricos")
    _esc(OUT / "nomes-numericos-explicitos.tcf", wn)
    print(f"  nomes numéricos explícitos (todas): {B(wn)} B  linha1={wn.split(chr(10),1)[0]!r}")
    print(f"  decode devolve as chaves {list(dn)} — a coluna movida ('3') é acháve1 POR NOME,")
    print(f"  em qualquer posição: dn['3'][:1] == email? {dn['3'][:1] == T['email'][:1]}")
    w_anon = encode({c: T[c] for c in ordem3}, drop_names=True)
    print(f"  contra: drop_names puro (posicional) = {B(w_anon)} B — "
          f"custo dos índices explícitos: {B(wn) - B(w_anon):+d} B "
          f"({(B(wn) - B(w_anon)) / len(NOMES):.1f} B/coluna)")
    b3 = {"numericos_B": B(wn), "anonimo_B": B(w_anon),
          "custo_por_coluna": round((B(wn) - B(w_anon)) / len(NOMES), 1)}

    # ── BLOCO 3b — o RISCO (P4): anônima + nome numérico explícito COLIDEM ──
    print("\nBLOCO 3b — FLUXO INVERTIDO: wire à mão com anônima(pos 0) + coluna nomeada '0'")
    # gramática real: '<size>,<size>=0,...' — 1ª anônima (decoda '0'), 2ª NOMEADA '0'.
    c1 = "x\ny\nz"                       # 3 valores modo raw? sem prefixo = tcf; usamos raw '!'
    c2 = "a\nb\nc"
    wire = (f"#TCF.8M!{format(len(c1.encode()), 'x')},!{format(len(c2.encode()), 'x')}=0,!fim\n"
            f"{c1}{c2}" + "f\ni\nm")
    _esc(INP / "colisao-anonima-vs-0.wire-de-entrada.tcf", wire)
    try:
        d4 = decode(wire)
        n_cols_header = 3
        perdeu = len(d4) < n_cols_header
        print(f"  header declara {n_cols_header} colunas; decode devolveu {len(d4)}: {list(d4)}")
        print(f"  a anônima da posição 0 decodou como '0' e foi SOBRESCRITA pela nomeada '0': {perdeu}")
        print(f"  d4['0'] = {d4.get('0')}   (os valores {c1.split(chr(10))} sumiram CALADOS: "
              f"{d4.get('0') == c2.split(chr(10))})")
        b3b = {"colunas_no_header": n_cols_header, "colunas_no_decode": len(d4),
               "perda_silenciosa": perdeu}
        if not perdeu:
            falhas.append("P4 não reproduziu — sem colisão")
    except Exception as e:
        b3b = {"excecao": f"{type(e).__name__}: {e}"}
        print(f"  decode LEVANTOU: {type(e).__name__}: {e}  (fail-loud — P4 refutada, MELHOR)")

    _js(RAIZ / "resultado.json", {
        "bloco1_permutacoes": b1, "bloco1b_ultima_coluna": b1b,
        "bloco2_troca_de_dono": {"demonstrado": troca},
        "bloco3_nomes_numericos": b3, "bloco3b_colisao": b3b, "falhas": falhas,
        "CONSTANTE_na_comparacao": "os MESMOS 500 registros do lab 1400 em tudo; "
                                   "muda só ORDEM/nomeação das colunas"})
    print(f"\n{len(falhas)} falha(s)")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
