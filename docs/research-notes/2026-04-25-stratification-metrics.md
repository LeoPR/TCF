---
title: Métricas de representatividade para amostragem estratificada
date: 2026-04-25
type: research-note
status: ATIVO — implementado em scripts/shaper/_stratify_metrics.py
---

# Métricas de representatividade — clássicas e modernas

Estratificação não pode ser apenas "executiva" — precisa ser **mensurada**
com métricas consagradas. Esta nota documenta o que implementamos e por quê.

## O que foi implementado

`scripts/shaper/_stratify_metrics.py` calcula 4 métricas + Wilson CI por grupo
toda vez que estratificação é aplicada. Resultados ficam disponíveis via
`ShapeResult.stratification_metrics()` ou `meta["_stratification_metrics"]`
após `load_dataset()`.

### Métricas implementadas

| Métrica | Range | Tipo | Interpretação |
|---------|-------|------|---------------|
| **TVD** (Total Variation Distance) | [0, 1] | Modern | "Diferença máxima de probabilidade" entre sample e população. TVD=0.05 = sample difere ≤5pp em norma TV. |
| **JSD** (Jensen-Shannon Divergence) | [0, 1] | Modern | Versão simétrica e bounded da KL divergence. Default em ML moderno. |
| **Hellinger** | [0, 1] | Classic | Mais sensível a diferenças nas caudas. Bounded e simétrico. |
| **Chi-square goodness-of-fit p-value** | [0, 1] | Classic | p>0.05: não rejeita H0 (sample=população). Atenção a low N. |
| **Wilson CI por grupo** | proporções | Classic | IC 95% binomial robusto a N pequeno. |

### Por que estas escolhas

**Critérios:**
- **Bounded** (TVD, JSD, Hellinger) — comparáveis entre experimentos sem normalização
- **Symmetric** (todas exceto chi2) — não importa qual é "P" e qual é "Q"
- **Mix de classic + modern** — clássicas têm interpretação estatística sólida; modernas têm uso comum em ML
- **Sem dependência externa** — implementadas em stdlib pura (Python math), respeitando invariante TCF

**Não implementamos:**
- KL divergence (não bounded, asymmetric — JSD é a versão sanitizada)
- Wasserstein (caro de calcular, mais útil para distribuições contínuas)
- MMD (kernel-based, requer escolha de kernel — over-engineering aqui)
- Cramér's V (mais para contingência cruzada do que para sample vs população)

## Validação empírica em Adult Census

Distribuição real: `<=50K`=76.1%, `>50K`=23.9% (n=48 842).

### Caso 1: vol=20, seed=42, stratify_by='class'

```
TVD=0.0107, JSD=0.0001, Hellinger=0.0088, chi2_p=0.9105
warn low N: True (expected count >50K = 4.78 < 5)

<=50K: pop=37155(0.761) -> sample=15(0.750) diff=-1.07pp CI=[0.5312, 0.8882]
>50K:  pop=11687(0.239) -> sample=5 (0.250) diff=+1.07pp CI=[0.1118, 0.4688]
```

**Leitura:** TVD=0.011 → divergência de 1.07pp em norma TV. chi2_p=0.91 →
amostra é estatisticamente consistente com população. Wilson CI mostra
incerteza esperada para N=20.

### Caso 2: random vs stratified, vol=20, 30 seeds

Métrica: % >50K na amostra (target real: 23.9%).

| Modo | Mean | Std | Range |
|------|------|-----|-------|
| Random | 24.2% | 9.7 | 10–45% |
| **Stratified** | **25.0%** | **0.0** | 25–25% |

Stratified reduz variância para zero (proporcional + min-1 garante
distribuição determinística por N).

### Caso 3: Edge case — 16 grupos (`education`), vol=50

```
TVD=0.0808, JSD=0.015, Hellinger=0.1046, chi2_p=0.5534
warn low N: True (16 grupos, expected média ~3 < 5)
```

TVD maior porque com 16 grupos e budget 50, minorias pequenas (1st-4th,
Preschool) ficam sub-representadas em valor absoluto (1 row), embora a
proporção absoluta seja baixa. Trade-off conhecido.

## Como interpretar e quando preocupar

| TVD | Diagnóstico |
|-----|------------|
| < 0.02 | Excelente representatividade |
| 0.02–0.05 | Boa, dentro do erro estatístico esperado |
| 0.05–0.10 | Aceitável; investigar low-N warning |
| > 0.10 | Suspeita; verificar se grupos minoritários estão sendo dropados |

| chi2_p | Diagnóstico |
|-------|------------|
| > 0.10 | Sample consistente com população |
| 0.05–0.10 | Marginal; reportar mas não invalidar |
| < 0.05 | Rejeita H0; sample diverge significativamente |
| Warning low N | Teste não confiável; usar TVD/JSD como referência |

**Wilson CI** mostra a faixa em que a proporção verdadeira pode estar
dado o tamanho da amostra. CI largo (ex: [0.11, 0.47]) sugere N
insuficiente para conclusões fortes — não é falha da estratificação,
é limitação amostral.

## Como usar nos experimentos

### Exemplo: M9 com stratify

```python
from data_sources import load_dataset

tables, meta = load_dataset(
    "canonical:adult-census",
    volume=100, seed=42,
    stratify_by="class",
)

# Métricas para registrar no manifest
strat_metrics = meta.get("_stratification_metrics", [])
for m in strat_metrics:
    record["stratification"] = {
        "by": m["stratify_by"],
        "tvd": m["tvd"],
        "jsd": m["jsd"],
        "chi2_p": m["chi2_pvalue"],
        "warn_low_n": m["chi2_warn_low_n"],
    }
```

Convenção sugerida para manifests futuros:
- Sempre registrar métricas quando `stratify_by` ativo
- Reportar pelo menos TVD + chi2_p + low_N flag
- Wilson CI por grupo opcional (verboso mas auditável)

## Referências

- Wilson 1927 — Probable Inference, the Law of Succession (CI score interval)
- Endres & Schindelin 2003 — A new metric for probability distributions (JSD)
- Cramér 1946 — Mathematical Methods of Statistics (Hellinger)
- Sui et al. 2024 — Table Meets LLM (informalmente cita TVD para sample assessment)

## Status no projeto

- [x] Implementação em `_stratify_metrics.py`
- [x] Integração em `fk_preserving` e `stratify` strategies
- [x] Exposição via `ShapeResult.stratification_metrics()`
- [x] Exposição via `load_dataset` em `meta["_stratification_metrics"]`
- [x] Validado em Adult Census (3 casos)
- [ ] Integrado em manifests M-series com stratify (pendente — quando rodar V1)
