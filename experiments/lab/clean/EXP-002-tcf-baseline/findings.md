# EXP-002 — Achados preliminares

## Achado 1: Bug do decoder TCF v0.2 com colunas booleanas

Decoder interpreta colunas com nomes ambiguos (ex: `active`) como FK de
outra "tabela", causando split em multiplos retornos no `decode()`.

**Sintoma**:
```python
>>> decode(encoded_text)
{'active': [{...}], 'data': [{'id_active': '2', ...}]}  # bug: 2 keys
```

**Esperado**:
```python
{'data': [{'active': True, ...}]}
```

**Workaround no lab**: extrair so a tabela com nome `data`. Veja
`framework/encoders.py::TCFEncoder.decode`.

**Recomendacao v0.4**: refatorar heuristica FK detection. Ticket
[29-B-decoder-freetext-bug](../../../workbench/tickets/open/29-B-decoder-freetext-bug.md)
ja existe; este achado adiciona evidencia.

## Achado 2: Bug do decoder em `categorical_heavy`

`KeyError: ''` quando dataset tem strings que coincidem com vocabulario
parecido com FK. Decoder tenta resolver name->id mas falha.

**Sintoma**: `KeyError: ''` em `decoder.py:148` (`row[f"id_{col}"] = name_to_id[row[col]]`)

**Recomendacao v0.4**: mesma decoder refactor.

## Achado 3: TCF L0 < CSV em datasets pequenos

Em `micro` (5 rows × 4 cols), TCF L0 raw = 222B, CSV = 103B.
TCF tem **overhead de cabecalho** (`# TCF v0.2 level=0`, `## data n=5`,
nomes de colunas como linha cada) que so se amortiza com tamanho.

**Implicacao**: cenario MIN. Para datasets nano/pequenos, CSV simples
e mais eficiente. TCF tem ROI a partir de ~50-100 linhas.

## Achado 4: TCF L2 vence em `categorical_heavy`

| Compressao | CSV | TCF L2 | Vencedor |
|------------|-----|--------|----------|
| none | 3350B | **2541B** | TCF (-24%) |
| gzip | **761B** | 797B | CSV (-4.5%) |
| brotli | **639B** | 671B | CSV (-5%) |

**Insight**: TCF L2 raw vence CSV raw, mas com compressao generica
(gzip/brotli) o ganho some — o compressor "encontra" a redundancia que
TCF ja explora. Sinergia esperada (TCF + compressao = best of both)
NAO se confirma em v0.2.

**Hipotese para v0.4**: com DICT + ordering inteligente, TCF L2 pode
emitir **menos redundancia** que o compressor sozinho explora. Se
isso funcionar, TCF L2 + brotli pode bater CSV + brotli.

## Achado 5: TCF perde em `wide_random`

Em dados sem padrao (10 cols float aleatorios), TCF L0 = 7925B vs
CSV = 7336B. TCF tem +8% overhead sem ganho compressivo.

**Implicacao**: cenario adverso confirmado. Dados aleatorios sem
estrutura categorica nao sao publico-alvo do TCF.

## Achado 6: TCF L3 (schema-only) — uso bem definido

Em `categorical_heavy`, TCF L3 = 1465B (vs 3350B CSV raw, 761B CSV+gzip).

Mais comprimido que CSV raw, mas perde para CSV+gzip. **L3 nao e para
roundtrip** — e para passar APENAS schema + STATS (caso de uso: LLM
generates SQL).

## Resumo para o paper

Dados deste EXP-002 sustentam:
- F-Q1 (TCF tem overhead em datasets pequenos)
- F-Q2 (TCF brilha em datasets categoricos sem compressor)
- F-Q3 (TCF + compressao generica nao tem sinergia em v0.2)
- 2 bugs de decoder a corrigir em v0.4

## Proximos experimentos

- **EXP-003**: TCF L2 com `sort_by` manual — ver se RLE explora mais
  com colunas ordenadas (espero mudanca em `categorical_heavy`)
- **EXP-004**: TCF v0.4 com DICT — testar Achado 4 hypothesis
- **EXP-005**: outros datasets (Adult Census real, TPC-H)
