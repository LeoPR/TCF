# TCF — Textual Columnar Format

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Tests](https://img.shields.io/badge/tests-112%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.2.0-orange)

Formato de serializacao textual **orientado a colunas** com compressao RLE,
desenhado para raciocinio de LLMs sobre dados tabulares.

TCF e, ate onde sabemos, o **primeiro formato columnar textual com compressao
proposto para LLMs**, e o **primeiro a embutir hints meta-cognitivos** (STATS)
que compensam limitacoes aritmeticas dos modelos.

## A historia em tres atos

### Ato 1 — O problema de compressao

Tabelas relacionais transmitidas como texto ficam grandes rapidamente.
CSV row-oriented repete colunas de alta cardinalidade a cada linha.
Com 500 linhas e 5 colunas, isso e ineficiente.

TCF resolve isso com orientacao **columnar + RLE textual**:

```
# TCF v0.2 level=2
## vendas n=509 sorted_by=pessoa
# STATS total: n=509 sum=147445.47 min=9.01 max=759.8 avg=289.68
pessoa:
8*Ana
12*Bruno
15*Carla
...
produto:
Caneta
3*Lapis
...
```

- `N*val` = val repetido N vezes (RLE legivel por humanos e LLMs)
- Colunas de baixa cardinalidade comprimem 40-65% vs CSV
- Schema (tipos, FK, stats) esta sempre no topo — visivel de imediato

### Ato 2 — O problema de LLM sobre dados tabulares

LLMs falham em aritmetica direta sobre dados tabulares: calcular uma soma
ou media lendo o CSV linha a linha produz ~40% de acuracia (erros de
truncamento, contagem errada, alucinacao de valores).

TCF resolve parte disso com **STATS hints** — estatisticas pre-computadas
que o LLM usa como atalho em vez de recalcular.

### Ato 3 — A descoberta: TCF como schema carrier para SQL (H-TCF2)

A descoberta mais importante nao foi prevista originalmente:

> Quando TCF e usado como **portador de schema** (nao dos dados),
> e o LLM gera SQL que o SQLite executa, a acuracia sobe para **96%+**.
> Isso funciona em 3 dominios, 3 modelos, 5 seeds e 10+ tipos de query.

O SQLite executa SQL com precisao exata — sem erros aritmeticos.
TCF fornece o schema (tabelas, colunas, FK, cardinalidades) em formato
compacto que cabe facilmente no contexto do LLM.

**Isso significa:** TCF nao e so formato de serializacao. E um vetor de
raciocinio estruturado que habilita modelos locais de 7-14B a responderem
perguntas de BI com acuracia de 96%+.

Ver [docs/FINDINGS_SUMMARY.md](docs/FINDINGS_SUMMARY.md) para os achados
principais, ou [docs/article/](docs/article/) para o artigo completo.

## Quick Start

```bash
# Instalar em modo editavel
pip install -e .

# Encode CSV -> TCF (levels 0, 1, 2, 3)
python -m tcf encode --meta data/metadata.json --data-dir data/ --level 2 --out output.tcf

# Decode TCF -> CSV
python -m tcf decode output.tcf --out-dir restored/

# Info sobre um arquivo TCF
python -m tcf info output.tcf
```

## Uso como Biblioteca

```python
from tcf import encode, decode, EncodeConfig

# Encode com configuracao
config = EncodeConfig(
    level=2,              # 0=expanded, 1=rle, 2=sorted+rle, 3=dict+sorted+rle
    include_stats=True,   # STATS hints (recomendado para LLMs)
    precision=None,       # casas decimais (None = auto)
)
tcf_text = encode("data/metadata.json", "data/", config=config)

# Decode (auto-detecta o nivel)
tables = decode(tcf_text, normalize=True)
```

## Niveis de Compressao

| Level | Descricao | Tamanho tipico | Uso recomendado |
|-------|-----------|----------------|-----------------|
| **L0** | Expanded (1 valor por linha) | Similar a CSV | Maxima legibilidade LLM |
| **L1** | RLE em runs naturais | 5-15% menor | Quando ordem importa |
| **L2** | Sort + RLE | 20-30% menor | Default, melhor tradeoff |
| **L3** | Dict + sort + RLE | 40-65% menor | Transporte + storage |

## Testes

```bash
python -m pytest tests/ -v
# 112 passed in ~15s
```

- Roundtrip (encode→decode) para todos os 4 niveis
- 12 cenarios sinteticos (retail, logs, survey, unique)
- Benchmark de compressao
- Infra (metrics, ground truth, parsers)

## Estrutura do Projeto

```
src/tcf/                    # Biblioteca (zero deps externas)
  encoder.py                # 4 niveis de compressao
  decoder.py                # Auto-deteccao de nivel
  compression.py            # RLE, dict, sort
  schema.py                 # Parser de metadata.json
  cli.py                    # CLI: encode, decode, info

experiments/eval/           # Pipeline de avaliacao cientifica M-series (Ollama)
  run_m1_codegen.py         # M1: schema carrier baseline (H-TCF2)
  run_m2_codegen.py         # M2: fewshot ablation + scale invariance
  run_m3_cross_domain.py    # M3: generalizacao cross-domain
  run_m4_baseline.py        # M4: CSV vs JSON vs TCF
  run_m5_intermediate.py    # M5: SQL vs Pandas vs Polars vs CoT
  run_m6_filter_questions.py # M6: WHERE/HAVING/GROUP-BY
  run_m6b_having_fix.py     # M6b: fix HAVING subquery fewshot
  run_m7_complex_queries.py # M7: subquery/CTE/COUNT DISTINCT
  analyze_results.py        # Analise unificada de qualquer manifest

tests/                      # 112 testes deterministicos
tests/fixtures/             # Geradores sinteticos (retail, logs, survey)

docs/                       # Hub de documentacao — "a Meca"
  README.md                 # Indice geral
  architecture/             # Arquitetura do projeto (overview, storage, telemetry)
  datasets/                 # Manuais por dataset
  methodology/              # Design experimental e testes
  article/                  # Artigo cientifico em capitulos
  research-notes/           # Pesquisas datadas
  reference/                # Glossarios e referencias rapidas

tickets/                    # Tickets de pesquisa (rastreabilidade)
  open/                     # Fase atual (numerados por prioridade)
  frozen/                   # Futuro trabalho (congelados)
  closed/                   # Concluidos + findings

config/                     # Configs locais (gitignored)
  storage.json.example      # template
```

## Dependencias

- **Core:** Python >= 3.10, **stdlib only** (zero dependencias externas)
- **Dev:** pytest >= 7
- **Eval (opcional):** requests >= 2.28 (Ollama client)

## Questoes de Pesquisa

- **RQ1:** TCF como schema carrier + SQL execution supera leitura direta de dados?
- **RQ2:** O ganho de acuracia e robusto a mudancas de dominio, modelo e escala?
- **RQ3:** Qual nivel de complexidade de SQL os modelos locais conseguem gerar corretamente?
- **RQ4:** TCF eficiente em tokens — qual nivel de compressao preserva acuracia?
- **RQ5:** Como o sistema se compara a modelos comerciais (Claude, GPT-4o)?

Ver [docs/article/01-introduction.md](docs/article/01-introduction.md)
para discussao completa.

## Documentacao

Toda a documentacao vive em **[docs/](docs/README.md)** — o hub central.

**Atalhos rapidos:**
- [docs/FINDINGS_SUMMARY.md](docs/FINDINGS_SUMMARY.md) — achados principais (A1-A6)
- [docs/methodology/model-ranking.md](docs/methodology/model-ranking.md) — ranking modelos locais (accuracy, latencia, failure modes)
- [docs/methodology/F-findings.md](docs/methodology/F-findings.md) — catalogo canonico de achados (F-Q1..F-Q21+)
- [docs/methodology/experimental-design.md](docs/methodology/experimental-design.md) — status M-series
- [docs/research-notes/INDEX.md](docs/research-notes/INDEX.md) — indice de notas de pesquisa
- [docs/article/README.md](docs/article/README.md) — artigo cientifico em capitulos
- [docs/README.md](docs/README.md) — hub de documentacao
- [tickets/README.md](tickets/README.md) — roadmap

## Status do Projeto

**Versao:** 0.2.0 (encoder estavel, serie de experimentos M1-M7 em andamento)

**Achados principais (resumo — ver [docs/FINDINGS_SUMMARY.md](docs/FINDINGS_SUMMARY.md)):**
- **A1:** H-TCF2 confirmada — schema carrier + SQL = 96%+ em perguntas de BI
- **A2:** Fewshot e obrigatorio (0% sem → 96%+ com 1 exemplo)
- **A3:** TCF ≈ JSON > CSV para SQL generation (96.8% vs 96.3% vs 93.7%)
- **A4:** SQL >> Pandas >> Polars; CoT-SQL nao melhora (custa 2.4× mais)
- **A5:** HAVING (2-level aggregation) = falha universal 93% (modelos locais 7-14B)
- **A6:** Generalizacao cross-domain confirmada (retail, medical, financial)

## Contribuindo

Contribuicoes sao bem-vindas. Por favor:

1. Fork o repositorio
2. Criar branch (`git checkout -b feature/minha-feature`)
3. Rodar testes (`python -m pytest tests/ -v`) — todos devem passar
4. Commit com mensagem descritiva
5. Abrir Pull Request

## License

MIT License. Livre para uso, modificacao e distribuicao, desde que mantendo
o aviso de copyright. Ver [LICENSE](LICENSE).

## Citacao

Se este projeto for util para seu trabalho, considere citar:

```bibtex
@software{souza2026tcf,
  author = {Souza, Leonardo Marques},
  title = {TCF: Textual Columnar Format for LLM Reasoning over Tabular Data},
  year = {2026},
  url = {https://github.com/<usuario>/tcf}
}
```

(URL sera atualizada apos publicacao do repo)

## Autor

Leonardo Marques Souza — 2026
