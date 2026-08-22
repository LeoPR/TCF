---
title: T-API-SCHEMA-PRESCRITIVO — o objeto Schema (forma longa do `schema=`) como portador do contrato
status: open
priority: P2
created: 2026-08-22
updated: 2026-08-22
target: "pré-1.0 (aditivo sobre o schema= do ADR-0047; nada muda no wire)"
blocked-by: []
related:
  - docs/adr/0047-schema-parametro-unico-de-spec.md
  - docs/adr/0041-spec-id-tres-planos.md
  - tickets/T-FMT-CONTRACT-SIGNATURE.md
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md
  - experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0600-quatro-camadas/
---

# T-API-SCHEMA-PRESCRITIVO — o objeto `Schema`

**[dispositivo → registro. Nada em `src/tcf` sem aprovação.]**

Registro pedido pelo owner (2026-08-22, ao aprovar o `schema=` do ADR-0047):

> *"registre que quero o Schema, pois ele é mais estruturado pra isso e posso colocar mais
> coisas depois, além de poder reaproveitar porque existe a ideia de contrato e ele sendo
> lido na forma de schema seria muito melhor."*

## O que é

A **forma longa** do parâmetro `schema=`: um objeto prescritivo que declara a tabela — hoje só
specs por coluna (as formas curtas str/dict já cobrem), amanhã o resto do **contrato**. Entra
como **mais uma forma aceita** por `resolve_schema()` (natures/__init__.py) — por isso o
parâmetro já nasceu com esse nome: o objeto é aditivo, não rename.

Distinto do `TableSchema` DESCRITIVO existente (`build_schema`, saída do encode com
`body_bytes`/`cardinality`): este é ENTRADA. Avaliar na hora se um vira base do outro ou se
ficam separados (os campos pós-encode não podem virar promessa de entrada).

## Campos previstos — cada um com demanda já registrada (não inventar por simetria)

| campo | demanda registrada |
|---|---|
| spec por coluna (nome OU posição) | ADR-0047 (já coberto pelas formas curtas) |
| tipo por coluna (int/float/bool/date…) | `T-DECODE-SAIDA-TIPADA` (decode devolve o objeto nativo, 17,5–19,3% do decode) |
| assinatura dos knobs que não reconstroem (`drop_names`, `sort_by`) | `T-FMT-CONTRACT-SIGNATURE` (fail-loud na ponta) |
| nomes/ordem das colunas | recuperação de `drop_names` (o receptor renomeia posicional→nome pelo contrato) |
| o contrato fora do fio ("sem-carimbo") | decisão 4 do ADR-0041 + direção contrato-externalizado (2026-07-16) + camada C4 do lab quatro-camadas: o Schema **é** "o contrato lido na forma de schema" — as duas pontas seguram o Schema e o fio dispensa o estático |

## Critério de aditividade (quando isto deixa de ser barato)

Enquanto o `Schema` for só **entrada** (mais uma forma do `schema=`), é aditivo — sem mudança
de wire, sem ADR de formato. No momento em que um campo dele precisar **viajar no wire** (ex.:
declarar tipo no meta), vira mudança de formato → ADR próprio + gates, e provavelmente conversa
com `T-FMT-OMIT-OR-DECLARE` (deduzir/convencionar/declarar).

## Extensões registradas (não feitas)

- **Sobrecarga escalar no `.8H` de 1 folha string** (2026-08-22): a tabela dict e o wire multi
  de UMA coluna já aceitam a forma escalar; o dataset `.8H` não — as folhas são derivadas
  fundo demais para a porta decidir "inequívoco" barato. Se um dia valer, a régua é a mesma:
  exatamente UMA folha scalar-string elegível.
- **`fast=true` / perfis de agrupamento** (direção owner 2026-08-22, alvo `.9`): um parâmetro
  que liga conjuntos de flags já trabalhados — já registrado como `T-PERFIS-MACRO`
  (PENDENTES NOMEADOS na STATUS); o Schema é candidato natural a carregá-lo.

## Não fazer agora

Nada. O `.8` fecha com as formas curtas; este ticket é o registro do destino para o desenho
não se perder.
