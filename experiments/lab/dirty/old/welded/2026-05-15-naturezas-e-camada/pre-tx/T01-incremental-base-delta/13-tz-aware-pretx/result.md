# Resultado — 13-tz-aware-pretx

**Status**: **TODOS RT OK** (3/3)

## Tabela

| Dataset | mode | v1 | v2 | v3 | v3/v1 | v3/v2 | RT |
|---|---|---:|---:|---:|---:|---:|---|
| [D11j-datetime-tz-Z](D11j-datetime-tz-Z/_SUMMARY.md) | `constant_tz` | 111 | 104 | **28** | 25.2% | 26.9% | OK |
| [D11k-datetime-tz-offset](D11k-datetime-tz-offset/_SUMMARY.md) | `constant_tz` | 118 | 109 | **33** | 28.0% | 30.3% | OK |
| [D11m-datetime-tz-variavel](D11m-datetime-tz-variavel/_SUMMARY.md) | `variable_tz` | 121 | 105 | **105** | 86.8% | 100.0% | OK |

## Discussao

Comportamento observado por mode:

- **constant_tz (D11j Z, D11k -03:00)**: tz e' parte estatica do template. Resto do template usa marker `??` em minuto + deltas (cadence 1 min). tz se mistura ao template sem custo extra de syntax.

- **variable_tz (D11m, 3 zonas)**: tz nao e' constante, sem extracao. Fallback: pre-tx == rows (sem template). v3 acaba igual a v2 nesse caso porque TCF canonical encoder ainda aplica HCC + smart escape.

## Limitacoes / aspectos engenhoca

- Encoder/decoder POC: minute-cadence single-hour (sem carry pra hora/dia)
- Initial minute assumido = 00 (MIN), igual convencao sub-exp 12
- tz suffix detectado por regex simples (`Z` ou `±HH:MM`); zonas nomeadas (UTC, EST) nao cobertas
- D11m fallback nao tenta UTC-normalization (uma alternativa: normalizar e tracker tz separadamente)

## Conexoes

- [`../12-templated-marker/`](../12-templated-marker/) — antecedente do template `??`
- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — smart_escape v2
- Sintaxe `??` aqui e' ilustrativa (engenhoca); preserva semantica de format hint (`??` = 2-char zero-padded, espelhando minute format `00`-`59`)
- [META-TYPE-ENCODERS](../../../../../../tickets/META-TYPE-ENCODERS.md) — plano-mestre
