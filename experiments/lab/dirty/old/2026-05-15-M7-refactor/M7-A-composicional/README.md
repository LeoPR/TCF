# M7.A — Composicional (refactor limpo)

**Tecnica**: identica ao M6.C — `~` cria ref auto-nomeado, `,` nao,
range = composicao por sequencia, pairwise binary.

**Diferenca de M6.C**: estrutura de codigo. Tres fases separadas
(tokenize / detect / emit), Phase 5 + 6 unificadas em emit.

## Fluxo

```
encode(linhas, unicas, tokens):
  pieces_per_line, line_meta, atom_count = _tokenize(...)
    # pieces: ('lit', text, prov_atom_id) | ('refs', [prov_ids])
  
  alias_to_sub = _detect(pieces_per_line, atom_count)
    # iterativo greedy; modifica pieces in place
    # ('alias_marker', alias_temp, sub) substitui sub-runs em 'refs'
  
  body, trace_info = _emit(pieces_per_line, line_meta)
    # single pass, atribui IDs decoder-style (atom + comp interleaved)
    # trace_info: prov→final, alias→final, missed pairs
```

Decoder identico ao M6.C (sem mudancas, ja' funcionava).

## Esperado

Bytes identicos a M6.C: D1=128, D2=175, D3=194, D4=122 → 619 total.

Codigo significativamente mais curto e legivel.
