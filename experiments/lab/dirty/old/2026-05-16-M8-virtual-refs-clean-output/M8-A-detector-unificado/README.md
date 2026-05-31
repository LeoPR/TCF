# M8.A — Detector unificado (generalizacao)

**Tecnica**: refs atomicos e refs virtuais (de aliases detectados em
iters anteriores) vivem no **mesmo espaco**. Detector itera
uniformemente em sub-tuplas de refs mixtos.

## Por que generaliza

M7.A tinha duas estruturas:
- `('refs', [atomic_ids])` — atomos
- `('alias_marker', alias_temp, sub)` — separado, opaco ao detector

Detector iterava SO' em `'refs'`. Pairs como (atom, alias_anterior) ou
(alias, alias) ficavam invisiveis. Resultado em D1-D4: ~28 bytes
deixados na mesa.

M8.A unifica:
- `('ref', ref_id)` onde `ref_id > 0` = atom prov, `ref_id < 0` = alias virtual
- Token list flat por linha (sem 'pieces' separados)
- Detector conta sub-tuplas em runs de REF consecutivos (independente do tipo)

Pair (atom_X, alias_Y) e' apenas mais um sub-tupla candidato. Igual
forma. Algebra de net identica.

## Emit com aliases recursivos

Quando alias_marker substitui K refs por -alias_temp (virtual id),
o alias pode ter sub que **contem outros virtuals**. Para emitir:

1. Resolver inner aliases primeiro (recursivo).
2. Emitir def como composition unit, com chain de refs ja' resolvidos.
3. Pairwise binarization aloca K-1 IDs para a chain.

Inner aliases emitidos antes ficam como units `,`-separadas na mesma
posicao do alias externo. Sintaxe natural:

```
P~Q,M~Y_final~N    # Y emitido primeiro (P~Q cria Y_final), depois X (M~Y~N cria X_final)
```

## Convencao output (nova)

- **Sem brackets** `[`/`]` (ver
  [`../../notas/convencao-output-tcf.md`](../../notas/convencao-output-tcf.md))
- **LF only** (single `\n`)

Decoder mantem skip de brackets pra back-compat.

## Esperado

- D1-D4 ganho vs M7.A-clean: ~10-20 bytes adicionais (capturando os
  pairs missed identificados pelo trace de M6/M7).
- Total estimado: ~600 (M7.A-clean = ~615 sem brackets).
