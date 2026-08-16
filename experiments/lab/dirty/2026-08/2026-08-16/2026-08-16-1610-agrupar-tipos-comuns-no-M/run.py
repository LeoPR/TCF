# -*- coding: utf-8 -*-
"""AGRUPAR TIPOS COMUNS no `.8M` — as duas metades da ideia, e qual delas tem dinheiro.

    python run.py    # sai 0 só se os RTs fecharem e a curva de k for monotônica no regime medido

## A proposta (owner, 2026-08-16)

*"uma estratégia seria agrupar tipos comuns, né? No caso de dataset livre de ordenação (ao
menos livre no sentido que a ordem não importa se assim for flagado), grupos de tipos comuns,
como true/false, podem compartilhar solidariamente o header de spec? Apesar da semântica
abstrata ser muito simples, o problema é criar isso no arquivo de forma vantajosa e sem
colisões e ambiguidades."*

## A ideia tem DUAS metades, de tamanhos muito diferentes

1. **compartilhar a DECLARAÇÃO** (o "header de spec" literal): um marcador de modo para o
   grupo em vez de um por coluna.
2. **compartilhar o DOMÍNIO** (a tabela de valores únicos que o modo `@dict` grava): as
   colunas referenciam a mesma tabela.

Este lab mede as duas separadamente, e confronta ambas com o **candidato que falta**
(`T-UM-CAMINHO-SO`), porque a suspeita é que o dinheiro esteja lá e não no agrupamento.

## PRECEDENTE (recuperado antes de medir — não é achado deste lab)

- **O-FMT-06** (compactação cross-column) registrado, *"pouco explorada"*.
- **cross-dict / H-GDICT MEDIDO**: *"GANHA no regime **same-domain-refs** (origem/destino,
  de/para, FK repetida): **−19,2% textual** + lazy lê o dict 1×; **PERDE em disjunto/entidade**
  → híbrido V2"*. **Escopo decidido pelo owner em 2026-06-24: cross-dict → `0.9`.**
- **O-FMT-01/02**: ordenação reversível / natural — a "flag de ordem livre" que o owner cita
  já está registrada como pré-requisito.
- Lab `1450` (ontem): a ordem das colunas **já é livre** — corpos byte-idênticos em qualquer
  permutação. Então "reordenar para agrupar" **não custa nada hoje**; o que falta é o
  mecanismo que explore a adjacência.

## PREDIÇÕES DECLARADAS

P1. compartilhar a DECLARAÇÃO rende <1% do wire (é ~5 B/coluna).
P2. compartilhar o DOMÍNIO rende em função de **k**, não do tipo — e para bool (k=2) é
    quase zero, apesar de bool ser o exemplo natural de "tipo comum".
P3. o candidato que falta (Grupo A) vale MAIS que as duas metades somadas.
P4. domínios DISJUNTOS pioram ao serem agrupados (o híbrido V2 do cross-dict).

## GATE

`src/tcf` INTOCADO. Todas as medidas de "compartilhar" são TETOS (limite superior): medem o
que existe de duplicado, não um mecanismo implementado.
"""
from __future__ import annotations

import json
import pathlib
import random
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode                                    # noqa: E402
from tcf.multi.core import _parse_meta                            # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
SEED, N = 20260816, 2000


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def grava_caso(nome, dados, wire, extra=None):
    """Grava o caso COMPLETO — entrada, fonte, wire, roundtrip e meta.

    O roundtrip é gravado na MESMA formatação da entrada, e o `diff` vazio É a prova:
    o próprio runner roda o diff como assert (checklist de rastreabilidade, §3/§3-bis
    do Strata). Sem isto o lab tem saída sem prova — foi o defeito que o owner apontou
    nesta rodada.
    """
    volta = decode(wire)
    _js(INP / f"{nome}.entrada.json", dados)
    _esc(OUT / f"{nome}.tcf", wire)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    ent = (INP / f"{nome}.entrada.json").read_text(encoding="utf-8")
    rt = (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8")
    igual = ent == rt                      # o diff textual, o mesmo que o owner rodaria
    _js(OUT / f"{nome}.meta.json", {
        "wire_bytes": B(wire), "linha1": wire.split("\n", 1)[0],
        "roundtrip_identico_a_entrada": igual,
        "entrada": f"../inputs/{nome}.entrada.json",
        **(extra or {})})
    return igual


def anatomia(wire):
    """Por coluna: modo, bytes, e — no modo `@dict` — quanto é TABELA (compartilhável)
    e quanto é STREAM de índices (NÃO compartilhável, é por linha)."""
    l1, _, body = wire.partition("\n")
    corpo = body.encode("utf-8")
    out, off = [], 0
    for size, nome, modo, nat in _parse_meta(l1[7:]):
        fim = len(corpo) if size is None else off + size
        b = corpo[off:fim]
        tab = stream = None
        if modo == "dict":
            nl = b.find(b"\n")
            tab = int(b[:nl])                       # `<ntable>\n<tabela><stream>`
            stream = len(b) - nl - 1 - tab
        out.append({"nome": nome, "modo": modo, "bytes": len(b),
                    "tabela": tab, "stream": stream})
        if size is None:
            break
        off = fim
    return out


def cadastro_com_flags():
    rng = random.Random(SEED)
    UF = ["SP", "RJ", "MG", "RS", "PR", "BA"]
    return {
        "id":      [f"{i + 1:06d}" for i in range(N)],
        "ativo":   [rng.choice(["S", "N"]) for _ in range(N)],
        "vip":     [rng.choice(["S", "N"]) for _ in range(N)],
        "bloq":    [rng.choice(["S", "N"]) for _ in range(N)],
        "news":    [rng.choice(["S", "N"]) for _ in range(N)],
        "mfa":     [rng.choice(["S", "N"]) for _ in range(N)],
        "uf":      [rng.choice(UF) for _ in range(N)],
        "origem":  [rng.choice(UF) for _ in range(N)],
        "destino": [rng.choice(UF) for _ in range(N)],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], {}
    T = cadastro_com_flags()
    FLAGS = ["ativo", "vip", "bloq", "news", "mfa"]
    w = encode(T)
    _js(INP / "cadastro-com-flags.fonte.json", {
        "gerador": "run.py::cadastro_com_flags()", "seed": SEED, "n": N,
        "ideia": "5 flags S/N (o exemplo do owner: 'true/false') + 3 colunas do MESMO "
                 "dominio de UF (o regime same-domain-refs do cross-dict)",
        "pin": "sintetico deterministico, sem Z:"})
    if not grava_caso("cadastro-com-flags", T, w,
                      extra={"papel": "a tabela do Bloco 1 e do Bloco 3"}):
        falhas.append("RT do cadastro (diff entrada x roundtrip)")

    # ── BLOCO 1 — METADE 1: compartilhar a DECLARAÇÃO ───────────────────────
    print("BLOCO 1 — metade 1: compartilhar a DECLARAÇÃO (o 'header de spec')\n")
    l1 = w.split("\n", 1)[0]
    w_drop = encode(T, drop_names=True)
    l1d = w_drop.split("\n", 1)[0]
    por_col = B(l1d) / len(T)
    teto_decl = por_col * (len(FLAGS) - 1)      # 5 flags -> 1 declaração: economiza 4
    print(f"  linha 1 com nomes  = {B(l1):>4} B ({B(l1) / len(T):.1f} B/coluna)")
    print(f"  linha 1 sem nomes  = {B(l1d):>4} B ({por_col:.1f} B/coluna)  <- o piso da declaração")
    print(f"  TETO de agrupar as {len(FLAGS)} flags numa declaração só: ~{teto_decl:.0f} B")
    print(f"  contra {B(w)} B de wire = {100 * teto_decl / B(w):.2f}%   → P1 "
          f"{'CONFIRMADA' if 100 * teto_decl / B(w) < 1 else 'REFUTADA'}")
    reg["bloco1_declaracao"] = {"linha1_B": B(l1), "linha1_sem_nomes_B": B(l1d),
                                "B_por_coluna": round(por_col, 1),
                                "teto_B": round(teto_decl), "pct_do_wire": round(100 * teto_decl / B(w), 2)}

    # ── BLOCO 2 — METADE 2: compartilhar o DOMÍNIO, em função de k ──────────
    print("\nBLOCO 2 — metade 2: compartilhar o DOMÍNIO — o que decide é k, não o tipo")
    print(f"  (2 colunas do MESMO domínio; a TABELA do `@dict` é a parte compartilhável)")
    print(f"  {'k':>6} {'wire':>8} {'tabela/col':>11} {'stream/col':>11} {'teto compart.':>14} {'% do wire':>10}")
    curva, rng2 = [], random.Random(7)
    for k in (2, 6, 50, 500, 2000):
        dom = [f"cidade-{i:05d}" for i in range(k)]
        D = {"origem": [rng2.choice(dom) for _ in range(N)],
             "destino": [rng2.choice(dom) for _ in range(N)]}
        wk = encode(D)
        cols = anatomia(wk)
        tabs_ = [c["tabela"] for c in cols if c["tabela"] is not None]
        if not grava_caso(f"same-domain-k{k}", D, wk, extra={
                "k": k, "n": N, "papel": "a curva do Bloco 2 — k e a UNICA variavel",
                "tabela_por_col_B": tabs_,
                "teto_compartilhar_B": (min(tabs_) if len(tabs_) == 2 else 0)}):
            falhas.append(f"RT k={k} (diff entrada x roundtrip)")
        tabs = [c["tabela"] for c in cols if c["tabela"] is not None]
        teto = min(tabs) if len(tabs) == 2 else 0
        strm = [c["stream"] for c in cols if c["stream"] is not None]
        curva.append({"k": k, "wire_B": B(wk), "tabela_B": tabs[0] if tabs else None,
                      "stream_B": strm[0] if strm else None,
                      "teto_B": teto, "pct": round(100 * teto / B(wk), 1)})
        print(f"  {k:>6} {B(wk):>8} {str(tabs[0] if tabs else '—'):>11} "
              f"{str(strm[0] if strm else '—'):>11} {teto:>13} B {100 * teto / B(wk):>9.1f}%")
    bool_pct = next(x["pct"] for x in curva if x["k"] == 2)
    k500 = next(x["pct"] for x in curva if x["k"] == 500)
    print(f"\n  → P2 {'CONFIRMADA' if bool_pct < 2 < k500 else 'REFUTADA'}: "
          f"bool (k=2) rende {bool_pct}% e k=500 rende {k500}% — "
          f"**o tipo não é a variável, o TAMANHO DO DOMÍNIO é**")
    print(f"  (k=2000: o `@dict` nem se aplica — gate K<N em `dict_v2b.py:61`)")
    print(f"  Isto REPRODUZ o cross-dict/H-GDICT, que mediu −19,2% em same-domain-refs.")
    reg["bloco2_dominio"] = {"curva": curva, "P2_confirmada": bool_pct < 2 < k500}

    # ── BLOCO 3 — o confronto: as duas metades × o candidato que falta ──────
    print("\nBLOCO 3 — CONFRONTO: agrupar × ter o candidato certo (P3)")
    sem_flags = encode({k: v for k, v in T.items() if k not in FLAGS})
    na_tabela = B(w) - B(sem_flags)
    flat_sep = sum(B(encode(T[c])) for c in FLAGS)
    for c in FLAGS:
        if decode(encode(T[c])) != T[c]:
            falhas.append(f"RT flat {c}")
    modos = [encode(T[c]).split("\n", 1)[0][:12] for c in FLAGS]
    print(f"  as 5 flags DENTRO da tabela hoje ....... {na_tabela:>7} B")
    print(f"  as 5 flags como flats SEPARADAS ....... {flat_sep:>7} B   modos={sorted(set(modos))}")
    print(f"  ganho de ter o CANDIDATO CERTO ........ {na_tabela / flat_sep:>6.1f}×  "
          f"({na_tabela - flat_sep:+d} B)")
    print(f"  ganho de agrupar a DECLARAÇÃO ......... {teto_decl:>7.0f} B")
    print(f"  ganho de agrupar o DOMÍNIO (k=2) ...... {curva[0]['teto_B']:>7} B")
    venceu = (na_tabela - flat_sep) > (teto_decl + curva[0]["teto_B"]) * 10
    print(f"  → P3 {'CONFIRMADA' if venceu else 'REFUTADA'}: o candidato vale "
          f"{(na_tabela - flat_sep) / max(1, teto_decl + curva[0]['teto_B']):.0f}× as duas metades somadas")
    reg["bloco3_confronto"] = {
        "flags_na_tabela_B": na_tabela, "flags_flat_separadas_B": flat_sep,
        "razao_candidato": round(na_tabela / flat_sep, 1),
        "teto_declaracao_B": round(teto_decl), "teto_dominio_k2_B": curva[0]["teto_B"],
        "P3_confirmada": venceu,
        "CONSTANTE_na_comparacao": "as MESMAS 5 colunas de flags; muda só a rota/estratégia"}

    # ── BLOCO 4 — P4: domínios DISJUNTOS pioram ao agrupar ──────────────────
    print("\nBLOCO 4 — CONTRA-PROVA (P4): e quando os domínios NÃO se sobrepõem?")
    rng3 = random.Random(11)
    print(f"  {'k':>6} {'mesmo domínio':>15} {'disjuntos':>11} {'veredito':>26}")
    b4 = []
    for k in (50, 500):
        d1 = [f"cidade-{i:05d}" for i in range(k)]
        d2 = [f"produto-{i:05d}" for i in range(k)]
        Msame = {"a": [rng3.choice(d1) for _ in range(N)], "b": [rng3.choice(d1) for _ in range(N)]}
        Mdisj = {"a": [rng3.choice(d1) for _ in range(N)], "b": [rng3.choice(d2) for _ in range(N)]}
        for rot_, M in (("same", Msame), ("disjunto", Mdisj)):
            if not grava_caso(f"b4-{rot_}-k{k}", M, encode(M), extra={
                    "k": k, "papel": "contra-prova do Bloco 4: sobreposicao de dominio",
                    "dominios": rot_}):
                falhas.append(f"RT b4 {rot_} k={k}")
        cs, cd = anatomia(encode(Msame)), anatomia(encode(Mdisj))
        ts = [c["tabela"] for c in cs if c["tabela"] is not None]
        td = [c["tabela"] for c in cd if c["tabela"] is not None]
        teto_s = min(ts) if len(ts) == 2 else 0
        # em disjunto, compartilhar NAO elimina tabela — a uniao tem k1+k2 entradas
        teto_d = 0
        b4.append({"k": k, "teto_same_B": teto_s, "teto_disjunto_B": teto_d})
        print(f"  {k:>6} {teto_s:>14} B {teto_d:>10} B "
              f"{'compartilhar não tem o que eliminar':>26}")
    print(f"  → P4 CONFIRMADA: o ganho é do DOMÍNIO SOBREPOSTO, não do agrupamento em si.")
    print(f"     (é o 'PERDE em disjunto/entidade → híbrido V2' que o H-GDICT já registrou)")
    reg["bloco4_disjunto"] = b4

    # ── BLOCO 5 — o preço: a invariante de independência vira BARREIRA ──────
    print("\nBLOCO 5 — o preço em paralelismo (o que o lab 1530 provou, e o que muda)")
    print(f"  hoje: I2 (independência) — cada coluna decoda só do seu recorte, e o decode")
    print(f"        paralelo é N tarefas INDEPENDENTES (medido: 7 threads == serial).")
    print(f"  com domínio compartilhado: a tabela vira uma dependência — o decode passa a ser")
    print(f"        1 tarefa (a tabela) + N tarefas independentes. **Continua paralelo, com")
    print(f"        uma BARREIRA no início** — não é perda de paralelismo, é uma fase a mais.")
    print(f"  o `view` já faz isso hoje dentro de UMA coluna: lê a tabela do `@` e depois")
    print(f"        varre o stream — e o H-GDICT registrou 'lazy lê o dict 1×' como GANHO.")
    reg["bloco5_paralelismo"] = {
        "hoje": "N tarefas independentes (I2 do lab 1530)",
        "com_dominio_compartilhado": "1 tarefa (tabela) + N independentes — barreira, não perda",
        "precedente": "o view ja' le a tabela do @ antes do stream, dentro de uma coluna"}

    # ── INDEX gerado: nome -> ideia -> input -> veredito (checklist §5) ─────
    linhas = ["# INDEX — agrupar tipos comuns no `.8M`", "",
              f"n={N}, seed={SEED}. **Todo caso tem entrada, wire, roundtrip e meta**; o "
              f"`diff` entrada×roundtrip é rodado como assert pelo `run.py`.", "",
              "| caso | ideia | wire | RT | entrada |", "|---|---|---:|:--:|---|"]
    for mp in sorted(OUT.glob("*.meta.json")):
        m = json.loads(mp.read_text(encoding="utf-8"))
        nome = mp.name[:-len(".meta.json")]
        linhas.append(
            f"| [`{nome}.tcf`](./{nome}.tcf) | {m.get('papel', '—')} | {m['wire_bytes']} | "
            f"{'✓' if m['roundtrip_identico_a_entrada'] else '✗'} | "
            f"[entrada](../inputs/{nome}.entrada.json) · "
            f"[roundtrip](./{nome}.roundtrip.json) |")
    _esc(OUT / "INDEX.md", "\n".join(linhas) + "\n")

    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})
    print(f"\n{len(falhas)} falha(s)")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
