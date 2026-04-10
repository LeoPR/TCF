---
title: Revisar banco de perguntas — cobertura de operacoes
type: research
status: OPEN
priority: MEDIUM
origin: Revisao de P05 (v0.1) + G23 + G24
---

# Revisar Banco de Perguntas

## Estado atual

### prompts.py (banco canonico): 13 questoes
- 2 math_control (sum, count) — Layer 0
- 1 decode_only (listar valores) — Layer 1
- 10 compute (Q1-Q10) — Layer 2

### Etapa 1+2 runners: 8 questoes
q1_sum, q2_avg, q3_max, q4_min, q5_count,
q6_top_product, q7_top_spender, q8_distinct

### G30: 6 questoes (subset)
q1_sum, q2_avg, q3_max, q5_count, q6_top_product, q7_top_spender

## Cobertura por tipo de operacao

| Tipo | Coberto | Questao | Nivel |
|------|---------|---------|-------|
| SUM | Sim | q1_sum | 1 |
| AVG | Sim | q2_avg | 2 |
| MAX | Sim | q3_max | 1 |
| MIN | Sim | q4_min | 1 |
| COUNT | Sim | q5_count | 1 |
| FILTER+COUNT | Sim (prompts.py) | q6_count_ana | 3 |
| FILTER+SUM | Sim (prompts.py) | q7_sum_ana | 3 |
| ARGMAX (freq) | Sim | q8_top_product | 3 |
| DISTINCT | Sim | q9_distinct | 2 |
| ARGMAX (agg) | Sim | q10_top_spender | 3 |
| FILTER (valor) | **NAO** | — | 2 |
| CONDICIONAL | **NAO** | — | 2 |
| MULTI-STEP | **NAO** | — | 4 |

## Gaps identificados

### Gap 1: Filter por valor especifico
"Qual o total de vendas de Caneta?"
- Requer: encontrar produto "Caneta" → filtrar rows → somar
- Testa: compreensao de lookup + soma parcial
- Proposta: **q11_filter_product_sum**

### Gap 2: Condicional numerico
"Quantos pedidos tem total acima de 50?"
- Requer: comparar cada valor → contar
- Testa: compreensao de threshold + iteracao
- Proposta: **q12_count_above_threshold**

### Nao incluir (complexidade excessiva para scope do paper):
- GROUP BY completo ("total por produto") — resposta e tabela, nao escalar
- MULTI-STEP ("quem comprou mais Caneta?") — 3 operacoes encadeadas
  (pode ser experimento futuro, mas extrapola o scope do paper atual)

## Incoerencia prompts.py vs runners

Os runners (etapa1, etapa2, g30) definem QUESTIONS internamente
e NAO usam prompts.py. Ha duplicacao e divergencia:
- prompts.py: q6 = "vendas Ana", q7 = "total Ana"
- runners: q6 = top_product, q7 = top_spender

**Recomendacao:** Unificar. Runners devem importar de prompts.py.
prompts.py deve ter as 12 questoes (10 atuais + 2 novas).

## Classificacao por dificuldade (ex-G23)

| Nivel | Questoes | Operacao |
|-------|----------|----------|
| 1 | q3_max, q4_min, q5_count | lookup direto |
| 2 | q1_sum, q2_avg, q9_distinct, q12_threshold | agregacao simples |
| 3 | q6_count_ana, q7_sum_ana, q8_top_product, q10_top_spender, q11_filter | filter + agregacao |

## Decisao

Para o paper:
- **10 questoes atuais sao suficientes** para cobrir os tipos principais
- **2 novas (filter, threshold) sao opcionais** — so adicionar se E-scale
  ou E-prompt-presentation precisarem de mais granularidade
- **Prioridade: unificar prompts.py ↔ runners** (eliminar duplicacao)

## Robustez do wording (pesquisa 2026-04-09)

Todas as nossas perguntas usam UMA formulacao fixa (pt-BR formal).
Literatura mostra variacao de 24-100% com wording diferente.

Para o paper, precisamos documentar que testamos variacao de wording
(via E-prompt-presentation variavel 5) e que os resultados sao robustos
— ou reportar como limitacao.

Ver tambem: Sui et al. 2024 (self-augmentation), PromptSET 2025,
"Same Meaning Different Scores" 2026.

## Tarefas

- [ ] Unificar QUESTIONS dos runners com prompts.py
- [ ] Adicionar q11_filter e q12_threshold em prompts.py (opcional)
- [ ] Implementar ground truth para questoes novas (se adicionadas)
- [ ] Classificar questoes por dificuldade no paper (tabela)
- [ ] Garantir que wording ablation (E-prompt-presentation) cobre q1_sum
