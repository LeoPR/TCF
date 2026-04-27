---
title: Teoria das queries — o que vem antes do SQL
date: 2026-04-23
type: research-note
status: CONCEITUAL — hipóteses abertas, pré-experimento
---

# Teoria das queries: o que o LLM "pensa" antes de emitir SQL

## Motivação

Linha B testa se o LLM gera SQL correto. Mas a formulação do SQL é a **etapa
final** de um raciocínio. Antes do SQL, o modelo:

1. Interpreta a pergunta em NL
2. Identifica entidades (tabelas, colunas) relevantes
3. Decide a **estrutura lógica** da operação (filtro, agregação, join)
4. Escolhe uma forma de expressão (SQL, subquery, CTE, etc.)
5. Emite tokens SQL

Esta nota explora hipóteses sobre as etapas 3-4: a **estrutura lógica**
anterior ao SQL textual. Pergunta central: existe uma representação
intermediária mais robusta que SQL direto para modelos pequenos?

## Hipóteses a testar

### H1 — Nem toda pergunta BI é expressável em SQL

Existe uma classe de perguntas que parece BI mas requer conhecimento
extra-relacional:

- "Qual produto está em promoção?" → requer concept de "promoção" que
  não está no schema
- "Quem são os clientes importantes?" → "importante" não é operacional
- "Vendas anormais em março?" → "anormal" precisa de threshold

**Implicação:** um classificador pré-SQL poderia detectar perguntas
não-expressáveis e pedir clarificação em vez de gerar SQL plausível-mas-errado.

### H2 — Formas intermediárias podem ser mais robustas

Testado parcialmente em M5 (SQL vs Pandas vs Polars vs CoT-SQL).
Resultado: SQL vence. Mas não testamos:

- **Álgebra relacional textual:** `π_nome(σ_total>100(vendas ⋈ produtos))`
- **Query algebra em pseudocódigo:** `FILTER(vendas, total>100) | JOIN(produtos) | SELECT(nome)`
- **Plano estruturado JSON:** `{"from":"vendas","join":{"produtos":"id_produto"},"filter":"total>100","select":"nome"}`

Hipótese: formas estruturadas mas sem sintaxe SQL rígida podem contornar
falhas de scope (F-Q19 HAVING). O plano JSON é convertível para SQL por
código determinístico.

### H3 — CoT com plano estruturado ≠ CoT natural

M5 mostrou CoT-SQL neutro/negativo. Mas CoT em M5 era texto livre:
"Preciso da tabela X, juntar com Y, filtrar Z...". Hipótese alternativa:
**CoT com plano estruturado** (JSON ou pseudocódigo) pode capturar ganho
que CoT natural não capturou, porque o modelo erra menos em sintaxe
formal que em texto livre sobre operações.

### H4 — Queries multi-passo (decomposição explícita)

Perguntas complexas podem ser decompostas:
```
"Para o cliente com mais compras, qual produto ele mais comprou?"
→ passo 1: "Qual cliente tem mais compras?" → C
→ passo 2: "Qual produto C mais comprou?"
```

Cada sub-pergunta é L1. Juntas, a resposta é equivalente a L3. Hipótese:
**decomposição explícita via 2 chamadas ao LLM** pode ser mais robusta
que uma única chamada com subquery.

Trade-off: 2× latência e custo. Mas possível pareto-dominância em accuracy
para modelos pequenos.

### H5 — O LLM tem uma "representação interna" da operação

Antes de emitir SQL, modelos reasoning (think=ON) podem ter um plano
explícito no thinking. Hipótese: analisar o thinking output pode revelar
se o LLM tinha a estrutura lógica correta antes de falhar na sintaxe.

Se sim: dois failure modes distintos:
- Tipo I: plano correto, SQL errado (recuperável com style hints — F-Q22)
- Tipo II: plano errado (requer decomposição ou clarification, não hint)

## Onde isto se conecta com achados existentes

| Achado | Conexão |
|--------|---------|
| F-Q12 | Modelo falha em aritmética direta → forçou Linha B (SQL como plano formal) |
| F-Q18 | SQL > Pandas/Polars; CoT-SQL neutro → estrutura SQL é o sweet spot **atual** |
| F-Q19 | HAVING é scope confusion — modelo tinha plano certo mas sintaxe errada → plausível Tipo I (H5) |
| F-Q20 | Column confusion em subquery → plausível Tipo II (plano errado) |
| F-Q22 | Style hints recuperam falhas zero-shot → viável porque o plano estava ~certo |
| F-Q23 | Style hints não compõem → sugere que os hints não alteram o plano interno, só a sintaxe final |

## Experimentos propostos

### M_decompose
Testar H4 — mesma pergunta L3 via 1 call (atual) vs 2 calls decompostos.
Medir accuracy + latência + token cost. Comparar nos 3 modelos locais
e em comerciais (M8).

### M_plan
Testar H2/H3 — pedir JSON plan antes de SQL:
```
{"from": "...", "joins": [...], "filter": "...", "agg": "...", "select": "..."}
```
Comparar com SQL direto (baseline M3).

### M_think_analysis
Testar H5 — para `phi4` e outros com thinking, extrair o thinking output
e verificar se o plano lógico foi correto mesmo em falhas de SQL. Classificar
falhas em Tipo I (plano certo, sintaxe errada) vs Tipo II (plano errado).

## Status

Nenhum experimento rodado. Hipóteses documentadas para orientação futura.

A decisão de atacar esta linha ou priorizar M8 (modelos comerciais) + M9
(mais domínios) é estratégica — depende se o paper V1 foca em **accuracy
com modelos atuais** (priorizar M8/M9) ou em **teoria de representação**
(priorizar experimentos desta nota).

## Referências internas

- M5 (SQL vs Pandas vs Polars vs CoT) — research-note:
  [2026-04-22-coverage-and-intermediate-forms.md](2026-04-22-coverage-and-intermediate-forms.md)
- F-Q19, F-Q22, F-Q23 em [F-findings.md](../methodology/F-findings.md)
- Invariantes como validação: [2026-04-23-embedded-query-invariants.md](2026-04-23-embedded-query-invariants.md)
- Safe-SQL flags: [2026-04-23-conservative-sql-flag.md](2026-04-23-conservative-sql-flag.md)
