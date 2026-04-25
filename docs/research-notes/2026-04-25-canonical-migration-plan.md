---
title: Plano de migração canonical — refazer M-series sobre dados reais
date: 2026-04-25
type: research-note
status: ROADMAP — implementação progressiva
---

# Plano de migração: M-series synthetic → canonical

## Motivação

Synthetic é controlado mas artificial. Canonical (TPC-H + Adult) é real
mas mais limitado em domínios e parametrização. O paper precisa de
ambos:

- **Canonical como evidência principal** — accuracy/findings em dados
  reais é mais defensável cientificamente
- **Synthetic como controle metodológico** — para ablações de dimensões
  que canonical não permite (N_entities, FK topology, null_rate)

F-Q24 (M9 vs M3) já validou que ambos produzem accuracy equivalente.
Próximo passo: **refazer todos os M-series sobre canonical**, mantendo
synthetic como comparação.

## Status atual (2026-04-25)

| Experimento | Synthetic | Canonical | Achado registrado |
|------------|-----------|-----------|------------------|
| M0 (qualificacao) | ✅ retail | — | F-Q10..F-Q12 |
| M1 (baseline H-TCF2) | ✅ retail | ❌ | F-Q7..F-Q9 |
| M2 (fewshot ablation) | ✅ retail | ❌ | F-Q6 |
| M3 (cross-domain) | ✅ retail/medical/financial | ❌ | F-Q16 |
| M4 (CSV/JSON/TCF) | ✅ 3 domínios | ❌ | F-Q17 |
| M5 (SQL/Pandas/Polars) | ✅ 3 domínios | ❌ | F-Q18 |
| M6 (filter/HAVING) | ✅ 3 domínios | ❌ | F-Q19 |
| M6b (HAVING fix) | ✅ 3 domínios | ❌ | F-Q19b |
| M7 (subquery/CTE) | ✅ 3 domínios | ❌ | F-Q20 |
| M8 (safe-sql isolated) | ✅ 3 domínios | ❌ | F-Q22 |
| M8b (safe-sql combos) | ✅ 3 domínios | ❌ | F-Q23 |
| M9 (TPC-H baseline) | — | ✅ TPC-H | F-Q24 |
| M_inv (invariants) | ✅ post-hoc | ❌ | F-Q21 |

## Plano de migração por experimento

### Tier 1 — Direto (TPC-H 3-tabela ou Adult single-table)

Estes têm tradução natural; mesma topologia:

| M | Adaptação canonical | Esforço | Datasets |
|---|---|---|---|
| M9 (já feito) | TPC-H partsupp/part/supplier | — | TPC-H |
| **M9b** | M9 estendido para Adult Census | ~1h | Adult |
| **M3-canonical** | 7 questions × 3 datasets canônicos | ~3h | TPC-H + Adult + 3º (Northwind/Chinook/Sakila) |
| **M4-canonical** | CSV/JSONL/TCF/TOON em canonical | ~2h | TPC-H + Adult |
| **M6-canonical** | Filter questions adaptadas (WHERE income='>50K' em Adult) | ~3h | TPC-H + Adult |
| **M6b-canonical** | HAVING fix em queries de Adult | ~1h | Adult (single table simplifica) |
| **M7-canonical** | CTE/subquery em Adult e TPC-H | ~3h | TPC-H + Adult |

### Tier 2 — Adaptação não-trivial

| M | Razão | Decisão |
|---|---|---|
| M5 (Pandas/Polars/CoT) | Independente de dataset; só precisa rodar runners em canonical | Migrar — ~2h |
| M8 (safe-sql isolated) | Independente de domínio; aplicar em queries canonical | Migrar — ~2h |
| M8b (safe-sql combos) | Idem M8 | Migrar — ~2h |
| M_inv | Pós-hoc; rodar sobre manifests dos canonical migrados | Trivial após migração |

### Tier 3 — Pode não fazer sentido

| M | Razão |
|---|---|
| M0 qualificação | Já feito uma vez; modelos não dependem de dataset |
| M1 baseline | Subsumido pelo M3-canonical |
| M2 fewshot ablation | Já provou F-Q6; replicar em canonical é redundante |

## Adições novas (não migração — extensão)

### Stratify-aware experiments

Com stratify funcionando (2026-04-25), novos experimentos viáveis:

- **M-strat**: comparar accuracy entre random sampling e stratified sampling
  - Hipótese: stratified mantém accuracy mais estável entre seeds
  - 2 datasets × 2 modos sampling × 5 seeds × 7 questions

- **M-balanced**: forçar balanceamento via stratify_by='class' em Adult
  - Hipótese: classes balanceadas reduzem viés de classe minoritária

### Novos formatos (gap da literatura)

Ver [research-notes/2026-04-25-tabular-formats-literature.md](2026-04-25-tabular-formats-literature.md):

- **M4-extended**: TCF + CSV + JSONL + **TOON** + **Markdown-KV** + **HTML+explanations**
  - 6 formatos × canonical TPC-H × 3 modelos × 5 seeds = 5400 combos? cuidado escala
  - Provavelmente reduzir para 2 modelos × 3 seeds = 540 combos viável

## Ordem de execução proposta

### Fase A — Habilitar canonical (próximas semanas)

1. **M9-Adult** (este turno ou próximo) — extensão de M9 para Adult
   - Definir profile + questions adaptadas
   - Validar GT
   - 7 questions × 3 modelos × 3 seeds = 63 combos (~20 min)
   - Esperado: ~95-100% accuracy (similar a M9-TPCH)

2. **M3-canonical** — cross-domain sobre canonical
   - TPC-H + Adult + 1 dataset adicional (escolher: Northwind, Chinook, ou Sakila)
   - 7 questions × 3 datasets × 3 modelos × 3 seeds = 189 combos
   - **Compara diretamente com F-Q16** (synthetic cross-domain)

3. **M-strat** (novo) — stratify vs random
   - Adult × 2 modos × 5 seeds × 7 questions = 70 combos
   - Reporta TVD/chi2_p por configuração

### Fase B — Ablações em canonical

4. **M4-canonical** — formatos
5. **M5-canonical** — execução intermediária
6. **M6+M6b+M7-canonical** — query complexity

### Fase C — Refinamentos

7. **M8/M8b-canonical** — safe-sql em canonical
8. **M_inv-canonical** — análise post-hoc

### Fase D — Comparações de paper

9. **Synthetic vs canonical side-by-side** — tabela final
10. **Multi-format** (M4-extended com TOON, Markdown-KV, etc.)

## Estimativas de tempo total

| Fase | Engenharia | Compute (LLM local) |
|------|-----------|---------------------|
| A | ~6h | ~3h |
| B | ~10h | ~6h |
| C | ~6h | ~4h |
| D | ~8h | ~10h |
| **Total** | **~30h** | **~23h** |

Spread em 2-3 semanas com paralelismo (LLM rodando em background).

## Política sobre synthetic

Após Fase A validar paridade canonical ≈ synthetic (esperado por F-Q24):

- **Manter synthetic** para:
  - Ablações de dimensões não-canonical (N_entities, null_rate, FK topology)
  - Comparação metodológica explícita no paper ("synthetic gives same answer
    as canonical for our protocol")
  - Quick-iteration durante desenvolvimento

- **Não usar synthetic como evidência principal** no paper:
  - Capítulos de resultado citam canonical como primário
  - Synthetic vai como "Methodological validation" ou apêndice

## Manifest schema mudará

A partir do M9-Adult e seguintes, manifests devem incluir métricas de
representatividade quando stratify ativo. Schema sugerido:

```json
{
  "key": "...",
  "phase": "m9_adult",
  ...
  "dataset": "adult-census",
  "volume": 100,
  "stratify_by": "class",
  "stratification_metrics": {
    "tvd": 0.0107,
    "jsd": 0.0001,
    "hellinger": 0.0088,
    "chi2_pvalue": 0.9105,
    "chi2_warn_low_n": true,
    "n_groups": 2
  },
  ...
}
```

Isto permite análise post-hoc de "amostragem influencia accuracy?".

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Adult tem distribuição muito desbalanceada (76/24) — accuracy pode parecer alta apenas por baseline | Reportar accuracy condicionada por classe; chi2 controlando |
| TPC-H é muito sintético (gerado, não dados reais reais) | Adicionar 3º canonical (Northwind = dataset real de produção) |
| Esforço de migração competindo com paper writing | Fazer Fase A antes do paper; demais durante refinamento |
| Manifests novos não comparam direto com antigos | Manter comparação por question type; F-Q references |

## Próxima ação

**M9-Adult** — implementar profile + questions específicas de Adult
Census, validar com runner adaptado. Deve produzir accuracy similar
a M9 TPC-H (~95-100% com tie-aware).
