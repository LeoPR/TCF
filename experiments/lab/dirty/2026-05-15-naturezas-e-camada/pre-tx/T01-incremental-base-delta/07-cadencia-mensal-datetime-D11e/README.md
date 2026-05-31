# 07 — Cadencia mensal em datetime (D11e) — escala `1M` em segundo

**Estado**: aberto (setima iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Dataset principal**: [D11e-datetime-mensal](../../../../../../../datasets/synthetic/D11e-datetime-mensal.csv)

## Pergunta cientifica

Em **datetime com cadencia mensal** (fatura mensal dia 5 ÀS 9h por
13 meses, formato `YYYY-MM-DD HH:MM:SS`), a escala `1M` traz
**ganho REAL de bytes** vs deltas-em-segundos?

Diferenca crucial vs D11c (que era day-only mensal): em
**granularidade segundo**, deltas em segundos VARIAM porque mes
tem 28/30/31 dias × 86400 segundos. Logo:
- Stage B (segundos): `[base, 2_678_400, 2_419_200, 2_678_400, 2_592_000, ...]` — pouca repeticao
- Stage C (escalas): `[base, 1M, 1M, 1M, 1M, ...]` — 12x exato

Hipotese: TCF de C << TCF de B em D11e.

## Hipoteses

- **H1 (RT)**: encoder v1 estendido preserva D11e via decode -> linhas.
- **H2 (escala vence em datetime mensal)**: TCF C < TCF B
  significativamente (esperado: ratio < 50%).
- **H3 (backward compat)**: D11d (second/minute) mantem TCF C = 34 bytes; D11c (day/mensal) mantem TCF C = 22 bytes.

## Comparacao das cadencias mensais

| Dataset | Granularity | Stage B deltas | Stage C deltas | Esperado |
|---|---|---|---|---|
| D11c | **day** | `[31, 28, 31, 30, ...]` (poucos valores distintos) | `[1M × 12]` | C ≪ B (validado: 22 vs 53) |
| D11d | second | `[60 × 12]` (ja uniforme) | `[1m × 12]` | C ≈ B (validado: 34 vs 34) |
| **D11e** | **second** | `[2_678_400, 2_419_200, ...]` (varia mais) | `[1M × 12]` | C ≪ B (a verificar) |

D11e e' o caso onde escala mostra valor maximo em second-granularity:
**lower unit varia, higher unit (mes) e' exato**.

## Dataset D11e (13 linhas, ~264 bytes raw)

```
val
2025-01-05 09:00:00    (base)
2025-02-05 09:00:00    (+31d × 86400 = 2.678.400s ou +1M)
2025-03-05 09:00:00    (+28d × 86400 = 2.419.200s ou +1M)
2025-04-05 09:00:00    (+31d × 86400 = 2.678.400s ou +1M)
2025-05-05 09:00:00    (+30d × 86400 = 2.592.000s ou +1M)
... (12 transicoes mensais ao todo)
2026-01-05 09:00:00    (+31d × 86400 = 2.678.400s ou +1M)
```

Realistic — fatura mensal com horario fixo. Common em sistemas de
cobranca recorrente (cf. diretriz dados-realistas).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/07-cadencia-mensal-datetime-D11e/run.py
```

## Saidas

`outputs/<dataset>/`:
- `stage-A-metadata.json`, `stage-B.txt`, `stage-C.txt`
- `tcf-puro.tcf`, `tcf-B.tcf`, `tcf-C.tcf`
- `rt.txt`

`result.md` — tabela consolidada D11c, D11d, D11e.

## Criterio de fechamento

- [ ] RT preservado em D11e (e D11c, D11d backward compat)
- [ ] TCF C de D11e significativamente menor que TCF B de D11e
- [ ] Demonstrar que ganho da escala em second-granularity ocorre
  quando **lower unit varia E higher unit e' exato**
