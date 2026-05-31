# Sub-exp 09 — Auto-detect cadence via heuristica (H-DA-09b)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-09b — auto-detect cadencia via heuristica
**Motivacao**: revisao conceitual de H-DA-07/H-DA-09 — sub-exp 06
mostrou que "always-on" piora 5/9 datasets. Pre stage com heuristica
poderia evitar essas regressoes?

## Hipotese a validar

**H-DA-09b**: Pre stage com heuristica simples — baseada em
**propriedades estruturais** (length uniformity, LCP+LCS ratio) —
pode decidir quando habilitar hint sem nomear tipo.

Se funcionar: melhor dos dois mundos
- D11+D16 (com cadencia): hint enabled, captura ganho
- D1-D9 (sem cadencia): hint disabled, evita regressao

## Heuristica proposta

```
detect_cadence(strings, n_sample=5, threshold=0.7):
  1. Se < n_sample strings: False
  2. Se lengths variam entre sample: False
  3. Pra cada par consecutivo (a, b) em sample:
       lcp = LCP(a,b)
       lcs = LCS(a,b)
       se (lcp + lcs) < threshold * len(a): False
  4. True
```

**Propriedades**:
- Type-agnostic: nao verifica formato, so' estrutura
- Single-pass: olha so' primeiras N strings
- Generic: threshold ajustavel
- Memoria O(N) onde N = sample size (~5)

## Testes

Aplicar em **TODOS os 20 datasets disponiveis** (D1-D9 + D11a-h +
D16a-c). Comparar 3 pipelines:

| Pipeline | Descricao |
|---|---|
| Baseline | OBAT canonical + HCC canonical |
| Always-on | OBAT fork shape-preserve (forced) + HCC fork |
| **Auto-detect** | Pre detecta cadencia, OBAT enable/disable hint, HCC fork |

Pro auto-detect:
- Datasets onde heuristica detecta = enable hint
- Datasets onde nao detecta = OBAT canonical (sem hint)

## Aceite

- **Confirmada** se: auto-detect e' melhor ou empate vs always-on
  E melhor que baseline em pelo menos 1 dataset adicional
- **Refutada** se: auto-detect introduz suas proprias regressoes
  ou nao captura ganhos detectaveis

## Ressalvas conceituais

- Heuristica de 0.7 e' arbitraria; outras configuracoes podem dar
  resultados diferentes
- Datasets ainda sao todos sinteticos; nao testa real-world
- N_sample=5 e' arbitraria; pode capturar/perder padroes
- Nao testa adversarial inputs (dataset que parece cadenciado mas
  nao e')

## Estrutura

```
09-auto-detect-cadence-heuristic/
├── README.md
├── auto_pre.py     (detect_cadence function)
├── run.py          (3 pipelines em 20 datasets)
├── summary.md
├── result.md
└── outputs/<ds>/
    ├── detect-result.txt
    └── body-comparativo.tcf
```
