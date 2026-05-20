# Sub-exp 02 — prototipos zero-risk (H-PERF-05b + 05c)

**Decisao sub-exp 01**: comecar pelas otimizacoes sem risco de byte loss:
- H-PERF-05b: `_estimate_baseline_chars` em counting direto (sem list+join+len)
- H-PERF-05c: skip `_build_trace` + `_build_rede` (dead code em pipeline canonical)

## Variantes

| ID | Mudanca | Risco bytes |
|---|---|---|
| v0 | baseline canonical | referencia |
| v1 | _est_baseline_chars otimizado | zero |
| v2 | v1 + skip trace/rede | zero |

## Validacao

1. Tokens emitidos IDENTICOS a v0 em D1-D9 + lineitem 1k+5k
2. Bytes TCF IDENTICOS
3. Tempo medido

## Implementacao

- `hcc_opts_v1v2.py` — funcoes otimizadas + helper de monkey-patch
- `benchmark.py` — roda baseline vs v1 vs v2

Monkey-patch em `tcf.composicional.syntax.M8AVirtualRefsSyntax`:
- `_estimate_baseline_chars` → versao otimizada (v1+)
- `_build_trace` → noop (v2+)
- `_build_rede` → noop (v2+)

## Aceite

- v1: bytes IDENTICOS, tempo lineitem 5k <35s
- v2: bytes IDENTICOS, tempo lineitem 5k <30s
- Documentar gap remanescente (espaco pra v3 incremental Counter)
