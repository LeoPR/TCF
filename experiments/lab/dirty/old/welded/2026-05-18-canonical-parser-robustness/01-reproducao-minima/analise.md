---
title: Sub-exp 01 — Analise diagnostica
type: analysis
status: closed
tags: [tcf, bug, hcc, root-cause, analysis]
created: 2026-05-19
---

# Sub-exp 01 — Analise do bug

## Resumo

10 casos testados. **3 falham**:

| # | Caso | Body emitido | RT |
|---|---|---|---|
| 1 | `["a,b"]` | `a,b` | OK |
| 2 | `[",abc"]` | `,abc` | OK |
| 3 | `["abc,"]` | `abc,` | OK |
| 4 | `["a,b,c"]` | `a,b,c` | OK |
| **5** | `["abcXYZ", "abcXYZ,def"]` | `abcXYZ` + **`1,def`** | **FAIL** |
| 6 | `["xyzABC", "def,xyzABC"]` | `xyzABC` + `def,1` | OK |
| **7** | `["abcXYZ...endZZZ", "abcXYZ,def,endZZZ"]` | refs + lit + refs | **FAIL** |
| 8 | TPC-H 5 strings | (varias) | OK |
| 9 | `["pending, bold reques", "pending, calm reques"]` | (refs + comma lit) | OK |
| **10** | 4 strings "prefix " | (multi pieces) | **FAIL** |

## Padrao identificado

Bug dispara em transicao **ref → lit** onde lit COMECA com `,`.

Body line typical: `1,def`
- Decoder ve `1` → ref mode
- Continua enquanto digit/comma/dot-dot/tilde
- Consome `1,` como ref expression
- Split em `,` produz `['1', '']`
- Empty unit ignorada
- Lit "def" sobra → decodada
- Resultado: ref(1) + "def" — **`,` perdido**

## Casos que NAO falham (importante)

- **Lit sozinho com `,`** (casos 1-4): nao ha' ref → lit transition,
  body comeca com literal direto, decoder entra em lit mode sem
  ambiguidade.
- **Lit ENDS com `,` + ref-suf** (caso 6): body tipo `def,1`. Decoder
  entra lit mode em 'd', vai ate' antes de '1' (digit break). Texto
  "def," capturado. Depois ref(1). OK.
- **Lit ja' contem `,` mas tem mais content antes** (caso 9): se HCC
  decide nao splittar a lit, body fica `1pending, calm reques`. Lit
  comeca com 'p' (nao `,`), parser entra lit mode imediatamente sem
  ambiguidade.

## Solucao requer (analise pra opcoes)

A transicao **ref → lit comecando com `,`** precisa de
desambiguacao. Opcoes:

### Opcao A: escapar `,` em `_escape_lit`

```python
elif c in ('*', '\\', '~', ','):
    out.append('\\' + c)
```

E adicionar `\,` reconhecimento no decoder.

**Impacto**:
- Bytes: literais com `,` ficam +1 byte each
- M9: pode mudar se D1-D9 tem `,` em literais (verificar)

### Opcao B: separator `*` em ref→lit ambiguo

```python
if kind == 'lit':
    if prev_type == 'lit':
        parts.append('*')
    elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
        parts.append('*')
    ...
```

**Impacto**:
- Bytes: +1 byte apenas em casos problematicos
- Decoder: inalterado
- M9: provavelmente preservado (caso especifico raro em D1-D9)

### Opcao C: separator sempre em ref→lit

Forcar `*` sempre apos refs antes de lit.

**Impacto**:
- Bytes: +1 byte em CADA ref→lit transition (comum)
- M9: certo de mudar
- Mais simples conceitualmente

## Recomendacao pra sub-exps

Testar **A** e **B** em sub-exps 02 e 03. C e' overkill. Comparar
bytes + correcao em D1-D9 + TPC-H.

## Caracter `~` (relacionado)

Mesmo problema teorico se lit comecar com `~` (ref-mode continuation).
NAO observado em casos reais, mas teoricamente vulneravel.
Solucao escolhida deve cobrir ambos `,` e `~`.

## Caracter `.` (parcialmente relacionado)

`..` (range) e' multi-char marker. Lit comecando com `..` apos ref
poderia ser problema. Improvavel em strings reais; deixar pra
investigacao futura se aparecer.

## See also

- [ADR-0007 DRAFT](../../../../docs/adr/0007-comma-in-literals-bug.md)
- [README sub-exp 01](README.md)
- [result.md](result.md)
