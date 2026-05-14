# M8 — Detector unificado + convencao output

**Data**: 2026-05-16
**Estado**: e' (em curso)
**Sucede**: [M7](../2026-05-15-M7-refactor/) — apos critica do user em
2026-05-15:
1. Pair (15, 16) em D3 nao detectado. Detector precisa generalizar
   para que **alias_markers e atomic refs vivam no mesmo espaco**.
2. Brackets `[`/`]` no output e CRLF eram artefatos. Documentar +
   adotar **convencao output limpa** desde M8.

## Resultado (apos 2 rodadas de refinamento)

| Sintaxe | D1 | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|---:|
| M1.E-clean | 145 | 176 | 202 | 137 | 660 |
| M7.A-clean | 124 | 171 | 190 | 118 | 603 |
| **M8.A** (detector unificado refinado) | **118** | **166** | **177** | **113** | **574** |

RT 16/16 OK.

- M8.A vs M7.A-clean: **-29 bytes**.
- M8.A vs M6.C original (619 com brackets): **-45 bytes** (-7.3%).
- M8.A vs M1.E baseline (676 com brackets): **-102 bytes** (-15.1%).

## Mudancas principais

### 1. Detector unificado (algoritmico)

`'refs'` pieces agora contem **refs mixtos** (atomos positivos +
virtuais negativos). Detector itera uniformemente em sub-tuplas
de qualquer mistura. Sem fase `'alias_marker'` separada.

**Restricao para inline expansion correto**: sub-tupla aceita se
tem 0 virtuais OU 1 virtual em position 0. Pairwise left-assoc
corrompe inner alias se nao esta no inicio da chain.

### 2. Convencao output

- Sem brackets `[`/`]` no encode (cada syntax modificada).
- LF only (`\n`); `run_lote.py` usa `write_bytes` pra evitar CRLF.
- Decoder mantem skip de brackets pra back-compat.

Documentado em
[`../notas/convencao-output-tcf.md`](../notas/convencao-output-tcf.md).

## Estrutura

```
M8-virtual-refs-clean-output/
  data/
  M1-E-clean/               (M1.E sem brackets)
  M7-A-clean/               (M7.A sem brackets — comparacao)
  M8-A-detector-unificado/  (refs unificados + clean output)
  resultados/
    tokens/<dataset>.txt    (alg16 raw compartilhado)
    matriz_*
  notas/
    conclusoes_M8.md
  run_lote.py               (write LF only)
```

## Detalhes

Ver [`notas/conclusoes_M8.md`](notas/conclusoes_M8.md).

## Direcoes futuras

- Permitir multiplos virtuais via binarization right-assoc.
- Pre-emit aliases standalone para usar final ids em positions.
- Detector global (nao greedy).
- Nos pos-construcao com literal+ref (registrado desde M6).
