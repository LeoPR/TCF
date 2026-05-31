# Sub-exp 06 — Auto-hint regression test (H-DA-09)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-09

## Hipotese a validar

**H-DA-09**: A versao mais simples de "auto-hint" (sempre habilitar
`prefer_shape_consistency=True`) e' **safe** — nao regride bytes
em datasets sem cadencia explicita.

## Teste

Aplicar o pipeline do sub-exp 04 (OBAT fork shape-preserve + HCC
fork seq-RLE) em **D1-D9** (datasets stress validados em M9, sem
cadencia explicita).

Comparar contra baseline (canonical OBAT + canonical HCC) em cada
dataset:
- Se NENHUM dataset regride → H-DA-09 confirmada (always-on safe)
- Se algum regride → hint precisa ser opt-in (Pre stage precisa
  inferir quando habilitar)

## D1-D9 (insumo)

| Dataset | Cenario |
|---|---|
| D1-emails-simples | Emails 3 dominios |
| D2-emails-quote-id | Emails com apostrofes |
| D3-stress-substring | URLs api/users/... |
| D4-caos-mix | Mix `[X]*'YYY'@4Z` |
| D5-padroes-multiplos | email + UUID |
| D6-poucos-em-ruido | Timestamps unicos |
| D7-aninhamento | `[start][a][middle][a][end]` |
| D8-cabeca-cauda | `prefix/X/suffix` |
| D9-frequencia-alta | `@@@KEY=valueX@@@` |

Baseline canonical M9: 1615 bytes total. 

## Aceite

- **Confirmada** se: ganho ou empate em **TODOS** os 9 datasets
  E RT 9/9 OK
- **Refutada parcial** se: regride em algum dataset (hint vira
  opt-in)
- **Refutada** se: regride em todos ou maioria (hint quebra
  generalidade)

## Estrutura

```
06-auto-hint-regression-D1-D9/
├── README.md
├── run.py          (reusa pipeline sub-exp 04 em D1-D9)
├── summary.md
├── result.md
└── outputs/<ds>/
    ├── 1-tokens-canonical.txt
    ├── 2-tokens-fork.txt
    ├── 3-body-baseline.tcf
    ├── 4-body-fork.tcf
    └── 5-rt-status.txt
```
