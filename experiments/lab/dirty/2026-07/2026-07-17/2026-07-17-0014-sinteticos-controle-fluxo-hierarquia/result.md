# Resultado — sintéticos de controle do fluxo hierárquico

**[probatório]** 12 casos, RT byte-diffável 12/12, wire real em `outputs/*.tcf`, navegação em
[outputs/00-resultado.txt](outputs/00-resultado.txt) + [outputs/01-navegacao.csv](outputs/01-navegacao.csv).
Suíte de pins: `tests/test_hierarchical_control_synthetics.py` (**18 passed**; suíte inteira
**772 passed, 2 skipped, 2 xfailed**).

## Confirmado (a navegação do fluxo, medida)

1. **O princípio "não expandir o óbvio" segura nos casos uniformes**: c01 (baseline) = 0 colunas
   de controle; c02 counts de 200 instâncias = 8 B; c08 counts de 2 níveis = 7+7 B; c10/c11 = 0
   controle (seq-RLE e refs fazem o trabalho no L1).
2. **Fan-out-split com dado realista = −9,5%** (c02 3134 B → c03 2836 B, MESMOS valores): o ganho
   do split depende da coerência por série — com random-walk é modesto; com folhas de baixa
   entropia é dominante (caso constante da revisão: folhas = 96,5% do wire). **Refina
   [[H-HIER-FANOUT-SPLIT-01]]**: o mecanismo é real, o tamanho do prêmio é função da entropia
   por série → decidir por medição (S4), não por regra fixa.
3. **Sintoma emask confirmado em regime realista**: c06 controle = 29% do wire (409 B vs 973 B).
   Menos extremo que o caso periódico da revisão (449>307 B), consistente com
   [[H-HIER-EMASK-SPARSE-01]].
4. **Sintoma NOVO — counts variáveis espalhados não colapsam** (c07): 60% arrays vazios
   intercalados → count 201 B ≈ dados 218 B. A "repetição de vazios" estrutural vira coluna de
   controle incompressível quando os vazios são espalhados (RLE é adjacente). Mesma família do
   sintoma emask → anotado em H-HIER-EMASK-SPARSE-01 (o portador esparso/por-instância cobre os
   dois). Candidato natural do S4.
5. **Achado de fronteira — ordem de chaves em ragged** (ver README): semântica preservada,
   byte-ordem do dump não; gap S0×`.8H`; pinado, registrado, não consertado.

## O que este lab NÃO decide

Forma física (S4-S7), weld de qualquer alternativa, contrato de ordem de chaves (owner).
Sintético de design com viés declarado; nenhum claim de ganho — os números são pinos de
OBSERVAÇÃO pra detectar regressão/melhora de fluxo daqui pra frente.

`confianca: Alta` p/ os pinos (byte-exatos, determinísticos, re-executáveis); `Média` p/ as
leituras comparativas (1 gerador, 1 seed — direção clara, magnitude depende do regime).
