r"""# 12 — Templated marker (POC do `?` como marker no template)

**Estado**: aberto (12a iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Origem**: proposta do usuario 2026-05-16 inspecionando D11g v2 do sub-exp 11

## Pergunta cientifica

Pode-se eliminar o sufixo de escala (`M`, `ms`, `us`, ...) nos deltas
encoding incremental, marcando a posicao-que-varia no template com `?`?

**Tradeoff**: ganhamos a info "qual unidade" via posicao do `?` no template
(self-describing). Perdemos o sufixo per-delta.

Caso simples: cadencia single-position (D11c, D11g).
Caso complexo: variacoes multi-position (D11i novo, com corrections).

## Convencao adotada (POC)

- Template tem `?` (ou multiplos `?`s consecutivos) na posicao do field
  que varia
- Initial value e' o **minimo do field** (month=01, day=01, hour=00, ms=000, ...)
- Deltas sao integers, sem sufixo, na unidade do field marcado
- Corrections (multi-position) usam syntax `<marker_delta>|<correctionN><unit>`,
  ex: `1|+2d` = +1 month + day correction de +2

Para uso geral fora desta POC, seria preciso:
- Carregar initial value explicitamente quando nao for o minimo
- Format-aware decoder (regex/estrutural)
- Auto-deteccao da change-position
- Carry/overflow handling pra fields adjacentes

## Datasets testados

- **D11c** (mensal, day-only): single-marker no month
- **D11g** (ms cadence, datetime us): single-marker em fractional
- **D11i** (mensal com correcao de dia, **novo**): multi-position com corrections

## Resultado

Ver [result.md](result.md). RT 3/3 OK em todos.

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/12-templated-marker/run.py
```

## Conexao com sub-exp 11

v2 do sub-exp 11 (escape dedutivel sobre staged pipeline) ja' tinha removido
escapes redundantes. v3 sub-exp 12 vai alem: remove tambem **sufixos de escala**
via marker no template.

Comparacao informal (mesmo dataset, valores aproximados pra contraste):

| Dataset | Sub-exp 11 v2 | Sub-exp 12 v3 | Delta |
|---|---:|---:|---:|
| D11c | 19 | 18 | -1 byte |
| D11g | 36 | 34 | -2 bytes |

Savings modestos absolutos, mas o principio composta em sequencias longas.

## Limitacoes

1. **POC especializada por dataset**: encoder hardcoded por D11c/D11g/D11i.
   Generalizacao requer format parser.
2. **RT validacao indireta**: decoder local opera sobre pretx output (lines
   apos TCF.decode), nao direto do .tcf. Auto-containment cadeia-completa
   precisaria de smart TCF decoder + smart pos-tx (futuro).
3. **Initial value implicito** = MIN. Funciona pros datasets D11x. Fora disso,
   precisaria de syntax adicional.

## Conexoes

- [feedback-abstrato-minimal-materializacao](#) — princípio aplicado
- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — antecedente
- T02 templated (na taxonomia META) — este sub-exp e' protótipo
"""
