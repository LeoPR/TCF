---
title: Sub-exp 05 — Fallback per-value com marker explicito
status: stub
---

# Sub-exp 05 — Fallback per-value

## Motivacao

Sub-exps 03/04 mostraram RT FAIL em D-CPF-corrupt: corrupt_check gera
CPFs com formato OK mas check invalido. Pre-tx faz "data quality fix"
implicito (regen check), mudando o valor original. RT byte-canonical
quebrado.

Sub-exp 05 implementa **fallback explicito**: marker no payload
distingue compressed vs literal.

## Design

Encoded payload eh 1 de 2 forms:
- **5 chars base-94**: compressed (formato CPF + check valido)
- **string original**: literal (qualquer outro caso)

Decoder distingue por `len(payload) == 5 and all(c in BASE94 for c in payload)`.

**Edge case**: string original de 5 chars que casa BASE94? Improvavel
pra CPF (sempre tem `.` ou letras), mas precisa garantir. Solucao
robusta: prefix marker explicito (`#` pra literal, ausencia = encoded).
Custa 1 byte por literal mas resolve ambiguidade.

## Policy configuravel

- **Estrito (default)**: check_invalid -> literal (preserva exato)
- **Loose**: check_invalid -> encode + flag `was_check_invalid`

## Datasets

- D-CPF-corrupt (5% corruptos com 4 tipos)
- D-CPF-mixed (50% sem mascara -> 500 fallbacks)

## Criterio de aceite

- RT byte-canonical 100% em ambos datasets
- Counts corretos: n_compressed + n_fallback = n_total
- Bytes vs variante B pura: leve overhead pelo marker, esperado.
