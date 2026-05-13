# Conclusões — v2 trade-off não-óbvio entre granularidade e refs múltiplas

Roundtrip 63/63 OK (21 datasets × 3 sintaxes). Compact v2 ganha
em 17 casos vs v1 (−6% a −41%); perde em 4 (+17% a +86%). No
agregado: v2 é **17% pior que v1**, mas ainda **36% melhor que
verbose**.

## A descoberta central

A intuição inicial — "marcadores inferidos pela ordem reduzem
bytes" — está parcialmente correta. **O ganho depende da
estrutura de quebras** que o algoritmo gera.

Reformulando o trade-off:

| Compact v1 | Compact v2 |
|---|---|
| Cada ref a slice → 1 marcador (`@N<K`, 4-5 chars) | Cada ref a slice → N idx separados por `,` (cresce com N) |
| Custo constante por slice | Custo proporcional ao número de quebras dentro do slice |
| Sintaxe explícita: `@N<K` ou `@N>K` | Sintaxe implícita pela posição |

Quando há **poucas quebras por nó**, v2 ganha: cada ref vira
1-2 idx (`5` ou `1,2`), menor que `@N<K` (4-5 chars).

Quando há **muitas quebras por nó**, v2 perde: cada ref vira
4-8 idx (`1,2,3,4,5,6`), muito maior que `@N<K`.

## Por que iso-N1000 perdeu drasticamente (+86%)

ISO timestamps em escala N=1000 têm strings tipo
`2026-05-11T08:00:00Z`. Cada timestamp difere de outros em
**várias posições simultaneamente** (dia, hora, minuto). O
algoritmo gera LCPs/LCSs de tamanhos diversos entre pares de
strings.

s1 acumula quebras em positions {10, 11, 12, 13, 14, 17, 18, 19, ...}.
Resultado: s1 vira **20+ fragmentos pequenos** (alguns de 1 char).

Cada ref subsequente a um slice de s1 tem que listar 5-10 idx
separados por `,`. Em vez de `@1<11` (5 chars), vira
`1,2,3,4,5,6,7,8,9` (17 chars).

A explosão é multiplicativa: 1000 strings × 5-10 idx/ref ×
~2 refs/string = ~10000+ idx no body total.

## Por que codigos-N1000 ganhou (-6%)

Codigos têm estrutura **simples**: 4 prefixos × 250 seriais.
Cada slice usado é "prefixo de 13 chars" (= `PED-2026-0000`)
ou "prefixo de 3 chars" (= `PED`). Apenas 2-3 quebras por
nó. Cada ref a slice vira 1-2 idx.

v2 ganha por eliminar o marcador `@N<K` explícito (3-5 chars
economizados por ref × milhares de refs = 1000 bytes
economizados).

## Casos onde v2 brilha (D2-mini, -16%)

D2-mini com 6 strings tem **estrutura limpa**: s1 é o nó-pai com
5 fragmentos, as outras 5 strings referenciam slices contíguos.
Cada ref vira 1-2 idx.

```
exp 21 (compact v1):    @2:@1<12'hot'@1>8     ← 17 chars
exp 22 (compact v2):    1,2'hot'4,5            ← 11 chars
```

## Validação da hipótese da nota

A nota previa:

> "Direção 2 — inferida pela ordem (...) muito compacto, mas
> decoder precisa de gramática rígida. Qualquer ambiguidade
> quebra tudo. Risco real de regredir em inspecionabilidade."

Realidade observada:
- **Compacto sim** em ~80% dos casos (17 de 21)
- **Pode regredir** em 20% (iso-N1000 quase dobrou de tamanho)
- Inspecionabilidade ficou pior (`1,2,3'a''b'4,5` é menos legível
  que `@1<3'ab'@1>5`)

A nota acertou nos riscos. A direção 2 é **especializada**, não
universalmente melhor.

## Onde a sintaxe v2 pode brilhar

1. **Datasets com poucos slices distintos por nó**: URLs
   com base comum, códigos com prefixo fixo, sub-redes IP
2. **Estruturas hierárquicas claras**: árvore com poucos pontos
   de derivação
3. **Quando inspecionabilidade não é prioridade**: por exemplo,
   compressão para storage ou transporte de baixo nível

## Onde a sintaxe v2 não deve ser usada

1. **Datasets com alta entropia de slices**: timestamps,
   coordenadas, métricas variadas
2. **Quando inspecionabilidade humana importa**: legibilidade
   cai significativamente
3. **Em N muito grande sem otimização adicional**: refs
   explodem

## Pontos a registrar

1. **Hipótese da nota validada parcialmente**: marcadores
   inferidos reduzem bytes em ~80% dos casos, mas regridem em
   casos extremos. Não é universalmente melhor.

2. **Bytes/unidade caiu em geral**: média v2 ~4.5
   bytes/unidade vs v1 ~7.7 e verbose ~14.

3. **Interface `Syntax` se manteve suficiente**: a 2ª sintaxe
   plugou sem mudanças no algoritmo nem na interface.

4. **Trade-off bytes ↔ universalidade**: v1 é mais previsível
   (custo fixo por ref). v2 é mais variável (custo proporcional
   a quebras).

5. **Próximo passo possível**: sintaxe **híbrida** — usar v1
   ou v2 por nó/dataset baseado em análise prévia das quebras.
   Detectar regime A (v2) vs regime B (v1) e escolher por nó.

## O que este experimento não mostra

- Comportamento em sintaxes binárias (chars Unicode reservados)
- Comparação com gzip downstream (se ganho sobrevive)
- Comparação com formatos externos (HTFC, FSST, Re-Pair)
- Sintaxe híbrida v1/v2 por nó

## Próximos experimentos naturais

1. **Sintaxe híbrida**: analisar quebras antes de emitir, usar
   v1 quando há muitas quebras, v2 quando há poucas
2. **Comparação externa real**: TCF + gzip vs CSV + gzip vs
   HTFC vs Re-Pair — saber se o TCF (qualquer sintaxe) compete
3. **Sintaxe binária / chars Unicode reservados**: explorar
   mais 1-2 bytes/unidade

Sugestão de prioridade:
- **Comparação externa** vem primeiro — saber se ganho vs
  CSV+gzip sobrevive é fundamental
- Depois decidir se vale investir mais em sintaxes (1, 2, ou
  híbrida)
- Sintaxe binária fica para depois — exploraria limite teórico
  mas só ganha se estamos competitivos no básico
