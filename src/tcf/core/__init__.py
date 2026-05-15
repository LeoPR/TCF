"""OBAT — Online Bidirectional Affix Tokenizer.

Camada 1 do TCF. Tokeniza sequencia de strings unicas via matching
de prefixo (LCP) + sufixo (LCS) contra strings anteriores.

Saida: lista de tokens por string (`TokLit`, `TokRefPref`, `TokRefSuf`).

Modulo `online.py` e' copia byte-exata de
`experiments/lab/dirty/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`
(codnome de origem: `alg16`, intocado desde 2026-05-11).

Modulo `syntax_base.py` define a interface `Syntax` que a camada
de Compactacao composicional (HCC) implementa.

Ver `docs/algorithms/OBAT.md` para detalhamento (estrutura,
sub-linguagem matematica, diferencial vs literatura).

Validado por M11 (welding step 1) — bytes byte-identicos a M9/M10.
"""
