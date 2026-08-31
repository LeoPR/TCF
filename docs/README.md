# TCF: o manual

Documentação do **TCF (Tabular Compact Format)**, um formato tabular textual e lossless: o
resultado comprimido continua sendo texto que você abre e lê.

> **Estado 0.8 (`#TCF.8`, pré-1.0 ADR-0032)**: o core combina dois mecanismos de compressão,
> **OBAT** (Online Bidirectional Affix Tokenizer) e **HCC** (Hierarchical Compositional
> Coding), com fallback, dicionário, split estrutural, cabeçalho compacto e uma consulta
> somente leitura (`view`). Código canônico em [`../src/tcf/`](../src/tcf/). Estado vivo:
> [`../STATUS.md`](../STATUS.md).

## Comece aqui

1. **[Tutorial: getting started](tutorials/getting-started.md)** ([pt-BR](tutorials/getting-started.pt-BR.md)).
   Cinco passos, do `pip install` até consultar sem descomprimir. É a porta de entrada.
2. **[Guia curto](../README.pypi.md)**, se você só quer o `encode`/`decode` em uma tela.
3. **[As receitas](how-to/)**, quando você já sabe usar e tem uma tarefa: encodar um CSV,
   ligar as naturezas, inspecionar a compressão, obter o comportamento de pandas, SQL ou polars.
4. **[A referência](reference/)**, para consultar o contrato de uma chamada específica.

Em uma tela, o mínimo:

```python
from tcf import encode, decode, view

text = encode({"email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]})
table = decode(text)        # round-trip exato
v = view(text)              # consulta sem descomprimir
```

## Os capítulos

| capítulo | o que ele responde |
|---|---|
| [`tutorials/`](tutorials/) | *nunca usei o TCF*: o primeiro contato, em linha reta |
| [`how-to/`](how-to/) | *tenho uma tarefa*: uma receita por pergunta, com o custo medido |
| [`reference/`](reference/) | *qual é o contrato desta chamada*: [api](reference/api.md), [knobs do encode](reference/encode-knobs.md), [view lazy](reference/lazy-view.md), [equivalência com JSON](reference/json-equivalence.md), [família bN](reference/familia-bn-bits.md) |
| [`algorithms/`](algorithms/) | *como o formato é por dentro*: [OBAT](algorithms/OBAT.md) (camada 1), [HCC](algorithms/HCC.md) (camada 2), [o formato](algorithms/TCF-format.md) |
| [`theory/`](theory/) | *por que é assim*: os fundamentos, agrupados por assunto |
| [`adr/`](adr/) | *quem decidiu, e com que argumento*: as decisões arquiteturais |
| [`vocabulary.md`](vocabulary.md) | *que palavra usar*: o vocabulário controlado |

## Para entender a evolução do projeto

→ [`historia-dirty-lab.md`](../experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md):
a narrativa canônica M0-M14 do desenvolvimento.

→ [`roadmap-hipoteses.md`](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md):
as direções futuras registradas.

→ [`../tickets/`](../tickets/): os tickets ativos e fechados, com o estado em
[`../tickets/ESTADO.md`](../tickets/ESTADO.md).

→ [`../CHANGELOG.md`](../CHANGELOG.md): as releases.

→ [`../CONTRIBUTING.md`](../CONTRIBUTING.md): para quem vai mexer no TCF, e não usá-lo.

## Material histórico v0.5 (acessório)

→ [`findings/`](findings/): **Phase 1 do LLM benchmark** (Q01-Q38), material histórico
válido. Pode informar uma Phase 2, se ressuscitada.

→ [`FINDINGS_SUMMARY.md`](FINDINGS_SUMMARY.md): o resumo paper-ready da Phase 1.

→ [`workbench/`](workbench/): research-notes e contexto de desenvolvimento (parcialmente
v0.6, parcialmente v0.5).

→ [`archive/`](archive/), material arquivado:
- `manual_v05/`: manual de uso v0.5 (`encode_rows`, `level=2`, etc.)
- `article_v05/`: drafts de paper v0.5
- `theory_components_v05/`: componentes v0.4 (TCF Core, LLM Interface, DB Extractor)
- `theory_architecture_v05/`: arquitetura v0.4 (boundaries, data-pipeline, storage)
- `theory_research_lines_v05/`: Linha A contra Linha B (LLM benchmark)
- `theory_methodology_v05/`: F-findings, llm-research-rigor, model-ranking
- `article_v01/`, `tickets_v01/`, `legacy_results/`: material legado

**Nenhum conteúdo de `archive/` conta como evidência viva para o 0.8 sem re-validação.**

## Mapeamento Diataxis (nomes locais → quadrantes canônicos)

O TCF usa nomes de pasta próprios em vez dos rótulos canônicos da
[Diataxis](https://diataxis.fr/), por decisão registrada no
[ADR-0012](adr/0012-diataxis-naming-local.md). O mapeamento:

| pasta TCF | Diataxis |
|---|---|
| [`tutorials/`](tutorials/) | **Tutorial** |
| [`how-to/`](how-to/) | **How-to** |
| [`reference/`](reference/) e [`algorithms/`](algorithms/) | **Reference** |
| [`theory/`](theory/) | **Explanation** (não existe `explanation/`, e isso é deliberado) |
| [`adr/`](adr/), [`findings/`](findings/), [`vocabulary.md`](vocabulary.md) | (extra) |

A convenção local será preservada: renomear quebraria muitos links em ADRs, READMEs e
notas. Para entrar, use a tabela dos capítulos acima.
