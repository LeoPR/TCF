"""EXP-017 — alvos mensais de data: bateria probatória. `python run.py`

Regenera `outputs/` e `report.md`. **Sai 0 só se tudo fechar.**

As cinco provas por caso (molde do EXP-016, adaptadas ao que este lab testa):

    1. RT estrito       decode(encode(v)) == v, contra os dados ORIGINAIS
    2. RT do alvo       decode_col(encode_col(v)) == v — o espelho do spec, isolado
    3. determinismo     encode duas vezes -> byte-idêntico
    4. nunca-pior       POR CONSTRUÇÃO neste harness (min sobre superconjunto — a
                        caçada adversarial apontou: como teste, é tautologia; fica como
                        documentação da invariante; a prova falsificável é pós-weld)
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
        # A LACUNA SO' E' INTERPRETAVEL QUANDO A NATURE VENCE o FLOOR (cacada adversarial:
        # quando ela perde, 'ordinal-soldado' e' o baseline emitido — grafia ORIGINAL — e
        # a subtracao compara payloads diferentes; 4 "negativos" do lab eram esse artefato).
        nature_venceu = cands["ordinal-soldado"][1].startswith("#TCF.8 :")
        if not nature_venceu:
            lacuna_rota = None
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
            "nature_venceu_floor": nature_venceu,
            "lacuna_rota_da_nature_B": lacuna_rota,
            "lacuna_rota_pct": (round(lacuna_rota / cands["ordinal-soldado"][0] * 100, 1)
                                if lacuna_rota is not None else None),
            "determinismo": det, "nunca_pior": nunca_pior, "artefato_ok": artefato_ok,
            "pin_ok": pin_ok, "cpu_core_ms": round(cpu_core, 1),
            "cpu_vencedor_ms": round(cpu_venc, 1),
            "mem_core_KiB": round(_mem(lambda: encode(vals)))})
        linhas.append(f"| {nome} | {len(vals)} | {cands['core'][0]} "
                      f"| {cands['ordinal-soldado'][0]} | {cands['ordinal-rota-plena'][0]} "
                      f"| {cands['mes31dia'][0]} | {cands['fimdemes'][0]} | {cands['anomes'][0]} "
                      f"| **{vencedor}** | {round((1 - b_vencedor / justo) * 100, 1)}% "
                      f"| {lacuna_rota if lacuna_rota is not None else 'n/i'} | {'✓' if pin_ok else 'X'} |")
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
    lac = [r for r in reais if (r["lacuna_rota_da_nature_B"] or 0) > 0]
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
**Este relatório incorpora as correções de uma caçada adversarial de 4 lentes**
(613 colunas varridas, 15 variantes realistas construídas) — as ressalvas abaixo
são dela.

## A resposta, com as ressalvas que ela precisa

**Nos dados de fato crus do corpus, os alvos mensais não pagam** — nenhuma das 9
colunas lógicas de data tem cadência mensal (varredura exaustiva: todas têm os 31
dias-do-mês quase uniformes). Ganho mediano real: **{ganho_reais}%** (neste n).

As TRÊS ressalvas que impedem a manchete simples:

1. **O "0%" é propriedade do n amostrado, não do dado**: a mesma coluna TPC-H dá
   0,3% em n=3000 e **18,7% em n=4000** (o candidato ordinal cai num penhasco entre
   n=3850-3900). Instabilidades de pré-passe criam penhascos — ver `T-PENHASCO-INICIO`.
2. **O regime mensal é ALCANÇÁVEL a partir do corpus**: colunas de agregado mensal
   derivadas do mesmo dado real (um registro por mês presente — a forma de qualquer
   tabela de agregado) ganham **1,8× a 9,8×**. O que não tem regime mensal são as
   colunas de FATO cruas.
3. **O "95% sintético" ({ganho_sint}% aqui) é O(n) e frágil**: em n=12 o alvo PERDE;
   com o escorregamento real de fim de semana (~29%) sobra 1,5×; com jitter ±2 dias,
   1,1×. E folha de pagamento (último/5º dia útil) fica NEGATIVA nos 3 alvos — mas um
   4º eixo (dia ÚTIL) recupera 99,0%. **Nenhum conjunto fixo de alvos cobre; é o
   argumento medido para "spec orienta eixos, não manda alvo"** (direção do owner).

## 1. Placar

| onde vence | reais |
|---|---:|
| **ordinal-dia** (o spec de hoje) | {classes_reais.get('ordinal', 0)} |
| alvo **mensal** | {classes_reais.get('mensal', 0)} — ambos por acidente estrutural de 0,1-0,3%, não regime |
| **nenhum** (core sozinho) | {classes_reais.get('nenhum', 0)} |

## 2. O achado transversal: a nature soldada não usa a rota plena

O candidato interno da nature sai de `_encode_column` — só o corpo do core, **sem
polaridade e sem bN** — enquanto a rota flat normal aplica os dois (provado byte-exato:
`encode(vals, nature=SPEC) == header + _encode_column(transformed)` em 20/20 colunas
reais onde a nature vence).

| coluna real | spec soldado | mesmo payload, rota plena | desperdiçado |
|---|---:|---:|---|
{linhas_lac}

Recalibrado pela caçada: **mediana ~5,7% no corpus amplo** (não os 6,7% deste
subconjunto), máx **11,9%** (CPF `socio_cpf` — a lacuna vale para QUALQUER nature),
**variando com n** (a mesma coluna vai de 6,4% em n=200 a 0,24% em n=15000). Os
"negativos" de versões anteriores eram artefato de métrica (a lacuna só é interpretável
quando a nature vence o FLOOR — casos agora marcados `n/i`). E a rota plena **é
nunca-pior por construção** (o FLOOR da polaridade devolve sufixo vazio quando não paga;
stress de 8000 colunas, 0 violações) — o conserto do `T-NATURE-CANDIDATO-BN` é trocar o
corpo do candidato pela rota plena, mantendo o FLOOR nature-vs-baseline que já existe.

## 3. Todos os casos

{tabela}

## 4. As provas — e o que cada uma vale

**RT estrito** e **RT do espelho** são as provas falsificáveis (o guard de re-emissão do
YM veio delas: dígitos Unicode colapsavam payloads — 4ª ocorrência da classe).
**Determinismo** e **artefato-é-o-wire** idem. **"Nunca-pior"** neste harness é
tautologia (min sobre superconjunto) — fica como documentação da invariante; a prova
real é pós-weld. Os **PINs** estão fixados no comportamento medido; os dois casos
`mensal` reais estão anotados como ruído de 0,1-0,3%, não regime.
"""


if __name__ == "__main__":
    raise SystemExit(main())
