# -*- coding: utf-8 -*-
"""DATE em dado REAL — as transformações sobrevivem? E quanto custa o `min()` ampliado?

    python run.py

## O que este lab fecha

O lab `…-0400` mediu 6 transformações em 14 regimes **sintéticos** e achou uma partição limpa:
`ordinal` na progressão regular, `delta` onde ela quebra, `delta2` nos saltos
irregulares-crescentes, `componentes` onde a ordem some. Ele terminou com duas ressalvas
explícitas, e **este lab existe para fechá-las**:

1. **tudo sintético** — e o precedente é duro: o `T-DATA-ALVO-MENSAL` deu **95% em sintético e
   0,0% em real**;
2. **CPU não medida** — um `min()` de 6 candidatos custa tempo (o análogo do
   `T-CANDIDATO-SEM-DEDUP` mediu **+84–93%** de encode).

## A disciplina que este lab acrescenta: PREDIÇÃO ANTES DA MEDIÇÃO

Medir 6 transformações em N colunas e depois escolher a melhor **não prova nada** — é pescar.
Então o lab **classifica o regime de cada coluna real primeiro**, **declara qual transformação
o lab sintético prevê**, e só então mede. O que vale é a **taxa de acerto da predição**.

Sem isso, "o delta ganhou em 3 colunas" seria indistinguível de sorte.

## GATE

`src/tcf` intocado. Nada aqui é proposta de weld — é a conta que precede a decisão de design
do protocolo de transformação de coluna.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import shutil
import sqlite3
import sys
import time
import tracemalloc
from collections import Counter

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ.parent / "2026-08-15-0400-date-processo-de-compressao"))

from tcf import decode, encode                                     # noqa: E402
from tcf.natures import SPEC_DATA_ISO                              # noqa: E402
import transformacoes as T                                         # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── as colunas de data do corpus ────────────────────────────────────────────
COLUNAS = [
    ("tpch-orderdate", "tpch-sf001", "SELECT o_orderdate FROM orders"),
    ("tpch-shipdate", "tpch-sf001", "SELECT l_shipdate FROM lineitem"),
    ("tpch-commitdate", "tpch-sf001", "SELECT l_commitdate FROM lineitem"),
    ("tpch-receiptdate", "tpch-sf001", "SELECT l_receiptdate FROM lineitem"),
    ("tpch01-orderdate", "tpch-sf01", "SELECT o_orderdate FROM orders"),
    ("br-cadastro", "br-identidades", "SELECT data_cadastro FROM pessoas"),
    ("br-abertura", "br-identidades", "SELECT data_abertura FROM empresas"),
    # A ÚNICA coluna real do corpus que já vem ORDENADA (ND=100%). Sem ela, o regime
    # onde `delta`/`delta2` ganham só existiria no par de contra-prova — isto é, seria
    # medição real de um caso de uso hipotético. Ela é CSV, não .db.
    ("football-date", "csv:football-results/results.csv", "date"),
]
N_ALVO = 2000


def carrega(db, sql, n=N_ALVO, modo="espalhada"):
    """Amostra a coluna. `modo` NÃO é detalhe — ver o BLOCO 1c.

    `espalhada` é a convenção do projeto (evita viés de cabeça). Mas ela **pula linhas**,
    e transformações que leem VIZINHOS (delta, delta2) enxergam a adjacência da amostra,
    não a da coluna. `contigua` preserva a adjacência real.
    """
    try:
        if db.startswith("csv:"):
            import csv as _csv
            with open(f"Z:/tcf-data/external/{db[4:]}", encoding="utf-8", newline="") as fh:
                v = [r[sql] for r in _csv.DictReader(fh) if r.get(sql)]
        else:
            con = sqlite3.connect(f"file:Z:/tcf-data/interim/{db}.db?mode=ro", uri=True)
            v = [r[0] for r in con.execute(sql) if r[0] is not None]
            con.close()
    except Exception:
        return None
    v = [str(x) for x in v]
    if len(v) > n:
        if modo == "espalhada":                 # passo espalhado, NUNCA LIMIT puro
            v = v[::max(1, len(v) // n)][:n]
        else:                                   # janela contígua do MEIO (não a cabeça)
            i = max(0, (len(v) - n) // 2)
            v = v[i:i + n]
    return v


# ── ESTÁGIO A — classificar o regime, e PREDIZER ────────────────────────────
def classifica(datas):
    """Mede a forma da coluna e prevê a transformação vencedora, ANTES de medir bytes."""
    o = T._ords(datas)
    d = {"canonica_iso": o is not None, "n": len(datas), "distintos": len(set(datas))}
    if o is None:
        d["predicao"] = "nucleo"
        d["motivo"] = "grafia não-canônica: nenhuma transformação se aplica"
        return d
    n = len(o)
    nao_decrescente = sum(1 for i in range(1, n) if o[i] >= o[i - 1])
    repete = sum(1 for i in range(1, n) if o[i] == o[i - 1])
    deltas = [o[i] - o[i - 1] for i in range(1, n)]
    cont = Counter(deltas)
    top = cont.most_common(5)
    dom = top[0][1] / len(deltas) if deltas else 0
    absd = sorted(abs(x) for x in deltas)
    d.update({
        "pct_nao_decrescente": round(100 * nao_decrescente / max(1, n - 1), 1),
        "pct_repete_anterior": round(100 * repete / max(1, n - 1), 1),
        "deltas_distintos": len(cont),
        "delta_dominante_pct": round(100 * dom, 1),
        "top5_deltas": [[k, v] for k, v in top],
        # DIAGNÓSTICO, fora da regra de predição — é a variável que o BLOCO 1c mostra
        # que o classificador NÃO lê (magnitude do salto, não só ordem e contagem).
        "delta_abs_mediano": absd[len(absd) // 2] if absd else 0,
        "pct_delta_ate_31d": round(100 * sum(1 for x in absd if x <= 31) / max(1, len(absd)), 1),
    })
    # a predição, pela partição do lab sintético — REGRA INALTERADA desde a 1ª rodada
    if d["pct_repete_anterior"] > 50:
        d["predicao"], d["motivo"] = "componentes", "repetição adjacente alta — a ordem não informa"
    elif d["pct_nao_decrescente"] < 70:
        d["predicao"], d["motivo"] = "componentes", "desordenada — só a igualdade sobrevive"
    elif dom > 0.8:
        d["predicao"], d["motivo"] = "ordinal", "progressão regular — o seq-RLE pega"
    elif len(cont) <= 12:
        d["predicao"], d["motivo"] = "delta", "poucos deltas distintos — alfabeto pequeno"
    else:
        d["predicao"], d["motivo"] = "delta2", "saltos irregulares e crescentes"
    return d


# ── ESTÁGIO B — medir ───────────────────────────────────────────────────────
def mede(datas):
    out = {}
    for rot, tfn, ifn, _ in T.TRANSFORMACOES:
        vals = tfn(datas)
        if vals is None:
            out[rot] = None
            continue
        w = encode(vals)
        try:
            ok = ifn(decode(w)) == list(datas)
        except Exception:
            ok = False
        out[rot] = B(w)
        out[f"{rot}_rt"] = ok
    return out


def crono(fn, rep=3):
    fn()
    return min(_t(fn) for _ in range(rep))


def _t(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, INT, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], []

    print("BLOCO 1 — as colunas REAIS: classificar, PREDIZER, e só então medir\n")
    print(f"  {'coluna':>18} {'n':>5} {'k':>5} {'ord?':>6} {'rep%':>6} {'Δdist':>6} "
          f"{'Δdom%':>6} | {'predição':>12} {'medido':>12} {'acerto':>7}")
    for nome, db, sql in COLUNAS:
        datas = carrega(db, sql)
        if not datas:
            print(f"  {nome:>18} (sem Z: — pulado)")
            continue
        cls = classifica(datas)
        _js(INP / f"{nome}.entrada.json", datas)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "run.py::COLUNAS", "db": db, "sql": sql,
             "amostragem": f"passo espalhado, alvo {N_ALVO} (nunca LIMIT puro)",
             "classificacao": cls, "pin": "corpus Z:/tcf-data/interim — não versionado"})
        m = mede(datas)
        for rot in [r for r, _, _, _ in T.TRANSFORMACOES]:
            if m.get(f"{rot}_rt") is False:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            if m.get(rot) is not None:
                _esc(OUT / f"{nome}.{rot}.tcf", encode(dict(T.TRANSFORMACOES)[rot](datas))
                     if False else encode(next(t for r, t, _, _ in T.TRANSFORMACOES
                                               if r == rot)(datas)))
        w_spec = encode(datas, nature=SPEC_DATA_ISO)
        if decode(w_spec, nature=SPEC_DATA_ISO) != datas:
            falhas.append(f"{nome}/spec: RT do spec welded não fechou")
        _esc(OUT / f"{nome}.spec-welded.tcf", w_spec)
        _js(OUT / f"{nome}.roundtrip.json", decode(w_spec, nature=SPEC_DATA_ISO))
        cands = {k: v for k, v in m.items()
                 if k in [r for r, _, _, _ in T.TRANSFORMACOES] and isinstance(v, int)
                 and m.get(f"{k}_rt") is not False}
        venc = min(cands, key=cands.get)
        acerto = venc == cls["predicao"]
        linha = {"coluna": nome, "db": db, **cls, **m, "spec_hoje": B(w_spec),
                 "vencedor_medido": venc, "min_todos": cands[venc],
                 "acerto_predicao": acerto,
                 "ganho_vs_spec_pct": round(100 * (1 - cands[venc] / B(w_spec)), 1),
                 "ganho_vs_ordinal_pct": (round(100 * (1 - cands[venc] / m["ordinal"]), 1)
                                          if isinstance(m.get("ordinal"), int) else None),
                 "CONSTANTE_na_comparacao": "a MESMA coluna e o MESMO encode; só a transformação muda"}
        reg.append(linha)
        _js(OUT / f"{nome}.meta.json", linha)
        print(f"  {nome:>18} {cls['n']:>5} {cls['distintos']:>5} "
              f"{cls.get('pct_nao_decrescente', 0):>5.0f}% {cls.get('pct_repete_anterior', 0):>5.0f}% "
              f"{cls.get('deltas_distintos', 0):>6} {cls.get('delta_dominante_pct', 0):>5.0f}% | "
              f"{cls['predicao']:>12} {venc:>12} {'SIM' if acerto else 'NAO':>7}")

    if reg:
        acertos = sum(1 for r in reg if r["acerto_predicao"])
        print(f"\n  PREDIÇÃO: {acertos} de {len(reg)} colunas — "
              f"{'a partição sintética se sustenta' if acertos > len(reg) / 2 else 'a partição NÃO transfere'}")
        ganham = [r for r in reg if (r["ganho_vs_ordinal_pct"] or 0) > 1]
        print(f"  GANHO REAL: {len(ganham)} de {len(reg)} colunas ganham >1% sobre o ordinal welded")
        for r in sorted(ganham, key=lambda x: -(x["ganho_vs_ordinal_pct"] or 0)):
            print(f"    {r['coluna']:>18}: ordinal {r['ordinal']:>6} -> {r['min_todos']:>6} B "
                  f"({r['ganho_vs_ordinal_pct']:>5.1f}%) via {r['vencedor_medido']}")

    # ── BLOCO 1b — O PAR DE CONTRA-PROVA: as mesmas colunas, ORDENADAS ──────
    #
    # As 7 previram `componentes`, e as 7 acertaram — mas isso testa UMA célula da
    # partição, não a partição. Se o classificador só sabe dizer "componentes", acertar
    # 7 de 7 não vale nada.
    #
    # A contra-prova: ordenar cada coluna. Mesmos valores, mesma cardinalidade — só a
    # ORDEM muda. A predição TEM de mudar, e a medição TEM de acompanhar. Se não mudar,
    # o classificador é um carimbo, não um classificador.
    print("\nBLOCO 1b — CONTRA-PROVA: as mesmas colunas ORDENADAS (só a ordem muda)")
    print(f"  {'coluna':>18} {'ord?':>6} {'Δdom%':>6} | {'predição':>12} {'medido':>12} "
          f"{'acerto':>7} | {'ordinal':>8} {'melhor':>8} {'ganho':>7}")
    reg_ord = []
    for r in reg:
        nome = r["coluna"] + "-ORDENADA"
        datas = sorted(json.loads(
            (INP / f"{r['coluna']}.entrada.json").read_text(encoding="utf-8")))
        cls = classifica(datas)
        _js(INP / f"{nome}.entrada.json", datas)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "sorted() da coluna real", "origem": r["coluna"],
             "ideia": "PAR DE CONTRA-PROVA: mesmos valores, mesma cardinalidade, só a ORDEM muda",
             "classificacao": cls, "pin": "derivado do corpus"})
        m = mede(datas)
        for rot in [x for x, _, _, _ in T.TRANSFORMACOES]:
            if m.get(f"{rot}_rt") is False:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            if m.get(rot) is not None:
                _esc(OUT / f"{nome}.{rot}.tcf",
                     encode(next(t for x, t, _, _ in T.TRANSFORMACOES if x == rot)(datas)))
        cands = {k: v for k, v in m.items()
                 if k in [x for x, _, _, _ in T.TRANSFORMACOES] and isinstance(v, int)
                 and m.get(f"{k}_rt") is not False}
        venc = min(cands, key=cands.get)
        acerto = venc == cls["predicao"]
        linha = {"coluna": nome, "origem": r["coluna"], **cls, **m,
                 "vencedor_medido": venc, "min_todos": cands[venc],
                 "acerto_predicao": acerto,
                 "ganho_vs_ordinal_pct": (round(100 * (1 - cands[venc] / m["ordinal"]), 1)
                                          if isinstance(m.get("ordinal"), int) else None),
                 "CONSTANTE_na_comparacao": "os MESMOS valores da coluna real; só a ORDEM muda"}
        reg_ord.append(linha)
        _js(OUT / f"{nome}.meta.json", linha)
        print(f"  {r['coluna']:>18} {cls.get('pct_nao_decrescente', 0):>5.0f}% "
              f"{cls.get('delta_dominante_pct', 0):>5.0f}% | {cls['predicao']:>12} {venc:>12} "
              f"{'SIM' if acerto else 'NAO':>7} | {m.get('ordinal', 0):>8} {cands[venc]:>8} "
              f"{linha['ganho_vs_ordinal_pct']:>6.1f}%")

    if reg_ord:
        mudou = sum(1 for a, b in zip(reg, reg_ord) if a["predicao"] != b["predicao"])
        ac_ord = sum(1 for r in reg_ord if r["acerto_predicao"])
        classes = {r["predicao"] for r in reg} | {r["predicao"] for r in reg_ord}
        print(f"\n  a predição MUDOU em {mudou} de {len(reg)} ao ordenar  "
              f"(se 0, o classificador é um carimbo)")
        print(f"  acertos na versão ordenada: {ac_ord} de {len(reg_ord)}")
        print(f"  classes distintas previstas nas duas rodadas: {sorted(classes)}")

    # ── BLOCO 1c — A AMOSTRAGEM É UMA TRANSFORMAÇÃO ─────────────────────────
    #
    # O BLOCO 1 amostrou com passo espalhado (v[::300]) — a convenção do projeto, que
    # existe pra evitar viés de cabeça. Mas medido na coluna INTEIRA de `lineitem`
    # (600572 linhas), a adjacência real é outra:
    #
    #     inteira          |Δ| mediano =  50   saltos <=31d = 34,7%
    #     espalhada v[::300] |Δ| mediano = 710   saltos <=31d =  2,6%   <- o que o BLOCO 1 viu
    #     contígua         |Δ| mediano =  51   saltos <=31d = 32,8%
    #
    # A causa é mecânica: `lineitem` está fisicamente ordenada por `l_orderkey`, e as
    # datas de um mesmo pedido são próximas. Passo 300 pula sempre pra outro pedido, e
    # portanto amostra SÓ a distribuição "entre pedidos".
    #
    # Para transformações que leem VIZINHOS, o passo espalhado não é uma amostra —
    # é uma transformação dos dados. Este bloco mede as duas amostragens lado a lado.
    #
    # PREDIÇÃO DECLARADA (antes de rodar):
    #  (a) o classificador vai prever `componentes` de novo nas 7 — a regra lê ORDEM
    #      (ND%) e CONTAGEM de deltas, nunca a MAGNITUDE. Ele é estruturalmente cego
    #      a este regime.
    #  (b) a MEDIÇÃO pode virar pra `delta` nas 4 colunas do TPC-H, porque o alfabeto
    #      cai (1249 -> ~500 deltas) e os saltos ficam pequenos.
    #  Se (a) e (b) se confirmarem juntos, o achado não é "delta ganha" — é que o
    #  classificador tem um ponto cego, e o BLOCO 1 mediu um regime que não existe.
    print("\nBLOCO 1c — CONTRA-PROVA DA AMOSTRAGEM: contígua × espalhada (mesma coluna)")
    print(f"  {'coluna':>18} {'amostra':>10} {'|Δ|med':>7} {'<=31d':>6} {'Δdist':>6} | "
          f"{'predição':>12} {'medido':>12} {'acerto':>7} | {'melhor B':>9}")
    reg_cont = []
    for r in reg:
        db, sql = next((d, s) for nm, d, s in COLUNAS if nm == r["coluna"])
        datas = carrega(db, sql, modo="contigua")
        if not datas:
            continue
        nome = r["coluna"] + "-CONTIGUA"
        cls = classifica(datas)
        _js(INP / f"{nome}.entrada.json", datas)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "run.py::carrega(modo='contigua')", "db": db, "sql": sql,
             "amostragem": f"janela contígua do MEIO, {N_ALVO} linhas",
             "ideia": "PAR DE CONTRA-PROVA DA AMOSTRAGEM: a mesma coluna, só o modo de "
                      "amostrar muda — isola quanto o passo espalhado destrói a adjacência",
             "classificacao": cls, "pin": "corpus Z:/tcf-data/interim — não versionado"})
        m = mede(datas)
        for rot in [x for x, _, _, _ in T.TRANSFORMACOES]:
            if m.get(f"{rot}_rt") is False:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            if m.get(rot) is not None:
                _esc(OUT / f"{nome}.{rot}.tcf",
                     encode(next(t for x, t, _, _ in T.TRANSFORMACOES if x == rot)(datas)))
        cands = {k: v for k, v in m.items()
                 if k in [x for x, _, _, _ in T.TRANSFORMACOES] and isinstance(v, int)
                 and m.get(f"{k}_rt") is not False}
        venc = min(cands, key=cands.get)
        linha = {"coluna": nome, "origem": r["coluna"], **cls, **m,
                 "vencedor_medido": venc, "min_todos": cands[venc],
                 "acerto_predicao": venc == cls["predicao"],
                 "venceu_no_espalhado": r["vencedor_medido"],
                 "delta_abs_mediano_espalhado": r["delta_abs_mediano"],
                 "ganho_vs_ordinal_pct": (round(100 * (1 - cands[venc] / m["ordinal"]), 1)
                                          if isinstance(m.get("ordinal"), int) else None),
                 "CONSTANTE_na_comparacao": "a MESMA coluna e o MESMO n; só o MODO DE AMOSTRAR muda"}
        reg_cont.append(linha)
        _js(OUT / f"{nome}.meta.json", linha)
        print(f"  {r['coluna']:>18} {'espalhada':>10} {r['delta_abs_mediano']:>7} "
              f"{r['pct_delta_ate_31d']:>5.1f}% {r['deltas_distintos']:>6} | "
              f"{r['predicao']:>12} {r['vencedor_medido']:>12} "
              f"{'SIM' if r['acerto_predicao'] else 'NAO':>7} | {r['min_todos']:>9}")
        print(f"  {'':>18} {'CONTIGUA':>10} {cls['delta_abs_mediano']:>7} "
              f"{cls['pct_delta_ate_31d']:>5.1f}% {cls['deltas_distintos']:>6} | "
              f"{cls['predicao']:>12} {venc:>12} "
              f"{'SIM' if linha['acerto_predicao'] else 'NAO':>7} | {cands[venc]:>9}")

    if reg_cont:
        virou = [r for r in reg_cont if r["vencedor_medido"] != r["venceu_no_espalhado"]]
        mesma_pred = sum(1 for r in reg_cont
                         if r["predicao"] == next(x["predicao"] for x in reg
                                                  if x["coluna"] == r["origem"]))
        ac = sum(1 for r in reg_cont if r["acerto_predicao"])
        print(f"\n  (a) o classificador previu O MESMO em {mesma_pred} de {len(reg_cont)} "
              f"ao trocar a amostragem")
        print(f"  (b) o VENCEDOR MEDIDO virou em {len(virou)} de {len(reg_cont)}: "
              f"{[r['origem'] + ': ' + r['venceu_no_espalhado'] + '->' + r['vencedor_medido'] for r in virou] or 'nenhum'}")
        print(f"  acertos da predição na amostragem contígua: {ac} de {len(reg_cont)}")
        if mesma_pred == len(reg_cont) and virou:
            print("  => PONTO CEGO CONFIRMADO: a regra lê ordem e contagem, nunca MAGNITUDE.")

    # ── BLOCO 2 — a CPU do `min()` ampliado ─────────────────────────────────
    print("\nBLOCO 2 — CPU do `min()` ampliado (dev-run declarado: razões, não absolutos)")
    print(f"  {'coluna':>18} {'hoje ms':>9} {'6 cands ms':>11} {'custo':>8} {'pico KB':>9}")
    cpu = []
    for r in reg:
        datas = json.loads((INP / f"{r['coluna']}.entrada.json").read_text(encoding="utf-8"))

        def rota_hoje():
            return min(encode(datas), encode(datas, nature=SPEC_DATA_ISO), key=len)

        def rota_ampliada():
            cands = [encode(datas), encode(datas, nature=SPEC_DATA_ISO)]
            for _rot, tfn, _ifn, _ in T.TRANSFORMACOES:
                v = tfn(datas)
                if v is not None:
                    cands.append(encode(v))
            return min(cands, key=len)

        t_h = crono(rota_hoje) * 1000
        t_a = crono(rota_ampliada) * 1000
        tracemalloc.start()
        rota_ampliada()
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        linha = {"coluna": r["coluna"], "ms_rota_hoje": round(t_h, 2),
                 "ms_rota_ampliada": round(t_a, 2),
                 "custo_pct": round(100 * (t_a / t_h - 1), 1),
                 "pico_KB": round(pico / 1024, 1),
                 "AVISO": "dev-run, máquina não quiescente — razões, não absolutos",
                 "REGUA": "o T-CANDIDATO-SEM-DEDUP mediu +84-93% p/ UM candidato análogo"}
        cpu.append(linha)
        print(f"  {r['coluna']:>18} {t_h:>9.2f} {t_a:>11.2f} {linha['custo_pct']:>+7.1f}% "
              f"{linha['pico_KB']:>9.1f}")

    _js(INT / "colunas-reais.json", reg)
    _js(INT / "colunas-ordenadas.json", reg_ord)
    _js(INT / "colunas-contiguas.json", reg_cont)
    _js(INT / "cpu.json", cpu)
    _js(RAIZ / "resultado.json", {"reais": reg, "ordenadas": reg_ord,
                                  "contiguas": reg_cont, "cpu": cpu, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — date em dado real, e a CPU do `min()` ampliado", "",
         "| coluna | n | k | predição | medido | acerto | ordinal | melhor | ganho |",
         "|---|---|---|---|---|---|---|---|---|"] +
        [f"| [`{r['coluna']}`](./{r['coluna']}.spec-welded.tcf) | {r['n']} | {r['distintos']} | "
         f"{r['predicao']} | **{r['vencedor_medido']}** | {'✓' if r['acerto_predicao'] else '✗'} | "
         f"{r.get('ordinal', '—')} | {r['min_todos']} | {r['ganho_vs_ordinal_pct']}% |"
         for r in reg]) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:15]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
