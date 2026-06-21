# 02 — Bordas de mes/ano (D11b) com encoder v0 (dia-only)

**Estado**: aberto (segunda iteracao do T01)
**Macro pai**: [`../README.md`](../README.md) — T01 incremental
**Dataset**: [`D11b-datas-borda.csv`](../../../../../../../datasets/synthetic/D11b-datas-borda.csv)
**Encoder**: v0 (dia-only, copiado de [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/))

## Pergunta cientifica

Encoder dia-only (`pretx_dia.encode`) preserva RT byte-canonical
em datas cruzando **bordas de mes e ano** (incluindo ano
bissexto)?

A transformacao `date1 - date2 = N dias` deve funcionar via
`datetime.timedelta` sem codigo especial pra borda. Esta iteracao
**valida** isso empiricamente.

## Hipoteses

- **H1 (RT)**: encoder v0 preserva RT em D11b, mesmo com transicoes
  Jan→Feb, Feb→Mar (com e sem ano bissexto), Dec→Jan.
- **H2 (bytes)**: pre-tx + TCF reduz bytes vs TCF puro em D11b
  (similar a D11a, mas com deltas mais variados).

## Datas no D11b (14 linhas)

Casos de borda exercitados:

| # | Data | Delta vs anterior (dias) | Caso |
|---|---|---:|---|
| 1 | 2024-01-31 | (base) | — |
| 2 | 2024-02-01 | 1 | Jan→Feb (mes 31 dias) |
| 3 | 2024-02-28 | 27 | dentro de Feb |
| 4 | 2024-02-29 | 1 | **Feb 29 (ano bissexto 2024)** |
| 5 | 2024-03-01 | 1 | **Feb 29 → Mar 1** |
| 6 | 2024-12-31 | 305 | fim do ano |
| 7 | 2025-01-01 | 1 | **Dec→Jan (year boundary)** |
| 8 | 2025-02-28 | 58 | até Feb fim |
| 9 | 2025-03-01 | 1 | **Feb 28 → Mar 1 (non-leap)** |
| 10 | 2025-12-31 | 305 | fim do ano |
| 11 | 2026-01-01 | 1 | **Dec→Jan** |
| 12 | 2026-01-31 | 30 | dentro de Jan |
| 13 | 2026-02-28 | 28 | Feb→Mar (non-leap, Feb tem 28 dias) |
| 14 | 2026-03-01 | 1 | **Feb 28 → Mar 1** |

Deltas observados: `[1, 27, 1, 1, 305, 1, 58, 1, 305, 1, 30, 28, 1]`

## Sub-perguntas a explorar

1. RT preserva todas as bordas (Feb 29, ano boundary, mes boundary)?
2. Deltas grandes (305) afetam compressao (sao maiores que os de D11a)?
3. O `1` repete 7 vezes em D11b (vs 5 em D11a) — compressao melhora?

## Linguagem do pre-tx

Mesma de [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/):
- Linha 0: data base (intocada)
- Linhas 1+: delta em dias (inteiro relativo a linha anterior)

Escalas (`1M`, `1Y`) ficam pra sub-experimento 03+.

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/02-bordas-D11b/run.py
```

## Saidas

`outputs/` (gitignored, regeneraveis):
- `00-input.txt` ... `08-rt-result.txt`
- `03-obat-tokens.txt`, `04-hcc-trace.txt`, `05-hcc-rede.txt` — debug
- `bytes-comparison.md` — tabela bytes

`result.md` (commitavel) — resumo dos resultados.

## Criterio de fechamento

- [ ] RT byte-canonical OK em todas as 14 linhas (incluindo bordas)
- [ ] Bytes pre-tx + TCF < TCF puro
- [ ] Sem erro de calendar (validar via `datetime.timedelta`)
- [ ] Comparacao com D11a: bytes proporcionalmente similares?
