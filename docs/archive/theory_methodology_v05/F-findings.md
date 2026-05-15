---
title: F-findings — catálogo canônico de achados metodológicos
date: 2026-04-21
type: methodology
status: CANONICAL
---

# F-findings — catálogo de achados metodológicos (LLM/Ollama/TCF)

Este documento é o **índice canônico** dos achados operacionais do projeto.
Cada achado tem um ID estável (`F-Q<n>`), uma formulação curta como
**conclusão científica**, uma **tag de linha de pesquisa**, e um ponteiro
para a nota de pesquisa detalhada.

Regra de estilo: cada F-finding é formulado como *descoberta reprodutível*
— nunca como "erro nosso". A razão é que os mesmos comportamentos afetam
qualquer pesquisador rodando os mesmos modelos; documentar como achado
reutilizável é mais útil que lamentar.

## Tags de linha de pesquisa

- `{A}` — Linha A: LLM como analista direto sobre TCF
- `{B}` — Linha B: TCF como schema carrier + LLM gera SQL
- `{shared}` — Infraestrutura/metodologia compartilhada por ambas

Ver [research-lines/README.md](../research-lines/README.md) para o contraste
entre as linhas.

## Índice por linha

**`{shared}`:** F-Q1, F-Q2, F-Q3, F-Q4, F-Q5, F-Q6, F-Q7, F-Q8, F-Q9, F-Q10, F-Q11
**`{A}`:** F-Q12
**`{B}`:** F-Q13, F-Q14, F-Q15, F-Q16, F-Q17, F-Q18, F-Q19, F-Q20, F-Q21, F-Q22, F-Q23, F-Q24, F-Q25, F-Q26, F-Q27, F-Q28

---

---

## Catalogo dividido por blocos tematicos

O catalogo completo (F-Q1..F-Q38) foi quebrado em 5 arquivos por tema
para facilitar leitura e manutencao. Veja [docs/findings/](../../findings/):

| Bloco | Range | Tema |
|-------|-------|------|
| [01-origins](../../findings/01-origins-Q01-Q12.md) | F-Q1..F-Q12 | Capacidades fundamentais |
| [02-linha-b](../../findings/02-linha-b-Q13-Q24.md) | F-Q13..F-Q24 | Linha B sintetica |
| [03-protocol](../../findings/03-protocol-Q25-Q28.md) | F-Q25..F-Q28 | Protocolo + canonical |
| [04-naturalness](../../findings/04-naturalness-Q29-Q36.md) | F-Q29..F-Q36 | Eixo naturalidade N0-N3 |
| [05-schema-scope](../../findings/05-schema-scope-Q37-Q38.md) | F-Q37..F-Q38 | Eixo horizontal schema |

Resumo paper-ready em [docs/findings/README.md](../../findings/README.md).
