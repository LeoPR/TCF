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

## O que e TCF

TCF codifica tabelas relacionais em texto ASCII compacto usando Markdown como base:

```
# TCF v0.2 level=2
# N*val = val repeated N times

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
Borracha
...
total:
2.5
11.0
1.0
...
```

- **Orientacao columnar:** todos os valores de uma coluna agrupados
- **RLE textual:** `N*val` = val repetido N vezes (legivel por humanos e LLMs)
- **STATS opcionais:** hints pre-computados que LLMs usam como atalho
- **4 niveis de compressao:** L0 (expanded) → L3 (dict + sorted + RLE)
- **100% reversivel:** encode → decode produz os mesmos dados (112 testes)

## Descoberta principal

Experimentos com 12 modelos LLM open (Ollama) revelaram que TCF e mais
eficaz que CSV/JSONL **porque combina** formato columnar compacto +
hints meta-cognitivos. Sem os STATS, accuracy cai 25-62pp.

> **TCF e uma ESTRATEGIA COMPOSTA:**
> formato columnar + hints que compensam limitacoes aritmeticas dos LLMs.

Ver [docs/article/](docs/article/) para o artigo cientifico completo
(v0.2, em andamento).

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

experiments/eval/           # Pipeline de avaliacao cientifica (Ollama)
  run_etapa1.py             # Formato x escala
  run_etapa2.py             # Multiplos modelos
  run_diagnostic_3layer.py  # Diagnostico aritmetica vs formato vs compute
  run_stats_ablation.py     # Quantifica o impacto dos STATS hints
  run_scale_progression.py  # Accuracy vs numero de linhas
  run_transport_compression.py  # TCF+gzip vs CSV+gzip

tests/                      # 112 testes deterministicos
tests/fixtures/             # Geradores sinteticos (retail, logs, survey)

docs/
  ARCHITECTURE.md           # Arquitetura do projeto
  SOURCE_MAP.md             # Rastreabilidade entre documentos
  article/                  # Artigo cientifico em capitulos

tickets/                    # Tickets de pesquisa (rastreabilidade)
  open/                     # Em andamento
  closed/                   # Concluidos + findings
```

## Dependencias

- **Core:** Python >= 3.10, **stdlib only** (zero dependencias externas)
- **Dev:** pytest >= 7
- **Eval (opcional):** requests >= 2.28 (Ollama client)

## Questoes de Pesquisa

- **RQ1:** Um formato columnar textual comprime mais que row-oriented?
- **RQ2:** LLMs interpretam formato columnar com accuracy similar ou superior?
- **RQ3:** Hints pre-computados (STATS) melhoram accuracy? Quanto?
- **RQ4:** A capacidade aritmetica dos modelos e o gargalo, ou e o formato?
- **RQ5:** Como accuracy escala com o tamanho do dataset?

Ver [docs/article/01-introduction.md](docs/article/01-introduction.md)
para discussao completa.

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura do projeto |
| [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md) | Rastreabilidade entre documentos |
| [docs/article/README.md](docs/article/README.md) | Meta-artigo cientifico |
| [docs/article/00-innovations.md](docs/article/00-innovations.md) | Inovacoes comprovadas (I1-I7) |
| [tickets/README.md](tickets/README.md) | Roadmap e status de experimentos |

## Status do Projeto

**Versao:** 0.2.0 (em desenvolvimento — encoder estavel, artigo em redacao)

**Findings principais (v0.2):**
- F30-F34: TCF escala, CSV/JSONL colapsam em > 200 rows
- F70-F73: TCF+gzip 29% menor que CSV+gzip em 5000 rows
- **F80-F84:** Diagnostic 3-layer revela que modelos usam STATS como atalho
- F85-F89: Sweet spot de accuracy em 100-200 rows
- **F90-F94:** STATS inflam accuracy em TODOS os modelos (25-62pp)

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
