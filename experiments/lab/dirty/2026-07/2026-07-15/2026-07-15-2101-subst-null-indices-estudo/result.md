# Resultado — índices de substituição (null pré-semeado): mecanismo + 2 formas de header

**[probatório]** `proto.py` (codec de dicionário com especiais pré-semeados, sentinela não-string)
+ `study.py`. Números: [outputs/00-medicoes.txt](outputs/00-medicoes.txt). Material de FORMA
(mecanismo + custo), não medida de ganho de produto.

## Confirmado

- **Lossless + 4 vias**: `null`(→None) ≠ `"null"`(string) ≠ `""`(string) ≠ ausente(=presença, fora).
  `None` NÃO aparece no arquivo (o dict guarda só as strings; índice 0 = None é conhecido pela VERSÃO).
  A **colisão que refutou "null=index"** (lab 2026-07-13-1921) some — o especial é sentinela não-string.
- **Unificação P3a+P3b**: null-em-campo e null-em-elemento usam o MESMO codec (o elemento null é só
  ref ao índice 0 no stream). É o ganho decisivo vs máscara-`0` (que precisaria de element-mask nova).
- **Byte-compat**: coluna sem especiais → byte combinatório zero/ausente → sem custo (compat do P1).
- **Pré-semeadura, não shift condicional**: a tabela nasce com os reservados; encode/decode não têm
  "if null" — só um dict que começa preenchido (validou o refinamento do owner).

## As perguntas do owner, medidas

- **Forma do header (A inline × B bloco)**: **não há vencedor único** — crossover por nº de
  colunas-com-especial. A (1 byte/col-especial) vence com POUCAS; B (bitmap `ceil(ncols/8)`) vence
  com MUITAS (16/16 → B por −14B; 0/16 → A por −2B; vira em ~2-3 col de 16). O crossover desloca com
  `ncols`. **Recomendação**: default + escolha por densidade (ou knob), não cravar uma forma.
- **Custo decimal do shift +1** (owner C): barato longe das fronteiras; +1 dígito por ref ao cruzar
  9/99/999 (Δ +4→+7B no stream medido). Confirma "medir, não assumir"; no comum é quase-grátis.
- **Índice × máscara-`0`**: índice **vence no null RARO** (p=0.1: −149B) — o caso comum de API; a
  máscara só edge no null frequente (p=0.5: +13B), e mesmo assim com ressalva (baseline de máscara
  CRUA, sem o RLE do L1 real). Robusto: a unificação + o comum favorecem o índice.

## Fronteira / o que NÃO estabelece

- **Byte exato é APROXIMADO**: o modelo é dict puro; o L1 real é afixo/HCC — o weld integra na
  numeração de referências real (`syntax.py`), onde os números podem diferir. A máscara-baseline está
  sem RLE (pessimista). O resultado robusto é qualitativo (unificação, colisão resolvida, crossover
  do header, ordem de grandeza do shift), não os bytes finos.
- **null-only**: true/false/bN NÃO implementados (hook deixado: stream de índices é empacotável por
  bN; tabela de reservados extensível). Ausência-como-índice (owner D) não medida aqui — próximo.
- **Toca L1 no weld**: aqui é engenhoca isolada; weldar mexe na numeração real (aprovação + gate
  byte-canônico; mesmo arquivo do BUG-SEQRLE-RANGE-EMPTY-B).

`confianca: Média` p/ o design (mecanismo provado, forma medida). Próximo (owner decide): ratificar
default de header + se ausência migra pro framework, então lab de integração ao L1 real (com aprovação).
