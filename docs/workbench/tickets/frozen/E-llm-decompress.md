---
title: LLM descomprime TCF — gerar CSV a partir de dados comprimidos
type: experiment
status: OPEN
priority: MEDIUM
---

# LLM Descomprime TCF

## Hipotese

Se a LLM consegue descomprimir TCF e gerar CSV correto, isso prova
compreensao TOTAL do formato — nao apenas leitura superficial.

## Niveis progressivos de teste

| Nivel | Input | Pergunta | Dificuldade |
|-------|-------|----------|-------------|
| D1 | TCF L0 (expanded) | "Gere CSV com estes dados" | Facil (transpor colunas) |
| D2 | TCF L2 (sorted+RLE) | "Descompacte e gere CSV" | Media (expandir N*val) |
| D3 | TCF L3 (dict+RLE) | "Resolva indices e gere CSV" | Dificil (dict + RLE) |
| D4 | TCF L2 com schema | "Reconstrua as 3 tabelas" | Dificil (normalize) |

## Avaliacao

Comparar CSV gerado pela LLM com CSV gerado pelo decoder programatico:
- Row count match?
- Valores match? (fuzzy para floats)
- Ordem match? (L2+ reordena, entao comparar sets)

## Tarefas

- [ ] Criar prompt para cada nivel D1-D4
- [ ] Testar com gemma3:12b (melhor modelo) e qwen3:8b
- [ ] Parser para extrair CSV da resposta da LLM
- [ ] Scoring automatico: diff com decoder programatico
- [ ] Documentar em article/07
