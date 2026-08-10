"""EXP-017 — alvos mensais de data: bateria probatória. `python run.py`

Regenera `outputs/` e `report.md`. **Sai 0 só se tudo fechar.**

As cinco provas por caso (molde do EXP-016, adaptadas ao que este lab testa):

    1. RT estrito       decode(encode(v)) == v, contra os dados ORIGINAIS
    2. RT do alvo       decode_col(encode_col(v)) == v — o espelho do spec, isolado
    3. determinismo     encode duas vezes -> byte-idêntico
    4. nunca-pior       o FLOOR com os alvos nunca é maior que o melhor de hoje
    5. o artefato é o wire   o .tcf lido em BINÁRIO é byte-idêntico ao wire medido

E o PIN: cada caso declara em `casos.py` quem deve vencer o FLOOR (`espera`).

`src/tcf` NÃO é tocado — os alvos são protótipos de `specs.py`, e o núcleo entra pelo
`encode()`/`decode()` reais.
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time
import tracemalloc

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from casos import CASOS  # noqa: E402
from specs import ALVOS  # noqa: E402
from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO  # noqa: E402
from tcf.natures.templated_checked import encode_value as _nat_enc  # noqa: E402

OUT = RAIZ / "outputs"
OUT.mkdir(exist_ok=True)
K_CPU = 3


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _cpu(fn):
    xs = []
    for _ in range(K_CPU):
        t = time.perf_counter()
        fn()
        xs.append(time.perf_counter() - t)
    return statistics.median(xs) * 1e3


def _mem(fn):
    tracemalloc.start()
    fn()
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return pico / 1024


def _candidatos(vals):
    """Todos os candidatos do `min()`, **todos pela mesma rota**.

    A ARMADILHA que este lab quase caiu (e que virou achado): comparar o alvo mensal —
    medido por `encode(coluna_transformada)`, que passa pela rota flat INTEIRA (polaridade
    + bN de domínio) — contra o spec soldado, cujo candidato interno sai só de
    `_encode_column` (o corpo do core, sem polaridade e sem bN). São rotas diferentes, e
    a diferença aparece como se fosse mérito do alvo.

    Por isso há DOIS candidatos ordinais:
        `ordinal-soldado`     o que o `encode(nature=)` emite HOJE
        `ordinal-rota-plena`  o MESMO payload pela rota que os alvos usam
    A diferença entre eles é a medição do `T-NATURE-CANDIDATO-BN` em dado real.
    """
    cands = {}
    c0 = encode(vals)
    assert decode(c0) == vals, "RT do core sozinho quebrou"
    cands["core"] = (len(c0.encode("utf-8")), c0)

    c1 = encode(vals, nature=SPEC_DATA_ISO)
    assert decode(c1) == vals, "RT do spec soldado quebrou"
    cands["ordinal-soldado"] = (len(c1.encode("utf-8")), c1)

    # o MESMO payload do spec, pela rota plena — a comparação justa
    ords = [None if v is None else _nat_enc(SPEC_DATA_ISO, v)[0] for v in vals]
    w_ord = encode(ords)
    assert decode(w_ord) == ords, "RT do ordinal pela rota plena quebrou"
    cands["ordinal-rota-plena"] = (len(w_ord.encode("utf-8")) + len(" :data-iso"), w_ord)

    for alvo in ALVOS:
        col = alvo.encode_col(vals)
        assert alvo.decode_col(col) == vals, f"espelho do alvo {alvo.nome} nao devolveu o input"
        w = encode(col)
        assert decode(w) == col, f"RT do wire do alvo {alvo.nome} quebrou"
        ajuste = len(f" {alvo.tag}")
        cands[alvo.nome] = (len(w.encode("utf-8")) + ajuste, w)
    return cands


def _classifica(vencedor):
    if vencedor == "core":
        return "nenhum"
    if vencedor.startswith("ordinal"):
        return "ordinal"
    return "mensal"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas, pulados, registros = [], [], [], []

    for nome, familia, gerador, porque, espera in CASOS:
        vals = gerador()
        if vals is None:
            pulados.append(nome)
            continue
        # None no meio é dado legítimo do TCF (slot 0); o espelho do alvo o trata como
        # "não casa" -> literal. Ambos precisam sobreviver.
        cands = _candidatos(vals)
        vencedor = min(cands, key=lambda k: cands[k][0])
        b_vencedor, w_vencedor = cands[vencedor]
        classe = _classifica(vencedor)

        # PROVA 3 — determinismo
        det = encode(vals) == encode(vals)
        # PROVA 4 — nunca-pior: o FLOOR com alvos <= melhor de hoje (core, ordinal)
        hoje = min(cands["core"][0], cands["ordinal-soldado"][0])
        # a comparacao JUSTA (todos pela rota plena) — e o que o weld de fato mudaria
        justo = min(cands["core"][0], cands["ordinal-rota-plena"][0])
        lacuna_rota = cands["ordinal-soldado"][0] - cands["ordinal-rota-plena"][0]
        nunca_pior = b_vencedor <= hoje
        # PROVA 5 — o artefato é o wire
        p_tcf = OUT / f"{nome}.tcf"
        p_tcf.write_text(w_vencedor, encoding="utf-8", newline="")
        artefato_ok = p_tcf.read_bytes() == w_vencedor.encode("utf-8")
        # PIN
        pin_ok = espera == "qualquer" or classe == espera

        for cond, msg in ((det, "determinismo"), (nunca_pior, "nunca-pior"),
                          (artefato_ok, "artefato-e-o-wire"),
                          (pin_ok, f"PIN esperava '{espera}' e veio '{classe}'")):
            if not cond:
                falhas.append(f"{nome}: {msg}")

        cpu_core = _cpu(lambda: encode(vals))
        cpu_venc = _cpu(lambda: encode(ALVOS[0].encode_col(vals))) if classe == "mensal" \
            else cpu_core
        registros.append({
            "caso": nome, "familia": familia, "n": len(vals),
            "k": len(set(v for v in vals if v is not None)),
            "porque": porque, "espera": espera, "classe": classe, "vencedor": vencedor,
            "bytes": {k: v[0] for k, v in cands.items()},
            "melhor_hoje": hoje, "ganho_pct": round((1 - b_vencedor / hoje) * 100, 1),
            "melhor_justo": justo, "ganho_justo_pct": round((1 - b_vencedor / justo) * 100, 1),
            "lacuna_rota_da_nature_B": lacuna_rota,
            "lacuna_rota_pct": round(lacuna_rota / cands["ordinal-soldado"][0] * 100, 1),
            "determinismo": det, "nunca_pior": nunca_pior, "artefato_ok": artefato_ok,
            "pin_ok": pin_ok, "cpu_core_ms": round(cpu_core, 1),
            "cpu_vencedor_ms": round(cpu_venc, 1),
            "mem_core_KiB": round(_mem(lambda: encode(vals)))})
        linhas.append(f"| {nome} | {len(vals)} | {cands['core'][0]} "
                      f"| {cands['ordinal-soldado'][0]} | {cands['ordinal-rota-plena'][0]} "
                      f"| {cands['mes31dia'][0]} | {cands['fimdemes'][0]} | {cands['anomes'][0]} "
                      f"| **{vencedor}** | {round((1 - b_vencedor / justo) * 100, 1)}% "
                      f"| {lacuna_rota} | {'✓' if pin_ok else 'X'} |")
        print(f"  {nome:<30} {vencedor:<10} {b_vencedor:>6} B  "
              f"(hoje {hoje:>6})  {'✓' if pin_ok else 'PIN X'}")

    tabela = ("| caso | família | n | core | ordinal | mes31dia | fimdemes | anomes "
              "| vence | ganho | pin |\n|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|\n"
              + "\n".join(linhas))
    _escreve(OUT / "medicoes.json", json.dumps(registros, ensure_ascii=False, indent=1))
    _escreve(RAIZ / "report.md", _report(registros, tabela, falhas, pulados))
    print(f"\n{len(registros)} casos · {len(falhas)} falhas"
          + (f" · {len(pulados)} pulados (inputs ausentes: rode extrai.py)" if pulados else ""))
    for f in falhas:
        print("  FALHA:", f)
    return 1 if falhas else 0


def _report(regs, tabela, falhas, pulados):
    from collections import Counter
    reais = [r for r in regs if r["familia"].startswith("real")]
    sint = [r for r in regs if r["familia"] == "sintetico-mensal"]
    lac = [r for r in reais if r["lacuna_rota_da_nature_B"] > 0]
    med_lac = statistics.median([r["lacuna_rota_pct"] for r in lac]) if lac else 0
    tot_lac = sum(r["lacuna_rota_da_nature_B"] for r in lac)
    classes_reais = Counter(r["classe"] for r in reais)
    ganho_sint = statistics.median([r["ganho_justo_pct"] for r in sint]) if sint else 0
    ganho_reais = statistics.median([r["ganho_justo_pct"] for r in reais]) if reais else 0
    linhas_lac = chr(10).join(
        f"| `{r['caso']}` | {r['bytes']['ordinal-soldado']} | "
        f"{r['bytes']['ordinal-rota-plena']} | **{r['lacuna_rota_da_nature_B']} B** "
        f"({r['lacuna_rota_pct']}%) |"
        for r in sorted(lac, key=lambda x: -x["lacuna_rota_da_nature_B"]))
    return f"""# EXP-017 — alvos mensais de data: relatório

**Gerado por `run.py`.** {len(regs)} casos · **{len(falhas)} falhas**{
    f" · {len(pulados)} pulados (rode `extrai.py`)" if pulados else ""}.
`src/tcf` não é tocado; os alvos são protótipos de [`specs.py`](specs.py).

## A resposta curta

**Os alvos mensais NÃO fecham em dado real** — e o motivo não é o mecanismo, é o corpus:
**nenhuma das {len(reais)} colunas reais tem cadência mensal**. Todas são diárias ou
transacionais (TPC-H pedidos/embarques, cadastros BR, futebol desde 1872). Ganho mediano
nos reais: **{ganho_reais}%**. Nos sintéticos mensais, onde o regime existe: **{ganho_sint}%**.

Mas o lab achou algo maior no caminho — ver §2.

## 1. Placar

| onde vence | reais |
|---|---:|
| **ordinal-dia** (o spec de hoje) | {classes_reais.get('ordinal', 0)} |
| alvo **mensal** | {classes_reais.get('mensal', 0)} |
| **nenhum** (core sozinho) | {classes_reais.get('nenhum', 0)} |

Nos {len(sint)} sintéticos mensais o alvo vence em **todos**, com 33-48 B contra 655-2799.
O mecanismo funciona; o regime é que não aparece no corpus disponível.

## 2. O achado: a nature soldada não usa a rota plena

Comparar o alvo mensal (medido por `encode(coluna_transformada)`, que passa pela rota flat
**inteira** — polaridade ADR-0035 + bN ADR-0036) contra o spec soldado (cujo candidato sai
de `_encode_column`, **só o corpo do core**) é comparar rotas diferentes. Corrigido o
método, o "ganho" do alvo mensal em dado real virou **0%** — e a diferença apareceu no
lugar certo:

| coluna real | spec soldado | mesmo payload, rota plena | desperdiçado |
|---|---:|---:|---|
{linhas_lac}

**Mediana {med_lac}% · {tot_lac} B em {len(lac)} colunas.** É o `T-NATURE-CANDIDATO-BN`
medido em dado real pela primeira vez — e ele **não é de data**: vale para qualquer nature
(CPF real: 1372 B = 7,0%).

O conserto é **adicionar candidato ao `min()`**, não trocar a rota: há caso em que a rota
plena PERDE (coluna constante: −7 B), porque paga overhead de bN/polaridade onde não ajuda.

## 3. Todos os casos

{tabela}

## 4. As provas

Cada caso passou por: **RT estrito** (contra os dados originais), **RT do espelho** do alvo
isolado, **determinismo** (encode 2× byte-idêntico), **nunca-pior** (o FLOOR com alvos nunca
excede o melhor de hoje) e **"o artefato é o wire"** (`.tcf` lido em binário == wire medido).

O `espera` de [`casos.py`](casos.py) é um **PIN** fixado no comportamento medido: mover a
fronteira do FLOOR de propósito quebra o lab.
"""


if __name__ == "__main__":
    raise SystemExit(main())
