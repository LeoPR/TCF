---
title: Sub-exp 02 — Opcao A (escape `,` em _escape_lit)
type: sub-experiment
status: active
tags: [tcf, bug-fix, hcc, fork, escape, comma]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-18-canonical-parser-robustness
hypothesis: H-FIX-01 (preserva M9) OU H-FIX-02 (re-baseline M9)
---

# Sub-exp 02 — Opcao A: escape `,` em `_escape_lit`

## Objetivo

Testar **Opcao A** do ADR-0007: escapar `,` em literais ao encodar +
reconhecer `\,` no decoder. Manter src/tcf intocado neste lab — usar
fork local.

## Mudanca proposta

### Encoder (`_escape_lit`)

```python
elif c in ('*', '\\', '~', ','):    # adicionar ','
    out.append('\\' + c)
```

### Decoder (`_parse_decl` escape branch)

Atual:
```python
if c == '\\':
    i += 1
    nc = resto[i]
    if nc.isdigit():
        # digit escape
    else:
        buf.append(nc)
        i += 1
```

Sem mudanca! `\,` ja' cai no else (append nc = ','). E' so' o
ENCODER que precisa mudar.

## Validacao

1. Sub-exp 01 reproducao casos → devem todos passar
2. D1-D9 (sub-exps via fork) → byte-canonical preservado OU
   re-baseline justificado
3. TPC-H — testar mesmas tabelas do EXP-013 e ver se RT melhora

## Aceite

- Casos sub-exp 01 (5, 7, 10) FAIL → OK apos fix
- D1-D9 bytes documentados (qualquer mudanca registrada)
- TPC-H tabelas: regression de cases passing em EXP-013 + ganho
  de cases que estavam failing

## Estrutura

```
02-opcao-A-escape-virgula/
├── README.md
├── hcc_fork_escape_comma.py  ← fork da M8AVirtualRefsSyntax
├── run.py                    ← roda sub-exp 01 cases + D1-D9 + TPC-H sample
└── result.md
```
