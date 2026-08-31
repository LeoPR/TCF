---
title: Compressibility strategy — score de raridade + bucketing + cache
type: task
status: OPEN
priority: 19
parent: 12-M-dataset-shaper
---

# Compressibility

`scripts/shaper/strategies/compressibility.py`
`scripts/shaper/cache.py`

## Score de raridade

Para cada row, score = soma de `-log2(freq(val) / total)` por coluna categorica.
Rows com valores raros = score alto = mais dificeis de comprimir via RLE.

## Bucketing por quantil

```python
compressibility_range=(0.0, 0.3)  # 30% mais faceis (compressiveis)
compressibility_range=(0.7, 1.0)  # 30% mais dificeis
```

Quantis calculados sobre o score de raridade.

## Cache sob demanda

```
Z:/tcf-data/shaper-cache/{dataset}/
  {table}_rarity.json    # {rowid: score}
  {table}_rarity_meta.json  # hash do DB, colunas usadas
```

Invalidacao: hash do SQLite file. Se DB muda, recalcula.

## Tarefas

- [ ] Implementar score de raridade (uma passada por tabela)
- [ ] Implementar bucketing por quantil
- [ ] Implementar cache (gravar/ler JSON em Z:)
- [ ] Implementar invalidacao por hash
- [ ] Registrar no pipeline (apos join, antes de stratify)
- [ ] Testes: faceis vs dificeis tem score medio diferente
- [ ] Testes: cache hit (segunda chamada nao recalcula)
- [ ] Testes: cache invalidation (DB mudou → recalcula)
