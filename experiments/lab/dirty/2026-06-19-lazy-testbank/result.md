# A1 — banco de testes do lazy (v0.8, workstream A) [resultado]

**Data**: 2026-06-19 · resultado (lab read-only; **`src/tcf` intocado** — fix foi no gadget
`scripts/tcf_lazy/`). Plano: [`v08-plano-etapas.md`](../notas/v08-plano-etapas.md) (A1+A2).
Script: [`a1_testbank.py`](a1_testbank.py) · saída: [`result.txt`](result.txt).

## Método

Valida TODAS as ops do lazy contra o **oráculo** (`decode()` completo + agregação manual), nos **4
modos** de coluna (tcf / raw `!` / dict `@` / split `%`), em ordem: sintéticos → volume real → bordas.
Ops: `nrows/count`, `group_count`, `where` (eq + pred + AND), `sum/min/max/avg` (total e filtrado),
`select` (alinhamento), `agg_by` (sobre layout `sort_by`). Mismatch lazy≠oráculo = bug.

## Resultado: correção VERDE

- **Todas as ops batem o oráculo** em todos os datasets/modos/bordas. **381 passed** na suíte (29 do
  lazy, +2 regressão).
- **Cobertura de modo** (confirmada nos dados reais): `adult` exercitou dict/raw/tcf; `tpch/orders`
  exercitou tcf/dict/**split** → os 4 modos cobertos. Em coluna tcf/split o lazy cai em fallback
  (decode da coluna) **corretamente** (resultado = oráculo).
- **Bordas** ok: vazios, UTF-8 (`ção`), 1 coluna, filtro encadeado (AND via pred), `select()` completo,
  e **coluna inexistente → `KeyError`**.

## Bug encontrado (A1) e fechado (A2)

**Dupla contagem em `touched` / `report()`** → a fração tocada ("a venda") dava **>100%**.
- **Causa**: uma coluna `@dict` tocada **estruturalmente** (`_dict_parts`, via `group_count`/`where` —
  não popula `_cache`) **e depois materializada** (`_col`, via `select`/`sum`) era adicionada a
  `self.touched` **duas vezes** (o `_col` guardava o append só pelo `_cache`, não pelo `touched`).
  Verificado: `group_count + where + select` na mesma coluna → `touched = ['status','status']`.
- **Fix (A2)**: em `_col`, guardar o append por `touched` (`if name not in self.touched`). Gadget,
  1 linha, sem tocar `src/tcf`. + 2 testes de regressão (`pct ≤ 100`, `touched` único).
- **Artefato de teste** (separado do bug): medir a venda com **view fresca por query** (reusar 1
  lazy acumula `touched` de todas as ops). Corrigido no script.

## A venda (pós-fix, view isolada por query)

`where(<texto>).sum(<num>)` toca, do blob:
- **adult** (5k×15): **10,0%** (`where(workclass).sum(education-num)`).
- **tpch/orders** (5k×9): **14,4%** (`where(o_orderstatus).sum(o_totalprice)`).
- sint-base (12×4): 50,7% · borda (6×2): 100% (tabela minúscula, tudo toca).
→ Em tabela real, a query toca **~10-14% do blob** — a tese central do lazy, agora medida e honesta.

## Encaminhamento

- **A1 ✅** (correção verde) + **A2 ✅** (bug de contagem fechado, regressão pinada).
- Próximo: **A3** (performance: medir tempo/memória por op + otimizar com a API atual → repetir A1);
  depois **A4** (promover o gadget → `tcf.view`). Ver [plano](../notas/v08-plano-etapas.md).
- `src/tcf` intocado; baselines intactos (381 passed).
