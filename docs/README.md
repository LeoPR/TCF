# TCF — Documentation Hub

Hub central da documentacao do projeto **TCF (Tabular Compact Format)**.

> **Estado 0.7 (`#TCF.7`, pré-1.0 ADR-0024)**: o core e' o algoritmo de
> compressao em duas camadas — **OBAT** (Online Bidirectional Affix
> Tokenizer) + **HCC** (Hierarchical Compositional Coding) — mais as camadas
> V2 multi-col (fallback/dicionario/split/header-minimo) e a view lazy
> read-only (`from tcf import view`). Codigo canonico em
> [`../src/tcf/`](../src/tcf/). Estado vivo: [`../STATUS.md`](../STATUS.md).
>
> Ciclo v0.5 (formato columnar para LLM benchmark) foi arquivado em
> [`archive/`](archive/) — **acessorio** ao core.

## Para entender o algoritmo (core canonico, 0.7)

→ [`algorithms/OBAT.md`](algorithms/OBAT.md) — camada 1: tokenizacao
bidirecional online via LCP + LCS.

→ [`algorithms/HCC.md`](algorithms/HCC.md) — camada 2: compactacao
composicional com operadores `~` (cria ref) e `,` (concat efemero).

→ [`algorithms/TCF-format.md`](algorithms/TCF-format.md) — formato
final, posicionamento na literatura, quando usar TCF vs alternativas.

→ [`algorithms/README.md`](algorithms/README.md) — index das camadas.

## Para entender a evolucao do projeto

→ [`../experiments/lab/dirty/notas/historia-dirty-lab.md`](../experiments/lab/dirty/notas/historia-dirty-lab.md)
— **narrativa canonica M0-M14** do desenvolvimento.

→ [`../experiments/lab/dirty/notas/roadmap-hipoteses.md`](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
— direcoes futuras (pre-tx delta, multi-coluna, escala, etc.).

→ [`../tickets/`](../tickets/) — tickets ativos e fechados.

→ [`../CHANGELOG.md`](../CHANGELOG.md) — releases logicas.

## Material historico v0.5 (acessorio)

→ [`findings/`](findings/) — **Phase 1 LLM benchmark** (Q01-Q38) —
material historico valido. Pode informar Phase 2 se ressuscitada.

→ [`FINDINGS_SUMMARY.md`](FINDINGS_SUMMARY.md) — resumo paper-ready
Phase 1.

→ [`workbench/`](workbench/) — research-notes e contexto de
desenvolvimento (parcialmente v0.6, parcialmente v0.5).

→ [`archive/`](archive/) — material arquivado:
- `manual_v05/` — manual de uso v0.5 (`encode_rows`, `level=2`, etc.)
- `article_v05/` — drafts de paper v0.5
- `theory_components_v05/` — componentes v0.4 (TCF Core, LLM Interface, DB Extractor)
- `theory_architecture_v05/` — arquitetura v0.4 (boundaries, data-pipeline, storage)
- `theory_research_lines_v05/` — Linha A vs B (LLM benchmark)
- `theory_methodology_v05/` — F-findings, llm-research-rigor, model-ranking
- `article_v01/`, `tickets_v01/`, `legacy_results/`, etc. — material legado

**Nenhum conteudo de `archive/` conta como evidencia viva para v0.6
sem re-validacao.**

## Para uso da API

```python
from tcf import encode, decode, view

text = encode({"email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]})
table = decode(text)
v = view(text)              # camada read-only lazy/consultavel
```

Multi-coluna (`#TCF.7 M`) e naturezas pre-tx (CPF/CNPJ/IP) **welded**. Receitas:
[`tutorials/getting-started.md`](tutorials/getting-started.md),
[`how-to/encode-csv-file.md`](how-to/encode-csv-file.md),
[`reference/encode-knobs.md`](reference/encode-knobs.md),
[`reference/lazy-view.md`](reference/lazy-view.md).

## Mapeamento Diataxis (nomes locais → quadrantes canonicos)

TCF usa nomes de pasta proprios em vez dos rotulos canonicos
[Diataxis](https://diataxis.fr/). O mapeamento conceitual:

| Pasta TCF | Diataxis | Foco |
|---|---|---|
| [`tutorials/`](tutorials/) | **Tutorial** | Onboarding mao-na-massa ([getting-started](tutorials/getting-started.md)) |
| [`algorithms/`](algorithms/) | **Reference** | Especificacao canonica (OBAT, HCC, TCF-format) |
| [`theory/`](theory/) | **Explanation** | Fundamentos teoricos, perspectiva tripartite |
| [`how-to/`](how-to/) | **How-to** | Receitas: [encodar CSV](how-to/encode-csv-file.md), [naturezas](how-to/use-natures.md), [inspecionar compressao](how-to/inspect-compression.md) + dev (audit, log) |
| [`adr/`](adr/) | (extra) | Decisoes arquiteturais — complementa Diataxis |
| [`findings/`](findings/) | (extra) | Achados consolidados de pesquisa (research compendium) |
| [`vocabulary.md`](vocabulary.md) | (extra) | Vocabulario controlado |

Esta convencao local sera preservada — renomear quebra muitos links
em ADRs, READMEs, memorias de IA. **Para entrar**: use a tabela acima
pra mapear "preciso de spec → `algorithms/`", "preciso de fundamento
teorico → `theory/`", "preciso de receita → `how-to/`".
