# Roadmap — hipoteses faltantes

**Data**: 2026-05-17
**Tipo**: nota transversal (direcoes futuras)
**Foco**: o que NAO foi explorado no dirty lab e merece atencao
futura, ordenado por proximidade/risco.

> Esta nota lista hipoteses **identificadas mas nao testadas** em
> M0-M9. Cada item tem proxy de complexidade e ganho esperado.
> Para historia do que foi testado, ver
> [`historia-dirty-lab.md`](historia-dirty-lab.md).

> **Nota (2026-07-01, DB-1 T-CLEAN-2)**: doc **HISTORICO** (2026-05-17, hipoteses faltantes de
> M0-M9). O **registry ATIVO** de hipoteses (mesmo nome, doc diferente) vive em
> [`experiments/lab/dirty/notas/roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md).
> Este fica como traco; consultar o ativo pro estado corrente.

## Curto prazo (protótipo imediato)

### 1. Migracao para protótipo limpo

**Status**: pendente.

**O que**: trazer M8.A pra `tcf/` (modulo principal) com:
- API publica clara
- Convencao output embutida (sem brackets, LF only)
- Header formal (versao, encoding)
- Tests automatizados

**Riscos**: misturar conceitos dirty (provisional ids, alias_temp)
com API publica. Manter encapsulamento.

### 2. Pre-tx delta (timestamps, IDs sequenciais)

**Status**: identificado em M9 (D6 timestamps).

**O que**: camada opcional antes do TCF-CORE que detecta timestamps/
IDs e os substitui por deltas relativos a um base. Decoder
reconstrói.

**Ganho esperado**: significativo em logs/time-series.
D6 atual: 54% raw. Com delta: estimado 30-40% raw.

**Complexidade**: media. Detector heuristico (regex pra ISO 8601,
unix timestamps); encoding compacto do delta.

### 3. Pre-tx estrutural (CPF, UUID, IP)

**Status**: identificado em M6 ([`comparacao-modular-camadas.md`]).

**O que**: camada que reconhece tipos estruturados (CPF
`XXX.XXX.XXX-XX`, UUID `xxxxxxxx-...`, IP `X.X.X.X`) e usa
representacao compacta (bytes binarios ou base32 por slot).

**Ganho esperado**: medio. Datasets com muito ID estruturado.

**Complexidade**: baixa-media. Detectores por regex.

## Medio prazo (algoritmo do detector)

### 4. Decomposicao pos-detector (caso `2~13` reuse)

**Status**: identificado em M8 sessao 2.

**O que**: apos detector greedy escolher alias_1 = (a, b, c, d), se
o intermediario (a, b) e' reusavel em outras posicoes do body,
DECOMPOR alias_1 em (alias_inner = (a, b), c, d).

**Ganho esperado**: pequeno-medio (~5-10 bytes em D4).
**Complexidade**: media-alta. Requer:
- Detector multi-passada (atual + decomposicao)
- Reorganizacao de alias_to_sub e final ids

### 5. Detector global (nao greedy)

**Status**: registrado em M8.

**O que**: ao inves de pick best-net-greedy iterativo, fazer busca
otimizada por SUBSET de aliases que minimiza bytes total.
Possivelmente ILP ou branch-and-bound.

**Ganho esperado**: ate' ~30-50 bytes extras em datasets
desafiadores. Estimativa baseada em M6/M8 missed analysis.

**Complexidade**: alta. Tempo exponencial sem heuristicas.

### 6. Slot variavel em wrapper (caso D9)

**Status**: identificado em M9 (D9).

**O que**: primitivo sintatico `7{}5` onde `{}` indica slot. Body
texto: `7{x1}5`, `7{x2}5`, ..., `7{x20}5`. Decoder substitui
slot pela next-line literal.

**Ganho esperado**: alto em datasets com wrapper-com-variacao.
D9 atual: 43% raw. Com slot: estimado 25-30% raw.

**Complexidade**: alta. Aumenta grammar. Ambiguidades a resolver.

## Longo prazo / pesquisa

### 7. Nos pos-construcao com literal+ref

**Status**: registrado em M6
([`marcadores-multiplo-proposito.md`]).

**O que**: alg16 segmenta strings em atomos baseado em prefix/suffix
matches. Permitir composicoes que envolvem **novos literais + refs
existentes** sem precisar pre-segmentar.

Exemplo (sintetico):
```
ABCDEFG → AB*CD*EFG (atoms 1, 2, 3)
BCD → B~2 cria ref 4 = BCD (literal B + ref 2 = CD)
```

**Ganho esperado**: indeterminado. Em datasets com substrings
pequenos repetidos sem prefix/suffix match disponivel.
**Complexidade**: alta. Mudanca fundamental no alg16 ou pos-tx.

### 8. Right-assoc binarization ou parenthesization

**Status**: registrado em M8.

**O que**: pairwise left-assoc atual restringe inner aliases a
position 0 (para correcao). Alternativas:
- Right-assoc (inverso)
- Mista (selecionar por composicao)
- Brackets na sintaxe `(a~b)~c` (aumenta grammar)

**Ganho esperado**: pequeno-medio. Permite mais sub-tuplas
detectaveis.

**Complexidade**: media. Decoder mais complexo.

### 9. Detector com peso por uso esperado

**Status**: nao explorado.

**O que**: detector atual usa R (count) uniforme. Poderia ponderar
por densidade/posicao/proximidade ou outros features.

**Ganho esperado**: pequeno. Refinamento marginal.
**Complexidade**: media.

### 10. Escala (N, K, L grandes)

**Status**: dirty so' testou em N=12-20 linhas com L=5-30 chars.

**O que**: medir comportamento em:
- N=1000+ linhas
- K=100+ aliases distintos
- L=100+ chars por linha

**Tudo**: validar ratios em escala. Identificar bottlenecks.

**Complexidade**: baixa (so' rodar). Cara em dataset
generation/curation.

## Pesquisa estendida (multi-componente)

### 11. Comparacao com gzip/zstd em scale

**Status**: M0 gziplotr feito como sinal qualitativo.

**O que**: medir TCF vs gzip/zstd em datasets reais e sinteticos
de varios tamanhos. Identificar quando TCF e' melhor.

### 12. LLM comprehension (Phase 2 prep)

**Status**: Phase 1 fechado em
[[../../docs/findings/]] (43% LLMs sobre TCF). Phase 2 em prep.

**O que**: re-medir LLM compreensao do TCF apos M8 vira protótipo
estavel. Avaliar se a nova syntax e' compreendida.

## Notas

- Numeracao nao implica prioridade absoluta. Comparar ganho × complexidade.
- Riscos: NAO comecar (2)-(6) antes do protótipo migrado (1).
- Itens 7-10 sao pesquisa de fronteira, baixa prioridade.
- (11) e (12) sao Phase 2+ separadas do dirty.

## Conexoes

- [[historia-dirty-lab.md]] — o que foi feito ate' agora
- [[../../2026-05-16-M8-virtual-refs-clean-output/notas/conclusoes_M8.md]] — atual
- [[../../2026-05-17-M9-stress-adversarial/notas/conclusoes_M9.md]] — limites identificados
- [[comparacao-modular-camadas.md]] — pre-tx layers
- [[marcadores-multiplo-proposito.md]] — composicional + nos pos-construcao
