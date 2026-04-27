---
title: LLM raciocinio qualitativo/aproximado — alem da precisao exata
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Visao de que LLMs podem ser uteis para "intuicao" sobre dados, nao so precisao
---

# LLM Raciocinio Qualitativo

## Contexto

F90-F94 mostraram que LLMs **nao somam** 509 numeros — dependem de STATS
para agregacoes exatas. Mas e se a pergunta for **qualitativa**?

"Os valores aumentaram ao longo do ano?"
"O produto X vende mais que o Y?"
"Existe algum cliente com comportamento atipico?"

Essas perguntas nao precisam de precisao — precisam de **intuicao de padroes**.
LLMs podem ser bons nisso justamente onde falham em calculo.

## Hipotese

**H-qual:** LLMs tem accuracy >> 90% em perguntas qualitativas sobre TCF,
mesmo modelos que falham em perguntas quantitativas exatas.

Se confirmado: TCF + LLM e viavel para **analise exploratoria**, nao so
Q&A exato. Isso amplia drasticamente os casos de uso.

## Tipos de perguntas qualitativas

### Comparativo relativo
- "Qual vende mais: Caneta ou Lapis?" (sem exigir contagem exata)
- "Ana gastou mais que Bruno?" (sim/nao)
- "Os precos subiram ou cairam?" (tendencia)

### Magnitudes aproximadas
- "Quantas vezes mais vendas tem o top produto vs o bottom?" (1x, 2x, 10x, 100x)
- "Que fracao dos clientes compraram mais de uma vez?" (metade, maioria, minoria)
- "O produto X e muito popular, pouco popular, medio?" (categoria)

### Anomalias e padroes
- "Ha algum valor muito fora do normal?" (outlier)
- "A distribuicao de vendas e uniforme ou concentrada?" (qualitativa)
- "Ha agrupamentos obvios de clientes?" (segmentacao intuitiva)

### Tendencia temporal (se ha coluna de data)
- "As vendas aumentaram no ultimo mes?"
- "Existe sazonalidade?"

## Design experimental

**Modelos:** gemma3:12b (STATS reader), qwen3:8b (processa), phi4, gpt-oss
**Formatos:** TCF L0 (com STATS) vs TCF L0 (sem STATS)
**Perguntas:** 10-15 perguntas qualitativas novas (ver acima)

**Metrica de scoring:** nao e mais exact match.
- **Comparativos (sim/nao):** exact match (trivial)
- **Magnitudes (ordem):** dentro de 2x e "ok", 10x+ e "errado"
- **Tendencias:** concordancia com ground truth qualitativa

### Ground truth qualitativa (novo)

Precisamos definir ground truth nao-exata:
```python
def qualitative_gt(tables):
    totals = [float(v["total"]) for v in tables["vendas"]]
    return {
        "precos_aumentaram": is_trending_up(totals),  # bool
        "top_vs_bottom_ratio": top/bottom,            # number, score by log distance
        "distribuicao_concentrada": gini(totals) > 0.5,  # bool
        "tem_outliers": has_outliers_iqr(totals),    # bool
    }
```

## Pergunta central

**Se um LLM acerta 90% das perguntas qualitativas mas so 50% das quantitativas,
para quem serve esse LLM?**

Resposta provavel: para **analise exploratoria** em dashboards, reports,
assistentes. Casos onde o usuario quer "entender" dados, nao "calcular" dados.

## Relacao com STATS

STATS ajudam questoes quantitativas (sum, avg) mas podem **atrapalhar**
questoes qualitativas que exigem visao holistica. Testar ambos.

## Tarefas

- [ ] Definir 15 perguntas qualitativas + ground truth derivavel
- [ ] Implementar scoring qualitativo (fuzzy)
- [ ] Rodar com 4 modelos, 2 formatos (com/sem STATS)
- [ ] Comparar com accuracy quantitativa dos mesmos modelos
- [ ] Se accuracy qualitativa >> quantitativa: finding central para o paper
- [ ] Documentar em article/07 como secao "Qualitative Reasoning"
