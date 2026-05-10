# EXP-005 — Progressao de formatos em datasets escalonados

## Objetivo

Comparar 5 formatos em datasets de escala progressiva (de minusculo
1col ate multi-tabela com FKs). NAO eh teste rigoroso — eh **intuicao
de evolucao** das diferencas conforme o tamanho/estrutura cresce.

## Formatos comparados

| Formato | Descricao |
|---------|-----------|
| **csv-naive** | CSV ordem original |
| **csv-sorted** | CSV ordenado por col chave (intuicao, nao rigoroso) |
| **json** | JSON compacto (1 array de objetos) |
| **ndjson** | NDJSON (1 obj por linha) |
| **tcf-v05** | TCF v0.5 SRDM com header shebang `#TCF.5 SRDM` |

Cada um passa por:
- Texto puro
- gzip -9 (transporte)
- Roundtrip decode -> compara com fonte (multiset de tuplas)

## Datasets

| ID | Descricao | Rows | Cols |
|----|-----------|-----:|-----:|
| D1 | 1col tiny (15 nomes ciclados) | 50 | 1 |
| D2 | 1col medium (6 nomes random) | 1000 | 1 |
| D3 | multicol tiny (mix categoricas + livres) | 100 | 8 |
| D4 | multicol medium | 1000 | 8 |
| D5 | 3-tables small (TPC-H subset) | 59 (3 tabs) | varia |
| D6 | 3-tables medium (sintetico) | 1100 (3 tabs) | varia |

## Resultados

### TCF v0.5 vs todos (sintese)

| Dataset | rows | TCF | TCF+gz | vs CSV | vs JSON | vs NDJSON |
|---------|-----:|----:|-------:|-------:|--------:|----------:|
| D1-1col-tiny-50 | 50 | 155 | 145 | **-54.3%** | -82.5% | -82.4% |
| D2-1col-medium-1000 | 1000 | 88 | 102 | **-98.7%** | -99.5% | -99.5% |
| D3-multicol-tiny-100 | 100 | 1934 | 967 | **-47.4%** | -82.8% | -82.8% |
| D4-multicol-med-1000 | 1000 | 22724 | 9758 | **-28.5%** | -80.2% | -80.2% |
| D5-3tables-small | 59 | 6025 | 2669 | -4.0% | -39.6% | -39.6% |
| D6-3tables-medium | 1100 | 13844 | 5372 | **-35.5%** | -79.9% | -79.9% |

### Detalhamento por dataset

#### D1 — 1col tiny (50 nomes em ciclo de 15 unicos)

| Formato | bytes | gz | vs csv | vs csv+gz |
|---------|------:|---:|-------:|----------:|
| csv-naive | 339 | 111 | 0% | 0% |
| csv-sorted | 339 | **127** | 0% | **+14.4%** ← sorted PIOR aqui |
| json | 885 | 142 | +161% | +28% |
| ndjson | 883 | 140 | +160% | +26% |
| **tcf-v05** | **155** | 145 | **-54%** | +30% |

**Note**: csv-sorted+gz piora em D1. Razao: 50 nomes ja tem padrao ciclico
("Ana, Bruno, ..., Otavio, Ana, Bruno..."), gzip ja explora isso. Sortar
quebra o ciclo em blocos contiguos nao-novos para o algoritmo gzip.

#### D2 — 1col medium (1000 nomes random de 6 unicos)

| Formato | bytes | gz | vs csv | vs csv+gz |
|---------|------:|---:|-------:|----------:|
| csv-naive | 6680 | 771 | 0% | 0% |
| csv-sorted | 6680 | **98** | 0% | **-87.3%** ← sorted **vence muito** |
| json | 17676 | 893 | +165% | +16% |
| ndjson | 17674 | 891 | +165% | +16% |
| **tcf-v05** | **88** | 102 | **-98.7%** | -86.8% |

**Note**: aqui csv-sorted+gz quase iguala TCF (98B vs 102B). TCF vence
em **texto puro** por margem absurda (-98.7%) — o body e basicamente
6 literais + RLE refs.

#### D3 — multicol tiny (100 rows × 8 cols)

| Formato | bytes | gz | vs csv |
|---------|------:|---:|-------:|
| csv-naive | 3680 | 1159 | 0% |
| csv-sorted | 3680 | 1143 | 0% (gz -1%) |
| json | 11233 | 1355 | +205% |
| ndjson | 11231 | 1354 | +205% |
| **tcf-v05** | **1934** | **967** | **-47%** (gz -17%) |

#### D4 — multicol medium (1000 × 8)

TCF -28.5% em texto, -19.6% pos gzip. Ganho diminui em escala mas
permanece positivo.

#### D5 — 3-tables small (TPC-H, 59 rows totais)

TCF apenas -4% texto. Por que? TPC-H supplier tem `s_name` unico
("Supplier#000000NNN"), `s_address` unico, etc. — pouca repeticao.
TCF se aproxima de CSV.

#### D6 — 3-tables medium sintetico (1100 rows totais com FKs)

TCF volta a vencer (-35%) porque cidades, categorias, status repetem.
Ainda assim, comparado a D2 (-99%) e D3 (-47%), o multi-tabela nao
brilha tanto: cada tabela tem strings unicas dominantes (Pessoa_NNNN,
Prod_NNN).

## Achados intuitivos

### A1 — TCF v0.5 vence consistentemente vs CSV/JSON/NDJSON em texto puro

Nas 6 amostras, TCF vence -4% a -98% vs CSV. JSON e NDJSON sao **sempre
piores que CSV** (overhead de chaves repetidas, +160% a +260%).

### A2 — CSV-sorted + gzip pode chegar perto de TCF

Em D2 (1000 rows com poucas categoricas), csv-sorted+gz = 98B, quase
empatado com TCF+gz = 102B. Sort sozinho quase iguala TCF estrutural.

**Caveat**: sort precisa escolher coluna **certa**. Aqui, sort em D1
(coluna `nome` com padrao ciclico) PIORA o gzip. Heuristica eh fragil.

### A3 — Roundtrip OK em TODOS os 30 testes (5 formatos × 6 datasets)

Nenhum format quebrou. TCF v0.5 SRDM reconstroe dados identicos a
fonte em todos os casos testados, inclusive multi-tabela.

### A4 — JSON/NDJSON sao caros mesmo apos gzip

JSON+gz e NDJSON+gz ainda perdem para CSV+gz por 16-28% em todos os
datasets. O overhead estrutural de chaves repetidas + colchetes nao
eh totalmente absorvido por gzip.

### A5 — Multi-tabela com strings unicas reduz vantagem do TCF

D5 (TPC-H supplier+part+partsupp) — TCF ganha so -4% pq strings
distintas dominam. Confirma: TCF brilha quando ha **repeticao**.

### A6 — Em datasets pequenos com header, ganho do shebang ajuda

D1 (50 rows): TCF 155B vs CSV 339B. Header shebang (~18B com sort
header) eh fracao maior, mas TCF ainda ganha forte.

## Arquivos produzidos

```
outputs/
  D1-1col-tiny-50/
    csv-naive.csv      csv-naive.csv.gz
    csv-sorted.csv     csv-sorted.csv.gz
    json.json          json.json.gz
    ndjson.ndjson      ndjson.ndjson.gz
    tcf-v05.tcf        tcf-v05.tcf.gz
  D2-1col-medium-1000/
    ...
  D3-multicol-tiny-100/
    ...
  D4-multicol-med-1000/
    ...
  D5-3tables-small/
    ...
  D6-3tables-medium/
    ...
  results.json
```

5 formatos × 6 datasets × 2 (texto + gz) = **60 arquivos** para inspecao
manual.

## Decisoes / pendencias

### Confirmado

- TCF v0.5 SRDM eh **dominante consistente** em texto puro
- Roundtrip exato preserva dados em todos os cenarios
- CSV sorted nao substitui TCF (ja visto em EXP-003a-extension; aqui reconfirmado)

### Observado para investigar

- **Multi-tabela com strings unicas** (D5) — TCF brilha pouco. Investigar
  com Affix-DICT (Proposta H — `Supplier#NNN` tem prefix) e/ou cross-DICT
  entre tabelas.
- **Heuristica de sort** pode piorar em datasets com padroes ciclicos
  (D1). Vale flag opcional para "preserve_input_order" quando ja
  bem-organizado.

### Registrado paralelo

[B-homonyms-key-collision](../../../docs/workbench/tickets/open/B-homonyms-key-collision.md)
+ [research-note](../../../docs/workbench/research-notes/2026-05-09-homonimos-key-collision.md)
— cuidado com colapso de homonimos quando key elimination for
implementada (Proposta I).

## Status

- [x] 6 datasets em escala progressiva
- [x] 5 formatos comparados
- [x] Roundtrip OK em todos
- [x] Outputs salvos para inspecao
- [x] CSV ordenado incluido (intuicao, nao rigoroso)
- [x] Tabela final com vs CSV / vs JSON / vs NDJSON
- [ ] (futuro) repetir com Affix-DICT (Proposta H) ativado em multi-tabela
- [ ] (futuro) ablacao formal 2x2 com mais variaveis
