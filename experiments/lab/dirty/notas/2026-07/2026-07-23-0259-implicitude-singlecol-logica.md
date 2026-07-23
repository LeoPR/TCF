# Regra de implicitude — a estrutura existe, mas não precisa ser explícita no wire [dispositivo→estudo]

**Data**: 2026-07-23 02:59. Direção do owner (inspecionando o catálogo `2026-07-23-0204`): o TCF é
melhor quando **infere e deixa implícito** o que é óbvio de entrada/saída, explicitando só o
irredutível. Aplicar **uma regra de implicitude por vez**, começando pela **single-column**.

## O gatilho: `encode([1,2,3])` hoje

Wire atual (rota `.8H`, 31 B):
```
#TCF.8H#V\z#:3[]:8n
\3
*3+1|\1
```
Mas `[1,2,3]` **não é hierarquia** (profundidade 0, sem aninhamento) **nem multi-coluna** — é uma
**coluna única tipada**. O `.8H` traz de carona: envelope `#V`, nome-vazio `\z`, coluna de
`#count`, colchete `[]`. Das ~10 marcações, **a única não-inferível é o `n` (número)**.

## A regra (o que é dedutível → implícito)

Para uma **coluna única** (lista de escalares), estruturalmente existe {lista, contagem, tipo}, mas:

| info | existe logicamente? | precisa viajar no wire? |
|---|---|---|
| **lista-ness** (é uma sequência) | sim | **não** — as linhas do body SÃO os elementos (os `\n` são a estrutura) |
| **count** (nº de elementos) | sim | **não** — é o nº de linhas do body (dedução grátis) |
| **estrutura hierárquica** | não (profundidade 0) | **não** — não há |
| **tipo string** | sim | **não** — é o DEFAULT (implícito, sem tag) |
| **tipo number/bool/null** | sim | **SIM** — 1 marcador mínimo (o único irredutível) |
| **spec** (CPF/CNPJ/IP) | sim | **SIM** — a nature JÁ é o tipo (`:id` self-describing) |

**Alvo**: uma **single-col TIPADA** = o body do órfão single-col (que o TCF já sabe fazer) + um
marcador de tipo mínimo, em vez de rotear pro `.8H`. Ex. conceitual: `#TCF.8:n\n*3+1|1\n` (~18 B).
Pela [ADR-0030](../../../../../docs/adr/0030-freeze-single-col-body-at-1.0.md), o body órfão congela
no 1.0 → isto seria um **desvio opt-in MARCADO**, não mutação da base.

Isto **refina o Passo 2**: naquele momento `[1,2,3]`→`.8H` só pra PRESERVAR o tipo — mas preservar
tipo não exige a maquinaria hierárquica.

## Escopo desta rodada (devagar, uma regra por vez)

1. **Registrar** (esta nota) + **testar em massa** o comportamento ATUAL da single-column por tipo,
   pra ter a baseline antes de qualquer código de core. Lab:
   [`2026-07-23-0300-implicitude-singlecol-massa`](../../2026-07/2026-07-23/2026-07-23-0300-implicitude-singlecol-massa/).
2. **string** já é implícita (órfão, 0 B header) — o ponto de partida. Medir **number/bool/null** e
   os **specs** (CPF/CNPJ/IP) pra ver quanto do wire é o tipo vs o overhead do `.8H`.
3. **Equivalência JSON obrigatória**: o RT do TCF tem que bater com o RT do JSON (mesmo objeto
   Python) — "os datasets têm que ser similares". Medido no lab.

## Perguntas abertas (pra decidir antes de código)

- Escopo do desvio-tipado: só **lista de escalares solta** (`[1,2,3]`), ou também **coluna tipada
  dentro de dict** (`{"a":[1,2,3]}`, que hoje também vai pro `.8H`)?
- Marcador de tipo: reusar o `:n`/`:b` do `.8H` num header single-col (`#TCF.8:n`)? Ou um discriminador?
- Interação com nature single-col (`#TCF.8 :cpf`) — a nature já é uma "coluna tipada"; unificar a moldura?

Relaciona: [Passo 2 / api.md](../../../../../docs/reference/api.md) · ADR-0030 (freeze single-col) ·
[T-OPT-INFERENCE](../../../../../tickets/T-OPT-INFERENCE.md) (otimizações por dedução) ·
catálogo [`2026-07-23-0204`](../../2026-07/2026-07-23/2026-07-23-0204-api-8-catalogo-de-casos/).
