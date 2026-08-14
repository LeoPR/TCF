# Resultado — um spec de inteiro faz sentido? **Sim, em três regimes nomeáveis**

16 casos sintéticos controlados, **0 falhas de round-trip, 16 pins verdes**. Os três alvos
são generalizações do que o projeto já soldou para outros tipos — nenhuma ideia nova.

## Onde o spec ganha

| caso | núcleo | melhor | ganho | alvo | herdado de |
|---|---:|---:|---:|---|---|
| `prog-epoch` (timestamp, passo 60) | 81 B | **29 B** | **2,79×** | OFFPAD | ordinal do `data-iso` |
| `prog-base-alta` (1e9+i) | 65 B | **26 B** | **2,50×** | OFFPAD | idem |
| `prog-passo7` | 48 B | **27 B** | 1,78× | PAD | padding do `IP` |
| `id-largura-fixa-11` | 7209 B | **4730 B** | 1,52× | B94 | base-94 do `CPF` |
| `prog-passo1` (1..600) | 36 B | **26 B** | 1,38× | PAD | padding do `IP` |
| `id-largura-fixa-6` | 4209 B | **3217 B** | 1,31× | B94 | base-94 do `CPF` |
| `com-nulos` | 240 B | 232 B | 1,03× | PAD | — |

## Onde o núcleo já resolve, e o FLOOR recusa (como deve)

`prog-largura-fixa` (22 B — a progressão já é limpa) · `faixa-pequena-0-100` ·
`cardinalidade-5` (território do bN) · `quase-constante` (RLE) · `prog-descendente` (25 B) ·
`zeros-a-esquerda` (a armadilha: `000001` não é o inteiro `1`, e o spec **recusa** por
não-canonicidade — mesmo guard de re-emissão do `data-iso`) · `negativos` · `sujo-10pct` ·
`misto-largura`.

**Nove dos dezesseis casos são recusa correta.** É metade do valor do lab: saber onde não
mexer.

## As três causas, nomeadas

1. **Largura variável quebra o marcador.** `1..600` sai em três marcadores (`*9+1|1`,
   `*90+1|10`, `*501+1|100`) porque o run quebra em 9→10 e 99→100. Com pad vira um. É o
   mesmo fenômeno que a docstring do `data_iso` descreve para ISO, e que o `IP` já resolve
   com padding zero-leading.
2. **Base alta desperdiça dígitos que não informam.** Em `1e9+i` só os 3 últimos dígitos
   variam; o offset para o mínimo transforma isso numa progressão curta. É a ideia do
   ordinal de data aplicada a inteiro.
3. **Largura fixa aleatória não tem o que comprimir em decimal.** 600 ids de 11 dígitos
   custam ~7,2 KB porque cada dígito ocupa um byte; base-94 os leva a 4,7 KB. É o CPF.

## Os quatro pins que corrigi (a expectativa era minha, não do código)

Eu havia pinado `prog-descendente`, `negativos`, `sujo-10pct` e `misto-largura` como "spec
ganha". Todos vieram `core`, e em todos o FLOOR está certo:

- **negativos**: o offset+pad **piora** (0,89×) — o `-` custa 1 char, o pad custa mais.
- **sujo-10pct**: cada literal quebra o run *e* paga o marcador.
- **misto-largura**: sem progressão, o pad não tem o que ativar.
- **prog-descendente**: o núcleo já entrega 25 B.

O pin serve exatamente para isso: quando diverge, ou o código está errado ou a expectativa
está. Aqui era a expectativa, e a correção está no `run.py` com a razão.

## Resposta à pergunta

**Sim, um spec de inteiro faz sentido** — mas não como "spec de número". Ele é útil em três
regimes com gatilho **detectável na própria coluna, antes de encodar**:

| gatilho | alvo | ganho medido |
|---|---|---|
| progressão + largura variável | PAD | 1,38–1,78× |
| progressão + base alta | OFFPAD | 2,50–2,79× |
| sem progressão + largura fixa | B94 | 1,31–1,52× |

Fora deles, **recusa** — e o FLOOR já garante isso sem trabalho extra.

## O que este lab NÃO responde

- **Corpus real.** Tudo aqui é sintético controlado, por escolha (isolar o mecanismo). O
  corpus dita o default: antes de soldar, medir em colunas reais **quais gatilhos aparecem e
  com que frequência**. É a mesma regra que valeu para data.
- **Decimais e moeda.** Fora de propósito — `12.34` não é inteiro. A medição prévia diz que
  centavos rendem só 1,17×, então é caso próprio.
- **Um alvo ou três?** Podem virar um spec com parâmetro ou três specs irmãos. O precedente
  CPF/CNPJ é "um objeto por grafia"; aqui a grafia é a mesma e o que muda é a **estratégia** —
  decisão a tomar com o corpus na mão.
- **Como o parâmetro viaja.** PAD precisa da largura; OFFPAD precisa da largura **e da base**;
  B94 precisa dos dígitos de origem. Hoje isso vive no objeto do spec (out-of-band). Para um
  spec welded, ou o id carrega o parâmetro, ou ele é deduzível do corpo. **É a mesma classe do
  requisito de meta que o M/H vai precisar** — anotado aqui para não ser descoberto tarde.
