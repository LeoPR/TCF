# Resultado — olhar pelo mês: o incremento fica melhor MESMO, e o design saiu de graça

**2026-08-09 · dirty · n=600, RT em 2 níveis (wire real + espelho) em todos os alvos de
todos os regimes. Números em [`outputs/medicoes.md`](outputs/medicoes.md).**

Direção do owner: *"olhar do ponto de vista do dia não é errado, mas temos que ver se é
possível olhar pelo mês, assim o incremento fica melhor."* Confirmado — e com um bônus:
**nenhum transform de coluna é necessário**. Todos os alvos mensais são per-valor com
válvula, o MESMO protocolo do `SPEC_DATA_ISO`; a mágica é que eles transformam
constância-de-dia em uniformidade-de-delta, que o core (M10 + ADR-0040) já come sozinho.

## O placar (bytes; alvos novos pagam +11 B de header)

| regime | hoje (A1 ordinal-dia) | melhor alvo mensal | fator |
|---|---:|---:|---:|
| **mensal-dia1** | 679 | **31** (A2 mês-época) | **21,9×** |
| mensal-dia15 (pagamento) | 679 | **33** (A4 mês×31+dia) | 20,6× |
| mensal-fim-do-mês (fecho) | 655 | **31** (A2f convenção-fim) | 21,1× |
| trimestral-dia1 | 139 | **31** (A2) | 4,5× |
| **mensal-com-faltas** | 2799 (spec recusa) | **41** (A2) | **68,3×** |
| YYYY-MM puro (H5 da triagem) | 826 (spec recusa) | **31** (spec irmão YM) | 26,6× |
| misto d01+d15 | 629 | **36** (A4) | 17,5× |
| diário (CONTROLE) | **32** (A1) | 136+ (todos perdem) | floor protege ✓ |

Dois destaques que não estavam no pedido:

- **mensal-com-faltas**: no eixo do dia, um mês pulado torna os deltas irregulares e o
  spec recusa a coluna inteira. No eixo do mês, a falta é só um delta `2` no meio de
  `1`s — **periódico ou quase**, e o ADR-0040 come (41 B). É o caso mais realista de
  todos (competência sem fato) e é onde o ganho é maior.
- **misto d01+d15**: o A4 faz os dois dias alternarem em deltas `[14,17]` — período 2,
  um marcador (36 B). O eixo transforma um regime "sujo" em cadência exata.

## A estrutura de design que os números revelam

| alvo | o que é | onde ganha | onde morre |
|---|---|---|---|
| **A4 mês×31+dia** | `(ano*12+mês-1)*31+(dia-1)` — **sem convenção**, injetivo p/ toda data | QUALQUER dia constante (33 B) e até misto (36 B); perde só 2 B do ótimo nos casos de convenção | fim-do-mês (745 — dia varia) e diário (136) |
| A2 mês-época d01 | convenção `dia==01` | dia1/trimestral/faltas (31–41 B) | qualquer outro dia (válvula total) |
| A2f mês-época FIM | convenção `dia==último` | fecho contábil (**31** vs 745 do A4) | todo o resto |
| A3 YYYYMM | legível, convenção d01 | nunca — perde de A2 sempre (55 vs 31; nas faltas 1731 vs 41, a virada `+89` quebra runs) | **morto** |
| YM grafia própria | parser de `YYYY-MM`, re-emite `YYYY-MM` | a grafia sem dia (31 B) | n/a (grafia distinta = tag distinta, senão RT quebra) |

**A3 morre** (a legibilidade do payload custa a aritmética — mesma lição do ISO-como-alvo
no lab 0235). **A2 vs A4**: a diferença nos regimes da convenção é 2 B (o template maior
do A4); a cobertura do A4 é muito maior. **A2f é a única convenção que paga** (24× sobre
o A4 no fecho).

## O que isso muda nas filas

1. **`T-SPEC-PARSE-X-ALVO` atingiu o critério de abertura.** A regra era "separar parse
   de alvo quando a segunda grafia aparecer": agora há DUAS grafias (`YYYY-MM-DD`,
   `YYYY-MM`) e TRÊS alvos medidos (ordinal-dia, mês-geral A4, mês-fim A2f) — 2×3 com
   payloads compartilhados. Fatorar vira economia real, não abstração especulativa.
2. **O `T-DATA-ALVO-DELTA` (delta-coluna) perde o caso mensal.** O teto dele no mensal
   era 349 B; o alvo mensal faz 31–33 B **dentro do protocolo per-valor existente** —
   10× melhor e sem mudança de protocolo. Sobram pro delta-coluna: espalhado-ordenado
   (644) e ciclo-quebrado (345 vs 677). A urgência cai de novo.
3. **Weld candidato barato**: mesma classe do `SPEC_DATA_ISO` — specs novos no registry,
   zero mudança de core/protocolo. Recomendação: **A4** (alvo mensal geral, tag p.ex.
   `:data-mes`) + **A2f** (fecho, `:data-mes-fim`) + **YM** (`:data-ym`, grafia
   `YYYY-MM`). O FLOOR decide entre eles e o ordinal como sempre — nunca-pior.

## Miúdos

- Per-valor exige **uma grafia de re-emissão por tag** — por isso `YYYY-MM` é spec
  IRMÃO, não um parser extra do mesmo spec: payloads iguais com grafias diferentes na
  mesma coluna quebrariam o RT. (É o guard de re-emissão do `DataIsoSpec`/ADR-0040 pela
  terceira vez.)
- O controle diário confirma o FLOOR: todos os alvos mensais perdem (136–2234 B) e o
  ordinal continua vencendo (32 B). Candidato entra, nunca substitui.
- `mensal-fim-do-mês` sem spec = 6455 B (o pior C0 da família data até hoje) — o fecho
  contábil é exatamente onde o dado real mais dói.

## Próximo passo

Decisão do owner sobre o weld (A4 + A2f + YM como specs; ou fatorar já no
`T-SPEC-PARSE-X-ALVO`). Depois, o **lab clean em massa** da família data consolida tudo
(EXP no molde do EXP-016).
