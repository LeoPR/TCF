# 06 — Staged pipeline estendido pra granularidade SEGUNDO

**Estado**: aberto (sexta iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Datasets**: D11a, D11b, D11c (backward compat day) + [D11d-datetime-min](../../../../../../../datasets/synthetic/D11d-datetime-min.csv) (novo, second granularity)

## Pergunta cientifica

Estender o pipeline staged pra detectar e processar **granularidade
de segundo** (datetimes `YYYY-MM-DD HH:MM:SS`), mantendo backward
compat byte-exato com sub-exps 01-05 nos datasets day-only?

Linguagem das escalas se generaliza limpo? Stage A detecta correto?
Stage B normaliza em segundos? Stage C otimiza onde encaixa (`1m`
pra cadencia de minuto)?

## Hipoteses

- **H1 (RT)**: 4/4 datasets — pipeline reconstroi byte-canonical.
- **H2 (backward compat)**: D11a → 42, D11b → 59, D11c → 22 bytes
  no TCF de C — identicos aos sub-exps anteriores (validados em 05).
- **H3 (Stage A detecta segundo)**: D11d → granularity=second.

## Extensoes

### Stage A — `stage_a_identify.py`
Detector estendido:
- Tentativa 1: `YYYY-MM-DD[T ]HH:MM:SS` -> granularity=second
- Tentativa 2: `YYYY-MM-DD` -> granularity=day
- Fallback: string

Detecta tambem `separator` (T ou espaco) pra preservar no decode.

### Stage B — `stage_b_normalize.py`
Despacha por granularidade:
- `day`: deltas em dias (igual sub-exps anteriores)
- `second`: deltas em segundos (parseando datetime)

### Stage C — `stage_c_optimize.py`
Despacha por granularidade:
- `day`: tenta `Y` -> `M` -> dia (igual)
- `second`: tenta `Y` -> `M` -> `D` -> `h` -> `m` -> segundo

"Exato" agora considera todos os componentes menores que a escala
(ano exato requer mes/dia/hora/min/seg iguais; mes exato requer
dia/hora/min/seg iguais; etc.).

### Decoder — `decoder.py`
Re-identifica meta da primeira linha. Despacha pra denormalize
apropriado.

## Linguagem das escalas (versao atual)

| Sufixo | Significado | Valida em |
|---|---|---|
| (nenhum) | unidade base detectada (dia ou segundo) | sempre |
| `Y` | ano | sempre |
| `M` | mes (capital, distingue de minuto) | sempre |
| `D` | dia | granularity=second |
| `h` | hora | granularity=second |
| `m` | minuto | granularity=second |
| sinal `-` | explicito pra negativos | sempre |

## D11d — dataset novo

Heartbeat de log a cada minuto, formato `YYYY-MM-DD HH:MM:SS`:

```
val
2026-05-15 09:00:00
2026-05-15 09:01:00
...
2026-05-15 09:12:00
```

13 linhas, todas com `:00` segundos -> cadencia de minuto exata.

Stage B em segundos: `[base, 60, 60, 60, ...]` (12 deltas de 60s).
Stage C: tenta `1m` pra cada -> `[base, 1m, 1m, 1m, ...]`.

Espera-se TCF compactar ambos via repeticao (`*12|`-style).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/06-staged-granularity-second/run.py
```

## Saidas

`outputs/<dataset>/`:
- `stage-A-metadata.json`, `stage-B.txt`, `stage-C.txt`
- `tcf-puro.tcf`, `tcf-B.tcf`, `tcf-C.tcf`
- `rt.txt`

`result.md` — tabela consolidada + hipoteses.

## Criterio de fechamento

- [ ] H1: RT 4/4
- [ ] H2: TCF de C de D11a/b/c bate 42/59/22 (backward compat byte-exato)
- [ ] H3: D11d -> granularity=second em Stage A
- [ ] Pipeline pronto pra estender pra ms/us/ns em iteracoes futuras

## Proximos passos (fora deste sub-exp)

- ms/us/ns granularity (sufixos multi-char)
- Timezone handling
- Datetime com fractional precision
- Composicao multi-granularity (Composite, natureza 5 da taxonomia)
