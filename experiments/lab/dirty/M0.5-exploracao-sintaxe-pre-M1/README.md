# M0.5 — Exploracao de sintaxe pre-M1

**Periodo**: 2026-05-11 a 2026-05-12 (12 experimentos)
**Estado**: fechado (consolidacao informal antes do reset macro M1)
**Marco final**: exp 28 (`sumida-e-slice`) — esgota variantes
sinteticas antes de M1.

## Proposito desta fase

Apos o algoritmo cristalizar no exp 16, esta fase explorou
**variantes de sintaxe textual** sobre o mesmo algoritmo:
verbose → compact v1, v1b, v2, v3 → escape vs quote (v4, v5) →
analise critica de ambiguidade → sumida + slice (v6).

A fase foi exploratoria sem estrutura de macro. Cada exp foi
adicionando uma sintaxe ou refinamento, ate' que o user pediu
um **reset mental** com macro M1 (estrutura controlada com
fases F1-F4, micros isolados, datasets canonicos D1-D4).

**M0.5 nao e' canonica** — e' a sequencia de tentativas de
sintaxe que precedeu M1.

## Marco — exp 28

Exp 28 consolidou os aprendizados sobre marcacao de ambiguidade
(ja' tinhamos escape, quote, sumida, slice em formas iniciais).
O user observou que **o algoritmo do exp 16 ja' faz o trabalho
pesado** — sintaxe e' refinamento marginal. Esse insight motivou
o reset em M1 com estrutura mais controlada.

## Lista de experimentos

| Ord | Tema | Tipo |
|---|---|---|
| 17 | familias-variadas | comportamento em 6 familias (URLs, UUIDs, ISO, IPs, CPFs, codigos) |
| 18 | escala | tempo e cobertura em N=50, 200, 1000 |
| 19 | par-AB-independente | busca exaustiva pares (descartado) |
| 20 | marcadores-modulares | interface Syntax — desacopla algoritmo de sintaxe |
| 21 | syntax-compact-v1 | primeira sintaxe alternativa |
| 22 | syntax-compact-v2 | idx automatico por fragmento |
| 23 | syntax-variations | 5 sintaxes lado a lado |
| 24 | syntax-ambiguidade | resistencia a chars ambiguos (escape vs quote) |
| 25 | syntax-adapt | v4-quote-fixed + v5-adapt |
| 26 | syntax-mixed | 3 sintaxes enxutas (escape, q-fix, mixed) |
| 27 | analise-ambiguidade | analisador puro (etapa 1 do flow semantico) |
| **28** | **sumida-e-slice** | **sumida implementada + slice analise — marco** |

## O que ficou

- **Interface `Syntax` desacoplada do algoritmo** (exp 20) — usada
  por todos os micros M1, M2, M3
- **Vocabulario de sintaxes**: verbose, compact, escape, quote,
  mixed, sumida, slice
- **Insight do user**: precisamos no maximo 2-3 comparacoes, nao
  combinatoria
- **Decisao do reset**: criar macro M1 com estrutura controlada

## O que NAO ficou

- Sintaxes informais (v1-v6) foram **reimplementadas do zero** em
  M1 sem importar
- Datasets ad-hoc da fase foram **substituidos** por D1-D4
  canonicos em M1

## Como referenciar

Estes experimentos sao **historicos** — exploracao que motivou
M1. Citar por:
- Conceito de sintaxe testado (escape pontual, quote em grupo, etc)
- Aprendizado sobre limites de cada abordagem
- NAO por bytes (variancia entre versoes, formato muda)

Para detalhes, ver `README.md` ou `conclusoes.md` de cada
subexperimento.
