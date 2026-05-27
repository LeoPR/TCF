---
title: 2026-05-27 — Baseline consolidado pos-consolidacao
type: dirty-lab
status: ATIVO (baseline-de-referencia)
foco: ponto de partida pra novas hipoteses; reference de bytes/RT
created: 2026-05-27
---

# Lab dirty — Baseline consolidado (2026-05-27)

## Por que este lab existe

Apos consolidacao do dirty lab (mover 17 labs welded/refuted pra
`old/`), surge necessidade de **um lab que materialize a baseline
canonical atual** pra comparacoes futuras nao terem que pescar
metricas em N pastas diferentes.

> "Ter muitos labs mesmo dirt comeca a aumentar a complexidade de
> busca e consolidacao geral." — owner 2026-05-26

Este lab serve como **espelho do `src/tcf/` em forma de dirty
artifacts**: rodar pipeline canonical em D1-D9 + D17a + reais,
salvar `.tcf`s comprimidos visiveis pra auditoria, registrar
bytes/RT na pasta. Sub-exps futuros comparam contra este.

## Conteudo

- [`METRICS.md`](METRICS.md) — bytes canonicos por dataset (D1-D9,
  D17a, real-world) + ratios. **Source of truth pra comparacao**.
- [`ADRs-INDEX.md`](ADRs-INDEX.md) — indice navegavel dos 16 ADRs
  (0001-0016) com 1-linha sumario + onde aplica.
- [`lessons-learned.md`](lessons-learned.md) — sintese de
  aprendizados dos 17 labs welded/refuted (o que sustentou, o que
  caiu, padroes a evitar).
- [`run-baseline.py`](run-baseline.py) — script que regenera todos
  os `.tcf` em `outputs/` a partir de `src/tcf/` atual.
- `outputs/` — `.tcf`s visiveis (gerados via `run-baseline.py`).

## Nao e' (escopo negativo)

- **Nao e' lab de exploracao** — nao testa novas hipoteses
- **Nao e' src/tcf/** — apenas materializa o output do canonical
- **Nao substitui `STATUS.md`** — STATUS e' bibliografico; este e'
  metrica empirica reproduzivel

## Como usar

### Comparar uma nova hipotese contra baseline

```bash
# 1. Rodar baseline (gera outputs/)
python experiments/lab/dirty/2026-05-27-baseline-consolidado/run-baseline.py

# 2. Comparar bytes
# - Abrir METRICS.md
# - Encontrar dataset relevante
# - Comparar com bytes do seu sub-exp
```

### Validar que canonical nao regrediu

```bash
# Regenerar baseline; bytes devem bater METRICS.md
python run-baseline.py
diff outputs/<dataset>.tcf old/welded/2026-05-22-pacote1-weld-canonical/outputs/<dataset>.tcf
```

### Reset apos welding novo (atualizar baseline)

Quando ADR novo entra (ex: ADR-0017 hipotetico), atualizar este lab:
1. Re-rodar `run-baseline.py`
2. Atualizar `METRICS.md` com novos bytes
3. Adicionar entrada em `ADRs-INDEX.md`
4. Anotar regressao/ganho em `lessons-learned.md`

## Baseline atual (2026-05-27)

Pipeline: **M10 + ADR-0013 multi-col + ADR-0014 API + ADR-0015
naturezas + ADR-0016 multi-delta**.

- **D1-D9 sint**: 1523B total em 2981 bytes raw (51.1% ratio), RT 9/9
- **D17a multi-col 13x4**: 322B INVARIANT (delta-tested em 16 ADRs)
- **Real-world** (Adult+TPC-H 57 cols, 136k linhas): -33.02% weighted
  vs raw, RT 57/57
- **Benchmark formats** (sub-exp 2026-05-24-benchmark-formats):
  TCF+nature+brotli vence em **4/6 datasets** vs csv+brotli/json+zstd

## Cross-links

- [STATUS.md](../../../../STATUS.md) — bibliografia ativa
- [MAP.md](../../../../MAP.md) — wayfinding map
- [old/welded/](../old/welded/) — labs welded historicos
- [old/refuted/](../old/refuted/) — labs refutados
- [notas/historia-dirty-lab.md](../notas/historia-dirty-lab.md) —
  narrativa M0-M14
- [notas/roadmap-hipoteses.md](../notas/roadmap-hipoteses.md) —
  hipoteses ativas/futuras
