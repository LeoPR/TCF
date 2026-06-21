# 13 — tz-aware pre-tx (POC)

**Estado**: aberto (13a iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Origem**: META-TYPE-ENCODERS — natureza datetime+timezone

## Pergunta cientifica

Quando uma serie de datetime carrega timezone, podemos:

1. Detectar se tz e' **constante** across rows
2. Se sim, extrair a tz pro template (uma vez), aplicar pipeline
   template-marker do sub-exp 12 no resto
3. Se variavel, fallback (no-op): manter rows como sao

A pergunta: ha' ganho de bytes (vs canonical / vs smart_escape) quando
tz e' constante? E o que acontece no fallback?

## Convencao adotada (POC, engenhoca)

- Template: `YYYY-MM-DD HH:??:SS<tz>` (tz colado ao template como
  parte estatica)
- `??` marker (espelha sub-exp 12) = field 2-char zero-padded (minuto)
- Deltas: int (minutos relativos ao anterior)
- Cadence single-hour (sem carry/overflow pra hora/dia)
- Initial minute = 00 (MIN), igual convencao sub-exp 12
- Fallback variable_tz: pretx == rows

**Sintaxe ilustrativa** — `??` aqui e' POC do conceito "marker no
template". A escolha sintatica final fica pra fase formal; o que
importa e' a IDEIA: tz constante e' parte estatica, tz variavel
permanece per-row.

## Datasets testados

- **D11j** (constant `Z`, 13 rows, 1-min cadence)
- **D11k** (constant `-03:00`, 13 rows, 1-min cadence)
- **D11m** (variable: `-03:00`, `+00:00`, `+02:00`, 6 rows)

## Resultado

Ver [result.md](result.md).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/13-tz-aware-pretx/run.py
```

## Limitacoes registradas

1. **POC engenhoca**: encoder/decoder e' single-hour minute-cadence.
   Carry pra hora/dia/mes nao implementado.
2. **tz patterns suportados**: `Z` e `±HH:MM`. Zonas nomeadas
   (UTC, EST, America/Sao_Paulo) fora do escopo.
3. **D11m fallback**: nao tenta UTC-normalization. Alternativa
   teorica: normalizar pra UTC + stream paralelo de tz. Fora do
   escopo da POC.
4. **Initial value = MIN**: igual sub-exp 12. Se dataset nao comeca
   no minimo, precisa de syntax adicional.

## Conexoes

- [`../12-templated-marker/`](../12-templated-marker/) — antecedente
  do `??` marker
- [`../11-escape-dedutivel/`](../11-escape-dedutivel/) — smart_escape
- [META-TYPE-ENCODERS](../../../../../../tickets/META-TYPE-ENCODERS.md) —
  plano-mestre, natureza timezone
- [feedback-materializacao-minimal] — extrair tz constante = nao gravar
  redundancia
