# EXP-019: relatório

**7 portões · 8 amostras reais estratificadas · 0 falhas.** Suíte do repositório: **1928
passed, 3 skipped**, inalterada (o lab não toca `src/tcf`).

O conjunto caiu de **390.863 B** para **290.949 B**, ou seja **−25,6%**, só por deixar de
escolher a família pela grafia da entrada.

## O ganho, por amostra

| amostra | `.8H` (antes) | `.8R` (hoje) | ganho |
|---|---:|---:|---:|
| wine-quality | 37.846 B | **20.203 B** | **−46,6%** |
| adult-census | 26.705 B | **15.937 B** | −40,3% |
| tpch-lineitem | 77.865 B | **50.376 B** | −35,3% |
| online-retail | 52.271 B | **37.892 B** | −27,5% |
| receita-cnpj | 42.783 B | **33.496 B** | −21,7% |
| br-identidades | 55.120 B | **45.273 B** | −17,9% |
| tpch-orders | 70.744 B | **61.366 B** | −13,3% |
| ibge-municipios | 27.529 B | **26.406 B** | −4,1% |

**O ganho varia sete vezes entre a melhor e a pior amostra, e isso é informação, não ruído.**
Ele mede o quanto o `min(tcf, raw, dict, split)` tinha a oferecer que o `tcf` sozinho não
oferecia. O wine-quality lidera porque é 13 colunas de float denso, onde o `%split` fatia a
grafia decimal e o `.8H` não tinha esse candidato. O ibge-municipios fecha a lista porque são
nomes próprios quase todos distintos: ali o `tcf` já era a melhor resposta, e o roteamento não
tinha o que melhorar.

Nenhuma amostra piorou, que é o que o G2 exige.

## O `sort_by`, depois do FLOOR

32 colunas-chave candidatas nas oito amostras. Em **nenhuma** delas o `sort_by` fez o wire
crescer:

| amostra | chaves | ordenou | melhor ganho | pior saldo |
|---|---:|---:|---:|---:|
| adult-census | 12 | 8 | −685 B | **0 B** |
| tpch-lineitem | 7 | 5 | −671 B | **0 B** |
| ibge-municipios | 4 | 2 | −288 B | **0 B** |
| receita-cnpj | 3 | 2 | −604 B | **0 B** |
| tpch-orders | 2 | 1 | −707 B | **0 B** |
| wine-quality | 2 | 0 | 0 B | **0 B** |
| online-retail | 1 | 0 | 0 B | **0 B** |
| br-identidades | 1 | 0 | 0 B | **0 B** |

A coluna `ordenou` é a que explica por que o FLOOR importa: em **18 das 32 chaves** a ordenação
venceu e foi emitida, e nas outras **14 ela perdeu e foi descartada**. Antes do ADR-0050 essas
catorze teriam sido emitidas assim mesmo, cobrando bytes que ninguém pediu. Agora o pior caso
é empatar.

Repare que as três amostras com `ordenou = 0` são justamente as de chave quase única
(`InvoiceNo`, `cpf`, e os floats do vinho): ali agrupar não tinha o que agrupar, e o encoder
percebeu sozinho.

## O que não mudou, e é metade do resultado

O G6 testou cinco perturbações sobre cada amostra: ragged, aninhado, `\n` no valor, `\r` no
valor e `\n` no nome. **Quarenta casos, quarenta continuam no `.8H`, quarenta fazem round-trip
exato.**

Isso não é formalidade. O `.8H` escapa folhas e nomes, e o flat os recusa, porque o wire é
LF-only e o LF separa o meta. Se a canonização tivesse ficado gulosa, esses quarenta casos
teriam trocado um round-trip que funciona por um `ValueError`: o usuário perderia uma
capacidade que já tinha, sem pedir e sem aviso.

## A view concorda consigo mesma

`select() == decode()` nas oito amostras. E `agg_by == group_sum` em **44 pares** de
(chave, coluna numérica), medidos dos dois lados: no blob que o FLOOR deixou fora de ordem e no
que ele ordenou. Era o risco que o ADR-0050 criou ao tornar a ordenação opcional, e ele está
fechado.

O `group_count` bateu com contar o decode em **28 de 28** chaves. Em 13 delas a coluna estava
em modo `@dict`, que é onde a resposta sai da estrutura sem expandir as linhas.

## O que este experimento não responde

**Desempenho.** Os microssegundos por chamada estão em `resultado.json`, mas o código não é
otimizado e a máquina não é controlada: eles servem de ordem de grandeza, não de medida. O
eixo é do `.9`, com o `bench_perf` e seus calibradores.

**Volume.** Oitocentas linhas por amostra é dimensionamento para *consistência*, não para
escala: o que se testa aqui é se as regras valem, e uma regra que vale em 800 linhas
estratificadas de oito fontes não passa a falhar em 800 mil. O comportamento *sob volume* é
outra pergunta, e o `bench_perf` já a cobre.

**Latência ao primeiro resultado**, que continua sem medição em lugar nenhum e é o único eixo
em que o layout ordenado ainda poderia ganhar (H-14-07).
