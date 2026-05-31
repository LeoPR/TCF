---
title: T-SHAPER-SCIENTIFIC-GATING — Gate cientifico de uso do shaper (tests estatisticos assertados)
status: open
priority: P1
created: 2026-05-30
blocked-by: []
related:
  - scripts/shaper/_stratify_metrics.py  (TVD/JSD/chi^2/Wilson — infra existe, nao gated)
  - scripts/shaper/strategies/  (6 strategies: volume, schema, join, order, stratify, fk_preserving)
  - tests/test_shaper.py  (50 tests; nenhum assert estatistico real)
  - feedback_tools_need_statistical_validation (memoria, principio 2026-05-30)
---

# T-SHAPER-SCIENTIFIC-GATING — Aprovacao cientifica do shaper

## Contexto

Auditoria 2026-05-30 (workflow paralelo de validacao do shaper) revelou
gap critico: o shaper tem 49 tests passando + 1 xfail, mas **nenhum
test asserta invariante estatistico**. Os tests existentes validam:
cardinalidade (`len() == N`), presenca de coluna, determinismo —
**mas nao** que as propriedades cientificas que o shaper claima sao
de fato preservadas.

Achado especifico do agente de validacao estatistica:

> "Infraestrutura estatistica existe (`_stratify_metrics.py`: TVD, JSD,
> Hellinger, chi^2, Wilson CI) mas NAO e' assertada em pytest. Metricas
> sao logadas e descartadas. Type I global: tests verdes dao falsa
> confianca."

Filosofia do owner (registrada [2026-05-30](C:/Users/leona/.claude/projects/.../memory/feedback_tools_need_statistical_validation.md)):

> "Tools cientificos auxiliares (shaper, samplers, gadgets) precisam de
> aprovacao cientifica/estatistica formal antes de uso em experimentos
> TCF. Nao basta 'cortar dados' — precisa confirmacao mensuravel."

**Sem este ticket fechado, shaper NAO esta aprovado** para uso em
experimentos que produzem evidencia empirica sobre TCF.

## Estado atual por strategy

| Strategy | Status | Gap |
|---|---|---|
| `volume` | PARTIAL | Doc/codigo divergem ("first N" vs `random.sample`); marginal nao validada |
| `schema` | PARTIAL | `SCHEMA_LEVELS` hardcoded sem audit vs `metadata.fk` |
| `join` | PARTIAL | Sem teste de `|flat| == |fact|` (LEFT JOIN integrity) |
| `order` | VALIDATED p/ sorted/reverse + TRIVIAL p/ random | OK |
| `stratify` | PARTIAL | Claim "proporcional" sem teste positivo passando (xfail) |
| **`fk_preserving`** | **MISSING** | **Zero tests** (strategy mais complexa, cascata recursiva) |
| `compressibility` | PARTIAL | Correlacao score x bytes-TCF nao validada |

## Plano — 5 tests prioritarios

### P1 — `test_fk_preserving_no_orphans` (CRITICO)

Strategy mais complexa, **zero cobertura hoje**. Bloqueia qualquer
experimento multi-tabela (EXP-011, EXP-013, futuros).

```python
def test_fk_preserving_no_orphans():
    r = shaper.apply(ShapeRequest(
        dataset="tpch-sf001", schema="chain",
        volume=100, fk_preserving=True, seed=42))
    fact = "lineitem"
    dim_meta = r.metadata["tables"]
    for fk_col, ref in dim_meta[fact]["fk"].items():
        ref_table, ref_col = ref.split(".")
        fact_fks = {row[fk_col] for row in r.tables[fact]
                    if row[fk_col] is not None}
        dim_pks = {row[ref_col] for row in r.tables[ref_table]}
        assert fact_fks.issubset(dim_pks), \
            f"FK overlap < 1.0 para {fk_col}"
```

Tambem: cascade fix-point (estabiliza em <= max_depth=10) +
no-amplification (`|filtered_dim| <= |original_dim|`).

### P2 — `test_stratify_chi2_passes` (wire-up de infra existente)

Aproveita `_stratify_metrics.py` ja' implementado, apenas asserta no
pytest em vez de descartar o log.

```python
def test_stratify_preserves_distribution():
    r = shaper.apply(ShapeRequest(
        dataset="adult-census", volume=2000,
        stratify_by="sex", seed=42))
    metrics_line = next(t for t in r.trace if "METRICS_JSON" in t)
    m = json.loads(metrics_line.split("METRICS_JSON: ", 1)[1])
    assert m["chi2_pvalue"] > 0.05, \
        f"H0 (proporcionalidade) rejeitada: chi2_p={m['chi2_pvalue']}"
    assert m["tvd"] < 0.05, \
        f"TVD acima do threshold: {m['tvd']}"
```

### P3 — `test_join_row_count_invariant`

LEFT JOIN preserva contagem do fact (zero perda silenciosa de linhas):

```python
def test_flat_preserves_fact_count():
    r_norm = shaper.apply(ShapeRequest(
        dataset="tpch-sf001", schema="core",
        join_level="normalized", volume=100))
    r_flat = shaper.apply(ShapeRequest(
        dataset="tpch-sf001", schema="core",
        join_level="flat", volume=100))
    assert r_flat.total_rows == len(r_norm.tables["orders"])
```

### P4 — `test_volume_marginal_distribution`

Sample sem stratify deve preservar marginal de colunas categoricas:

```python
def test_volume_random_marginal_unbiased():
    pop = shaper.apply(ShapeRequest(
        dataset="adult-census")).tables["adult"]
    sample = shaper.apply(ShapeRequest(
        dataset="adult-census", volume=5000,
        order="random", seed=42)).tables["adult"]
    for col in ["sex", "race", "education"]:
        pop_c = Counter(r[col] for r in pop)
        smp_c = Counter(r[col] for r in sample)
        m = compute_stratification_metrics(pop_c, smp_c)
        assert m["chi2_pvalue"] > 0.01, f"{col}: amostra viesada"
```

### P5 — `test_schema_levels_match_fk_topology`

`SCHEMA_LEVELS` e' hardcoded em codigo; muda em `metadata.fk` nao
invalida levels. Audit garante coerencia:

```python
def test_schema_core_has_fk_relationship():
    reader = DatasetReader("tpch-sf001")
    core = SCHEMA_LEVELS["tpch-sf001"]["core"]
    fks_inside = sum(
        1 for t in core
        for ref in reader.metadata["tables"][t]["fk"].values()
        if ref.split(".")[0] in core
    )
    assert fks_inside >= 1, "core tem 0 FKs internas"
```

## Criterio de aceite

- [ ] P1 (`fk_preserving` integridade + cascade + no-amplification) implementado e passando
- [ ] P2 (`stratify` chi^2 + TVD assertados via trace) implementado e passando
- [ ] P3 (`join` row count invariant) implementado e passando
- [ ] P4 (`volume` marginal preservation) implementado e passando
- [ ] P5 (`SCHEMA_LEVELS` x metadata.fk consistency) implementado e passando
- [ ] Documentar em `scripts/shaper/README.md` quais claims foram validados e quais nao
- [ ] Atualizar `CLAUDE.md` na secao "Filosofia dos gadgets auxiliares" referenciando o gate

## Riscos / cuidados

- **Doc vs codigo em `volume.py`**: docstring diz "first N" mas codigo
  faz `rng.sample`. Decidir qual e' o comportamento correto antes do
  P4 (talvez mudar a docstring, talvez mudar o codigo).
- **Test xfail `test_stratify_proportional`**: T-FIX-SHAPER-STRATIFY-TEST
  ja' documenta. Resolver junto com P2 ou separadamente.
- **Type II error em P2**: chi^2 com N pequeno tem baixo poder. Talvez
  exigir N >= 1000 ou TVD threshold mais apertado pra strata muito
  desbalanceadas.

## Conexao

- **Bloqueia**: uso do shaper em qualquer experimento que produza
  evidencia empirica sobre TCF
- **Bloqueia parcialmente**: T-REGRESSION-REAL-WORLD se este usar
  shaper pra amostrar Adult/TPC-H/retail
- **Filosoficamente alinhado a**: filosofia "TCF supoe dados felizes"
  + "gadgets so' alertam" (CLAUDE.md). Aqui o gadget alerta atraves
  de tests verdes — mas tests verdes precisam significar algo.
- **Origem**: workflow paralelo de auditoria 2026-05-30
- **Custo estimado**: 1-2 sessoes (P1 e P2 sao os mais trabalhosos;
  P3-P5 sao curtos)
