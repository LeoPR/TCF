# TCF -- Arquitetura do Projeto

## 1. Visao Geral

**TCF (Textual Columnar Format)** e um formato de codificacao textual compacto,
orientado a colunas, com compressao RLE, para raciocinio de LLMs sobre dados tabulares.

TCF e construido sobre **Markdown** — formato no qual LLMs foram massivamente treinadas.
A compactacao usa tecnicas de bancos colunares adaptadas para texto legivel:
- **Orientacao colunar** (todos os valores de um campo agrupados)
- **RLE** para repeticoes (`N*val` = val repetido N vezes)
- **Ordenacao** por coluna de maior repeticao (maximiza RLE)
- **Dictionary encoding** opcional (strings → indices curtos)

### Pergunta Central

> Dados compactados em formato columnar baseado em Markdown permitem
> que LLMs realizem raciocinio matematico com a mesma ou melhor precisao
> que formatos expandidos (CSV/JSON), usando menos tokens?

### Objetivo Final

1. **Biblioteca `tcf`** — encoder/decoder via `pip install tcf`
2. **Artigo cientifico** — evidencia experimental comparando formatos
3. **Guia de uso** — como usar TCF para alimentar LLMs com dados tabulares
4. **Pipeline reproduzivel** — Ollama local + APIs externas (OpenAI, Claude, Gemini)

---

## 2. Estrutura do Repositorio

```
TCF/
├── src/tcf/                 Biblioteca (encode, decode, EncodeConfig)
│   ├── encoder.py           Encoder com 4 niveis de compressao
│   ├── decoder.py           Decoder (auto-detecta nivel)
│   ├── compression.py       Primitivas: RLE, dict, sort
│   ├── schema.py            Parser de metadata.json
│   └── cli.py               CLI: encode, decode, info
│
├── experiments/eval/        Pipeline de avaliacao (Ollama)
│   ├── run_etapa1.py        Etapa 1: formato x escala (modelo fixo)
│   ├── run_etapa2.py        Etapa 2: modelos x formato (dados fixos)
│   ├── run_g30_*.py         Hiperparametros (thinking, temperature)
│   └── llm_eval/            Modulos: client, formats, metrics, prompts
│
├── tests/                   Testes (112 passando)
│   ├── test_encode_decode.py       Roundtrip levels 0-3 + CLI
│   ├── test_compression_benchmark.py  12 cenarios sinteticos
│   └── fixtures/            Dados: referencia (L0-L6) + sinteticos v2
│
├── data/                    Dataset de referencia (30+12+41)
├── docs/                    Documentacao (ver secao 5)
├── tickets/                 Pesquisa: open/ e closed/
└── archive/                 Codigo e testes legados (v0.1)
```

---

## 3. Encoder/Decoder

### 3.1 Niveis de compressao

| Level | Nome | O que faz | Quando usar |
|-------|------|-----------|-------------|
| 0 | Expanded | 1 valor por linha, sem compressao | Debugging, max interpretabilidade |
| 1 | RLE | Comprime repeticoes consecutivas | Dados com repeticao natural |
| 2 | Sorted+RLE | Ordena por melhor coluna + RLE | **Recomendado para LLMs** |
| 3 | Dict+Sorted+RLE | Strings → indices + sorted + RLE | Max compressao, menos legivel |

### 3.2 Formato de saida (Level 2)

```
# TCF v0.2 level=2
# N*val = val repeated N times

## vendas n=509 sorted_by=produto
# STATS total: n=509 sum=51234.5 min=0.95 max=423.1 avg=100.66
pessoa:
3*Ana
2*Bruno
...
produto:
45*Borracha
38*Caderno
...
total:
12.5
3.0
...
```

### 3.3 API Python (recomendado)

```python
from tcf import encode_rows, decode, EncodeConfig
rows = [{"name": "Ana", "age": 25}, {"name": "Bruno", "age": 30}]
text = encode_rows("people", rows, EncodeConfig(level=2))
tables = decode(text)
```

Se ja tem dados columnar:
```python
from tcf import encode_columns
columns = {"name": ["Ana", "Bruno"], "age": ["25", "30"]}
text = encode_columns("people", columns)
```

Cookbook completo (CSV, JSON, JSONL, Pandas, Polars, Parquet, SQL) em
[../components/1-tcf-core.md](../components/1-tcf-core.md).

### 3.4 CLI (legacy CSV mode)

CLI aceita apenas CSV + metadata.json. Para outros formatos use API Python.

```bash
python -m tcf encode --meta data/metadata.json --data-dir data/ --level 2
python -m tcf decode arquivo.tcf --out-dir restored/
python -m tcf info arquivo.tcf
```

Para detalhes de cada formato comparado, ver [docs/article/03-tcf-format.md](../article/03-tcf-format.md).

---

## 4. Pipeline de Avaliacao

```
Etapa 1: DADOS (modelo fixo, variar formato/escala)
  → qwen3:8b × {CSV, TCF L0, L2, L3} × {50, 200 orders}
  → Resultado: qual compressao funciona?

Etapa 2: MODELOS (dados fixos, variar modelos)
  → retail_200 × {CSV, TCF L0, L2} × 12 modelos
  → Resultado: quais modelos entendem TCF?

Etapa 3: HIPERPARAMETROS (isolar thinking, temperature)
  → qwen3 × thinking on/off × temperature 0/0.6

Etapa 4: DECORACAO (isolar apresentacao)
  → code fences, XML tags, few-shot examples
  → Resultado: a forma de apresentar importa?
```

---

## 5. Documentacao

| Arquivo | Responsabilidade |
|---------|-----------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Este arquivo — estrutura e fluxo geral |
| [article/03-tcf-format.md](article/03-tcf-format.md) | Comparacao detalhada de formatos |
| [article/02-related-work.md](article/02-related-work.md) | Literatura e referencias |
| [EXPERIMENT_DESIGN.md](EXPERIMENT_DESIGN.md) | Metodologia das fases |
| [TESTS.md](TESTS.md) | Como rodar testes, fixtures |
| [SOURCE_MAP.md](SOURCE_MAP.md) | Rastreabilidade entre documentos |
| [article/](article/README.md) | Meta-artigo em capitulos |

**Rastreabilidade:** Ver [SOURCE_MAP.md](SOURCE_MAP.md) para hierarquia de fontes.

---

## 6. Convencoes

- CLI: `python -m tcf encode`, `decode`, `info` (sem sufixos de versao)
- Python: `from tcf import encode, decode` (sempre a versao corrente)
- Resultados em `experiments/results/` (gitignored)
- Ground truth programatico: `ground_truth.compute(data_dir)` (nunca hardcoded)
- Testes: `python -m pytest tests/ -v`
