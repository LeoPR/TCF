# Resultado — 11-escape-dedutivel

**Status global**: **TODOS RT OK** (8/8)

## Tabela consolidada

| Dataset | v1 bytes | v2 bytes | Saving | % | Escapes removidos | RT |
|---|---:|---:|---:|---:|---:|---|
| [D11a-datas-dia](D11a-datas-dia/_SUMMARY.md) | 42 | **36** | 6 | **14.3%** | 6 | OK |
| [D11b-datas-borda](D11b-datas-borda/_SUMMARY.md) | 59 | **51** | 8 | **13.6%** | 8 | OK |
| [D11c-datas-mensal](D11c-datas-mensal/_SUMMARY.md) | 22 | **19** | 3 | **13.6%** | 3 | OK |
| [D11d-datetime-min](D11d-datetime-min/_SUMMARY.md) | 34 | **28** | 6 | **17.6%** | 6 | OK |
| [D11e-datetime-mensal](D11e-datetime-mensal/_SUMMARY.md) | 34 | **28** | 6 | **17.6%** | 6 | OK |
| [D11f-datetime-ms](D11f-datetime-ms/_SUMMARY.md) | 39 | **32** | 7 | **17.9%** | 7 | OK |
| [D11g-datetime-us](D11g-datetime-us/_SUMMARY.md) | 43 | **36** | 7 | **16.3%** | 7 | OK |
| [D11h-datetime-ns](D11h-datetime-ns/_SUMMARY.md) | 46 | **39** | 7 | **15.2%** | 7 | OK |
| **TOTAL** | **319** | **269** | **50** | **15.7%** | **50** | OK |

## Conclusao

Optimizacao 'escape dedutivel' reduz 319 → 269 bytes (15.7%) nos 8 datasets do T01.
RT byte-canonical preservado em 8/8 datasets.

**Princípio aplicado**: `feedback-abstrato-minimal-materializacao`
— digit-run que nao pode ser ref (valor > nodes existentes) e' literal-
sem-ambiguidade, escape `\` redundante.

## Limitacao da implementacao (apenas T01)

Esta implementacao assume **1 lit piece por linha** (T01 incremental).
Compositions complexas (multiple lits, refs intra-body) precisariam de
parser estrutural completo. Caso geral fica como Track 2 L06 — estudo futuro.

## Backward compat

**Quebra com TCF v1 atual**: decoder canonical interpretaria digits bare
como refs. Implementacao futura requer:
- Versionamento explicito do formato
- Decisao sobre migracao (in-band header? sentinela?)
- Revalidacao completa do canonical chain D1-D9 -> M14

## Conexoes

- [`../10-pacote-completo-com-validacao/`](../10-pacote-completo-com-validacao/) — fonte do v1 tcf-C.tcf
- [meta: feedback-abstrato-minimal-materializacao] — princípio aplicado
- [META-TYPE-ENCODERS L06](../../../../../../tickets/META-TYPE-ENCODERS.md) — estudo Track 2 registrado
