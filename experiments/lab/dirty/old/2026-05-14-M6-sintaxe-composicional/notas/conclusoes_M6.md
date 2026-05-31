# Conclusoes M6 — Sintaxe composicional

**Data**: 2026-05-14
**Vem de**: critica do user sobre M5 (M2.A preambulo regressao + M4.C1'
marker close redundante) que apontou para um framework mais geral:
markers como **operadores composicionais**.

## Resultado

| Sintaxe | D1 | D2 | D3 | D4 | Total | vs M1.E |
|---|---:|---:|---:|---:|---:|---:|
| M1.E baseline | 149 | 180 | 206 | 141 | 676 | 0 |
| M4.C1' atual (M5 lider) | 138 | 174 | 196 | 128 | 636 | -5.9% |
| M6.A (M2.A inline) | 142 | 177 | 203 | 142 | 664 | -1.8% |
| **M6.C (composicional)** | **128** | **175** | **194** | **122** | **619** | **-8.4%** |

RT 16/16 OK. M6.C reduz **17 bytes adicionais** sobre M4.C1' atual.

## Achados

### Achado 1 — M6.C composicional supera M4.C1'

Algebra previa **R bytes/composicao** de economia. Empirico **17 bytes
total D1-D4** (R medio ~3 vezes ~5-6 composicoes ≈ 15-18 bytes).
Confirmado dentro da margem.

Origem da economia:
- **1 byte na 1a aparicao**: sintaxe composicional usa `~` no lugar de `,`
  (sem close marker). M4.C1' atual gasta `~tupla~` (2 chars).
- **1 byte por reuso**: composicional reusa com bare ref id (`19`).
  M4.C1' reusa com `&N` (1 + len(N) chars).

### Achado 2 — M6.A (M2.A inline) ganha pouco

D1-D4 total: 664 vs M2.A preambulo (M5 result 666) = -2 bytes apenas.
Esperado pela algebra: -2 + len(N) bytes/alias = -3 bytes/alias para
len(N)=1, ~ -6-9 bytes total esperado.

**Diferenca empirica menor que algebra** porque:
- M2.A detector usa **sufixos K>=3 only** (coverage restrita)
- D1-D4 tem aliases que sao sufixos curtos ou subseqs no meio — M2.A
  pega menos casos que M4.C1' / M6.C
- Logo M2.A inline aplica em menos lugares; o ganho por aplicacao
  e' o esperado mas multiplicado por menos aliases

**Conclusao parcial**: M2.A INLINE ainda fica dominada por M4.C1' atual
e por M6.C composicional. Mas a "dominacao algebrica" do M5 estava
correta em direcao — apenas exagerada (preambulo amplifica o gap).

### Achado 3 — composicional expoe a hierarquia do alg16

O insight do user "alg16 ja' gera grupos de grupos naturalmente; sintaxe
deve expor" se manifesta empiricamente:

Em D1 linha 6 (`maria@hotmail.com`):
```
7~8,3~15~5~6
```
- `7~8` cria ref 16 = "maria" (composicao binaria de mari+a)
- `3~15~5~6` cria refs 17, 18, 19 (pairwise: @+hot, @+hot+mail, full)
- ref 19 reusado em linhas 7 e 8 (pedro@hotmail.com, ana@hotmail.com)

A hierarquia (`maria` como composicao de 2 atomos, `@hotmail.com` como
composicao de 4 atomos) e' explicita no body — sem marker pair, sem
preambulo, sem `&` prefix.

### Achado 4 — pairwise binarization usa ids mas nao paga overhead

Cada composicao K-ary aloca K-1 ids (pairwise left-assoc). Em D1-D4:
- 4-5 composicoes detectadas por dataset
- ~10-15 ids extras alocados por dataset
- Ids ainda 2-digit em D1-D4 (16-25 ids totais)
- Reuso custa 2 chars (id 2-digit), igual `&N` 1-digit do M4.C1'

Em datasets maiores, ids podem chegar a 3-digit — reuso cresce para
3 chars. Margem composicional reduz mas ainda positiva.

## Limitacao registrada

### Ids inflacionados em escala grande

Composicional aloca K-1 ids por composicao. Para 100 composicoes K=4:
300 ids extras. Combinado com atoms (talvez 200): total 500 ids,
len(N)=3 chars uniformemente.

Reuso M6.C = 3 chars; M4.C1' reuso = 4 chars (`&100`). Composicional
ainda ganha mas margem fica menor.

**Limite teorico**: quando len(N_composicional) >= len(N_M4) - 1,
a diferenca empata. Em datasets de escala arbitraria, depende de quanta
detecccao de composicao versus baseline acontece.

## Trace/debug do detector (adicionado 2026-05-14)

Adicionado em M6.C: cada `<dataset>.optimization_trace.txt` em
`debug/` mostra:
- Atomos provisional → final mapping
- Iteracoes do detector com top 10 candidatos por net (formula explicita)
- Picks + linhas afetadas + ocorrencias substituidas
- Ambiguidades (multiplos candidatos com mesmo net)
- Compositions finais (id + sub + emissao)
- **Missed opportunities** post-hoc: pares (X,Y) adjacentes com R>=2 e
  net>0 que detector nao capturou (porque alias_markers ficam opacos
  apos substituicao)

### Quantificacao em D1-D4

| Dataset | Missed pairs | Est. savings |
|---|---|---:|
| D1 | (10,6) | 4 bytes |
| D2 | (4,12), (10,12) | 7 bytes |
| D3 | (15,16), (14,22), (15,3), (3,11), (8,3) | 11 bytes |
| D4 | (10,18), (10,7), (1,7) | 6 bytes |
| **Total** | | **28 bytes** |

Se detector visse alias_markers como refs sinteticas (proposta de
melhoria do detector, fora do escopo M6), a economia adicional seria
~28 bytes em D1-D4 → ~591 total (-12.6% vs M1.E baseline 676).

### Insight do trace

Em D3 iter 1, 5 candidatos empataram em net=8 — greedy escolheu o
primeiro por ordem de Counter. Decisao arbitrária; outra ordem
poderia render diferenca. Trace permite identificar esses casos.

Em D4 iter 1, picked `(2,11,12,4)` com R=3 net=14 — sub-tupla nao
contigua. Pairwise composicao crio 3 ids (16, 17, 18). Outras
sub-tuplas com sufixo/prefixo dessa NAO foram detectaveis nas
iters seguintes porque seu refs viraram alias_marker opaco.

## Pendencias / proximo passo

Dirty fechado novamente. Migrar para prototipo com:

- TCF-CORE intocado (alg16)
- Sintaxe core: **M1.E base + M6.C composicional** (M4.C1' obsolescido)
- Pre-tx opcionais: delta (datas), estrutural (CPF/UUID)

Direcoes futuras (nao protótipo inicial):
- Nos pos-construcao com literal+ref (ver
  [[../../notas/marcadores-multiplo-proposito.md]])
- Detector mais sofisticado (escolha entre `~` e `,` por composicao
  com calculo de id-pressure)
- Avaliacao em escala (N grandes, K grandes)

## Conexoes

- [[../../notas/marcadores-multiplo-proposito.md]] — analise algebrica
- [[../../notas/vetores-de-comparacao-alem-de-bytes.md]] — vetores nao-byte
- [[../../2026-05-14-M5-pilha-M2A-M4C1p/notas/conclusoes_M5.md]] — M5 superado
- [[../../2026-05-13-M4-desfragmentacao-arvore/notas/conclusoes_M4_C1.md]] —
  M4.C1' base que foi superada por composicional
