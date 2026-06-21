# 08 — Granularidades finas (ms / us / ns)

**Estado**: aberto (oitava iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)

## Pergunta cientifica

Estender o pipeline staged pra detectar e processar **granularidades
sub-segundo** (ms, us, ns), incluindo **sufixos multi-char** (`1ms`,
`1us`, `1ns`) sem quebrar backward compat dos sub-exps 01-07?

## Hipoteses

- **H1 (RT)**: 8 datasets passam roundtrip byte-canonical
  (5 backward compat + 3 novos).
- **H2 (backward compat)**: D11a/b/c/d/e mantem bytes TCF C
  exatos (42/59/22/34/34).
- **H3 (Stage A detecta sub-second)**: D11f→ms, D11g→us, D11h→ns.
- **H4 (sufixos multi-char funcionam)**: D11g emite `1ms` (multi-char),
  D11h emite `1us` (multi-char). Stage C parse longest-first
  pra desambiguar `ms` vs `s`.

## Linguagem das escalas (cumulativa, versao final do T01)

| Sufixo | Significado | Valido em granularidade |
|---|---|---|
| (none) | unidade base detectada em A | sempre |
| `Y` | ano | sempre |
| `M` | mes (capital pra distinguir de minuto) | sempre |
| `D` | dia | second, ms, us, ns |
| `h` | hora | second, ms, us, ns |
| `m` | minuto | second, ms, us, ns |
| `s` | segundo | ms, us, ns |
| `ms` | milissegundo (multi-char) | us, ns |
| `us` | microssegundo (multi-char) | ns |
| sinal `-` | negativo | sempre |

Parser **longest-first** pra distinguir `1ms` (milissegundo) de
`1m` + s (minuto + s? — invalido, nao acontece com parser correto).

## Implementacao da granularidade NS

Python `datetime` so' tem precisao us nativamente. Pra ns:

- Parse: separa fractional em `us_part` (6 dig) + `ns_extra` (3 dig)
- Computacao: total_ns = (datetime_us-since-epoch * 1000) + ns_extra
- Stage B: deltas em total_ns (integer)
- Stage C: tenta Y/M/D/h/m/s/ms/us, depois fallback ns
- Format de volta: split novamente em us + ns_extra

`stage_b_normalize._parse_dt_and_ns()` faz o parsing. Internal
representation = (datetime, ns_extra ∈ [0,999]).

## Datasets

- **D11f-datetime-ms.csv** (13 linhas): heartbeat a cada 1s,
  formato `.fff`. Stage C deve emitir `1s` × 12.
- **D11g-datetime-us.csv** (13 linhas): cadencia a cada 1ms (1000us),
  formato `.ffffff`. Stage C deve emitir **`1ms` × 12** (multi-char).
- **D11h-datetime-ns.csv** (13 linhas): cadencia a cada 1us (1000ns),
  formato `.fffffffff`. Stage C deve emitir **`1us` × 12** (multi-char).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/08-granularidades-finas/run.py
```

Roda 8 datasets (5 backward + 3 novos), gera outputs/<dataset>/.

## Resultados (ver result.md gerado pelo run.py)

Stage C outputs dos 3 novos:

```
D11f (ms granul):  [base, 1s × 12]
D11g (us granul):  [base, 1ms × 12]   ← multi-char
D11h (ns granul):  [base, 1us × 12]   ← multi-char
```

## Criterio de fechamento

- [ ] RT 8/8 OK
- [ ] Backward compat D11a/b/c/d/e byte-exato
- [ ] Stage A detecta ms/us/ns em D11f/g/h
- [ ] Stage C emite multi-char correto (`1ms`, `1us`)
