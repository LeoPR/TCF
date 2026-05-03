---
title: Revisao critica do nucleo TCF (encoder/decoder/compression) pos-achados
type: review
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Conversa de reorganizacao (apos M-Acomm + M-schema-scope concluidos)
user_quote: "vou querer refazer atividades do núcleo do TCF"
see_also:
  - src/tcf/encoder.py, decoder.py, compression.py, schema.py
  - docs/findings/ (achados que justificam ou questionam decisoes do core)
  - docs/workbench/tickets/open/H-advanced-compression-v03.md
  - docs/workbench/tickets/open/23-P-numeric-precision.md
  - docs/workbench/tickets/open/29-B-decoder-freetext-bug.md
---

# Revisao critica do nucleo TCF (v0.3 candidate)

## Motivacao

Os 38 findings F-Q1..F-Q38 acumulados nos ultimos meses revelam pontos
do design v0.2 que merecem reavaliacao. Antes de fazer trabalho novo
em cima do encoder, vale auditar o existente com a luz dos achados.

## Pontos a auditar criticamente

### 1. STATS hint — virou crutch ou continua util?

F-Q8 (origem) mostrou que STATS adiciona +20-30pp em accuracy de
agg full-table. Mas:
- F-Q28 mostrou que STATS so resolve **full-table agg**; em filter+agg
  Linha A continua 0%
- F-Q31 mostrou que comerciais com reasoning fazem 100% mesmo sem
  precisar do STATS (lendo dados crus)

**Questao**: STATS deve ser:
- (a) Sempre incluido (status quo)
- (b) Opcional (custo/accuracy tradeoff por workload)
- (c) Generalizado para mais tipos (median, percentil, mode) — uteis
  em agg filter
- (d) Stratified (STATS por subgrupo de col categorico) — atacaria
  filter+agg em Linha A

### 2. Niveis L0..L3 — quais fazem sentido?

L0 (raw expanded), L1 (DICT), L2 (RLE+STATS), L3 (schema-only). Pos-achados:
- L0: usado para debug — manter
- L1: pouco testado isoladamente — vale L1 ou L1 = L0+DICT pode ser fundido?
- L2: padrao Linha A — manter, sem mexer
- L3: padrao Linha B — manter, sem mexer
- **Faltam niveis intermediarios?** L2.5 = L2 + extras (median, percentil)?

### 3. Compressao avancada — H-advanced-compression-v03 ja proposto

Ticket H-advanced-compression-v03 propoe: delta encoding, FOR
(Frame-of-Reference), scale-to-int para floats, bucket, knee algorithm
para transicao L0→L2 automatica. **Vale separar essa decisao**:
- Compressao adicional importa para Linha A (LLM le mais bytes)?
  Resposta empirica de F-Q8 + F-Q31: STATS importa, RLE importa, demais
  e ganho marginal vs custo de complexidade
- Para Linha B importa? Nao — Linha B usa schema-only

**Recomendacao tentativa**: priorizar **Stratified STATS** (proposta
nova) sobre delta/FOR (proposta antiga).

### 4. Numeric precision (ticket 23) — issue real?

`23-P-numeric-precision.md` aberto — ate agora nao bloqueou
experimento, pois GTs permitem tolerancia 1%. Mas para roundtrip
exato + datasets cientificos pode importar.

**Decisao**: manter como issue de v0.3 ou fechar como WONTFIX?

### 5. Decoder freetext bug (ticket 29)

Bug em decoder L0 com strings contendo certos caracteres especiais.
Nao afeta Linha A (LLM nao decoda) nem Linha B (executa SQL no DB).

**Decisao**: fix em v0.3 OR descartar (apenas afeta roundtrip Python
puro, nicho)?

### 6. Schema_qualifier — nova camada faz parte do core?

Achado F-Q38 mostra que schema pruning AJUDA dramaticamente (-33pp em
N3). Roadmap em
`docs/workbench/research-notes/2026-04-24-schema-qualifier.md`.

**Questao**: schema_qualifier deveria ser:
- (a) Camada externa (app callers fazem pruning antes de chamar TCF)
- (b) Funcao no Shaper (`scripts/shaper/`)
- (c) Parte do core TCF (encoder aceita "minimal/core/chain/full" como
  parametro e podem ate sugerir prune automatico)

### 7. API publica — esta em forma final?

Atual:
```python
from tcf import encode, encode_rows, decode, EncodeConfig
```

Issues conhecidas:
- `decode` retorna `dict[str, list[dict]]` para multi-table; valores
  como str (nao reverte tipos). Inconsistente com `encode_rows` que
  recebe `list[dict]` com tipos nativos.
- `encode` (legacy CSV-based) vs `encode_rows` (preferido) — manter
  ambos ou deprecar `encode`?
- `EncodeConfig.sort_by` precisa ser uma string; deveria aceitar list
  para multi-key sort?

### 8. v0.3 — escopo e timeline

Se houver v0.3 redesign, o que entra:
- [ ] Stratified STATS (proposta nova)
- [ ] Schema_qualifier integrado (F-Q38)
- [ ] Decoder type recovery (decode -> tipos originais)
- [ ] Bug fix 29 (decoder freetext)
- [ ] Numeric precision (issue 23)
- [ ] Compressao avancada (H-advanced-compression-v03) ou descartar
- [ ] Atualizar Apendice A do paper apos v0.3

## Criterio de aceite

- [ ] Audit doc escrito (este ticket pode evoluir para audit-doc completo)
- [ ] Decisao por ponto: keep / change / drop
- [ ] Se v0.3: roadmap com tickets filhos para cada feature
- [ ] Atualizar `docs/components/` apos decisoes

## Dependencias

- Paper Cap 7+8 (justificam ou questionam decisoes do core)

## Impacto estimado

- Audit so (sem implementacao): 2-3 dias
- v0.3 implementacao: 2-4 semanas dependendo do escopo

## Notas de revisao futura

Quando reabrir este ticket:
- Verificar se algum achado novo (F-Q39+) justifica mudar prioridade
- Se nucleo refeito: snapshot do v0.2 fica em git tag `v0.2-final`
- Atualizar [CHANGELOG.md](../../../../CHANGELOG.md) com v0.3-redesign

## Decisoes pendentes (para o usuario)

1. Iniciar audit ja ou apos paper finalizado?
2. v0.3 redesign agora vs apos publicacao?
3. Manter compatibilidade v0.2 ou breaking-change OK?
