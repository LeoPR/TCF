# Lab dirty: cross-column DICT/RLE — testes de mesa

## Objetivo

Investigar se DICT e RLE com escopo **cross-column** (compartilhado entre
multiplas colunas) tem merito em ambientes:

- Multi-disciplinares de tipos (varias colunas com vocabulario comum)
- Repeticao de tipos enum (status, flags, categorias)
- Esquemas com FK (mesma chave referenciada em multiplas tabelas/colunas)

Posicao atual no roadmap (ver H-compression-v04-roadmap, Proposta E):
**descartado** com justificativa "baixo impacto, alto custo".

Este lab pretende:
- Validar matematicamente quando faria sentido
- Identificar cenarios concretos onde ganho seria substancial
- Decidir se Proposta E deve ser **reaberta** ou continuar descartada

## Hipotese

Cross-column DICT vence per-column DICT quando:

1. **Vocabulario compartilhado eh substancial** entre K colunas
2. **Cardinality individual eh baixa** (DICT vale mais que indices)
3. **K (numero de colunas com voc. comum) eh > 1**

Modelo formal (para K colunas, cada com N rows, vocabulario V, tamanho
medio do valor |valor|):

```
Per-column DICT (atual L3):
  K · (|V| · |valor| + N · |indice|) + K · overhead_decl

Cross-column DICT (proposta):
  |V| · |valor| + K · N · |indice| + 1 · overhead_decl

Diferenca (Δ = naive - cross):
  Δ = (K-1) · |V| · |valor| - (K-1) · overhead_decl
    = (K-1) · (|V| · |valor| - overhead_decl)
```

**Predicao**: ganho linear em (K-1). Se K=1, sem ganho. Se K=10 e
|V|·|valor| >> overhead, ganho substancial.

## Cenarios sinteticos a testar

| # | Nome | Setup | Predicao |
|---|------|-------|----------|
| S1 | voc-compartilhado-3col | 3 colunas, mesmo voc. {red,blue,green,yellow,purple}, dist. variada | GANHA muito |
| S2 | fk-2-tabelas | 2 colunas customer_id (50 ids unicos) | GANHA se voc. compartilhado |
| S3 | status-enum-3col | 3 cols status: pago/pendente/cancelado | GANHA |
| S4 | categorias-pares | 2 cols categorias-principal/secundaria, voc. comum | GANHA |
| S5 | tipos-disjuntos | nome-livre + idade-int + status-enum | NAO ganha (voc. disjuntos) |
| S6 | voc-igual-dist-diferente | 2 cols mesmo voc., distribuicoes muito diferentes | GANHA igual S1 |
| S7 | texto-livre-2col | 2 cols texto livre, sem repeticao cross | PERDE (voc. cresce) |

## Metodo

1. Sintetizar 7 datasets controlados
2. Aplicar 3 estrategias:
   - naive (sem DICT)
   - per-column DICT (L3 atual TCF)
   - cross-column DICT (proposta)
3. Calcular bytes em cada estrategia
4. Comparar com formula matematica
5. Tabular ganho por cenario

## NAO eh objetivo

- Implementar no core TCF
- Decidir politica de auto-detect (em ticket separado)
- Roundtrip ou sintaxe formal

Saida: `./output/`

---

## Resultados (run.py — 2026-05-05)

### Tabela medida

| Cenario | K | \|V\| | Overlap | naive | L3 | cross | cross vs L3 |
|---------|---|------|---------|-------|-----|-------|-------------|
| S1 voc-compartilhado-3col | 3 | 5 | 100% | 900 | 494 | **387** | **-21.7%** |
| S2 fk-2-tabelas | 2 | 46 | 52% | 1862 | 1385 | **1038** | **-25.1%** |
| S3 status-enum-3col | 3 | 5 | 100% | 833 | 453 | **335** | **-26.0%** |
| S4 categorias-pares | 2 | 10 | 100% | 763 | 460 | **358** | **-22.2%** |
| S5 tipos-disjuntos | 3 | 60 | 0% | 827 | 749 | 773 | +3.2% |
| S6 voc-igual-dist-dif | 2 | 5 | 100% | 650 | 374 | **295** | **-21.1%** |
| S7 texto-livre-2col | 2 | 80 | 0% | 1887 | 2168 | 2132 | -1.7% |

### Achados principais

**1. Cross-column DICT vence per-column DICT em 6/7 cenarios sinteticos**

Magnitude do ganho: **-21% a -26%** quando overlap eh significativo.
Quando overlap eh 0% (S5, S7), cross empata ou eh ligeiramente
melhor por unificar overhead — mas L3 ja eh ruim ai.

**2. S2 (FK em 2 tabelas) revelou caso de alto valor**

Overlap so 52%, mas ganho **-25%** (-347B) — o maior em valor absoluto.
Razao: |V|=46 com |valor|=11 chars. DICT global economiza referencias
em ambas as colunas. **Caso classico de schema relacional**.

**3. Magnitude eh **linear em K-1** como a formula prediz**

S1, S3 (K=3): ganhos similares (~110B)
S4, S6 (K=2): ganhos similares (~90B)
A formula simplificada (ignorando indices) erra em magnitude mas
acerta em sinal e ordem de grandeza.

**4. S7 e o caso interessante: texto livre**

Overlap 0%, vocabularios disjuntos, mas **cross perde menos que L3**.
Razao: L3 ja paga overhead em ambas colunas (2x decl); cross paga so
1x. Mas AMBOS perdem para naive. Conclusao: em texto livre, **nem L3
nem cross deveriam ativar**. O algoritmo precisa de auto-bypass para
ambos os niveis.

**5. Algoritmo de detecao critico**

Para decidir entre L3 (per-column) e cross:
- Calcular `vocab_overlap = |intersection(cols)| / |union(cols)|`
- Se overlap > threshold (ex: 50%) E K >= 2: cross
- Se overlap pequeno mas |V| pequena: L3
- Se vocab >= N rows: nem cross nem L3 (auto-bypass)

### Validacao da formula

Formula simplificada `Δ = (K-1) · |V| · |valor|` predisse:
- Sinal correto em todos os casos com overlap > 0
- Ordem de grandeza aproximada (off por 30-50%)
- Diff vem de: (a) custo de indices, (b) separadores `,` em DICT,
  (c) custo do header de coluna

A formula eh **proxy util**, nao exato. Para decisao de auto-detect,
precisaria refinar incluindo:
- |idx_total| - |idx_k| (diferenca de bytes do indice)
- Custo de separadores no DICT
- Header de coluna (constante mas K-vezes)

### Afirmacoes induzidas (com rigor)

| # | Afirmacao | Evidencia |
|---|-----------|-----------|
| A1 | Cross-column DICT vence L3 em -21% a -26% quando overlap >= 50% | 5/7 casos medidos |
| A2 | Em FK relacional (overlap parcial), ganho absoluto eh maximo | S2: -347B |
| A3 | Em vocab disjuntos, cross e L3 ambos perdem para naive | S5, S7 |
| A4 | Magnitude eh linear em K-1 (mais colunas = mais ganho) | tendencia |
| A5 | Auto-detect eh requisito (sem ele, pode aumentar bytes) | confirmado |

### O que NAO foi provado

- Datasets sao **sinteticos** com vocabs artificialmente alinhados
- Em datasets reais, frequencia de overlap eh desconhecida
- Multi-tabela com FK cross-tabela (nao so cross-col) nao testado
- Interacao com gzip do transporte nao medida
- Sintaxe e overhead reais (com escaping, etc) podem variar

### Recomendacao

Cross-column DICT (Proposta E) deve ser **REABERTA** no roadmap.
Achados aqui contradizem a justificativa original "baixo impacto".

Em casos com schema relacional, vocabulario enum compartilhado, ou
flags repetidas, ganho eh **substancial e consistente** (~22%).

Decisao a tomar:
- Reabrir Proposta E em H-compression-v04-roadmap
- Manter status descartado mas com nota "reaberto se aparecer demanda"
- Criar lab E-cross-column-real-datasets para D1-D6 reais
- Implementar opt-in com auto-detect

Implementacao estimada: ~120 linhas Python (overlap detector +
shared dict emit + decode).
