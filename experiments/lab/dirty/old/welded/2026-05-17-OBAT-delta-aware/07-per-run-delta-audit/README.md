# Sub-exp 07 — Per-run delta audit (H-DA-08)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-08

## Hipotese a validar

**H-DA-08**: Extender detector seq-RLE pra aceitar pares onde
**diferentes escape-digit runs tem diferentes deltas** (incluindo
runs com delta=0). Exemplo D11b: `9\2-\28` → `9\2-\29` (run "2"
Δ=0, run "28" Δ=+1).

## Audit (Fase 1)

Analisa todos os body fork+fork dos sub-exps 04 e 05 (D11a-h +
D16a-c). Identifica pares NAO compactados que SE QUALIFICARIAM
para per-run delta:
- mesmo length
- runs em mesmas posicoes (runs_a == runs_b)
- nem todas runs com mesmo delta (caso contrario detector atual
  ja' pega)

Quantifica bytes potencialmente recuperaveis vs. custo de
implementacao.

## Sintaxe proposta (se viavel)

`*N+delta@run_idx|template` — N linhas, shift somente da run
de index `run_idx` por delta.

Exemplo D11b: `*2+1@1|9\2-\28` (15 chars)
- N=2, delta=+1, run_idx=1 (segunda run, "28"→"29")
- Decoder: shift somente run 1 → `9\2-\29`

## Aceite

- **Confirmada** se: ganho >= 20 bytes total em D11+D16
- **Refutada** se: ganho < 10 bytes (complexidade nao vale)

## Estrutura

```
07-per-run-delta-audit/
├── README.md
├── audit.py
├── audit.md
└── result.md
```
