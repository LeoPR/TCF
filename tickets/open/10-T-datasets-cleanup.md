---
title: Cleanup — mover retail_sales antigo para poor-reference
type: task
status: OPEN
priority: 9
parent: 01-M-datasets-setup
---

# Cleanup do dataset antigo

## Objetivo

Mover o dataset `retail_sales` sintetico (Ana, Bruno, Caneta) da
posicao "principal" para `datasets/poor-reference/`, deixando claro
que e apenas para comparacao com literatura que usa dados minimalistas.

## O que mover

### Arquivos de dados
- `tests/fixtures/synthetic_v2.py` → **manter aqui** (e usado por tests)
  - Mas adicionar **comentario de topo** explicando que e "poor-reference"
- Nao existe dataset estatico no disco — e tudo gerado runtime

### Referencias na documentacao
- `docs/article/04-methodology.md` — mencoes a `retail_sales`
- `docs/article/07-results.md` — todos os findings atuais (F30-F103)
  sao sobre `retail_sales`

**Decisao:** NAO reescrever a documentacao agora. Os findings atuais
sao **baseline metodologico** — servem de prova de que o pipeline
funciona. Quando rodarmos em TPC-H+Adult, geraremos novos findings
que vao **substituir** ou **complementar** os atuais.

### Manifests antigos
- `experiments/results/etapa1/manifest.jsonl`
- `experiments/results/etapa2/manifest.jsonl`
- `experiments/results/g30_hyperparams/manifest.jsonl`
- `experiments/results/diagnostic_3layer/manifest.jsonl`
- `experiments/results/scale_progression/manifest.jsonl`
- `experiments/results/stats_ablation/manifest.jsonl`

**Decisao:** nao apagar. Estao no `.gitignore` (nunca foram para git).
Ficam na maquina local como historico. Renomear a pasta para
`experiments/results-legacy-retail-sales/` para deixar claro.

## Criar pasta de poor-reference

```
datasets/poor-reference/
├── README.md              # explica o proposito
└── retail-sales-synthetic/
    ├── description.md     # explica os dados
    ├── generator.py       # symlink ou copia de synthetic_v2.py
    └── sample.csv         # amostra para documentacao
```

## Conteudo do README explicativo

```markdown
# Poor Reference Datasets

Esta pasta contem datasets minimalistas usados em papers anteriores
de LLM+Table (incluindo trabalhos preliminares desta pesquisa).

Os dados aqui sao **propositalmente pobres**:
- Nomes genericos (Ana, Bruno, Caneta)
- Estruturas simples (1-3 tabelas)
- Dominios triviais (vendas fakes)

**Por que manter?** Para **comparacao** com papers que usam dados pobres.
Se um paper reporta "TCF 88% em retail sintetico", precisamos poder
reproduzir esse setup para validar.

**Nao usar como baseline principal.** Os baselines reais sao:
- TPC-H SF=0.01 — `datasets/canonical/tpch-sf001/`
- Adult Census — `datasets/canonical/adult-census/`
```

## Tarefas

- [ ] Criar `datasets/poor-reference/README.md`
- [ ] Criar `datasets/poor-reference/retail-sales-synthetic/description.md`
- [ ] Adicionar aviso no topo de `tests/fixtures/synthetic_v2.py`
- [ ] Renomear `experiments/results/` → `experiments/results-legacy-retail/`
  (ficam fora do git mesmo, so renomeia localmente)
- [ ] Atualizar menções em `docs/article/` com notas "[legacy dataset]"
- [ ] Commit: so os README + aviso no synthetic_v2.py

## O que NAO fazer

- **Nao apagar** synthetic_v2.py (e dependencia dos tests que ainda existem)
- **Nao reescrever** os capitulos 05 e 07 do paper (por enquanto)
  — quando tivermos resultados TPC-H+Adult, reescrevemos com dados novos
- **Nao apagar** manifests antigos (podem ser uteis para comparacao)

## Criterio

- `datasets/poor-reference/` existe com README claro
- `synthetic_v2.py` tem aviso de topo
- Ninguem confunde "dataset principal" com "poor reference"
- Historia preservada no git (nao apagamos nada)
