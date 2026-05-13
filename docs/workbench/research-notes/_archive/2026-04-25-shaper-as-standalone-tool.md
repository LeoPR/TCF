---
title: Shaper como ferramenta independente — extração estratificada de datasets
date: 2026-04-25
type: research-note
status: HIPÓTESE / IDEIA — investigar viabilidade
---

# Shaper como ferramenta independente

## Contexto

`scripts/shaper/` foi construído dentro do projeto TCF para alimentar
experimentos M-series com subsets controlados de datasets canônicos
(TPC-H, Adult Census). Em 2026-04-25 (Etapa 2 da unificação), o Shaper
ganhou a estratégia `fk_preserving` e passou a ser o único caminho para
dados canônicos via `experiments/eval/data_sources.py`.

**Observação:** o Shaper foi projetado **sem dependências de TCF**. As
estratégias operam sobre `dict[table, list[dict]]` genérico; o
DatasetReader é input opcional; ShapeRequest é dataclass pura.

Isto sugere que o Shaper pode ser **extraído como biblioteca standalone**
e republicado para uso em qualquer projeto de ML/LLM sobre dados tabulares.

## O que o Shaper resolve

Problema: ao testar pipelines ML/LLM em datasets reais, precisamos de
**subsets reproduzíveis e parametrizáveis** com:
- Volume controlado (N rows ou fração)
- Schema controlado (subset de tabelas)
- Integridade FK preservada (multi-tabela)
- Ordering reproduzível (random com seed, sorted, natural)
- Stratificação por chave (classes balanceadas)
- Seleção por compressibilidade (alta/baixa cardinalidade)

A biblioteca atual de ferramentas Python (pandas, sklearn) não tem
abstração comparável. Cada projeto reinventa o sampling.

## Estado atual (in-tree)

Estrutura:
```
scripts/shaper/
├── request.py          # ShapeRequest (dataclass declarativa)
├── pipeline.py         # Shaper().apply(req) executa estratégias em ordem
├── result.py           # ShapeResult (tables + metadata + trace + stats)
└── strategies/
    ├── schema.py            # filtra tabelas
    ├── join.py              # placeholder
    ├── compressibility.py   # placeholder
    ├── stratify.py          # placeholder
    ├── fk_preserving.py     # FK-aware sampling (2026-04-25)
    ├── volume.py            # samples N rows
    └── ordering.py          # natural/random/sorted
```

Dependências externas: **zero** (apenas stdlib + DatasetReader que é
opcional). DatasetReader pode ser substituído por qualquer cliente que
forneça `rows(table_name)`.

## O que falta para standalone

### Trabalho técnico
1. **Abstrair o reader** — atual pipeline.py importa DatasetReader
   diretamente. Refatorar para receber qualquer objeto que implemente
   um protocolo `TableReader` (ABC com `tables`, `rows`, `metadata`)
2. **Implementar estratégias placeholder** — `compressibility`, `stratify`,
   `join` estão como no-ops; precisariam ser implementadas
3. **Tests independentes** — criar suite de testes que não dependa de
   `Z:/tcf-data/` nem de TPC-H/Adult Census
4. **Adapters de input** — provedores para Postgres, CSV files, Parquet,
   Pandas DataFrame
5. **API documentada** — README, exemplos, type hints completos
6. **Empacotamento** — `pyproject.toml` separado, `pip install`

### Trabalho de validação
- Rodar Shaper em 3-5 datasets externos diferentes para validar generalização
- Benchmark contra alternativas (random.sample, sklearn.train_test_split em
  modos multi-tabela)

## Por que isso pode ser interessante

**Para a comunidade ML/LLM:**
- Sampling FK-aware é problema recorrente em benchmarks de text-to-SQL
- Não há ferramenta dedicada — todo projeto faz inline
- Shaper é dataset-agnostic; pode atender vários casos de uso

**Para o projeto TCF:**
- Citação no paper como "ferramenta auxiliar publicada"
- Contribuição open-source independente (separada do paper TCF principal)
- Reduz acoplamento — TCF não precisa carregar o framework

**Riscos:**
- Manutenção paralela (outro projeto para cuidar)
- Pode atrasar TCF principal
- Mercado não-claro (pode ser pequeno demais para justificar)

## Como decidir

Critérios para extrair:
1. Pelo menos 2 estratégias placeholder (compressibility, stratify) devem
   ser implementadas e validadas — caso contrário, biblioteca está
   incompleta para release
2. Shaper precisa ter sido usado em pelo menos 2-3 projetos internos
   diferentes (não só M9) — para validar a abstração
3. Tempo estimado de extração: ~2 semanas (refatoração + testes + docs +
   empacotamento)

**Decisão atual:** **adiar**. Foco do projeto é o paper TCF + finalização
da unificação. Reavaliar pós-paper.

## Próximos passos práticos

Curto prazo (no projeto TCF):
- Implementar `stratify` quando experimento ablacional o exigir
- Implementar `compressibility` quando precisarmos isolar efeitos de RLE
- Documentar API em `docs/architecture/data-pipeline.md` (já feito)

Médio prazo (pós-paper):
- Avaliar viabilidade de extração com base em uso real
- Preparar repositório separado se decisão for positiva

## Referências internas

- [data-pipeline.md](../architecture/data-pipeline.md) — uso atual do Shaper
- [F-Q24](../methodology/F-findings.md) — M9 validou FK-preserving sampling
- `scripts/shaper/strategies/fk_preserving.py` — implementação core
