# 0001 — TCF format shebang (`#TCF.<minor>`)

**Status**: accepted
**Date**: 2026-05-09 (decisao original) / 2026-05-18 (migrado pra ADR)
**Deciders**: project owner
**Tags**: format, header, versioning

## Context and Problem Statement

Como identificar formato e versao em arquivos `.tcf` de forma compacta
e extensivel?

## Considered Options

1. **Sem header** — economiza bytes, mas perde identificacao
2. **Header verboso** (`# TCF version 0.5 sort=true rle=true`) — clear
   mas custoso
3. **Shebang** (`#TCF.5 SRDM`) — magic line estilo `#!/bin/bash`, flags
   compactas

## Decision Outcome

**Opcao 3 — Shebang.**

Forma final:
```
#TCF.<minor>[ <FLAGS>]
```

### Regras de versao

| Versao | Header | Bytes |
|---|---|---:|
| 0.5 | `#TCF.5` | 6 |
| 0.6 | `#TCF.6` | 6 |
| 1.0 | `#TCF1` | 5 |
| 1.3 | `#TCF1.3` | 7 |
| 2.10 | `#TCF2.10` | 8 |

**Algoritmo**:
- Major 0 → omite `0`, escreve `.<minor>`
- Minor 0 → omite `.0`, escreve so' `<major>`
- Caso geral → `<major>.<minor>`

### Flags

- Single-character apos magic, separados por espaco
- Hoje: `M` = multi-column (ver [ADR-0004](0004-multi-column-header-compacto.md))
- v0.5 tinha SRDM (Sort/RLE/Dict/Marked) — obsoleto em v0.6

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| Sem header | -6 bytes | Nenhuma identificacao do formato |
| Header verboso | Self-documenting | Custa muitos bytes; humanos nao precisam ler header de arquivos compactados |
| **Shebang** | Compacto, extensivel, padrao reconhecivel | Requer convencao parser |

## More Information

- Origem: `docs/workbench/research-notes/_archive/2026-05-09-formato-header-shebang.md`
- Validacao: EXP-004c (ratio C vs A: -10.07% medio)
- Aplicacao v0.6: EXP-010 (single-column), EXP-011 (multi-column)
- Custo medido: +7 bytes por arquivo single-col (`#TCF.6\n`)

## Cross-references

- [ADR-0004](0004-multi-column-header-compacto.md) — flag `M` + meta line
- [O-FMT-11 em futuras-otimizacoes](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md) — historico de iteracoes
