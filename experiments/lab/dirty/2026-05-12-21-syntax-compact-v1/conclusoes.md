# Conclusões — sintaxe compacta v1 corta bytes ~45% sem mudar algoritmo

Roundtrip 21/21 OK em ambas as sintaxes. Total: **156126 → 85508
bytes** (redução de 45.2%) com o mesmo algoritmo do exp 16.

## Validação das hipóteses anteriores

### 1. A nota `marcadores-compactos` previu este resultado

> "Hoje a sintaxe verbosa tem custo elástico alto. Marcadores
> compactos reduzem bytes 1-2× sem mudar comportamento."

Confirmado: razão média 0.548. O ganho está bem alinhado com
a estimativa intuitiva da nota.

### 2. A métrica de "unidades de informação" é invariante de
   sintaxe

A coluna `unid` é idêntica nas duas sintaxes. Confirma que a
métrica de unidades captura a **estrutura** (refs + chars de
literal), independente de como os marcadores são representados
em texto. Justifica retrospectivamente a decisão de reportar
unidades em todos os exps anteriores.

### 3. O exp 19 estava correto sobre par A+B

O exp 19 mostrou que par A+B independente não reduz unidades,
mas pode mudar a relação refs/literais. Em sintaxe verbose isso
piorava bytes (refs > literais curtos). **Em sintaxe compacta o
trade-off muda**:

- Literal curto verbose: `"X"` = 3 chars
- Ref verbose: `noN[-K:]` = 10 chars (para N e K de 1 dígito)
- Literal curto compact: `'X'` = 3 chars
- Ref compact: `@N>K` = 4 chars

Em compact, ref é só **1 char mais cara** que literal curto. O
trade-off bytes vs unidades praticamente desaparece. **A
escolha do exp 16 ainda é boa**, mas a do exp 19 deixaria de ser
penalizada.

## Onde a redução é maior e menor

**Maior redução** (razão < 0.55) em datasets do **regime A**:

- D2-completo: 0.509
- iso-timestamps: 0.499
- urls/iso/codigos/ips em escala: 0.522-0.571

Característica comum: muitas refs (poucos literais grandes).
Cada ref corta 4-5 chars na nova sintaxe.

**Menor redução** (razão > 0.80) em datasets do **regime B**:

- uuids: 0.886 (-11%)
- cpfs: 0.807 (-19%)

Característica: quase todo literal. Como `"X"` → `'X'` é igual
em chars, o ganho vem só dos overheads estruturais (macros,
ids de nó). Confirma que sintaxe compacta beneficia
proporcionalmente **mais o algoritmo do que o conteúdo**.

## Custo por unidade — métrica nova interessante

Calculei `bytes / unidades` para ver o "custo médio" de
representar 1 unidade de informação:

| Dataset | bv/u | bc/u | redução |
|---|---:|---:|---:|
| D2-mini | 4.43 | 2.47 | -44% |
| urls-N1000 | 13.88 | 7.76 | -44% |
| iso-N1000 | 14.83 | 8.04 | -46% |
| ips-N1000 | 13.60 | 7.19 | -47% |
| codigos-N1000 | 14.17 | 7.88 | -44% |

Em verbose, cada unidade custa ~14 bytes em escala N=1000. Em
compact, custa ~7-8 bytes. **Aproximadamente metade.**

O "limite ideal" de 1 unidade = 1-2 bytes (mencionado na nota
`custo-de-marcadores`) ainda está distante. Marcadores binários
ou sintaxe inferida (Direção 2) podem chegar lá — fica para
experimentos futuros.

## O que isto valida na interface `Syntax`

Esta foi a **primeira troca radical** de sintaxe usando a
interface. A `CompactV1Syntax` foi escrita do zero, sem mexer
em `online.py`, `syntax_base.py`, ou `syntax_verbose.py`. Run
em paralelo com a verbose, comparação direta.

**A interface se mostrou suficiente** para sintaxes
significativamente diferentes (mudança de macro, marcador,
estrutura de declaração, concatenação implícita). Não foi
preciso evoluir a abstração.

Próximas sintaxes vão poder ser implementadas do mesmo modo:

- **Compact v2** com inferência pela ordem (Direção 2 da nota)
- **Compact v3** com chars unicode reservados para marcadores
- **Hibrida** com algumas partes binárias (base64 para refs grandes)

Cada uma é classe nova que herda `Syntax`. O run pode rodar
todas em paralelo, gerar TCFs separados, comparar bytes
diretamente.

## Pontos a registrar

1. **Redução de 45.2% no total de bytes** sem mudar o algoritmo
   nem o roundtrip.

2. **Custo por unidade caiu ~50%** (8.5 → 4.6 bytes/unid em
   média). Aproxima o limite teórico de 1-2 bytes/unidade.

3. **Razão estável** em datasets do regime A (0.5-0.6) confirma
   que o ganho vem da estrutura, não de casos isolados.

4. **Interface `Syntax` se mostrou suficiente** para essa
   primeira troca radical. Não precisou evoluir.

5. **A métrica de unidades** se confirma como métrica adequada
   para comparar variantes de algoritmo (não muda com sintaxe).

6. **Limite atual da abordagem textual**: ainda 4-8 bytes/unidade
   em escala. Para chegar a 1-2, seria preciso marcadores
   binários ou inferência pela ordem.

## O que este experimento não mostra

- Comparação com gzip(verbose) e gzip(compact) — se o ganho
  sobrevive após compressão estatística
- Outras sintaxes alternativas (Direção 2 da nota, binária,
  hibrida)
- Comportamento em datasets com aspas simples no conteúdo
  (limitação registrada)
- Comparação com formatos externos (Re-Pair, HTFC, FSST,
  gzip+CSV) — virá no exp dedicado a benchmarks
- Custo de parsing/decoding em escala — não medido aqui

## Próximos experimentos naturais

Duas direções complementares:

### Direção A — outras sintaxes alternativas

- **Compact v2** com inferência pela ordem (Direção 2 da nota
  `marcadores-compactos`). Pode reduzir mais — id de nó implícito
  por ordem da linha, marcador de tipo pela posição na sequência.
- **Compact v3** com chars Unicode reservados (pode chegar perto
  de 1 byte por marcador estrutural).

### Direção B — comparação externa real

- Comparar `verbose + gzip`, `compact_v1 + gzip` e `csv + gzip`
  para ver onde o TCF realmente compete. A nota
  [`teoria-compressao-strings.md`](../../../docs/workbench/_archive/2026-05-12-teoria-compressao-strings.md)
  (arquivada) discutia esse critério.
- Comparar com Re-Pair, HTFC, FSST quando viável.

Sugestão de ordem: **Direção B antes** — saber se TCF compete
externamente é input para decidir se vale gastar tempo em mais
sintaxes alternativas. Se já vence externalmente, sintaxes v2/v3
viram refinamento; se perde, talvez seja preciso outra abordagem.
