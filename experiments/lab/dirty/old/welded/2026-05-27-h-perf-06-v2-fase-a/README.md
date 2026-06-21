# 2026-05-27 — H-PERF-06-v2 Fase A (dirty lab)

**Tema**: prune algoritmico + early-term em HCC `_detect_compositions`.

**Hipotese de partida (H-PERF-06-v2)**: `_detect_compositions` em
`src/tcf/composicional/syntax.py` consome ~88% do tempo de encode em
datasets reais com strings repetitivas. Fase A confirma o profile real
antes de qualquer mudanca algoritmica.

## Estrutura

- `00-baseline/` — cProfile do encode atual (M10 canonical).
  Mede onde o tempo realmente vai antes de propor podas/early-term.
- (futuras sub-pastas) — variantes de prune e early-term, comparadas
  contra `00-baseline`.

## Dataset alvo

Online-retail amostra 20k linhas (CSV em
`Z:/tcf-data/external/online-retail/online_retail.csv`). Strings
repetitivas (Description, Country, StockCode) — workload realista pra
exercitar o detector.

## Regras

- NAO modificar `src/tcf/`. Toda variante vive aqui.
- Cada sub-exp imprime baseline numerico (cumtime, % do total, calls).
- Resultado final: ADR ou ticket fechado com numeros, nao texto.
