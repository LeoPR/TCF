"""EXP-017 — alvos mensais de data: bateria probatória. `python run.py`

Regenera `inputs/`, `intermediates/`, `outputs/` e `report.md`. **Sai 0 só se tudo fechar.**

## Rastreabilidade (refeita 2026-08-10 a pedido do owner)

A versão anterior deste lab falhava a inspeção: olhando `outputs/valv-ym-unicode.tcf`
não dava pra saber qual input o gerou, com que parâmetros, nem se passou no round-trip.
Violava a convenção canônica (`dirty-lab-convencoes.md`, obrigatória desde 2026-07-05):
sem `intermediates/`, sem `datasets-provenance.md`, **zero** `roundtrip.json`, inputs
nomeados por FONTE e não por CASO, e `outputs/` acumulando lixo de execuções anteriores.

Agora, para CADA caso `<c>`, o disco conta a história inteira:

    inputs/<c>.entrada.json            o que entrou (sintético MATERIALIZADO também)
    inputs/<c>.fonte.json              procedência: gerador, ideia, pin, n/k, hash
    intermediates/<c>.candidatos.json  todos os candidatos: bytes, rota, o que ficou
                                       CONSTANTE na comparação, e quem venceu
    intermediates/<c>.payloads.json    a coluna transformada por cada alvo (amostra+hash)
    outputs/<c>.tcf                    o wire vencedor
    outputs/<c>.roundtrip.json         decode(wire) — **diff contra a entrada**
    outputs/INDEX.md                   nome -> ideia -> input -> wire -> RT -> veredito

`inputs/<c>.entrada.json` e `outputs/<c>.roundtrip.json` são escritos com a MESMA
formatação: a contra-prova é `diff` dar vazio. O `run.py` faz esse assert também.

`outputs/` e `intermediates/` são **limpos** no início — artefato órfão de execução
anterior é indistinguível de resultado atual, e foi exatamente o que aconteceu
(`real-football.tcf` sobreviveu a um rename de caso).

## As provas por caso

    1. RT estrito       decode(encode(v)) == v, contra os dados ORIGINAIS
    2. RT do alvo       decode_col(encode_col(v)) == v — o espelho do spec, isolado
    3. RT em ARQUIVO    outputs/<c>.roundtrip.json == inputs/<c>.entrada.json (diffável)
    4. determinismo     encode duas vezes -> byte-idêntico
    5. nunca-pior       POR CONSTRUÇÃO neste harness (min sobre superconjunto — a caçada
                        adversarial apontou que, como teste, é tautologia; fica como
                        documentação da invariante; a prova falsificável é pós-weld)
    6. o artefato é o wire   o .tcf lido em BINÁRIO é byte-idêntico ao wire medido

E o PIN: cada caso declara em `casos.py` quem deve vencer o FLOOR (`espera`).

`src/tcf` NÃO é tocado — os alvos são protótipos de `specs.py`, e o núcleo entra pelos
`encode()`/`decode()` reais.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
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

INP = RAIZ / "inputs"
INT = RAIZ / "intermediates"
OUT = RAIZ / "outputs"
K_CPU = 3

# A formatação é a MESMA na entrada e no roundtrip: a contra-prova é o `diff` dar vazio.
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _escreve(p: pathlib.Path, t: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _json(p: pathlib.Path, obj) -> None:
    _escreve(p, json.dumps(obj, **JSON_KW))


def _hash(vals) -> str:
    return hashlib.sha256(json.dumps(vals, **JSON_KW).encode("utf-8")).hexdigest()[:12]


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


def _limpa() -> None:
    """Artefato órfão é indistinguível de resultado atual — some antes de gerar.

    `inputs/fontes/` NÃO é limpo: é o corpus extraído de Z: por `extrai.py`, que roda
    separado (e o lab tem de funcionar sem Z:).
    """
    for d in (INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for padrao in ("*.entrada.json", "*.fonte.json"):
        for p in INP.glob(padrao):
            p.unlink()
    INP.mkdir(exist_ok=True)


def _candidatos(vals):
    """Todos os candidatos do `min()`, **todos pela mesma rota**.

    A ARMADILHA que este lab já caiu (e que virou achado): comparar o alvo mensal —
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
    cands["core"] = (len(c0.encode("utf-8")), c0, "encode(vals)")

    c1 = encode(vals, nature=SPEC_DATA_ISO)
    assert decode(c1) == vals, "RT do spec soldado quebrou"
    cands["ordinal-soldado"] = (len(c1.encode("utf-8")), c1,
                                "encode(vals, nature=SPEC_DATA_ISO)")

    ords = [None if v is None else _nat_enc(SPEC_DATA_ISO, v)[0] for v in vals]
    w_ord = encode(ords)
    assert decode(w_ord) == ords, "RT do ordinal pela rota plena quebrou"
    cands["ordinal-rota-plena"] = (len(w_ord.encode("utf-8")) + len(" :data-iso"), w_ord,
                                   "encode(encode_value(SPEC_DATA_ISO, v)) + tag")

    payloads = {}
    for alvo in ALVOS:
        col = alvo.encode_col(vals)
        assert alvo.decode_col(col) == vals, f"espelho do alvo {alvo.nome} nao devolveu o input"
        w = encode(col)
        assert decode(w) == col, f"RT do wire do alvo {alvo.nome} quebrou"
        cands[alvo.nome] = (len(w.encode("utf-8")) + len(f" {alvo.tag}"), w,
                            f"encode({alvo.nome}.encode_col(v)) + tag '{alvo.tag}'")
        payloads[alvo.nome] = col
    return cands, payloads, ords


def _classifica(vencedor):
    if vencedor == "core":
        return "nenhum"
    if vencedor.startswith("ordinal"):
        return "ordinal"
    return "mensal"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    linhas, falhas, pulados, registros = [], [], [], []

    for nome, familia, gerador, porque, espera in CASOS:
        vals = gerador()
        if vals is None:
            pulados.append(nome)
            continue

        # ── inputs/: o que entrou, POR CASO (sintético materializado também) ──
        p_entrada = INP / f"{nome}.entrada.json"
        _json(p_entrada, vals)
        # SIDECAR do input (padrão do EXP-016 + manifesto-por-input dos labs dirty): a
        # `.entrada.json` é o array PURO — tem de ser diffável contra o roundtrip. Os
        # metadados moram ao lado, senão o diff nunca fecharia.
        _json(INP / f"{nome}.fonte.json", {
            "_o_que_e": f"procedência da entrada do caso {nome}",
            "caso": nome, "familia": familia, "ideia": porque, "pin_espera": espera,
            "gerador": getattr(gerador, "__name__", "lambda em casos.py"),
            "n": len(vals), "k": len(set(v for v in vals if v is not None)),
            "sha256_12": _hash(vals), "amostra_6": vals[:6],
            "entrada": f"{nome}.entrada.json"})

        cands, payloads, ords = _candidatos(vals)
        vencedor = min(cands, key=lambda k: cands[k][0])
        b_vencedor, w_vencedor, _cmd = cands[vencedor]
        classe = _classifica(vencedor)
        hoje = min(cands["core"][0], cands["ordinal-soldado"][0])
        justo = min(cands["core"][0], cands["ordinal-rota-plena"][0])
        lacuna = cands["ordinal-soldado"][0] - cands["ordinal-rota-plena"][0]
        # A LACUNA SO' E' INTERPRETAVEL QUANDO A NATURE VENCE o FLOOR (caçada adversarial:
        # quando ela perde, 'ordinal-soldado' é o baseline emitido — grafia ORIGINAL — e a
        # subtração compara payloads diferentes; 4 "negativos" do lab eram esse artefato).
        nature_venceu = cands["ordinal-soldado"][1].startswith("#TCF.8 :")
        if not nature_venceu:
            lacuna = None

        # ── intermediates/: como se chegou lá ──
        _json(INT / f"{nome}.candidatos.json", {
            "caso": nome, "ideia": porque,
            "entrada": f"../inputs/{nome}.entrada.json",
            "entrada_hash": _hash(vals), "n": len(vals),
            "k": len(set(v for v in vals if v is not None)),
            "CONSTANTE_na_comparacao": (
                "mesmo input, mesma rota flat single-col, mesmo ajuste de header por tag; "
                "varia SÓ o payload de cada candidato"),
            "candidatos": {k: {"bytes": v[0], "como": v[2],
                               "header": v[1].split("\n")[0][:32]}
                           for k, v in cands.items()},
            "vencedor": vencedor, "classe": classe,
            "melhor_hoje": hoje, "melhor_justo": justo,
            "nature_venceu_floor": nature_venceu,
            "lacuna_rota_da_nature_B": lacuna,
            "wire": f"../outputs/{nome}.tcf",
            "roundtrip": f"../outputs/{nome}.roundtrip.json"})
        _json(INT / f"{nome}.payloads.json", {
            "caso": nome,
            "nota": "a coluna TRANSFORMADA por cada alvo — o 'como' de cada candidato",
            "ordinal_dia": {"amostra_10": ords[:10], "hash": _hash(ords)},
            **{a: {"amostra_10": c[:10], "hash": _hash(c)} for a, c in payloads.items()}})

        # ── outputs/: o wire + a CONTRA-PROVA diffável ──
        p_tcf = OUT / f"{nome}.tcf"
        _escreve(p_tcf, w_vencedor)
        volta = decode(w_vencedor)
        if vencedor in payloads:                      # wire de payload transformado
            alvo = next(a for a in ALVOS if a.nome == vencedor)
            volta = alvo.decode_col(volta)
        elif vencedor == "ordinal-rota-plena":
            volta = [None if p is None else SPEC_DATA_ISO.decode_value(p) for p in volta]
        p_rt = OUT / f"{nome}.roundtrip.json"
        _json(p_rt, volta)
        rt_arquivo_pre = p_rt.read_bytes() == p_entrada.read_bytes()

        # SIDECAR de procedência: responde "o que gerou ESTE arquivo?" sem sair da pasta.
        # Foi o buraco que o owner apontou olhando `valv-ym-unicode.tcf`.
        _json(OUT / f"{nome}.meta.json", {
            "_o_que_e": f"procedência de {nome}.tcf — o wire vencedor deste caso",
            "ideia_do_caso": porque,
            "entrada": {"arquivo": f"../inputs/{nome}.entrada.json",
                        "sha256_12": _hash(vals), "n": len(vals),
                        "k": len(set(v for v in vals if v is not None))},
            "parametros": {"rota": "single-col flat", "candidato_vencedor": vencedor,
                           "como_foi_gerado": cands[vencedor][2],
                           "header_do_wire": w_vencedor.split(chr(10))[0][:40]},
            "bytes": {
                "medido_no_relatorio": b_vencedor,
                "tamanho_do_arquivo_tcf": len(w_vencedor.encode("utf-8")),
                "_por_que_podem_diferir": (
                    "os ALVOS-protótipo pagam um ajuste de header pela tag hipotética "
                    "(':data-mes' etc.), que ainda não existe na gramática — o número do "
                    "relatório inclui esse ajuste, o arquivo é o wire sem ele. Para "
                    "`core` e `ordinal-soldado` os dois coincidem.")},
            "contra_prova": {"arquivo": f"{nome}.roundtrip.json",
                             "como_conferir": (f"diff inputs/{nome}.entrada.json "
                                               f"outputs/{nome}.roundtrip.json  # vazio = ok"),
                             "passou": rt_arquivo_pre},
            "decisao_completa": f"../intermediates/{nome}.candidatos.json"})

        # PROVA 3 — a contra-prova é o diff dar vazio
        rt_arquivo = rt_arquivo_pre
        det = encode(vals) == encode(vals)
        artefato_ok = p_tcf.read_bytes() == w_vencedor.encode("utf-8")
        nunca_pior = b_vencedor <= hoje
        pin_ok = espera == "qualquer" or classe == espera
        for cond, msg in ((rt_arquivo, "RT em ARQUIVO (roundtrip.json != entrada.json)"),
                          (det, "determinismo"), (nunca_pior, "nunca-pior"),
                          (artefato_ok, "artefato-e-o-wire"),
                          (pin_ok, f"PIN esperava '{espera}' e veio '{classe}'")):
            if not cond:
                falhas.append(f"{nome}: {msg}")

        registros.append({
            "caso": nome, "familia": familia, "n": len(vals),
            "k": len(set(v for v in vals if v is not None)),
            "porque": porque, "espera": espera, "classe": classe, "vencedor": vencedor,
            "bytes": {k: v[0] for k, v in cands.items()},
            "melhor_hoje": hoje, "ganho_pct": round((1 - b_vencedor / hoje) * 100, 1),
            "melhor_justo": justo, "ganho_justo_pct": round((1 - b_vencedor / justo) * 100, 1),
            "nature_venceu_floor": nature_venceu, "lacuna_rota_da_nature_B": lacuna,
            "lacuna_rota_pct": (round(lacuna / cands["ordinal-soldado"][0] * 100, 1)
                                if lacuna is not None else None),
            "rt_arquivo": rt_arquivo, "determinismo": det, "nunca_pior": nunca_pior,
            "artefato_ok": artefato_ok, "pin_ok": pin_ok,
            "entrada": f"inputs/{nome}.entrada.json", "wire": f"outputs/{nome}.tcf",
            "roundtrip": f"outputs/{nome}.roundtrip.json",
            "cpu_core_ms": round(_cpu(lambda: encode(vals)), 1),
            "mem_core_KiB": round(_mem(lambda: encode(vals)))})
        linhas.append(f"| {nome} | {len(vals)} | {cands['core'][0]} "
                      f"| {cands['ordinal-soldado'][0]} | {cands['ordinal-rota-plena'][0]} "
                      f"| {cands['mes31dia'][0]} | {cands['fimdemes'][0]} | {cands['anomes'][0]} "
                      f"| **{vencedor}** | {round((1 - b_vencedor / justo) * 100, 1)}% "
                      f"| {lacuna if lacuna is not None else 'n/i'} | {'✓' if pin_ok else 'X'} |")
        print(f"  {nome:<30} {vencedor:<20} {b_vencedor:>6} B  {'✓' if pin_ok else 'PIN X'}"
              f"{'' if rt_arquivo else '  RT-ARQUIVO X'}")

    tabela = ("| caso | n | core | ord-soldado | ord-rota-plena | mes31dia | fimdemes "
              "| anomes | vence | ganho justo | lacuna rota | pin |\n"
              "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|\n"
              + "\n".join(linhas))
    _json(OUT / "medicoes.json", registros)
    _escreve(OUT / "INDEX.md", _index(registros))
    _escreve(RAIZ / "report.md", _report(registros, tabela, falhas, pulados))
    print(f"\n{len(registros)} casos · {len(falhas)} falhas"
          + (f" · {len(pulados)} pulados (rode extrai.py)" if pulados else ""))
    for f in falhas:
        print("  FALHA:", f)
    print("\nÍndice de inspeção: outputs/INDEX.md")
    return 1 if falhas else 0


def _index(regs):
    """O índice que responde 'o que gerou este arquivo?' sem abrir o código."""
    por_fam = {}
    for r in regs:
        por_fam.setdefault(r["familia"], []).append(r)
    secoes = []
    for fam, rs in por_fam.items():
        linhas = "\n".join(
            f"| [`{r['caso']}.tcf`]({r['caso']}.tcf) | {r['porque']} "
            f"| [`{r['caso']}.entrada.json`](../inputs/{r['caso']}.entrada.json) "
            f"(n={r['n']}, k={r['k']}) | `{r['vencedor']}` · {r['bytes'][r['vencedor']]} B "
            f"| [`.roundtrip.json`]({r['caso']}.roundtrip.json) {'✓' if r['rt_arquivo'] else 'X'} "
            f"| {'✓' if r['pin_ok'] else 'X'} (`{r['espera']}`) |"
            for r in rs)
        secoes.append(f"### {fam}\n\n"
                      "| wire | a ideia do caso | entrada | candidato vencedor "
                      "| contra-prova | pin |\n|---|---|---|---|---|---|\n" + linhas)
    corpo = chr(10).join(secoes)
    return f"""# Índice de inspeção — EXP-017

**Gerado por `run.py`.** Uma linha por artefato: o que ele é, o que o gerou, e onde está
a prova. Cada `.tcf` desta pasta tem aqui a sua origem completa.

## Como conferir um caso, sem ler código

```
1. o que entrou:            inputs/<caso>.entrada.json
2. como se decidiu:         intermediates/<caso>.candidatos.json   (todos os candidatos,
                                  bytes, e o que ficou CONSTANTE na comparação)
3. o payload de cada alvo:  intermediates/<caso>.payloads.json
4. o wire emitido:          outputs/<caso>.tcf
5. a CONTRA-PROVA:          diff inputs/<caso>.entrada.json outputs/<caso>.roundtrip.json
                                  -> tem de sair VAZIO
```

O `run.py` já faz esse `diff` como assert (prova 3) e **falha** se divergir.

{corpo}

## Legenda

- **candidato vencedor** — quem ganhou o `min()`: `core` (só o núcleo), `ordinal-soldado`
  (o `SPEC_DATA_ISO` como o encoder o emite hoje), `ordinal-rota-plena` (mesmo payload
  pela rota flat inteira), ou um dos alvos-protótipo (`mes31dia`/`fimdemes`/`anomes`).
- **pin** — o que `casos.py` declarava que deveria vencer. Divergir **quebra o lab**.
- **contra-prova** — `roundtrip.json` byte-idêntico à `entrada.json`.
"""


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
Índice de inspeção artefato-a-artefato: [`outputs/INDEX.md`](outputs/INDEX.md).
**Este relatório incorpora as correções de uma caçada adversarial de 4 lentes**
(613 colunas varridas, 15 variantes realistas construídas) — as ressalvas abaixo são dela.

## A resposta, com as ressalvas que ela precisa

**Nos dados de fato crus do corpus, os alvos mensais não pagam** — nenhuma das 9 colunas
lógicas de data tem cadência mensal (varredura exaustiva: todas têm os 31 dias-do-mês
quase uniformes). Ganho mediano real: **{ganho_reais}%** (neste n).

As TRÊS ressalvas que impedem a manchete simples:

1. **O "0%" é propriedade do n amostrado, não do dado**: a mesma coluna TPC-H dá 0,3% em
   n=3000 e **18,7% em n=4000** (o candidato ordinal cai num penhasco entre n=3850-3900).
   Instabilidades de pré-passe criam penhascos — ver `T-PENHASCO-INICIO`.
2. **O regime mensal é ALCANÇÁVEL a partir do corpus**: colunas de agregado mensal
   derivadas do mesmo dado real (um registro por mês presente) ganham **1,8× a 9,8×**. O
   que não tem regime mensal são as colunas de FATO cruas.
3. **O "{ganho_sint}% sintético" é O(n) e frágil**: em n=12 o alvo PERDE; com o
   escorregamento real de fim de semana (~29%) sobra 1,5×; com jitter ±2 dias, 1,1×. E
   folha de pagamento (último/5º dia útil) fica NEGATIVA nos 3 alvos — mas um 4º eixo
   (dia ÚTIL) recupera 99,0%. **Nenhum conjunto fixo de alvos cobre; é o argumento medido
   para "spec orienta eixos, não manda alvo"**
   ([triagem](../../../../docs/theory/spec-orienta-nao-manda-triagem.md)).

## 1. Placar

| onde vence | reais |
|---|---:|
| **ordinal-dia** (o spec de hoje) | {classes_reais.get('ordinal', 0)} |
| alvo **mensal** | {classes_reais.get('mensal', 0)} — por acidente estrutural de 0,1-0,3%, não regime |
| **nenhum** (core sozinho) | {classes_reais.get('nenhum', 0)} |

## 2. O achado transversal: a nature soldada não usa a rota plena

O candidato interno da nature sai de `_encode_column` — só o corpo do core, **sem
polaridade e sem bN** — enquanto a rota flat normal aplica os dois (provado byte-exato em
20/20 colunas reais onde a nature vence).

| coluna real | spec soldado | mesmo payload, rota plena | desperdiçado |
|---|---:|---:|---|
{linhas_lac}

Recalibrado pela caçada: **mediana ~5,7% no corpus amplo** (não os {med_lac}% deste
subconjunto de {len(lac)} colunas, {tot_lac} B), máx **11,9%** (CPF `socio_cpf` — vale
para QUALQUER nature), **variando com n** (6,4% em n=200 → 0,24% em n=15000). E a rota
plena é **nunca-pior por construção** (stress de 8000 colunas, 0 violações) — o conserto
do `T-NATURE-CANDIDATO-BN` é trocar o corpo do candidato pela rota plena, mantendo o
FLOOR nature-vs-baseline que já existe.

## 3. Todos os casos

{tabela}

## 4. As provas — e o que cada uma vale

**RT estrito**, **RT do espelho** e **RT em arquivo** (`diff` entrada × roundtrip) são as
falsificáveis — o guard de re-emissão do YM veio delas (dígitos Unicode colapsavam
payloads, 4ª ocorrência da classe). **Determinismo** e **artefato-é-o-wire** idem.
**"Nunca-pior"** neste harness é tautologia (min sobre superconjunto) — fica como
documentação da invariante; a prova real é pós-weld. Os **PINs** estão fixados no
comportamento medido.
"""


if __name__ == "__main__":
    raise SystemExit(main())
