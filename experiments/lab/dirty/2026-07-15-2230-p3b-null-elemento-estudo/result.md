# Resultado — estudo P3b (null em elemento de array)

**[probatório]** `proto.py` (element-mask, extrai a ideia — não copia o core) + `study.py`. RT 8/8
nas formas didáticas ([outputs/00-resultado.txt](outputs/00-resultado.txt)); roundtrip diffável.

## Confirmado (design da element-mask)

- **RT em todas as formas**: null inicial/meio/fim, array todo-null, vazio≠`[null]`≠`[v]`, elemento
  OBJETO null, 4-vias no elemento (null/`""`/`"null"`/valor), duas listas (só uma com null), aninhado.
- **Alinhamento count×emask×dense** consistente — inclusive elemento-objeto (recursa só nos não-null)
  e aninhamento (array em objeto em array).
- **`?` deduzido do dado**: só onde há null (`tel#?[]` vs `email#[]`). Byte-compat: array sem null
  não paga emask.
- **2-estados** (`.`/`0`, sem `-`) — correto: a posição do elemento é fixada pelo count.

## Design pronto pro weld (aguarda go do owner)

Mecanismo (L2, aditivo, consistente com P3a):
- **schema**: array ganha flag `elem_null` (derivada: algum elemento null em qualquer instância).
- **leaves**: array element-nullable → count, **emask**, elementos (nessa ordem).
- **emit**: por elemento, null → emask `0` (sem corpo); valor → emask `.` + corpo.
- **read**: emask `0` → None; `.` → lê elemento.
- **meta**: `nome#:csize?:emsize[...]` (o `?:emsize` entre count e `[`).

No CORE isso é uma 5ª informação por nó de array (`elem_null`) + a coluna emask — mudança maior que
o P3a. Por isso o estudo antes. **Probes adversariais obrigatórios no weld** (lição do P1): emask
corrompida/tamanho errado/char inválido → fail-loud; null-elemento + campo-null juntos; array-de-
objetos-null vazios; exaustão de emask.

## Alternativa registrada (H-PROFILE-01)

O **índice-de-substituição** unificaria P3a+P3b (null é o mesmo índice reservado em campo E elemento),
mas toca o L1. Fica a MEDIR em massa sob perfil de uso; a element-mask é a rota L2 de baixo risco agora.

`confianca: Média-Alta` p/ o design (RT 8/8; falta o gate real do weld + adversarial). Sintético
declarado (didático, viés total pra forçar as formas).
