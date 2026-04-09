# TCF -- Textual Columnar Format

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Tests](https://img.shields.io/badge/tests-151%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

Formato de codificacao textual compacto, orientado a colunas, com compressao
RLE, otimizado para raciocinio matematico de LLMs sobre dados tabulares.

## O que e TCF?

TCF codifica tabelas relacionais em texto ASCII compacto, usando Markdown como base:

```
## vendas n=41
id_pessoa: 1 2 1 3 1 5 7 ...
id_produto: 22 33 11 22 44 ...
vl: 2.5 11 1 3.75 2.9 4.5 ...
id_pessoa[sorted]: 3:1 2:2 2:3 1:5 1:7 ...
```

- Cada linha = uma coluna inteira (orientacao columnar)
- `N:val` = val repetido N vezes (RLE)
- `[sorted]` = versao ordenada (revela distribuicao)
- 3-6x menor que JSONL, competitivo com CSV em escala

## Quick Start

```bash
# Instalar
pip install -e .

# Encode: CSV -> TCF
python -m tcf encode --meta data/metadata.json --data-dir data/ --out output.tcf

# Decode: TCF -> CSV
python -m tcf decode output.tcf --out-dir restored/

# Info
python -m tcf info output.tcf
```

## Uso como Biblioteca

```python
from tcf import encode, decode, EncoderConfig

# Encode com configuracao customizada
config = EncoderConfig(
    numeric="raw_float",     # raw_float | int_scaled | bins_16
    fk_mode="inline",        # id_raw | dict | hint | inline
    include_sorted=True,     # colunas ordenadas com RLE
    include_stats=True,      # hints de sum/avg/count para LLMs
)
tcf_text = encode("data/metadata.json", "data/", config=config)

# Decode
tables = decode(tcf_text)
```

## Pipeline de Avaliacao

Harness cientifico para comparar TCF vs CSV vs JSONL com modelos LLM locais (Ollama)
e APIs externas (planejado).

```bash
python -m experiments.eval discover            # Modelos disponiveis
python -m experiments.eval phase0              # Gate: encode/decode OK?
python -m experiments.eval phase1 --models auto  # Formatos x modelos
python -m experiments.eval phase2              # Variantes TCF (ablacao)
python -m experiments.eval status              # Progresso
```

## Testes

```bash
python -m pytest tests/ -v     # 151 testes
```

## Estrutura

```
src/tcf/              Biblioteca (zero deps, pip installable)
experiments/eval/     Pipeline de avaliacao cientifica
tests/                Testes unitarios (151, all passing)
data/                 Dataset de referencia (30 pessoas, 12 produtos, 41 vendas)
docs/                 Documentacao
  ARCHITECTURE.md     Arquitetura e intencoes
  EXPERIMENT_DESIGN.md Metodologia experimental
  TESTS.md            Registro de testes
  article/            Artigo cientifico em capitulos
tickets/              Tickets de pesquisa (G01-G13)
TICKETS.md            Roadmap mestre
```

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura do projeto e do artigo |
| [EXPERIMENT_DESIGN.md](docs/EXPERIMENT_DESIGN.md) | Design experimental em fases |
| [TESTS.md](docs/TESTS.md) | Documentacao de testes por capitulo |
| [Article (capitulos)](docs/article/README.md) | Meta-artigo cientifico completo |
| [tickets/](tickets/README.md) | Roadmap e status de todos os tickets |
| [SOURCE_MAP.md](docs/SOURCE_MAP.md) | Mapa de rastreabilidade entre documentos |

## Dependencias

- **Core:** Python >= 3.10, stdlib only (zero dependencias externas)
- **Dev:** pytest >= 7
- **Eval:** requests >= 2.28 (Ollama client)

## Pergunta de Pesquisa

> Dados compactados em formato columnar baseado em Markdown (TCF) permitem
> que LLMs realizem raciocinio matematico com a mesma ou melhor precisao
> que formatos expandidos (CSV/JSON), usando menos tokens?

## License

MIT License. Ver [pyproject.toml](pyproject.toml).

## Contributing

1. Fork o repositorio
2. Criar branch (`git checkout -b feature/minha-feature`)
3. Rodar testes (`python -m pytest tests/ -v`)
4. Commit e PR

## Autor

Leonardo (2025-2026)
