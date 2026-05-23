---
title: Reflexao sobre naturezas numericas (2026-05-23)
type: brainstorm-conceitual
status: rascunho
tags: [theory, numericas, naturezas, futuro, brainstorm]
created: 2026-05-23
related:
  - docs/theory/data-natures-taxonomy.md
  - tickets/META-TYPE-ENCODERS.md
  - tickets/T-EXP-H-DA-11.md
  - tickets/T-CODE-PACOTE1-WELD-CANONICAL.md
---

# Reflexao — naturezas numericas

> Brainstorm 2026-05-23 apos H-PERF-05d (Fase 2 closed-validated-with-byte-divergence).
> Owner mencionou ~10 naturezas numericas, ~4 ja' bem abordadas. Reflexao
> conceitual pra organizar futuras direcoes.

## Naturezas numericas (catalogacao tentativa)

Strings sao numericas quando representam valores quantitativos. Por
**natureza COMPORTAMENTAL** (nao por tipo), podemos catalogar:

### Ja' abordadas (canonical M10 cobre)

| # | Natureza | Mecanismo atual | Welded em |
|---|---|---|---|
| 1 | **Incremento sequencial** | seq-RLE near-identical (`*N+delta\|template`) | HCCSeqRLE / ADR-0011 |
| 2 | **Cadencia detectavel** | detect_cadence regra 1 (LCP/LCS uniforme) | auto_cadence / ADR-0008 |
| 3 | **Alta cardinalidade numerica** | detect_cadence regra 2 (`is_numeric AND card > 0.5`) → shape-preserve | auto_cadence / ADR-0008 (refino) |
| 4 | **Comprimento previsivel** | detect_min_len heur v3 (avg_len + card + is_numeric) | auto_min_len / ADR-0010 |

### Parcialmente abordadas (sequenciais via OBAT mas nao explicitas)

| # | Natureza | Status |
|---|---|---|
| 5 | **Range constante** (todos valores em [min, max] estreito) | OBAT pode capturar via prefix comum, MAS nao tem encoder "subtract min" explicito |
| 6 | **Step variavel mas regular** (1, 2, 4, 8, 16, ...) | OBAT/HCC nao capturam — seria pre-tx separado |
| 7 | **Classes / buckets** (valores agrupados em N classes) | Enumerated nature (ja' catalogado mas nao welded canonical) |

### Nao abordadas (candidatas pre-tx natureza)

| # | Natureza | Exemplo | Mecanismo possivel |
|---|---|---|---|
| 8 | **Arredondamento implicito** | precos R$X.99, taxas %.5, etc. | encoder devolve (X, residuo)? |
| 9 | **Deducao por contexto** | valor = func(linha_anterior); calculavel | encoder grava so' input da func + flag |
| 10 | **Lossy-recoverable** | floats com precisao tolerable | round + delta-erro registrado |
| 11 | **Range descontinuo** | discounts {0, 0.02, 0.04, ..., 0.10} | enumerated + small dict |
| 12 | **Magnitude / order-of-magnitude** | timestamps ms vs us vs ns | unit-aware encoding (T01 sub-exp 09 abordou) |

## Avaliacao por cobertura atual

### Bem cobertas (>= 80% do ganho potencial em real-world atual)

- **#1 Incremento**: HCCSeqRLE captura runs near-identical perfeitamente.
  D9 colapsa 158B → 66B; c_custkey -91.94% real-world.
- **#3 Alta-card numerica**: detect_cadence regra 2 dispara em fnlwgt,
  c_acctbal, l_extendedprice (Adult+TPC-H).
- **#4 Comprimento previsivel**: heur v3 captura 9.87% real-world.

### Parcialmente cobertas (10-40% do ganho potencial)

- **#2 Cadencia**: detect_cadence funciona pra wrapper+counter mas nao
  pra cadencias mais sutis (e.g., timestamps com saltos regulares mas
  nao uniformes).
- **#5 Range constante**: OBAT prefixo comum captura mas nao explicita
  range. Pra IDs numericos em range estreito (`1000`..`9999`), poderia
  comprimir mais com "base + 4-digit local" mas hoje nao faz.

### Nao cobertas (oportunidade futura)

- **#6 Step variavel regular**: progressao geometrica (`1, 2, 4, 8`)
  ou aritmetica diferente (`1, 3, 5, 7`). Pre-tx detectaria padrao.
  Limitado a casos especificos — provavelmente nao vale prioridade.
- **#7 Classes/enumerated**: discounts limitados, status codes,
  payment_methods. Real-world TPC-H lineitem tem `l_discount` (11
  valores unicos em 0.00..0.10 step 0.01), `l_returnflag` (3 valores),
  `l_linestatus` (2 valores). Hoje TCF M10 ja' captura via low-card
  + RLE — mas explicit enumerated encoder poderia ser mais eficiente.
- **#8 Arredondamento**: precos varejo, percentuais. Pode haver ganho
  significativo em datasets financeiros.
- **#9 Deducao**: muito especifico — `total = sum(parts)`, `delta_t =
  t_n - t_(n-1)`. Encoder precisaria detectar relacao. Complexo.
- **#10 Lossy-recoverable**: trade-off compressao vs precisao —
  requereria definir tolerancia explicita.
- **#11 Range descontinuo**: subset de classes. Atual TCF captura
  parcialmente via enumerated implicito (dedup).
- **#12 Magnitude**: T01 sub-exp 09 abordou (ms/us/ns normalization)
  mas foi superseded em Pacote 1.

## Direcoes futuras priorizadas

### Alta prioridade (ganho potencial alto, complexidade baixa-media)

1. **#7 Enumerated canonical** (T03 da META-TYPE-ENCODERS):
   detect_enumerated heuristica (cardinality < threshold AND uniform_value)
   → dicionario inline + indices. Pra l_discount, l_linestatus,
   l_returnflag em TPC-H. Estimativa: 5-15% ganho adicional real-world.
   - **Critério reabertura META-TYPE-ENCODERS**: este e' caso onde
     Pacote 1 + ADR-0008 + ADR-0010 nao bastam (cobre numericos
     high-card mas nao categoricos)

2. **#5 Range constante** (sub-natureza incremento):
   detect_range (min/max apertados) → emit `base + N` ao inves de
   string completa. Pra IDs sequenciais grandes (e.g., c_custkey
   1..150000 ja' captura via shape-preserve, mas valores mid-range
   nao). Estimativa: 2-5% adicional em colunas especificas.

### Media prioridade

3. **#8 Arredondamento** (T-novo): detectar precos / percentuais com
   formato fixo (e.g., `.99` cents). Pre-tx separar parte inteira de
   residuo. Ganho dependente de dataset.

4. **#11 Range descontinuo**: subset de #7 — pode ser absorvido em
   enumerated canonical se threshold cardinalidade for ajustada.

### Baixa prioridade (complexa OU ganho marginal)

5. **#6 Step variavel regular**: caso especifico, poucos datasets
   beneficiariam. Talvez NAO vale implementar.

6. **#9 Deducao contextual**: muito complexo (detectar relacoes
   inter-linhas), ganho incerto.

7. **#10 Lossy-recoverable**: requer definicao explicita de tolerancia.
   Fora do escopo "lossless byte-canonical" atual.

8. **#12 Magnitude**: ja' tentado (T01) e absorvido — nao reabrir.

## Conexao com META-TYPE-ENCODERS

META-TYPE-ENCODERS (OPEN desde 2026-05-15) ainda lista T02-T07 +
L01-L05 como adiados. Criterio reabertura: "casos real-world onde
Pacote 1 + ADR-0008 nao bastem".

Apos welding canonical Pacote 1 (ADR-0011) + ColumnFeatures (H-DA-11c),
infraestrutura pra adicionar novas heuristicas esta pronta:
- `analyze_column` pode ser estendido com `n_unicas`, `value_range`,
  `value_step` se necessario
- Pre-pass features unificado simplifica integracao

**Recomendacao**: reabrir META-TYPE-ENCODERS com foco em **T03
enumerated** primeiro (natureza #7). Pacote 5 candidato.

## Naturezas vs Pacotes

Cobertura atualizada (apos welding Pacote 1):

| Pacote | Foco | Naturezas cobertas |
|---|---|---|
| Pacote 1 (delta-aware) | seq-RLE + shape-preserve + min_len + cadence | #1, #2, #3, #4 |
| Pacote 2 (escape) | refutada | — |
| Pacote 3 (parser) | bug fixes | infra |
| Pacote 4 (perf) | OBAT trigram | infra |
| **Pacote 5** (candidato) | **enumerated + range** | **#5, #7, #11** |
| Pacote 6 (candidato) | composite/templated | T02/T05 META-TYPE-ENCODERS |
| Pacote 7 (candidato) | arredondamento | #8 |

## Proximo passo concreto sugerido

~~**Sub-exp exploratorio: T03 enumerated em real-world**~~
**TESTADO 2026-05-23 — NO-GO**

Ver `experiments/lab/dirty/2026-05-23-pacote5-t03-enumerated/01-caracterizacao/`.

**Resultado**: M10 ja' captura enumerated implicitamente via dedup +
HCCSeqRLE. Encoder explicit seria PIOR em low-card com runs adjacentes:
- l_linestatus M10=4137B vs enum LB=10002B → M10 -141.77% MELHOR
- l_returnflag M10=8075B vs enum=10004B → M10 -23.89%
- adult class M10=8229B vs enum=10009B → M10 -21.63%

Enum so' ganha em valores LONGOS sem runs:
- c_mktsegment (5 valores, ~12 chars): +30.20%
- adult relationship (6 valores, "Husband" etc.): +27.18%

Weighted real-world total: **-2.28%** (regressao se forcar enum).

**Aprendizado meta** (mesmo padrao Pacote 2 escape deduction):
- Hipotese promissora conceitualmente pode refutar em medicao empirica
- TCF M10 (dedup + seq-RLE + auto-min_len + auto-cadence) e' mais
  robusto que aparenta — cobre naturezas implicitamente

## Atualizacao categorizacao (pos-medicao)

Re-classifico natureza #7 (enumerated) como **JA COBERTA implicitamente
via M10**, nao "parcialmente coberta":

| # | Natureza | Status atualizado |
|---|---|---|
| 7 | **Classes/enumerated** | **JA COBERTA via dedup + seq-RLE (M10)**. Encoder explicit refutado em medicao 2026-05-23. |

## Naturezas remanescentes (candidatos futuros)

Pos-Pacote 5 refutado, candidatos com potencial real-world incerto:

- **#5 Range constante** (sub-natureza incremento): IDs em range
  estreito poderiam comprimir mais com "base + N local", mas OBAT
  prefix ja' captura parcialmente. Medicao necessaria.
- **#8 Arredondamento implicito**: precos varejo, percentuais. Dataset-
  dependente. Sem dataset financeiro real-world disponivel para teste.
- **#9 Deducao por contexto**: muito complexo (relacoes inter-linhas),
  ganho incerto.

**Hipotese geral**: M10 esta proximo do otimo pra naturezas COMUNS
em real-world tabular. Ganhos adicionais provaveis vêm de:
1. **Performance** (H-PERF-05d adiado, H-PERF-06 Cython)
2. **Naturezas raras** dataset-dependentes (financeiro/cientifico)
3. **Refinos de heuristica** existentes (H-DA-09c/d/e)

Pacotes futuros podem focar mais em PERF + ROBUSTNESS que em
COMPRESSAO adicional via novas naturezas.

## See also

- [Taxonomia formal](../../../docs/theory/data-natures-taxonomy.md)
- [META-TYPE-ENCODERS](../../../tickets/META-TYPE-ENCODERS.md)
- [Roadmap hipoteses](roadmap-hipoteses.md)
- [STATUS](../../../STATUS.md)
