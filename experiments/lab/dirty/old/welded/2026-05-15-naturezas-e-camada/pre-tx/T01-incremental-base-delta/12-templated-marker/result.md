# Resultado — 12-templated-marker

**Status**: **TODOS RT OK** (3/3)

## Tabela

| Dataset | v1 | v2 | v3 | v3/v1 | v3/v2 | RT |
|---|---:|---:|---:|---:|---:|---|
| [D11c-datas-mensal](D11c-datas-mensal/_SUMMARY.md) | 109 | 95 | **18** | 16.5% | 18.9% | OK |
| [D11g-datetime-us](D11g-datetime-us/_SUMMARY.md) | 120 | 110 | **34** | 28.3% | 30.9% | OK |
| [D11i-datas-mensal-com-correcao](D11i-datas-mensal-com-correcao/_SUMMARY.md) | 57 | 45 | **36** | 63.2% | 80.0% | OK |

## Discussao

Comparacao v3 (template marker) vs v2 (escape dedutivel) vs v1 (canonical):

- **D11c (cadencia mensal)**: marker `2025-??-05` + 13 deltas de `1`. Pre-tx output sao 14 linhas. TCF aplica RLE: `*12|1`. Compara com v2 que tinha `*12|\1M`.
- **D11g (cadencia ms)**: marker `2025-05-15 09:00:00.0??000` + deltas de `1`. Pre-tx tem 14 linhas. TCF: `*12|1`. Compara com v2 `*12|\1ms`.
- **D11i (mensal com correcao)**: marker no month + corrections em dia quando day != template default. RLE quebra parcialmente porque deltas variam.

## Observacao

Esta POC encoder/decoder e' especializado por dataset (hardcoded). Uma versao geral exigiria:
- Format-aware parser (regex ou estruturado)
- Identificacao automatica do change-position
- Mapeamento posicao -> field/unit
- Convencao mais robusta pra carregar initial value no template

## Limitacao registrada

Initial value e' assumido como minimo do field (month=01, ms=000, etc.). Pra dados que nao comecam no minimo, precisa de syntax adicional.

## Conexoes

- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — fonte do v2 + smart_escape
- Relacao com **T02 templated** (nature 2) — esta POC e' protótipo
- [META-TYPE-ENCODERS](../../../../../../tickets/META-TYPE-ENCODERS.md) — plano
