# M6.B — M4.C1' open-only (analisado, NAO implementado)

**Estado**: foi (analise algebrica conclui que valor pratico e' marginal;
absorvido por M6.C).

## Por que nao foi implementado

A ideia inicial era: dropar marker close (`~tupla~` → `~tupla`).
Em analise refinada, o ganho fica restrito a aliases em **end-of-line**:

| Posicao do alias | Savings vs M4.C1' atual |
|---|---:|
| End-of-line (sem refs apos) | 1 byte (drop trailing `~`) |
| Mid-line (refs apos) | 0 bytes (`~` close vira `*` close, mesma overhead) |

Em D1 (3 aliases, 2 EOL): save 2 bytes.
Em D1-D4 estimado: ~5-10 bytes savings.

## Por que M6.C subsume

M6.C trata markers como operadores composicionais. Composicao usa `~`
entre refs (replace `,`), reuso usa bare ref id (sem prefixo `&`).
NAO precisa close marker porque:
- Composicao se "fecha" no proximo non-ref char OU termina o operador
- Reuso bare nao precisa close (so' o id)
- Range `a..b` se "fecha" no nao-digit/non-dot apos `b`

Economia M6.C: 1 byte na 1a aparicao + 1 byte por reuso (vs M4.C1' atual).
Para 3 aliases R=3 medio: ~12 bytes/dataset. Domina M6.B.

## Conexao

- [[../README.md]] — M6 macro
- [[../M6-C-composicional/]] — sintaxe composicional (substitui M6.B)
- [[../../notas/marcadores-multiplo-proposito.md]] — analise algebrica completa
