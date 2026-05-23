# 0007 — Bug: `,` em literais corrompe decode

**Status**: accepted + welded
**Date**: 2026-05-18 (draft) → 2026-05-19 (welded) → 2026-05-23 (validated + accepted)
**Deciders**: project owner
**Tags**: bug, hcc, canonical, decode, src/tcf, welded

## Context and Problem Statement

Durante EXP-013 (TPC-H real-world test), descoberto que literais
contendo `,` corrompem no decode.

Exemplo concreto (TPC-H p_comment row 328):
- **Original**: `'pending, bold reques'`
- **Decoded**: `'pending bold reques'`

O `,` desapareceu.

### Reproducao minima (a confirmar antes de implementar fix)

Caso suspeito:
```
String "ABC, def" tokenizada por HCC em pieces.
Se quebra cai EM um ponto que produz piece "," sozinho OU
piece terminando em "," seguida de outra piece, a body line
pode ter sequencia tipo `5,xyz`.

Decoder ve `5,` em ref mode (`,` e' separator), parsea como
refs [5] (split em "," produz "5" + ""). O "," e' perdido.
Resto da linha decodifica do ponto pos-"," → texto que perdeu
o ","
```

Ver Estagio 1 (Reproducao minima) abaixo.

### Causa raiz arquitetural

`,` no body grammar do HCC e' **multi-proposito**:
- Em ref expressions: separator (`1,2,3` = refs [1,2,3])
- Em literais: NAO escapado (`_escape_lit` so' escapa `*`, `\`, `~`, digits)

Esta ambiguidade quebra quando contexto deveria mudar mas decoder
mantem modo errado.

## Considered Options

### Opcao A — Escapar `,` em `_escape_lit`

Adicionar `,` aos chars escapados:
```python
elif c in ('*', '\\', '~', ','):
    out.append('\\' + c)
```

**Impacto**:
- Encoder: literais com `,` ficam +1 byte cada
- Decoder: precisa reconhecer `\,` como literal `,`
- **M9 baseline**: verificar quais D1-D9 tem `,` em literais.
  Se algum tiver, bytes aumentam → M9 byte-canonical quebra.
- Pro: causa raiz tratada (escape canonical)
- Con: M9 pode shiftar; impacto na compressao geral

### Opcao B — Adicionar separator `*` antes de literal "ambiguo"

Encoder: se lit comeca com char que pode ser confundido
(`,`, etc.), preceder com `*` mesmo se previa pieces nao
exigiriam.

**Impacto**:
- Encoder: mais bytes em casos especificos
- Decoder: inalterado
- Pro: menos invasivo no escape grammar
- Con: heuristica complicada (precisa saber quando)

### Opcao C — Length-prefix em literais

Mudar body grammar pra prefixar lits com length:
`L5:abcde` ou similar.

**Impacto**:
- Encoder + decoder: refactor grande
- Pro: zero ambiguidade
- Con: massivo; quebra TUDO; nao single-pass-friendly

### Opcao D — Sentinel pra final de ref expression

Encoder emite sentinel apos refs antes de literal: `1,2,3|` ou
similar.

**Impacto**:
- Body grammar muda significativamente
- Pro: clareza
- Con: novo char reservado; complexo

### Opcao E — Disallow `,` em literais (nivel de spec)

Documentar limite: TCF nao suporta literais com `,`.

**Impacto**:
- Encoder: detecta e erro
- Decoder: inalterado
- Pro: nenhum codigo muda
- Con: refuta caso de uso real (TPC-H comments)

## Recomendacao tentativa (a debater)

**Opcao A — escapar `,`** parece o mais alinhado com a filosofia
existente (`_escape_lit` ja' escapa chars reservados; `,` deveria
estar la' desde o inicio mas foi esquecido).

**Pontos a validar antes de aplicar**:
1. Quantos literais em D1-D9 tem `,`?
2. Se sim, quanto M9 baseline mudaria?
3. Decoder lida com `\,` corretamente (precisa adicionar caso no
   escape parser)?

## Action plan (ESTAGIOS, conforme `docs/how-to/fluxo-hipotese-producao.md`)

### Estagio 1 — Reproducao minima (sub-exp 01 do lab novo)

Lab: `experiments/lab/dirty/2026-05-18-canonical-parser-robustness/`

Sub-exp 01: criar caso minimo que reproduz bug. Strings com `,` em
posicoes variadas:
- "abc,def" (no meio)
- ",abc" (no inicio)
- "abc," (no fim)
- Combinado com outras strings que geram quebras especificas

Identificar EXATAMENTE em que cenarios o bug dispara.

### Estagio 2 — Hipoteses (roadmap)

Adicionar ao roadmap:
- **H-FIX-01**: opcao A (escape `,`) resolve bug e preserva M9
- **H-FIX-02**: opcao A muda M9 baseline (re-baseline necessario)
- **H-FIX-03**: opcao B (sep `*` heuristico) funciona sem mudar escape

### Estagio 3 — Sub-experimentos dirty (testar opcoes)

- Sub-exp 02: opcao A (escape `,`) em fork
- Sub-exp 03: opcao B (separator) em fork
- Validar em datasets: D1-D9 (regressao), D17a (multi-col),
  TPC-H amostrado (resolver bug original)

### Estagio 4 — Prototype clean

Quando opcao escolhida estabilizar: criar EXP-014 (ou similar)
welding o fix.

### Estagio 5 — ADR final

Este doc (ADR-0007) e' DRAFT. Apos sub-exps, atualizar com:
- Opcao escolhida
- Resultados empiricos
- Justificativa final
- Re-baseline M9 se aplicavel (ou justificar manutencao)

### Estagio 6 — Integracao src/tcf

So' apos ADR aceito. Validacao multi-camada:
- EXP-007 (D1-D9 — se M9 mudou, novo baseline documentado)
- EXP-010 (delta-aware 20 datasets)
- EXP-011/012/013 (multi-col real-world — bug 3 fixado)

### Estagio 7 — Producao

Apos validacao, src/tcf canonical recebe fix. Bug 3 resolvido.

## Justificativa pra tocar src/tcf canonical

Mesma logica de ADR-0006:
- Bug fundamental (corrompe dados validos)
- Fix integrado (nao surface)
- Validacao multi-camada obrigatoria
- Re-baseline M9 e' OPCAO se justificavel

## Riscos residuais (apos fix hipotetico)

- Outros chars multi-proposito nao identificados: investigar full
  grammar
- Performance: escape adiciona bytes em casos comuns
- Backward-compat: arquivos antigos sem `\,` escape decodariam
  como antes (sem `,` em literais) — mas isso e' o bug; nao ha'
  arquivos "legitimos" com `,` em literal sem escape

## Cross-references

- [ADR-0006](0006-empty-string-decode-fix.md) — bugs canonical anteriores
- [EXP-013](../../experiments/lab/clean/EXP-013-real-world-tpch/) — descoberto aqui
- [Fluxo hipotese-producao](../how-to/fluxo-hipotese-producao.md) — metodologia seguida

## Outcome (atualizado 2026-05-23)

**Opcao escolhida**: B (separator heuristico) — veja sub-exp 04 do lab
`2026-05-18-canonical-parser-robustness/`.

**Razoes**:
1. Mesma cobertura corretiva da Opcao A (10/10 casos minimos)
2. Mesma preservacao de M9 baseline 1615B (na epoca; agora M10 1523B)
3. Overhead muito menor em datasets reais
   (TPC-H customer.c_comment: +7B vs +116B Opcao A)
4. Mudanca menos invasiva (so' encoder; decoder inalterado)

**Implementacao welded** em `src/tcf/composicional/syntax.py`
`_emit_body` (linhas 435-442 atual):

```python
elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
    # Bug fix 2026-05-19 (ADR-0007): separator `*` quando
    # ref->lit transition e lit comeca com `,` ou `~`.
    # Sem o separator, parser do decoder entra ref mode
    # em "1,..." e consome o `,` como continuacao do ref
    # expression, perdendo o `,` literal.
    parts.append('*')
```

## Validacao multi-camada (sub-exp 05, 2026-05-23)

Lab: `2026-05-18-canonical-parser-robustness/05-validar-welding-canonical/`

| Camada | Resultado |
|---|---|
| Casos minimos sub-exp 01 | **10/10 OK** (era 7/10 pre-fix) |
| D1-D9 M10 baseline (1523B) | PRESERVADO EXATO |
| D1-D9 RT 100% | 9/9 |
| Adult Census 1k/5k + TPC-H region/customer/lineitem 5k RT | 57/57 |
| Real-world bytes | 889,714B (sem regressao vs pre-validacao) |

**WELDING PACOTE 3 CONFIRMED**.

## Cross-references finais

- [ADR-0006](0006-empty-string-decode-fix.md) — bugs canonical anteriores
- [Lab Pacote 3](../../experiments/lab/dirty/2026-05-18-canonical-parser-robustness/)
- [Sub-exp 05 validacao](../../experiments/lab/dirty/2026-05-18-canonical-parser-robustness/05-validar-welding-canonical/)
- [src/tcf/composicional/syntax.py:435-442](../../src/tcf/composicional/syntax.py)
