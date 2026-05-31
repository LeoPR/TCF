# 0004 — Multi-column header compacto (`#TCF.6 M` + `# size=name,...`)

**Status**: accepted
**Date**: 2026-05-17
**Deciders**: project owner
**Tags**: format, multi-column, header

## Context and Problem Statement

Como representar multiplas colunas em um arquivo `.tcf` mantendo:
- Compactacao (header overhead minimo)
- Auto-contencao (decoder so' precisa do arquivo)
- Sem conflict de delimitador no body
- Compatibilidade com convencao de header existente (ADR-0001)

Tentativa inicial: header verboso `# tcf-multi-column rows=N cols=M`
seguido de `# COL=<name> bytes=<n>` por coluna. Errado: viola
princip-io "descricoes livres = erro de design".

## Considered Options

1. **Header verboso** — `# tcf-multi-column rows=13 cols=4` + `# COL=name bytes=N` × cols
2. **Compacto byte-precise** — `#TCF.6 M` + `# 61=name1,28=name2,...` + bodies concat
3. **Delimitador no body** — `## col_name` antes de cada body

## Decision Outcome

**Opcao 2 — Compacto byte-precise.**

Formato:
```
#TCF.6 M
# <size1>=<name1>,<size2>=<name2>,...
<body1 size1 bytes><body2 size2 bytes>... (concatenado sem delimitador)
```

### Por que byte-precise (nao delimitador)

HCC body pode comecar linhas com `#` (chars `#` em literais nao sao
escapados pelo `_escape_lit`). Delimitador `# ...` poderia colidir.
Byte-count via meta line evita.

### Por que `M` flag

Multi-column e' uma extensao opcional do formato. Single-column
nao tem flag (apenas `#TCF.6`). Decoder distingue por presenca/ausencia
de `M`.

### Restricoes assumidas

- Nomes de coluna nao contem `,` ou `=` (escaping futuro se necessario)
- Header sempre emitido por default (`include_shebang=True`)
- Excepcao: `include_shebang=False` quando caller garante formato
  out-of-band (raro)

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| Header verboso | Self-documenting | ~120 bytes overhead em D17a; viola convencao TCF |
| **Compacto byte-precise** | ~52 bytes overhead; segue convencao shebang; sem conflict | Nao self-documenting (intencional — algoritmo nao precisa) |
| Delimitador no body | Conceptualmente simples | Conflict com `#` em literais |

## Validacao empirica (D17a)

- Header verboso: 393 bytes total
- **Header compacto**: 321 bytes (**-72 bytes**, -46.6% vs raw CSV)
- RT byte-canonical OK

Decode:
1. Validar linha 1: `#TCF.6 M`
2. Parsear linha 2: `size=name` pairs (separados por `,`)
3. Ler `size[i]` bytes pra cada body, decode_column

## More Information

- Implementacao: `experiments/lab/clean/EXP-011-multi-column-basic/multi_col.py`
- Antecedente: [ADR-0001](0001-tcf-format-shebang.md) — shebang convention
- Critica do user que motivou refactor:
  `experiments/lab/dirty/notas/diario/2026-05-17.md` D39-D42

## Em aberto (registrado pra futuro)

- Single-col deveria emitir shebang tambem? **DECIDIDO**: sim
  (uniformizado 2026-05-17, +7B por arquivo)
- Nomes com `,`/`=` precisam escaping
- Outros flags alem de `M` pra v0.6
- Multi-tabela (varias tabelas no mesmo arquivo) — [O-FMT-13](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md) (per-channel header)

## Cross-references

- [ADR-0001](0001-tcf-format-shebang.md) — shebang versao
- `experiments/lab/dirty/notas/futuras-otimizacoes-formato.md` —
  O-FMT-11, O-FMT-11b, O-FMT-13
