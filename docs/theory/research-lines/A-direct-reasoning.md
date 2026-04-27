---
title: Linha A — LLM como analista direto sobre TCF
date: 2026-04-23
type: research-line
status: RESULTADOS CONSOLIDADOS — não ativamente em desenvolvimento
---

# Linha A — LLM lê TCF diretamente e calcula a resposta

## Tese

TCF é um formato textual columnar com compressão e hints meta-cognitivos (STATS).
A hipótese inicial era: **se TCF apresenta os dados em formato compacto e
enriquecido com estatísticas pré-computadas, modelos LLM conseguem responder
perguntas de BI lendo o conteúdo diretamente**, sem precisar de backend externo.

## Paradigma de avaliação

```
Pergunta NL + payload (TCF/CSV/JSON) → LLM → resposta numérica/textual
                                        ↓
                      comparar com ground-truth calculado em Python
```

O LLM é o calculador final. Accuracy mede se o valor produzido é o correto.

## Experimentos nesta linha

| Experimento | Objetivo | Manifest |
|-------------|---------|----------|
| phase1 | Accuracy por formato (CSV/JSONL/TCF) × escala | `experiments/results/etapa1/manifest.jsonl` |
| phase2 | 12 modelos × formato principal | `experiments/results/etapa2/manifest.jsonl` |
| stats_ablation | Efeito dos STATS hints (com/sem) | `experiments/results/stats_ablation/manifest.jsonl` |
| diagnostic_3layer | Aritmética vs formato vs compute | `experiments/results/diagnostic_3layer/manifest.jsonl` |
| scale_progression | Accuracy vs número de linhas | `experiments/results/scale_progression/manifest.jsonl` |
| g30_hyperparams | Temperature, top_k, seed effects | `experiments/results/g30_hyperparams/manifest.jsonl` |
| frontier_search | Painel completo × task com config ótima (L3+N_space_val) | `experiments/results/frontier_search/manifest.jsonl` |
| rle_notation | Comparação de notações RLE (N*val, N val, etc.) | `experiments/results/rle_notation/manifest.jsonl` |
| language_matrix | PT vs EN para reasoning direto | `experiments/results/language_matrix/manifest.jsonl` |
| alias_bench | Efeito de aliases de colunas | `experiments/results/alias/manifest.jsonl` |
| bridge_instructions | Instruções intermediárias de desambiguação | `experiments/results/bridge_instructions/manifest.jsonl` |

## Achados canônicos desta linha

| F-Q | Conclusão | Impacto |
|-----|-----------|---------|
| F-Q12 | Aritmética sobre colunas com muitas linhas falha universalmente | **Define o teto da Linha A** |
| F-Q13 (parcial) | STATS hints dão +25-62pp de accuracy | Confirma que hints são vetor principal |
| (shared F-Q1..F-Q11) | Metodologia de seleção de modelos | Aplica a ambas as linhas |

**Conclusão científica da Linha A:** modelos locais 7-14B não ultrapassam ~70%
de accuracy em perguntas BI quando lendo dados diretamente — nem com TCF L3,
nem com STATS hints. A limitação é intrínseca à capacidade aritmética dos
modelos, não ao formato.

## O que essa linha ensinou e entregou

1. **TCF como formato de transporte funciona**: compressão L3 reduz tokens 40-65%
   vs CSV sem perda de reversibilidade (L0 reconstrói byte-exato)
2. **STATS hints são acessados pelos modelos**: quando presentes no topo, modelos
   usam o valor pré-computado em vez de tentar calcular (+25-62pp)
3. **Capacity floor existe**: modelos <1B não passam no gate de compreensão básica
4. **Thinking mode não resolve aritmética**: think=ON em deepseek-r1:7b melhora
   raciocínio mas não compensa capacity de aritmética

## Status

Linha A está **consolidada**, não ativamente em desenvolvimento. Os resultados
são válidos e publicáveis como contribuição do paper — tanto pela confirmação
do teto quanto pela motivação empírica que levou à Linha B.

Para continuar investindo nesta linha faria sentido:
- Modelos comerciais (Claude, GPT-4o) — verificar se o teto é de modelos locais ou universal
- Datasets com >1000 linhas — escalonamento continua degradando ou estabiliza?
- Fine-tuning específico para aritmética tabular — fora do escopo atual

## Ver também

- [B-schema-carrier.md](B-schema-carrier.md) — linha sucessora
- [../methodology/F-findings.md](../methodology/F-findings.md) — achados com tag `{A}`
- [../FINDINGS_SUMMARY.md](../FINDINGS_SUMMARY.md) — resumo consolidado
