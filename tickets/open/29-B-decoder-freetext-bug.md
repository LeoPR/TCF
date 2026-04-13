---
title: BUG — decoder confunde texto livre terminado em ':' com header de coluna
type: bug
status: OPEN
priority: 28
discovered: 2026-04-13
discovered_in: test_encode_canonical.py (TPC-H customer.c_comment, lineitem.l_comment)
---

# Decoder Bug: freeform text with ':'

## Problema

O decoder (`src/tcf/decoder.py`) usa a heuristica "linha que termina com ':'
e nao comeca com digito = header de coluna" para detectar blocos de dados.

Quando uma coluna contem texto livre (como TPC-H `c_comment` ou `l_comment`),
valores que terminam com `:` sao interpretados erroneamente como headers.

Exemplo de dado real que quebra:
```
c_comment:
accounts use carefully along the foxes
pending requests:                          ← decoder pensa que e coluna "pending requests"
ly even packages alongside of the final
```

O decoder ve `pending requests:` e acha que e um header de coluna.

## Impacto

- **Dados afetados:** qualquer coluna de texto livre com `:` no final
- **TPC-H:** c_comment (customer), l_comment (lineitem), s_comment, etc.
- **Adult:** nao afetado (sem colunas de texto livre longo)
- **Dados sinteticos anteriores:** nao afetado (nomes curtos sem `:`)

## Causa raiz

`decoder.py` linha ~96:
```python
if line.endswith(":") and not line[0].isdigit():
    # Assume it's a column header
```

Isso e uma heuristica que funciona para dados estruturados mas falha
com texto livre.

## Possiveis solucoes

### A. Escapar ':' no encoder (simples, quebraria legibilidade)
Encoder poderia escapar `:` no final de valores, mas isso complica o formato.

### B. Usar contagem de colunas (robusta)
Decoder sabe quantas colunas esperar (do header `## table n=X`). Depois
de ler N colunas, parar de procurar headers. Requer refactoring do decoder.

### C. Marcar fim de dados explicitamente
Adicionar marcador `# END` ou usar blank line dupla entre colunas.
Mudaria o formato mas seria mais robusto.

### D. Usar prefixo no header de coluna
Em vez de `col_name:`, usar `@col_name:` ou `> col_name:`. Distingue
de texto livre. Mudaria formato.

### E. Excluir colunas de texto livre (workaround)
Nao encodar colunas com texto livre longo (c_comment, etc).
Workaround, nao solucao.

## Decisao para agora

**Workaround E** nos testes: excluir colunas _comment. Registrar bug como
ticket aberto. A solucao real (B ou C) sera implementada quando refatorarmos
o formato TCF v0.3.

## Workaround aplicado

Em `tests/test_encode_canonical.py`, colunas terminadas em `_comment` sao
excluidas dos testes de roundtrip. Isso nao afeta os testes de compressao
(que sao sobre dados estruturados, nao texto livre).
