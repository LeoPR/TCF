# Buffer e refragmentacao — raciocinio sobre quando comprimir

**Data**: 2026-05-13
**Contexto**: discussao no macro M4 (desfragmentacao da arvore)
durante exploracao do D4-caos-mix.tcf de M3.B.
**Vem de**: [`../M4-A-instrumentacao/conclusoes.md`](../M4-A-instrumentacao/conclusoes.md)
revelou que ha' 114 bytes potenciais em "no intermediario implicito"
mas 0 em "decl explicita" (M3 ja' confirmara). User pediu para
revisitar o caso D4 e analisar estrategia.
**Sucede**: orienta a decisao de M4.B (simples, sem buffer) vs
M4.C (idx implicito, com decisao de buffer).

## Caso concreto observado

No arquivo
[`../../2026-05-13-M3-encadeamento-declaracoes/M3-B-encadeamento/output/D4-caos-mix.tcf`](../../2026-05-13-M3-encadeamento-declaracoes/M3-B-encadeamento/output/D4-caos-mix.tcf),
varias sequencias de refs se repetem entre linhas mas em
SOBREPOSICAO:

| Linha | TCF | Sequencias notaveis |
|---|---|---|
| 2 (eid 1) | `[a*]\*'*foo*'@\4*\2` | — (declaracao) |
| 3 (eid 2) | `1..4\3` | `1..4` (1a vez) |
| 4 (eid 3) | `1..4\4` | `1..4` (2a — repetiu) |
| 5 (eid 4) | `[b2..5` | `2..5` |
| 6 (eid 5) | `8,2..4\3` | `8,2..4` (1a) |
| 7 (eid 6) | `8,2..4\4` | `8,2..4` (2a) |
| 9 (eid 8) | `1,2,11,12,4,6` | `2,11,12,4` (1a) |
| 10 (eid 9) | `8,2,11,12,4,5` | `2,11,12,4` (2a) + `8,2,11` (1a) |
| 11 (eid 10) | `8,2,11,12,4\3` | `2,11,12,4` (3a) + `8,2,11` (2a) |
| 12 (eid 11) | `1,2,11z4,5` | `1,2,11` (variante) |
| 13 (eid 12) | `8,2,11,14,4,5` | `8,2,11` (3a — com 14 no meio, nao 12) |

## Sobreposicoes problematicas

Em linhas 10 e 11 ha' 2 padroes candidatos sobrepostos:
- `2,11,12,4` (9 chars textuais) — R=3 (linhas 9, 10, 11)
- `8,2,11` (6 chars textuais) — R=3 (linhas 10, 11, 13)
- `8,2,11,12,4` (11 chars) — R=2 superset dos dois (linhas 10, 11)

**Decisao greedy local pode ser sub-otima** porque escolher
`2,11,12,4` cedo pode impedir `8,2,11,12,4` superset depois.

## Estrategia de buffer

O tamanho do buffer (quantas linhas o detector ve antes de decidir)
determina o regime de compressao:

| Tamanho | Mecanismo | Caso D4 |
|---|---|---|
| **buffer 0/1** (online) | a cada linha nova, atualiza candidato | linha 9 ve `2,11,12,4` 1a vez; linha 10 ve 2a vez — ja' aloca idx imediato. Pode escolher cedo demais. |
| **buffer medio** (K linhas) | janela deslizante | mais visibilidade local, ainda pode perder padroes longe |
| **buffer batch** (todo input) | depois de tudo, escolhe global | otimo global. Custo: O(N) memoria |
| **buffer hibrido** | online + refragmentacao posterior | greedy local, mas **desfaz** alias se superset melhor emergir |

## Calculo de net no D4 (cenario isolado)

Para cada candidato (ignorando custos de declaracao = idx
implicito):

| Alias | R | Lt | Eco/uso | Net total |
|---|---:|---:|---:|---:|
| `&1=2,11,12,4` | 3 | 9 | 9-2=7 | +21 |
| `&1=8,2,11` | 3 | 6 | 6-2=4 | +12 |
| `&1=8,2,11,12,4` | 2 | 11 | 11-2=9 | +18 |

**`&1=2,11,12,4` somente** rende +21, melhor que superset (+18).

**Mas se for hibrido**: `&1=2,11,12,4` (R=3, +21) + `&2=8,2,11`
(R=3, +12, mas com sobreposicao em linhas 10,11 onde ambos
poderiam ser usados — precisa regra de prioridade).

## Conceito "gasta processamento pra ordenar/desfazer"

User levantou: pode valer a pena **refragmentar** alias decidido
cedo demais se padrao melhor emerge. Exemplo D4:

1. Linha 10: detector ve `8,2,11,12,4` (R=2) — aloca `&1`.
2. Linha 13: detector ve `8,2,11,14,4,5`. **Reconhece** que
   `8,2,11` e' o padrao estavel (R=3) e `12,4` era acidente.
3. **Decisao**: desfazer `&1=8,2,11,12,4`, criar `&2=8,2,11`.
   Linhas 10, 11 ficam `&2,12,4` em vez de `&1`.

Trade-off:
- Custo: processamento extra (rastrear historico, refragmentar)
- Beneficio: compressao melhor proxima do batch sem ler tudo

Analogo aproximado: Re-Pair faz iteracoes de substituicao —
similar a refragmentacao.

## Trade-offs concretos (a medir em M4.C)

| Variante | Bytes | Tempo | Memoria | Decoder |
|---|---|---|---|---|
| C1 batch greedy | proximo ao otimo | medio | alto (todo input) | simples (alias pre-declarado ou implicito) |
| C2 online greedy | sub-otimo possivelmente | rapido | baixo | simples (alias por demanda) |
| C3 online + refrag | proximo do C1 | maior | medio | mais complexo (rastrear historico) |

## Decisao orientadora

Plano sequencial (fechado em conversa de 2026-05-13):

1. **M4.B** — realocacao densa + inline (sem buffer issue, ~18B)
2. **M4.C1** — batch greedy (idx implicito ou explicito, decisao
   global). **Foco do proximo passo.** Mede teto pratico.
3. **M4.C2 (opcional)** — online greedy. So' se C1 mostrar ganho
   significativo, comparar custo/beneficio do streaming.
4. **M4.C3 (opcional)** — online com refragmentacao. So' se C2
   mostrar perda significativa vs C1.

Se em qualquer ponto a complexidade explodir sem retorno claro,
voltar para pos-otimizacao tipo M2 (mais simples, ganho menor mas
seguro).

## Conexoes com outras notas

- [[../M4-A-instrumentacao/conclusoes.md]] — limites teoricos por
  tecnica
- [[../README.md]] — manifesto M4
- [[../../../notas/quebra-de-linha-como-marcador.md]] (a criar) —
  teoria relacionada sobre fronteiras de container
- [[../../2026-05-12-M1-marcacao-ambiguidade/notas/regra-de-agrupamento.md]] —
  regra geral de agrupamento (separador natural)

## Resumido em 1 linha

"O quanto de buffer determina compressao vs velocidade; M4.C1
batch primeiro, depois decidir se vale online + refrag."
