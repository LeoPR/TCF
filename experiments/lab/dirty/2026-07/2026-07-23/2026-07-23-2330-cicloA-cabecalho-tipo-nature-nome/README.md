# 2026-07-23-2330 — Ciclo A: cabeçalho single-col (tipo × nature × nome) — **v3**

Primeiro ciclo do [plano de revisão integral do `.8`](../../../notas/2026-06/tcf8-estrutura-plano.md)
(§5 S1), seguindo o **fluxo §3.2** e a convenção do catálogo
[`2026-07-23-0204`](../2026-07-23-0204-api-8-catalogo-de-casos/).

> **v1/v2 DESCARTADAS** — eram manipulação abstrata de strings, sem dataset/JSON/encode/roundtrip, e
> **inventaram comportamento** (um escaping que não existe; a forma (1) "refutada" sem base). O porquê
> e a tabela do que foi inventado × o que é real estão no [`MANIFESTO.md`](MANIFESTO.md#cicloa-v3--reescrita-2026-07-23-correção-do-owner).

## Fluxo por caso (materializado em arquivo)

```
inputs/<ID>-fonte.json                     fonte literal
  -> json.loads
intermediates/<ID>-dataset-consumido.json  o dataset que o TCF consome
  -> tcf.encode(dataset)
outputs/<ID>-wire.tcf                      WIRE REAL (nunca reconstruído à mão)
  -> tcf.decode
outputs/<ID>-dataset.roundtrip.json        RT real
```

`outputs/` só contém o que o TCF **realmente emite**. As gramáticas hipotéticas ficam em
`intermediates/` marcadas como hipótese.

## Casos (11 · RT 8/8 ✅ · 3 fail-loud esperados)

| id | investiga | wire real (linha-0) |
|---|---|---|
| A1 | nada a declarar | *(órfão, sem header)* |
| A2 | forma (1) com nome vazio | `#TCF.8 :cpf` |
| A3 | forma (1) completa | `#TCF.8 doc:cpf` |
| A4 | nome = tag de tipo (`b`) | `#TCF.8 b:cpf` ✅ funciona |
| A5 | nome = discriminador (`M`) | `#TCF.8 M:cpf` ✅ funciona |
| A6 / A6b | nome com `:` / `\n` | **rejeitado** (fail-loud) |
| A6c | `name=` sem `nature=` | **rejeitado** — forma (3) não existe |
| A7 / A8 | bool / int single-col | `#TCF.8H#V\z#:3[]:17b` — **a lacuna** |
| A9 | version-stamp | `#TCF.8` + `\n` |

## As 6 formas do owner — veredito ancorado em wire real

| forma | status | índice 6 | veredito |
|---|---|---|---|
| (1) `#TCF.8 {nome}:{id}` | **REAL** | `' '` | **robusta** — nome `b`/`M` funcionam (A4/A5) |
| (2) `#TCF.8{nome}:{id}` | hipotética | 1º char do NOME | frágil (contraste com A5) |
| (3) `#TCF.8 {nome}` | **não existe** | `' '` | A6c rejeita — rótulo sozinho não é rota |
| (4) `#TCF.8{nome}` | hipotética | 1º char do NOME | **indistinguível de (6)** + frágil |
| (5) `#TCF.8:{id}` | hipotética *sem espaço* | `':'` **livre** | discriminador novo viável (−1 B) |
| (6) `#TCF.8{id}` | hipotética | 1º char do ID | **defensável** — id é namespace FECHADO |

**O cerne — (4) vs (6)**: como *forma* são idênticas (`#TCF.8` + token nu). O que as separa é a
**natureza do token**: **nome** é ABERTO (dado do usuário, não restringível sem quebrar contrato);
**id** é FECHADO (vocabulário do formato, pode excluir `M`/`H` por definição). A intuição do owner de
que 4 e 6 se confundem **confirma-se**.

**Por que (1) não quebra com nome colidente**: o índice 6 é o **espaço** (a marca da rota), então o 1º
char do nome nunca compete com o Eixo-1; o id sai pelo **último** `:`.

**Escaping**: o formato **proíbe**, não escapa (A6/A6b) — contrato fail-loud em vez de sequência de
escape. Simplifica o parse, restringe nomes.

**Combinação que a evidência favorece: (1)+(6)** — espaço marca "tem nome"; ausência marca "token nu
do namespace fechado". A hipótese de que ` ` e `:` desambiguam é *parcialmente* verdadeira: separam as
rotas, mas (2)/(4) seguem expondo o índice 6 a nome arbitrário.

## O que este ciclo NÃO conclui

Não escolhe gramática. Não mede custo em body real nem os critérios de julgamento (§S1.7 inspeção,
§S1.9 streaming, §S1.10 paridade S/M/H). **Nada em `src/tcf/`.**

## Rodar

```
python run.py     # 11 casos · regenera inputs/ intermediates/ outputs/ + result.md
```
