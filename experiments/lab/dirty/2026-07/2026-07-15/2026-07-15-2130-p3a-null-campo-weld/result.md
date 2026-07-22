# Resultado — WELD P3a (null em campo)

**[probatório]** `run.py` (core weldado, RT obrigatório em cada etapa). Números:
[outputs/00-resultado.txt](outputs/00-resultado.txt). Evidência diffável: `outputs/*.tcf` + `-rt.json`.

## Confirmado (didático → realista → massa, RT 120%)

- **Didático 7/7**: null escalar (`apelido?:5`), null objeto (`end?:5{...}`), null array
  (`tels?:8#:8[...]` — null ≠ `[]` ≠ presente), all-null (`obs?:6`, corpo vazio), null+ausente
  (as 3 distintas), 4-vias, null aninhado em objeto. Cada um RT byte-exato + wire inspecionável.
- **Realista**: cadastro API-like (email/obs/nascimento/complemento nulos) RT byte-exato.
- **Massa (dado real, null REAL sem coerção)**: receita-cnpj `nome_fantasia=None` (não mais coerido
  a `""` como no P1) — RT byte-exato até 25% (**24069 nulls reais** em 50105 est). A população inteira
  esbarra no `BUG-SEQRLE-RANGE-EMPTY-B` (L1, free-text — separado do P3a).

## Mecanismo (aditivo, L2)

Estende a máscara do P1: `_field_node` aceita null (kind dos não-nulos; all-null → escalar vazio;
`masked = optional | has_null`); `_emit_row` null → mask `0` (sem corpo); `_read_object` mask `0` →
None. `?` no meta = "campo mascarado" (ausência e/ou null). Zero mudança no L1 (`syntax.py`); a
"costura" do null-repr (mask × índice) fica em `_emit_row`/`_read_object` p/ o swap futuro (H-PROFILE-01).

## Fronteira (segue fail-loud, NUNCA silencioso)

null em ELEMENTO de array (**P3b**, próximo incremento); tipos estruturais mistos (P2); array de
objetos sem chaves; N raízes; N:N. Todos `HierarchicalError`.

## Gate

Suíte **693 passed, 2 skipped, 1 xfailed** (o xfail é o BUG-SEQRLE, separado); flat byte-canônico
(D1-D9=1523/D17a=300/real-world=89616) intacto; uniforme byte-idêntico. `confianca: Alta` p/ P3a
(3 etapas + suíte + dado real).

## Próximo

- **P3b** (null em elemento de array) — precisa de máscara no nível dos elementos (a alternativa do
  índice unificaria P3a+P3b; a MEDIR sob H-PROFILE-01).
- Registrar como candidato de otimização (`.9`): índice-de-substituição vs máscara, medido em massa.
