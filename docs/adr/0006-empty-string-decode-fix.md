# 0006 — Empty string body line deve ser decodada como string vazia

**Status**: accepted
**Date**: 2026-05-18
**Deciders**: project owner
**Tags**: bug-fix, hcc, decode, canonical, src/tcf

## Context and Problem Statement

Durante EXP-012 (Adult Census real-world test), `decode_table` falhou
com `IndexError: list index out of range` em colunas com missing
values (workclass, occupation, native-country).

Causa raiz: encoder `M8AVirtualRefsSyntax._emit_body` emite
`body.append('')` quando string unica e' `""` (caso comum: missing
values mapeados pra string vazia). Decoder `M8AVirtualRefsSyntax.decode`
tinha:
```python
if not linha or linha in ("[", "]"):  # back-compat
    continue
```

O `not linha` skipava empty lines, desalinhando `nos_decl` indexing
quando body subsequente usava `^N` line-refs.

## Considered Options

1. **Workaround caller**: substituir `""` por sentinel (`"?"`, `"\0"`, etc.)
   antes de encode, reverter no decode
2. **Sentinel no encoder**: encoder emite marker especial pra empty
   (ex: `\E` ou outro)
3. **Fix no decoder canonical**: distinguir empty body line de
   blank line back-compat

## Decision Outcome

**Opcao 3 — Fix minimo no decoder canonical.**

Remover `not linha` do skip; manter `linha in ("[", "]")` pra
back-compat:

```python
for raw in tcf_text.splitlines():
    linha = raw.strip()
    # Bug fix 2026-05-18: NAO skipar empty linha — representa
    # string vazia legitima (encoder emite body.append('') quando
    # lit e' ""). Skipar quebrava decode de qualquer coluna com
    # missing values mapeados pra "". Descoberto em EXP-012.
    # Brackets ainda skipados pra back-compat.
    if linha in ("[", "]"):
        continue
    ...
```

`_parse_decl("", ...)` ja' retorna `""` corretamente (while loop nao
executa). Logica downstream funciona naturalmente.

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| Caller workaround | NAO toca src/tcf canonical | Bug latente pra novos callers; nao resolve causa raiz |
| Sentinel no encoder | Resolve sem mexer no decoder | Quebra byte-compatibility com M9 baseline; precisa fork de encoder |
| **Fix no decoder** | Resolve causa raiz; 1 linha; nao quebra encoder | Toca src/tcf canonical (mexer com cuidado) |

## Validacao apos fix

- **EXP-007** (validacao byte-canonical D1-D9): **9/9 OK, 1615 bytes**
  inalterado. M9 baseline preservado.
- **EXP-010** (single-col delta-aware D1-D9 + D11 + D16):
  **RT 20/20 OK** mantido.
- **EXP-012** (Adult Census real-world): **RT 4/4 OK** sem
  workaround (volumes 100, 500, 1000, 5000). Antes do fix:
  IndexError em colunas com missing.

## Justificativa pra tocar src/tcf canonical

Principio do projeto: "src/tcf intocado sem aprovacao explicita".

Esta excecao foi feita porque:
1. Bug fundamental (decoder nao decode legitimate input)
2. Fix minimo (1 linha removida; comentario adicionado)
3. Backward-compatible (D1-D9 baseline preservado)
4. Aprovacao explicita do user (opcao 1 do menu pos-EXP-012)
5. Testes pre/pos confirmam zero regressao

## Riscos residuais

- Se algum body em algum lugar emite blank line POR ENGANO (nao
  intencional), agora vira string vazia no output. Risco baixo —
  encoder emite blank line APENAS pra empty literal.
- Outros formatos legados que dependiam de blank lines como
  delimitadores — nenhum identificado.

## More Information

- Origem: EXP-012 trace de IndexError em
  `experiments/lab/clean/EXP-012-real-world-adult-census/`
- Arquivo modificado: `src/tcf/composicional/syntax.py` linha 723-743
- Diario do dia: `experiments/lab/dirty/notas/diario/2026-05-18.md`

## Cross-references

- [ADR-0001](0001-tcf-format-shebang.md) — formato canonical
- [ADR-0005](0005-discoverability-claude-md-root.md) — sistema docs
- [EXP-007](../../experiments/lab/clean/EXP-007-prototipo-tcf-core/) — validacao byte-canonical
- [EXP-012](../../experiments/lab/clean/EXP-012-real-world-adult-census/) — onde bug foi descoberto
