---
title: T-test-harness-mvp — meta-programa de validacao do TCF
type: task
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Decisao "TCF nao tem transport/server; harness externo simula tudo"
see_also:
  - docs/theory/components/6-test-harness.md (design completo)
  - docs/workbench/tickets/open/E-compression-combinations.md
  - docs/workbench/tickets/open/E-format-comparison-bench.md
---

# T-test-harness-mvp — implementar meta-programa MVP

Construir infraestrutura **fora do TCF** que orquestra:

```
encode → (compress?) → (transport?) → (decompress?) → decode → compare
```

Permitindo trocar **encoder** (TCF/CSV/JSON/TOON), **compressor**
(gzip/brotli/none), **transport** (memory/disk/http) sem alterar
nada no TCF core.

Design completo em [6-test-harness.md](../../../theory/components/6-test-harness.md).

## Localizacao

`experiments/harness/` (novo subdir)

## MVP — Sprint 1 (Sprint Harness 1)

### Sub-tarefas

- [ ] Criar `experiments/harness/` skeleton
- [ ] `pipeline.py` com `simulate(rows, encoder, compression, transport)`
- [ ] `transports/memory.py` (default, sem latencia)
- [ ] `compressors/gzip_codec.py` + `brotli_codec.py`
- [ ] `encoders/tcf_encoder.py` + `csv_encoder.py` + `json_encoder.py`
- [ ] `compare.py` com `compare_formats(rows, encoders, compressions)`
- [ ] Smoke test: rodar Adult vol=100 com 3 encoders × 2 compressores

### Saida esperada

```
$ python experiments/harness/run.py --scenario adult_100

| encoder | compression | bytes | encode_ms | decode_ms |
| tcf     | none        | 7188  | 0.2       | 0.15      |
| tcf     | gzip        | 2200  | 0.5       | 0.4       |
| tcf     | brotli      | 1900  | 5.0       | 1.0       |
| csv     | none        | 9000  | 0.1       | 0.1       |
| csv     | gzip        | 3500  | 0.3       | 0.3       |
| csv     | brotli      | 3000  | 4.5       | 0.9       |
| json    | none        | 14000 | 0.3       | 0.4       |
| json    | gzip        | 4200  | 0.8       | 0.6       |
| json    | brotli      | 3800  | 6.0       | 1.2       |

Roundtrip: all OK
```

## Sprints futuros

Ver [6-test-harness.md](../../../theory/components/6-test-harness.md)
para roadmap completo (Sprint 2-5).

## Criterio de aceite (MVP)

- [ ] Skeleton estabelecido em `experiments/harness/`
- [ ] 3 encoders + 2 compressores + 1 transport (memoria)
- [ ] `compare.py` produz tabela markdown
- [ ] Smoke test em Adult vol=100 passa com roundtrip OK
- [ ] Manifests JSONL em `experiments/results/harness/`
- [ ] README.md no harness explicando como rodar

## Dependencias

- `pip install brotli` (ja temos no env)
- TCF v0.2 atual funciona — nao precisa esperar v0.4

## Impacto estimado

3-5 dias para MVP funcionando.

## Notas para revisar

Quando reabrir:
- Estado: `experiments/harness/` provavelmente vazio
- Ordem: este ticket vem ANTES de E-compression-combinations
  (que precisa do harness para rodar)
