# TCF -- Mapa de Fontes (Source of Truth)

Este arquivo define **qual documento e a fonte primaria** de cada tipo de informacao.
Quando um dado muda, a fonte primaria e atualizada primeiro, e os outros documentos
**referenciam** a fonte ao inves de duplicar o valor.

## Principio

```
Fonte Primaria (1 arquivo)  →  Referenciado por N arquivos
Se o dado muda             →  Atualizar APENAS a fonte
Outros arquivos            →  Referenciam a fonte, nao copiam o valor
```

**Se um arquivo precisa mostrar um numero (ex: "TCF 67%"), deve indicar a fonte:**
> TCF accuracy com dict mode: 67% (fonte: [06-results-e3.md](article/06-results-e3.md))

---

## Mapa de Fontes por Tipo de Dado

### Resultados Experimentais (numeros, tabelas, accuracy)

| Dado | Fonte Primaria | Quem Referencia |
|------|---------------|-----------------|
| Phase 0 reversibility | [05-results-e1-e2.md](article/05-results-e1-e2.md) | tickets/README.md |
| Compression benchmark (C1-C5) | [05-results-e1-e2.md](article/05-results-e1-e2.md) | tickets/README.md |
| Phase 1 results (F1-F7) | [06-results-e3.md](article/06-results-e3.md) | tickets/README.md (status apenas) |
| Phase 2 ablation (F8-F11) | [07-results-e4-e8.md](article/07-results-e4-e8.md) | tickets/README.md (status apenas) |
| G04 stats ablation (F12-F14) | [07-results-e4-e8.md](article/07-results-e4-e8.md) | tickets/README.md (status apenas) |
| Dados brutos (JSONL) | `experiments/results/phaseN/` | Capitulos de resultados |

### Estrutura e Intencoes

| Dado | Fonte Primaria | Quem Referencia |
|------|---------------|-----------------|
| Arquitetura de software | [ARCHITECTURE.md](ARCHITECTURE.md) | README.md (resumo) |
| Design experimental (fases) | [EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md) | ARCHITECTURE.md, article/04 |
| Testes unitarios (fixtures, coverage) | [TESTS.md](TESTS.md) | tickets/README.md (contagem) |
| Roadmap e status | [tickets/README.md](../tickets/README.md) | README.md (resumo) |

### Artigo Cientifico

| Dado | Fonte Primaria | Quem Referencia |
|------|---------------|-----------------|
| Inovacoes comprovadas (I1-I12) | [00-innovations.md](article/00-innovations.md) | Capitulos 1, 3, 8, 9 |
| Related work e referencias | [02-related-work.md](article/02-related-work.md) | Cap 1 (intro) |
| Formato TCF (spec) | [03-tcf-format.md](article/03-tcf-format.md) | ARCHITECTURE.md, appendix A |
| Metodologia | [04-methodology.md](article/04-methodology.md) | EXPERIMENT_DESIGN.md |
| Findings (F1-F14) | Cap 5-7 (onde sao descobertos) | 00-innovations.md, cap 8 |
| Conclusions (C1-C5) | [05-results-e1-e2.md](article/05-results-e1-e2.md) | 00-innovations.md |

### Codigo e Configuracao

| Dado | Fonte Primaria | Quem Referencia |
|------|---------------|-----------------|
| EncoderConfig (variantes) | `src/tcf/encoder.py` | ARCHITECTURE.md, article/03 |
| Perguntas (Q1-Q10) | `experiments/eval/llm_eval/prompts.py` | article/04-methodology.md |
| Ground truth | `experiments/eval/llm_eval/ground_truth.py` | article/04-methodology.md |
| System prompts | `experiments/eval/llm_eval/prompts.py` | appendix B |

---

## Hierarquia de Documentos

```
README.md                    Porta de entrada (links para tudo)
  │
  ├── docs/ARCHITECTURE.md   Pilar conceitual (intencoes, NUNCA resultados)
  │     └── refs: EXPERIMENT_DESIGN, encoder.py, prompts.py
  │
  ├── docs/EXPERIMENT_DESIGN.md   Metodologia (fases, criterios)
  │     └── refs: prompts.py, ground_truth.py
  │
  ├── docs/TESTS.md          Registro de testes (fixtures, coverage)
  │     └── refs: test_g01_*, fixtures/
  │
  ├── docs/SOURCE_MAP.md     ESTE ARQUIVO (mapa de rastreabilidade)
  │
  ├── docs/article/          Artigo cientifico (RESULTADOS aqui)
  │     ├── 00-innovations.md   Inovacoes comprovadas (I-series)
  │     ├── 01-09              Capitulos do artigo
  │     │     └── refs: dados em experiments/results/
  │     └── appendices/        Material de suporte
  │
  ├── tickets/README.md             Roadmap operacional (status, nao dados)
  │     └── refs: cada G/H/P ticket aponta para secao do artigo
  │
  └── experiments/results/   Dados brutos (fonte ultima)
        ├── phase0/          reversibility.json
        ├── phase1/          manifest.jsonl, summary.json, survivors.json
        ├── phase2/          manifest.jsonl, ablation.json, top_configs.json
        └── g04_stats/       manifest.jsonl, summary.json
```

---

## Regras de Propagacao

### Quando um resultado muda (ex: re-rodar Phase 1)

1. Dados brutos atualizam automaticamente (`experiments/results/phase1/`)
2. Rodar `analyze_phase1.py` → atualiza `summary.json`
3. Atualizar **fonte primaria**: `docs/article/06-results-e3.md` (tabelas, findings)
4. `tickets/README.md`: atualizar apenas STATUS (ex: "JSONL 63%" no resumo)
5. `00-innovations.md`: atualizar se muda uma inovacao comprovada
6. NAO atualizar ARCHITECTURE.md (nunca tem resultados)

### Quando um experimento novo completa

1. Dados gravados em `experiments/results/gNN_*/`
2. Criar/atualizar capitulo correspondente em `docs/article/07-results-e4-e8.md`
3. Se inovacao comprovada: adicionar em `00-innovations.md`
4. Atualizar tickets/README.md: marcar grupo como CLOSED + resumo 1 linha
5. NAO duplicar tabelas de dados em ARCHITECTURE.md ou README.md

### Quando a arquitetura muda

1. Atualizar `docs/ARCHITECTURE.md` (fonte primaria)
2. Se muda CLI: atualizar README.md (quick start)
3. Se muda pipeline: atualizar EXPERIMENT_DESIGN.md
4. NAO colocar detalhes de implementacao nos capitulos do artigo

---

## Referencia Cruzada: Findings (F-series)

| Finding | Definido em | Referenciado por |
|---------|------------|-----------------|
| F1-F7 | article/06-results-e3.md | 00-innovations, 02-related-work, 04-methodology, 08-discussion |
| F8-F11 | article/07-results-e4-e8.md | 00-innovations |
| F12-F14 | article/07-results-e4-e8.md | 00-innovations |

## Referencia Cruzada: Conclusions (C-series)

| Conclusion | Definido em | Referenciado por |
|------------|------------|-----------------|
| C1-C5 | article/05-results-e1-e2.md | 00-innovations |

## Referencia Cruzada: Innovations (I-series)

| Innovation | Definido em | Comprovado por |
|------------|------------|----------------|
| I1-I5 | article/00-innovations.md | Caps 5-7 (dados) |
| I6-I12 | article/00-innovations.md | Pendente |
