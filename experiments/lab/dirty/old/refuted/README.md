# dirty/old/refuted/ — labs refutados / closed-insufficient-gain

Labs cuja hipotese **nao se sustentou em real-world** ou cujo ganho
foi insuficiente pra justificar welding. Movidos pra ca em
2026-05-27 durante consolidacao do dirty lab.

> Refutacao e' resultado cientifico valido. Preservados pra evitar
> repetir hipoteses ja' testadas e pra documentar boundary do que
> NAO funciona.

## Indice

| Pasta | Data | Hipotese | Status | Aprendizado |
|---|---|---|---|---|
| [`2026-05-20-hcc-perf-optimization/`](2026-05-20-hcc-perf-optimization/) | 2026-05-20 | H-PERF-05: HCC perf via cache | `ADIADO` | Cache adicionou overhead > ganho; reverter |
| [`2026-05-20-obat-perf-phase2-trigram-middle/`](2026-05-20-obat-perf-phase2-trigram-middle/) | 2026-05-20 | H-PERF-04: trigrama no meio | `ADIADO` | Complexidade > ganho; perf real-world plano |
| [`2026-05-21-escape-deduction/`](2026-05-21-escape-deduction/) | 2026-05-21 | Pacote 2: escape dedutivel (-15.7% sint) | `CLOSED-INSUFFICIENT-GAIN` | **Motivador do criterio `confirmada-empirica`** (15.7% sint -> 0.13% real-world) |
| [`2026-05-22-h-perf-05d-counter-incremental/`](2026-05-22-h-perf-05d-counter-incremental/) | 2026-05-22 | H-PERF-05d: counter incremental HCC | `CLOSED-INSUFFICIENT-GAIN` | Complexidade nao justificou |
| [`2026-05-23-h-da-09c-d-e-refinos-cadence/`](2026-05-23-h-da-09c-d-e-refinos-cadence/) | 2026-05-23 | Refinos detect_cadence (9c/d/e) | `CLOSED-PARCIAL` | Trade-off: ganho em alguns, regressao em outros |
| [`2026-05-23-naturezas-raras-exploracao/`](2026-05-23-naturezas-raras-exploracao/) | 2026-05-23 | Naturezas raras (UUID, hash, base64) | `CLOSED-INSUFFICIENT-GAIN` | Raras = poucos casos; ROI baixo |
| [`2026-05-23-pacote5-t03-enumerated/`](2026-05-23-pacote5-t03-enumerated/) | 2026-05-23 | T03 enumerated dictionary | `CLOSED-INSUFFICIENT-GAIN` | Subsumido por HCC seq-RLE |

## Por que preservar

1. **Evitar repetir** — sub-exp futuro pode propor mesma hipotese
2. **Documentar boundary** — onde TCF NAO ganha (e' resultado)
3. **Cruzar com hipoteses ativas** — sub-exp 13 (base-aware seq-RLE,
   2026-05-24, tambem refutado, ainda no topo pq parte do CPF lab)
4. **Bytes absolutos** preservados — pra revisitar com novas metricas

## Sub-exps refutados embarcados em labs nao movidos

Alguns sub-exps refutados estao **dentro** de labs ativos (nao
movidos pq o lab inteiro nao foi fechado):
- `2026-05-24-cpf-templated-checked/13-base-aware-seq-rle/` — base-aware
  seq-RLE refutado (sub-exp dentro de lab CPF)
- `2026-05-24-cpf-templated-checked/12-hex-ip-variant/` — variante hex
  abandonada (sub-exp dentro de lab CPF)

Ver [`../../notas/roadmap-hipoteses.md`](../../notas/roadmap-hipoteses.md)
pra registry cross-lab de hipoteses (incluindo refutadas).
