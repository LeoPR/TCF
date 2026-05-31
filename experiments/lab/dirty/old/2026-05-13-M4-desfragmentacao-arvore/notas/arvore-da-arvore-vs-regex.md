# Arvore da arvore + comparacao com regex

**Data**: 2026-05-13
**Tipo**: nota teorica (orienta M4.C1' e seguintes)
**Vem de**: [`buffer-e-refragmentacao.md`](buffer-e-refragmentacao.md)
e [`indice-incremental-de-padroes.md`](indice-incremental-de-padroes.md)
durante analise do resultado M4.C1 v1 (que so' captura runs
inteiras).
**Conecta com**: Patricia tree (M0/Mobsolete), Re-Pair (Mobsolete
Lab 13), conceito de grammar-based compression.
**Status**: orienta a implementacao de M4.C1' (subsequencias).

## Observacao concreta que motivou

D1 (canonico) tem padrao claro nao-capturado por M4.C1 v1:

```
linhas 7-9 do TCF M1.E/M4.C1:
  7,8,3,11,5,6
  9,2,3,11,5,6
  10,8,3,11,5,6
```

Cada run inteira e' UNICA (Counter da 1 cada). Mas a subsequencia
`3,11,5,6` aparece **3x** em runs diferentes — invisivel para
detector de runs inteiras.

## Tese 1 — "ramos diferentes da arvore nao se enxergam"

Se varias subsequencias repetidas existem em runs diferentes,
provavelmente vieram da **mesma segmentacao** subjacente — mas
estao em "galhos diferentes" da arvore. Precisariamos de mecanismo
que **conecte galhos** pra detectar essas repeticoes.

## Tese 2 — "arvore da arvore"

Conceito: olhar a propria arvore (de tokens/refs) novamente em
busca de padroes recursivos.

- Busca bruta (combinar tudo com tudo): captura todos os padroes
  mas custosa
- Busca sequencial (uma linha vs anteriores): captura simples mas
  perde paralelos entre galhos
- **Arvore da arvore**: busca padroes na arvore mesma, possivelmente
  recursiva — meio termo

Analogia: Re-Pair (Mobsolete Lab 13 `2026-05-10-13-repair-bottomup/`)
faz isso recursivamente — substitui par mais frequente, recursa.

## Tese 3 — busca inteligente acelera caso medio

Se a arvore for compressivel (ja' tem alguns padroes detectados),
busca subsequente so' precisa olhar **nos indexados repetidos** —
nao mais nas runs originais.

- Caso medio: arvore comprime bem → busca cresce mais devagar
- Pior caso: tudo unico → busca volta ao combinatorio

## Comparacao com regex

| Aspecto | Regex | Nosso caso |
|---|---|---|
| Padrao | dado (input) | emerge dos dados |
| Tarefa | encaixe | descoberta + medida de utilidade |
| Otimizacao | maior ou menor encaixe | **balanceamento otimo** (nem max nem min) |

**Insight chave**: nosso problema e' **mais dificil que regex**
porque:
1. O padrao tem que ser descoberto
2. Tem que ser MEDIDO (custo vs beneficio)
3. O optimo nao e' "maior" nem "menor" — depende do contexto
   (substring maior ganha mais por uso mas pode aparecer menos)

Isso conecta com a regra de ouro do agrupamento
([../../2026-05-12-M1-marcacao-ambiguidade/notas/regra-de-agrupamento.md](../../2026-05-12-M1-marcacao-ambiguidade/notas/regra-de-agrupamento.md)):
agrupar so' compensa quando contexto ja' tinha separador natural.

## Implicacao concreta para M4.C1'

V1 (runs inteiras) deu -10B. Limite teorico (M4.A) e' 114B
intermediario implicito. Espaco de melhoria grande.

M4.C1' precisa detectar subsequencias. Implementacao minima:
1. Para cada run, considerar TODOS os sufixos (K≥2)
2. Para cada run, considerar TODOS os prefixos (K≥2)
3. Contar globalmente
4. Greedy por net (compensa marker `~` + uso `&N`)
5. Aplicar substituicao

Custo computacional: O(N · L²) onde L = tamanho medio da run.
Para D1-D4 (12 linhas, L medio 6): viavel.

Sub-substituicoes (ex: `3,11,5,6` engole `,5,6`) decididas por
ordem de net decrescente — primeiro o maior, ocorrencias cobertas
removem candidatos menores.

## Quando esta abordagem chega no limite

Para subsequencias **arbitrarias** (nao so' prefixo/sufixo), busca
e' O(N · L³) ou pior. Para datasets grandes precisa estrutura
indexada (suffix automaton, Patricia generalizada — ver
[`indice-incremental-de-padroes.md`](indice-incremental-de-padroes.md)).

No dirty atual (12 linhas), forca bruta com sufixos/prefixos basta.

## Conexoes

- [[buffer-e-refragmentacao.md]] — estrategias de buffer
- [[indice-incremental-de-padroes.md]] — abstracao de armazenamento
- [[../../2026-05-12-M1-marcacao-ambiguidade/notas/regra-de-agrupamento.md]] —
  regra do separador natural
- Mobsolete Lab 13 `repair-bottomup` — Re-Pair como analogia
- Mobsolete Lab 17-19 `patricia-*` — estrutura de indice de
  strings

## Resumido em 1 linha

"Padroes vivem em galhos diferentes da arvore; busca recursiva
(subsequencias) capta. Diferente de regex: padrao + medida +
optimo balanceado."
