# EXP-010 — Prototype TCF delta-aware (report)

**Total bytes prototype**: 2412
**Total bytes reference (sub-exp 09 dirty)**: 2272
**Diff**: +140 bytes
**RT**: 20/20
**Body byte-match com referencia**: 0/20
**Cadence detected**: 12/20

## Tabela

| Dataset | det? | runs | bytes proto | bytes ref | Δ | body match | RT |
|---|---|---:|---:|---:|---:|---|---|
| D1-emails-simples | no | 0 | 125 | 118 | +7 | ✗ | OK |
| D2-emails-quote-id | no | 0 | 173 | 166 | +7 | ✗ | OK |
| D3-stress-substring | no | 0 | 184 | 177 | +7 | ✗ | OK |
| D4-caos-mix | no | 0 | 120 | 113 | +7 | ✗ | OK |
| D5-padroes-multiplos | no | 0 | 288 | 281 | +7 | ✗ | OK |
| D6-poucos-em-ruido | no | 0 | 294 | 287 | +7 | ✗ | OK |
| D7-aninhamento | no | 0 | 222 | 215 | +7 | ✗ | OK |
| D8-cabeca-cauda | yes | 0 | 107 | 100 | +7 | ✗ | OK |
| D9-frequencia-alta | yes | 2 | 73 | 66 | +7 | ✗ | OK |
| D11a-datas-dia | yes | 3 | 78 | 71 | +7 | ✗ | OK |
| D11b-datas-borda | no | 0 | 180 | 173 | +7 | ✗ | OK |
| D11c-datas-mensal | yes | 2 | 79 | 72 | +7 | ✗ | OK |
| D11d-datetime-min | yes | 2 | 68 | 61 | +7 | ✗ | OK |
| D11e-datetime-mensal | yes | 2 | 91 | 84 | +7 | ✗ | OK |
| D11f-datetime-ms | yes | 2 | 73 | 66 | +7 | ✗ | OK |
| D11g-datetime-us | yes | 2 | 78 | 71 | +7 | ✗ | OK |
| D11h-datetime-ns | yes | 2 | 81 | 74 | +7 | ✗ | OK |
| D16a-ids-3digits | yes | 1 | 18 | 11 | +7 | ✗ | OK |
| D16b-ids-4digits | yes | 2 | 35 | 28 | +7 | ✗ | OK |
| D16c-ids-prefixados | yes | 2 | 45 | 38 | +7 | ✗ | OK |

## Validacao

⚠ **RT OK mas bytes diferem**: investigar divergencia vs dirty lab.

## Pipeline

Pipeline single-column:
```
rows = load
unicas = dedup_preserve_order(rows)
detected, _ = detect_cadence(unicas, threshold=0.7)
if detected:
    tokens = processar_with_hint(unicas, prefer_shape_consistency=True)
else:
    tokens = processar(unicas)  # canonical
body = HCCSeqRLE().encode(rows, unicas, tokens)
```

## Limitacoes

- Single-column. Multi-column expansao futura.
- Datasets sao **sinteticos**. Real-world (TPC-H, Adult Census) NAO testado.
- Threshold 0.7 do auto-detect e' arbitrario.

