# Procedência dos dados — e o viés declarado

## Sintéticos (5 casos + 11 pontos de virada)

Gerados em `run.py`, **sem `random`** — o sorteio do ponto de virada usa um LCG determinístico,
para o lab ser reprodutível byte-a-byte. Gravados em `inputs/<caso>.entrada.json` com
`<caso>.fonte.json`.

Os 5 casos variam **as duas coisas que decidem o resultado**, de propósito:

| caso | k | n | o que isola |
|---|---:|---:|---|
| `k096-n0672` | 96 | 672 | repetição alta (7 dias do mesmo dia) |
| `k096-n096` | 96 | 96 | **progressão perfeita**, sem repetição |
| `k1440-n1440` | 1440 | 1440 | progressão com k alto |
| `k2000-n2000` | 2000 | 2000 | todos distintos — pior caso do `bN` |
| `k0024-n2000` | 24 | 2000 | melhor caso do `bN` |

**Viés declarado, e é o principal deste lab**: quatro dos cinco são **progressões aritméticas
perfeitas**. Isso é o melhor caso possível para o `seq-RLE` e o **pior** para qualquer
bit-packing — e é justamente por isso que estão aqui: o achado central (*binarizar destrói a
estrutura*) só aparece contra um caso onde há estrutura. **Nenhum deles estima ganho no
mundo.**

### O defeito corrigido no ponto de virada

A 1ª versão gerava `_hh((i % k) * (86400 // k))`, que varia `k` **e** a regularidade juntas — o
resultado saiu não-monotônico (k=1440 vencia, k=288 perdia). É o mesmo erro do artefato de
alinhamento de 2026-07-23. **Corrigido**: as horas são sorteadas de um pool de `k` valores, com
LCG, então a ordem é irregular em todo `k` e só a cardinalidade varia. É o que torna a virada
legível.

## Real (1 coluna)

`Z:/tcf-data/interim/online-retail.db`, a parte de hora de `InvoiceDate` (split no espaço).
Passo espalhado, alvo 2000 → **564 distintos**. **Não versionado**; o lab roda sem `Z:`.

**Viés**: uma coluna, de uma fonte, e ela **não é hora pura** — é o campo de hora de um
timestamp de varejo, com **segundo constante `00`**. Mas é justamente por ser irregular e ter
k=564 (acima do teto de 256 do `bN`) que ela cai no nicho que o lab identifica. O ganho de
46,5% vale **para esse regime**, não para "hora" em geral — e o corpus não tem outra coluna
para confirmar.

**Lacuna declarada**: a base que traria hora de verdade (`beijing-pm25.db`, telemetria horária)
está com **0 bytes**. É literalmente o dataset que o ADR-0018 citou em 2026-05-27 ao registrar
os 228,8% de inflação da coluna `hour`. **O caso canônico da hipótese não pode ser medido hoje.**
