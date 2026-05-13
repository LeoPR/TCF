---
title: Datasets canonicos, representatividade estatistica
type: research
status: OPEN
priority: LOW (pos-paper v1)
---

# Datasets Canonicos

## Estado atual

Usamos apenas dados sinteticos (retail_sales da synthetic_v2.py).
Parametros: Zipf s=1.0, 1:10 customer:order, 20 produtos, null_rate=5%.
Vantagem: ground truth exato, reproducivel, controlavel.

## Por que importa para o paper

Reviewer pode perguntar: "funciona com dados reais?"
Resposta defensiva: nosso sintetico e inspirado em TPC-H e reproduz
distribuicoes realistas (Zipf, nulls, mixed types). Mas nao substitui.

## Datasets candidatos

| Dataset | Dominio | Rows | Cols | Disponivel |
|---------|---------|------|------|------------|
| TPC-H | retail/vendas | variavel | 7-16 | Gerador open-source |
| WikiTableQuestions | Wikipedia | 100-500 | 3-20 | GitHub |
| SQA (Sequential QA) | Wikipedia | ~6000 tabelas | variavel | Microsoft |
| TabFact | Wikipedia | 16K tabelas | variavel | GitHub |
| HiTab | hierarchical | 3.5K tabelas | variavel | GitHub |

## Avaliacao

Para o paper v1, sinteticos sao suficientes — o focus e formato, nao dominio.
Dados reais ficam como extensao/futuro trabalho.
Se tempo permitir, TPC-H seria o mais relevante (mesmo dominio que retail_sales).

## Tarefas

- [ ] Pesquisar TPC-H generator Python
- [ ] Avaliar WikiTableQuestions como benchmark comparativo
- [ ] Decidir se inclui no paper v1 ou deixa como futuro trabalho
