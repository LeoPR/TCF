# Sub-exp 05 — validar welding canonical Pacote 3 (bug `,` em literais)

## Status pre-validacao

Fix aplicado em `src/tcf/composicional/syntax.py` linhas 435-442
(comentario menciona 'Bug fix 2026-05-19 (ADR-0007)').
ADR-0007 ainda status `proposed`. Roadmap H-FIX-01/02/03 aberta.

Este sub-exp valida que welding esta funcional + sem regressao.

## Casos minimos (sub-exp 01)

**10/10 OK** (era 7/10 pre-fix).

Casos 5, 7, 10 (FAIL pre-fix) devem agora estar OK.

## D1-D9 M10 baseline

Total D1-D9: **1523B** (== 1523B preservado)
RT: 9/9

## Adult Census + TPC-H

- 57 cols testadas
- RT: 57/57
- Bytes total: 889,714

## Veredito

- Casos minimos: OK
- D1-D9 baseline: OK
- D1-D9 RT 100%: OK
- Real-world RT 100%: OK

**WELDING PACOTE 3: CONFIRMED**

