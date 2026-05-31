# M9 — Stress adversarial (M8.A em 9 datasets)

**Data**: 2026-05-17
**Estado**: foi (fechado)
**Foco**: testar M8.A nos canonicos D1-D4 + 5 adversariais novos
(D5-D9). Identificar limites e oportunidades futuras.

## Datasets

| ID | Foco | Linhas | Caracteristica |
|---|---|---:|---|
| D1 | emails-simples | 12 | gmail/hotmail/yahoo |
| D2 | emails-quote-id | 12 | nomes com apostrofe |
| D3 | stress-substring | 12 | URLs api/users/* |
| D4 | caos-mix | 12 | mix `[X]*'YYY'@4Z` |
| **D5** | **padroes-multiplos** | 12 | email + uuid coexistentes |
| **D6** | **poucos-em-ruido** | 12 | timestamps unicos + mod repetidos |
| **D7** | **aninhamento** | 12 | sub-padrao em multiplas positions |
| **D8** | **cabeca-cauda** | 12 | prefix/suffix fixos, meio varia |
| **D9** | **frequencia-alta** | 20 | um wrapper R=20 com middle varia |

## Resultados

RT 9/9 OK.

| Dataset | bytes | raw | ratio |
|---|---:|---:|---:|
| D1 | 118 | 191 | 62% |
| D2 | 166 | 248 | 67% |
| D3 | 177 | 348 | 51% |
| D4 | 113 | 157 | 72% |
| D5 | 281 | 419 | 67% |
| D6 | 287 | 528 | 54% |
| D7 | 215 | 335 | 64% |
| **D8** | **100** | **384** | **26%** (melhor) |
| D9 | 158 | 363 | 43% |

**Total**: 1615 bytes em 2973 raw = 54.3% ratio.

## Conclusoes principais

1. **M8.A robusto**: RT 9/9 OK em datasets variados.
2. **Compressao limitada por padrao subjacente**: D8 (26%) prova
   eficacia quando padrao estavel; D4 (72%) prova teto quando caos
   alto.
3. **Limites identificados**:
   - Timestamps difíceis (D6): pre-tx delta resolveria.
   - Wrappers com slot variavel (D9): primitivo `7{}5` hipotetico.
   - Caos alto (D4): teto inerente.

Detalhes: [`notas/conclusoes_M9.md`](notas/conclusoes_M9.md).

## Pendencias / direcoes futuras

Registradas em
[`../notas/roadmap-hipoteses.md`](../notas/roadmap-hipoteses.md):

- Pre-tx delta (timestamps, IDs sequenciais)
- Pre-tx estrutural (CPF, UUID, IP)
- Decomposicao pos-detector (caso `2~13`)
- Detector global (nao greedy)
- Slot variavel em wrapper
