---
title: Niveis de compressao progressivos — reversibilidade e auto-deducao
type: hypothesis
status: OPEN
priority: HIGH
---

# Niveis de Compressao Progressivos

## Hipotese

O TCF pode operar em niveis progressivos de compressao onde cada nivel
sacrifica algo especifico em troca de compactacao:

| Nivel | O que mantem | O que perde | Reversivel? |
|-------|-------------|-------------|-------------|
| L0 | Tudo (nomes, ordem, valores) | Nada | 100% |
| L2 | Nomes, valores (reordena) | Ordem original | 100% (dados, nao ordem) |
| L3 | Indices, valores | Nomes inline (usa dict) | 100% (com dict) |
| L4* | Valores agrupados | Detalhes individuais | Parcial (aggregates) |
| L5* | Apenas resumos/stats | Valores individuais | Nao (lossy) |

*L4 e L5 sao hipoteticos — GROUP BY e STATS-only.

## Sobre chaves e relacionamentos

**Com chaves (tabelas separadas):**
- Encode inclui header com schema: `(from: pessoas=pessoa, produtos=produto)`
- Decode reconstroi tabelas de referencia via `unique()` e IDs sequenciais
- Reversivel: relacoes preservadas, IDs originais perdidos

**Sem chaves (tabelao flat):**
- Encode gera supertable sem nenhuma informacao de schema
- Decode retorna tabela flat como esta
- Nao reversivel para tabelas separadas (nao sabe o que era FK)

**O usuario escolhe:** `--with-schema` ou sem.

## Insight de F81 (diagnostic 3-layer)

Os STATS lines funcionam como "meta-dados cognitivos" — modelos que nao
sabem calcular (gemma3) usam STATS como shortcut. Isto abre uma dimensao
nova: niveis de HINTS, nao apenas niveis de compressao.

| Nivel hint | O que inclui | Quem se beneficia |
|------------|-------------|-------------------|
| H0 | Sem hints | So modelos que genuinamente calculam (qwen3) |
| H1 | STATS basicos (n, sum, min, max, avg) | Modelos que leem hints (gemma3) |
| H2 | STATS + top values + distribution | Ajuda em argmax/distinct |
| H3 | Full pre-computed answers | Trivial — qualquer modelo acerta |

Experimento critico: STATS ablation (H1 vs H0) para separar
"accuracy real" de "accuracy inflada por hints".

## Tarefas

- [ ] Testar reversibilidade de cada nivel com dados v2
- [ ] Medir perda de informacao em cada nivel
- [ ] Testar se LLM consegue descomprimir (decode reverso)
- [ ] Documentar claramente o que cada nivel perde
- [ ] STATS ablation: rodar Etapa 2 com include_stats=False
- [ ] Definir se STATS sao feature ou confounding variable
