# evidencia-0.8 — material comprobatório do #TCF.8/0.8.0 (T-QA-8)

Resultados VERSIONADOS (exceção no `.gitignore` — outputs visíveis pra auditoria).
Produzidos por [`scripts/bench_evidencia.py`](../../../scripts/bench_evidencia.py)
(runner; F1) com sondas portáveis em
[`scripts/bench_evidencia_probes.py`](../../../scripts/bench_evidencia_probes.py)
(F0-3: conceitos independentes de OS/linguagem; sondas isoladas com fallback —
campo AUSENTE = sonda indisponível na plataforma, nunca medição quebrada).

Layout: `<fase>/<dataset>.jsonl` (1 registro por linha; append) + `.tcf` de
exemplo quando `--save-blob`. Fases: `f2` controle · `f3` sintéticos/escala ·
`f4` públicos.

## Regras (T-QA-8 §2 — o que um registro PROMETE)

- `rt_ok: true` obrigatório pra QUALQUER número (RT na mesma run; sem RT não
  há bytes no registro). `rt_mode` diz o cheque: `identidade` ou
  `idempotencia-2a-geracao` (transformação declarada: sort_by/anônimas).
- Todo campo é MEDIDO (nada derivado/copiado). Runner validado contra a régua:
  `python scripts/bench_evidencia.py --validate-pins`
  (D1-D9=1523B · D17a=300B · real-world=89616B — divergiu = bug do runner).

## Schema `evidencia-0.8/v1` (campos)

| campo | conteúdo |
|---|---|
| `dataset` | id, source, n_rows, n_cols, kind (single/multi) |
| `encode_kwargs`, `seed` | proveniência do caso |
| `rt_ok`, `rt_mode`, `deterministic` | RT + encode duas vezes byte-idêntico |
| `bytes` | total / header / body (medidos do blob) + `input_join_lf` (baseline raw) |
| `timing.encode/.decode` | `median_ns`, `p95_ns`, `min/max_ns`, `n`, `warmup` (mediana de n≥9 com warmup — protocolo do conceito) |
| `memory` | `encode/decode_peak_heap_bytes` (tracemalloc, run separada — mede o heap PYTHON; alocações nativas, ex. Cython, NÃO entram: comparação cross-linguagem usa `process_peak_rss_bytes`), `process_peak_rss_bytes` (sonda por plataforma; ausente = sem sonda) |
| `side` | SideOutputs serializado: `multi_info` (col_modes, fallback/dict/split), `per_col` (body_bytes=candidato vs emitted_bytes/emitted_mode=emitido — semânticas distintas, BUG-07), `nature_apply` |
| `env` | python/platform/cpu, tcf_version, cython_accel, **probes ativas** |
| `run_utc`, `schema` | carimbo + versão do schema |

Unidades explícitas no nome (`_ns`, `_bytes`). Claims de paralelismo usam SÓ
wall-clock + byte-identidade + `parallel_workers` (CPU/mem de workers é
inobservável via stdlib — regra de honestidade §2.4).
