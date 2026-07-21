"""A matriz e' DADO CONGELADO (`cases.json`), nao codigo — regra R2 do desenho.

Se o `.9` gerar a lista de casos por codigo, o codigo deriva (alguem adiciona um
dataset, muda um `limit`, renomeia um kwarg) e o join `.8`<->`.9` fica
silenciosamente errado. O run `.9` consome o MESMO arquivo que o `.8` consumiu e
aborta em qualquer caso ausente.

Este modulo gera o arquivo UMA vez. Depois disso o arquivo manda, nao ele.

    python -m bench_perf.cases            # escreve scripts/bench_perf/cases.json

Os 11 vetores viram as coordenadas do `case_id`. Comparabilidade = mesmo ponto no
espaco, entao TODO eixo vai gravado mesmo quando esta' no default.
"""

from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# ------------------------------------------------------------------ niveis

CAMINHOS_PLANOS = ("tcf-flat", "json-ref-str", "csv-ref", "repr-null")
FORMAS_PLANAS = ("flat-mixed", "free-text", "structured", "low-entropy")
FORMAS_ANINHADAS = ("nested-object", "nested-array", "nested-optional")

# V6 — OFAT a partir da base (R=1e4, C=4, L=32, K=0.1) + 4 cantos de interacao
BASE = {"R": 10_000, "C": 4, "L": 32, "K": 0.1}
PONTOS_ESCALA = [
    ("base",   dict(BASE)),
    ("R1e2",   {**BASE, "R": 100}),
    ("R1e3",   {**BASE, "R": 1_000}),
    ("R1e5",   {**BASE, "R": 100_000}),
    ("R6e5",   {**BASE, "R": 600_000}),
    ("C1",     {**BASE, "R": 2_000, "C": 1}),
    ("C8",     {**BASE, "R": 2_000, "C": 8}),
    ("C32",    {**BASE, "R": 2_000, "C": 32}),
    ("C128",   {**BASE, "R": 2_000, "C": 128}),
    ("L8",     {**BASE, "L": 8}),
    ("L128",   {**BASE, "L": 128}),
    ("L512",   {**BASE, "L": 512}),
    ("K0001",  {**BASE, "K": 0.001}),
    ("K001",   {**BASE, "K": 0.01}),
    ("K1",     {**BASE, "K": 1.0}),
    ("cantoRC-min",  {"R": 100, "C": 1, "L": 32, "K": 0.1}),
    ("cantoRC-larg", {"R": 100, "C": 128, "L": 32, "K": 0.1}),
    ("cantoRC-alto", {"R": 100_000, "C": 1, "L": 32, "K": 0.1}),
    ("cantoRC-both", {"R": 100_000, "C": 32, "L": 32, "K": 0.1}),
]
ORCAMENTO_CELULAS = 4_000_000     # R*C acima disso sai dropped:"over-budget"

COMPRESSORES_DEFAULT = ("gzip-6", "zstd-3", "brotli-5")
COMPRESSORES_MAX = ("gzip-9", "zstd-19", "brotli-11")

SEED = 20260721


def _caso(bloco: str, **v) -> dict:
    vet = {
        "caminho": v.get("caminho", "tcf-flat"),
        "forma": v.get("forma", "flat-mixed"),
        "escala": v.get("escala", {"point_id": "base", **BASE}),
        "granularidade": v.get("granularidade", "call"),
        "concorrencia": v.get("concorrencia", {"internal": "serial", "test": "t1"}),
        "knobs": v.get("knobs", {}),
        "compressao": v.get("compressao", "none"),
        "accel": v.get("accel", "cython"),
    }
    e = vet["escala"]
    fonte = v.get("fonte", "synth")
    # a fonte E' coordenada: adult-20k e lineitem-20k no mesmo ponto sao celulas distintas
    cid = "|".join([
        vet["caminho"], fonte, vet["forma"], e.get("point_id", "?"), vet["granularidade"],
        f'{vet["concorrencia"]["internal"]}+{vet["concorrencia"]["test"]}',
        ",".join(f"{k}={vv}" for k, vv in sorted(vet["knobs"].items())) or "-",
        vet["compressao"], vet["accel"],
    ])
    return {"case_id": cid, "bloco": bloco, "fonte": fonte,
            "vectors": vet, "nota": v.get("nota", "")}


def gerar() -> list[dict]:
    cs: list[dict] = []

    # B0 — Regua: calibra e mede o proprio instrumento (V11)
    for pino in ("D1-D9", "D17a", "real-world"):
        cs.append(_caso("B0", fonte=f"pin-{pino}", forma="flat-mixed",
                        nota=f"validate-pins cronometrado: {pino}"))
    for i in range(3):
        cs.append(_caso("B0", fonte="sentinela", forma="flat-mixed",
                        escala={"point_id": f"sentinela{i}", **BASE},
                        nota="piso de ruido / deriva termica"))
    cs.append(_caso("B0", fonte="sentinela", forma="flat-mixed",
                    concorrencia={"internal": "serial", "test": "t4"},
                    escala={"point_id": "sentinela-concorrente", **BASE},
                    nota="sentinela solo vs concorrente (contencao do proprio teste)"))
    cs.append(_caso("B0", fonte="sondas", nota="smoke de cada sonda (wall/cpu/heap/rss)"))

    # B1 — Caminho x Forma no pivo (o denominador do estudo)
    for cam in ("tcf-flat", "json-ref-str", "csv-ref"):
        for forma in ("flat-mixed", "free-text", "structured"):
            cs.append(_caso("B1", caminho=cam, forma=forma))

    # B2 — Escala: 2 caminhos x 19 pontos
    for cam in ("tcf-flat", "json-ref-str"):
        for pid, esc in PONTOS_ESCALA:
            cs.append(_caso("B2", caminho=cam, forma="flat-mixed",
                            escala={"point_id": pid, **esc}))

    # B3 — Granularidade
    for pid in ("R1e3", "base", "R1e5"):
        esc = dict(next(e for p, e in PONTOS_ESCALA if p == pid))
        for forma in ("flat-mixed", "free-text"):
            cs.append(_caso("B3", forma=forma, granularidade="layer",
                            escala={"point_id": pid, **esc},
                            nota="perfil por camada (serial; monkeypatch nao atravessa spawn)"))
        cs.append(_caso("B3", granularidade="candidate", knobs={"fallback": False},
                        escala={"point_id": pid, **esc},
                        nota="A/B do custo dos candidatos perdedores do _best_of"))
    esc_c8 = dict(next(e for p, e in PONTOS_ESCALA if p == "C8"))
    for i in range(8):
        cs.append(_caso("B3", granularidade="column",
                        escala={"point_id": f"C8-col{i}", **esc_c8},
                        nota="decomposicao por coluna (amostras independentes)"))
    cs.append(_caso("B3", knobs={"side_outputs": True},
                    nota="mede a alegacao 'overhead zero' do ADR-0014 — nunca foi medida"))

    # B4 — Concorrencia: interno x teste (a hipotese do owner, como interacao)
    for tabela in ("adult-20k", "lineitem-20k"):
        for w in ("p2", "p4", "p8"):
            cs.append(_caso("B4", fonte=tabela, concorrencia={"internal": w, "test": "t1"}))
        for t in ("t2", "t4", "t8"):
            cs.append(_caso("B4", fonte=tabela, concorrencia={"internal": "serial", "test": t},
                            nota="paralelismo do TESTE: N encodes independentes concorrentes"))
        cs.append(_caso("B4", fonte=tabela, concorrencia={"internal": "p4", "test": "t2"},
                        nota="interacao interno x teste"))
        cs.append(_caso("B4", fonte=tabela, concorrencia={"internal": "p4", "test": "t1"},
                        granularidade="process-tree",
                        nota="memoria por arvore de processos (tracemalloc do pai nao ve filhos)"))

    # B5 — Hierarquico .8H
    for cam in ("tcf-8h", "json-ref-nested"):
        for forma in FORMAS_ANINHADAS:
            for pid in ("R1e3", "base"):
                esc = dict(next(e for p, e in PONTOS_ESCALA if p == pid))
                cs.append(_caso("B5", caminho=cam, forma=forma,
                                escala={"point_id": pid, **esc}))
    cs.append(_caso("B5", caminho="tcf-8h", forma="flat-mixed",
                    nota="nao-regressao do .8H sobre dado plano"))
    cs.append(_caso("B5", caminho="json-ref-typed", forma="structured",
                    nota="isola o custo de TIPAR (e' do dado, nao do TCF)"))

    # B6 — Compressao: MESMO compressor e nivel em TODOS os caminhos
    for cam in ("tcf-flat", "json-ref-str", "csv-ref", "tcf-8h"):
        for cp in COMPRESSORES_DEFAULT:
            cs.append(_caso("B6", caminho=cam, compressao=cp,
                            nota="cadeia total: serialize+compress / decompress+parse"))
    for cam in ("tcf-flat", "json-ref-str"):
        for cp in COMPRESSORES_MAX:
            cs.append(_caso("B6", caminho=cam, compressao=cp))

    # B7 — Acelerador Cython vs puro (o "2.1-2.3x" que hoje vive num comentario)
    for forma in ("free-text", "flat-mixed"):
        for pid in ("R1e3", "base", "R1e5"):
            esc = dict(next(e for p, e in PONTOS_ESCALA if p == pid))
            cs.append(_caso("B7", forma=forma, accel="pure",
                            escala={"point_id": pid, **esc},
                            nota="processo filho dedicado: monkeypatch global contaminaria o resto"))

    # B8 — Knobs restantes
    for knob in ({"sort_by": "col00"}, {"drop_names": True}, {"nature": "cpf"},
                 {"min_len": 3}, {"pre_pass": False}, {"hcc_seq_rle": False},
                 {"obat_shape_preserve": False}):
        cs.append(_caso("B8", knobs=knob))

    return cs


def main() -> int:
    brutos = gerar()
    # Dedup por case_id: mesma coordenada = MESMA medicao. Um ponto citado por dois
    # blocos (ex: `base` em B1 e B2) e' uma celula so', com os dois blocos anotados —
    # medir duas vezes o mesmo ponto so' gastaria relogio e confundiria o join.
    casos: list[dict] = []
    por_id: dict[str, dict] = {}
    for c in brutos:
        ja = por_id.get(c["case_id"])
        if ja is None:
            c["blocos"] = [c.pop("bloco")]
            por_id[c["case_id"]] = c
            casos.append(c)
        else:
            b = c["bloco"]
            if b not in ja["blocos"]:
                ja["blocos"].append(b)
            if c["nota"] and c["nota"] not in ja["nota"]:
                ja["nota"] = (ja["nota"] + " · " + c["nota"]).strip(" ·")
    n_dedup = len(brutos) - len(casos)
    for c in casos:                                  # guarda de orcamento (V6)
        e = c["vectors"]["escala"]
        if e.get("R", 0) * e.get("C", 0) > ORCAMENTO_CELULAS:
            c["dropped"] = "over-budget"
    saida = {
        "schema": "perf-baseline-09/cases-v1",
        "seed": SEED,
        "orcamento_celulas": ORCAMENTO_CELULAS,
        "n_casos": len(casos),
        "n_dedup": n_dedup,
        "por_bloco": {b: sum(1 for c in casos if b in c["blocos"])
                      for b in sorted({b for c in casos for b in c["blocos"]})},
        "casos": casos,
    }
    p = AQUI / "cases.json"
    p.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"{len(casos)} celulas unicas ({n_dedup} deduplicadas) -> {p}")
    for b, n in saida["por_bloco"].items():
        print(f"  {b}: {n}")
    n_drop = sum(1 for c in casos if c.get("dropped"))
    if n_drop:
        print(f"  (over-budget: {n_drop})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
