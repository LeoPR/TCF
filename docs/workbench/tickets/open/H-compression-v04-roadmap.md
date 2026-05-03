---
title: H-compression-v04-roadmap — propostas tecnicas de compressao para v0.4
type: hypothesis
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Foco no nucleo TCF como compressor/descompressor (conversa pos-reorg)
user_quote: "as compressoes novamente detalhar mais essa parte"
see_also:
  - docs/theory/components/4-compression-deep-dive.md (deep dive completo)
  - docs/workbench/tickets/open/H-advanced-compression-v04.md (proposta antiga 2026-04-15)
  - docs/workbench/tickets/open/R-tcf-core-revisit.md (audit)
  - docs/workbench/tickets/open/M-architecture-v04.md (split)
---

# Roadmap de compressao para TCF v0.4

Substitui/refina o ticket antigo `H-advanced-compression-v04` (de
2026-04-15) com base nos achados de M-Acomm (F-Q28, F-Q31, F-Q38) e
no novo foco arquitetural (TCF nucleo + extras).

Detalhamento tecnico em
[../../theory/components/4-compression-deep-dive.md](../../../theory/components/4-compression-deep-dive.md).

## 7 propostas avaliadas

| Id | Proposta | Impacto | Custo | Decisao tentativa |
|----|----------|---------|-------|-------------------|
| **A** | Stratified STATS | alto (Linha A filter+agg) | medio | **incluir** |
| **B** | Type-preserving decode | medio (DX) | baixo | **incluir** |
| C | Delta encoding | alto p/ time series | alto | futuro |
| D | Frame-of-Reference (FOR) | baixo | medio | **descartar** |
| E | DICT global cross-coluna | baixo | alto | **descartar** |
| **F** | Auto-detect sortedness | medio (DX) | medio | **incluir** |
| G | Schema_qualifier | alto (F-Q38) | alto | separar (extras) |

Tres propostas selecionadas: **A, B, F**. Plus 2 fixes conhecidos:
**bug 29 (decoder freetext)** e **issue 23 (numeric precision)**.

## Proposta A — Stratified STATS

### Motivacao

F-Q28 mostra que Linha A local cai para 0% em filter+agg. STATS atual
ajuda apenas em agg full-table. Stratified STATS emite agregacoes
condicionadas por categorical:

```
# v0.2 atual:
# STATS hours-per-week: n=100 sum=4243 min=7 max=99 avg=42.43

# v0.4 proposta:
# STATS hours-per-week: n=100 sum=4243 min=7 max=99 avg=42.43
# STATS hours-per-week|sex=Male: n=68 avg=44.98
# STATS hours-per-week|sex=Female: n=32 avg=37.21
```

### API proposta

```python
encode_rows("adult", rows, config=EncodeConfig(
    level=2,
    include_stats=True,
    stratify_stats=["sex", "class"],   # NOVO
))
```

### Estimativa de impacto

- Locais Linha A `q_avg_hours_male`: 0% atual → projeto 60-80% com
  stratified STATS (LLM le `STATS hours-per-week|sex=Male` direto)
- Custo bytes: ~50-100 bytes por (coluna × subgrupo). Para Adult com
  2 subgrupos × 4 numericas: +400-800 bytes (~10% do payload)

### Riscos

- Explosao se ha varias categoricals com alta cardinalidade
- Usuario precisa decidir quais cruzamentos
- LLM pode ignorar stratified STATS se prompt nao orienta

### Criterio de aceite

- [ ] Implementar parametro `stratify_stats: list[str]` em EncodeConfig
- [ ] Limitar a categoricas com cardinality <= 10 (evitar explosao)
- [ ] Round-trip exato: decoder ignora STATS no recover
- [ ] Test em Adult: q_avg_hours_male local sobe de 0% para >50%
  com stratified STATS

## Proposta B — Type-preserving decode

### Motivacao

`decode(encode_rows(rows))` retorna valores como `str`. Quem chama
`encode_rows` com `int`/`float`/`bool` espera roundtrip puro.

### API proposta

```python
# Encoder grava tipos no header (opcional)
text = encode_rows("t", rows, config=EncodeConfig(
    level=2, preserve_types=True,
))

# text contem:
# # TCF v0.4 level=2
# # TYPES id=int name=str age=int active=bool

restored = decode(text)
assert isinstance(restored[0]["age"], int)  # AGORA preserva
```

### Implementacao

Encoder coleta `type(rows[0][col])` para cada coluna. Encoder grava
linha `# TYPES col1=int col2=str ...` no header.

Decoder le essa linha e converte com `int()`, `float()`, `bool()`,
`json.loads()` (para None / nested).

### Backwards compat

Sem `preserve_types=True`, formato fica identico ao v0.2. Decode
funciona com tcf v0.2 e v0.4.

### Criterio de aceite

- [ ] Header opcional `# TYPES col1=type1 col2=type2 ...`
- [ ] Decoder reconverte usando essa linha quando presente
- [ ] Fallback para str quando linha ausente (compat v0.2)
- [ ] Test: `decode(encode_rows(rows, preserve_types=True)) == rows`
  para tipos primitivos

## Proposta F — Auto-detect sortedness

### Motivacao

`sort_by` parameter exige usuario decidir manualmente. Tipicamente
existe escolha obvia (categoria de baixa cardinalidade), e detectar
isso automaticamente melhora DX.

### Algoritmo

```python
def detect_best_sort_by(rows: list[dict]) -> str | None:
    candidates = []
    for col in rows[0].keys():
        values = [r[col] for r in rows]
        cardinality = len(set(values))
        if cardinality > len(rows) * 0.5:
            continue  # alta cardinalidade — RLE nao ajuda
        # Estimativa: bytes ganhos com sort
        sorted_runs = count_runs(sorted(values))
        unsorted_runs = count_runs(values)
        gain = unsorted_runs - sorted_runs
        candidates.append((col, gain, cardinality))
    if not candidates:
        return None
    # Maior ganho prevalece; tie-break por cardinality menor
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return candidates[0][0]
```

### API

```python
# Auto-detect
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by="auto",  # default ou opt-in
))

# Manual continua funcionando
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by="class",
))

# Sem sort
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by=None,
))
```

### Tradeoff

- **Pros**: usuario nao precisa pensar; encoder otimiza ele mesmo
- **Cons**: encoder mais lento (precisa contar runs em N candidatos);
  pode escolher sort que **altera semantica** (ordem original era
  significativa para usuario)

### Criterio de aceite

- [ ] Funcao `detect_best_sort_by(rows) -> str | None`
- [ ] EncodeConfig aceita `sort_by="auto"`
- [ ] Default permanece `sort_by=None` (nao quebra v0.2 behavior)
- [ ] Adult Census: auto detect deve retornar `class` ou `sex`
- [ ] Logging opcional: log que coluna foi escolhida

## Bug 29 — decoder freetext fix

### Motivacao

Strings com `*`, `:`, `\n` em conteudo confundem decoder L0.

### Solucao

Encoder ja escapa `:` em values. Estender para `*` no comeco
(conflito com RLE) e `\n` (newlines em valores).

```
# v0.2 issue:
name:
A:B           ← parse error
3*foo         ← interpretado como RLE
multi
line          ← split em 2 valores

# v0.4 fix:
name:
"A:B"           ← strings com chars conflitantes ficam quoted
"3*foo"
"multi\nline"
```

### Criterio de aceite

- [ ] Encoder detecta caracteres conflitantes e quota o valor
- [ ] Decoder le valores quoted (handle `"..."` no L0)
- [ ] Test: roundtrip exato para strings arbitrarias
- [ ] Bug 29 fechado

## Issue 23 — numeric precision

### Motivacao

Floats podem perder precisao em roundtrip (`repr(0.1+0.2)` = `'0.30000000000000004'`).

### Solucao opt-in

Flag `numeric_precision` em EncodeConfig:

```python
EncodeConfig(level=2, numeric_precision="repr")    # padrao v0.2 (rapido)
EncodeConfig(level=2, numeric_precision="str")     # padrao Python str()
EncodeConfig(level=2, numeric_precision="json")    # json.dumps
EncodeConfig(level=2, numeric_precision="hex")     # bit-exact (float.hex())
```

`hex` garante bit-exact mas e ilegivel para LLM. Util apenas para
roundtrip cientifico.

### Criterio de aceite

- [ ] EncodeConfig.numeric_precision aceita 4 valores
- [ ] Decoder detecta automaticamente (ex: hex starts with `0x`)
- [ ] Tolerancia 1% no scoring continua default (pra LLM eval)
- [ ] Bit-exact opcional para tests cientificos
- [ ] Issue 23 fechado

## Roadmap consolidado

### Sprint 1 (1 semana)
- [ ] B — type-preserving decode
- [ ] Bug 29 — decoder freetext fix
- [ ] Issue 23 — numeric precision opt-in

### Sprint 2 (1 semana)
- [ ] F — auto-detect sortedness
- [ ] A — stratified STATS

### Sprint 3 (validacao)
- [ ] Test stratified STATS em Adult Linha A — verificar +50pp claim
- [ ] Atualizar Apendice A (TCF spec) com v0.4
- [ ] Update CHANGELOG.md
- [ ] Tag git `v0.4.0`

## Total estimado

3 semanas focadas para core v0.4.

## Notas para revisar este ticket

Quando reabrir:
- Snapshot deste arquivo no commit `<ts>`
- Codigo atual: `src/tcf/encoder.py` v0.2
- Tests atuais: `tests/test_encode_decode.py` (se existir)
- Ticket relacionado [H-advanced-compression-v04](H-advanced-compression-v04.md)
  (proposta antiga, subset deste)

## Decisao para o usuario

1. **Sprint 1 e suficiente** para v0.4, ou queres tudo (1+2+3)?
2. **Stratified STATS**: API exigir lista explicita ou auto-detect
   (igual sortedness)?
3. **Bug 29 e Issue 23**: incluir em v0.4 ou postpor?
