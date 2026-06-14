# TCF — Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Format](https://img.shields.io/badge/format-%23TCF.6%20frozen-green)

> **E se desse pra transmitir a mesma tabela com bem menos bytes — sem virar um arquivo binário que ninguém mais consegue abrir e ler?**

Um cadastro pequeno, nos três formatos — **bytes reais, saída de verdade**:

**JSON** — repete o nome de cada campo em toda linha · *480 B*

```json
[ { "nome": "Ana Souza",  "email": "ana@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium" },
  { "nome": "Bruno Lima", "email": "bruno@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium" }, … ]
```

**CSV** — tira os nomes repetidos; uma linha por registro · *213 B*

```
nome,email,cidade,plano
Ana Souza,ana@acme.com.br,Sao Paulo,Premium
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium
```

**TCF** — o que se repete vira referência · *182 B (saída real do `encode`)*

```
#TCF.6 M
# 45=nome,42=email,28=cidade,20=plano
Ana Souza
Bruno Lima
Carla Nunes
Diego Rocha
an*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
```

**Como ler:** a 1ª linha é o cabeçalho (`tamanho=nome` de cada coluna); depois
vêm os corpos, um bloco por coluna. `*3|Sao Paulo` = *"Sao Paulo, 3 vezes"*
(repetição); `^1` = *"igual ao valor da linha 1"* (substituição). Na coluna de
**e-mail** o TCF vai mais fundo: o começo único de cada um + o domínio comum
(`@acme.com.br`) escrito uma vez e referenciado — é onde ele mais economiza, e
onde o texto fica mais denso.

JSON repete a estrutura inteira; CSV repete os valores; o **TCF fatora o que se
repete** e referencia o resto — continuando **texto ASCII que você abre e lê**.
Mas note: quanto mais fundo ele fatora (veja o e-mail), mais denso o texto fica.
*Legível não quer dizer óbvio à primeira vista.* Em tabelas grandes a diferença
cresce — ver [Resultados](#resultados-v10).

## O que é o TCF

Um formato **textual** e **sem perdas** (`decode(encode(x)) == x`) para tabelas
de strings. Comprime parecido com um zip/gzip — mas, ao contrário deles, o
resultado **continua texto ASCII que você abre e inspeciona**, sem descomprimir.
Não é tão óbvio quanto o original — quanto mais o TCF fatora, mais denso o texto
fica — mas nunca vira um blob opaco. Cada coluna passa por um pipeline próprio.

É essa a faixa que o TCF ocupa: **compacto como um compressor, inspecionável
como texto**. (Precisa de ratio máximo? Dá pra rodar gzip/brotli por cima —
eles se compõem.)

## Como ele faz isso — OBAT + HCC

- **OBAT** (Online Bidirectional Affix Tokenizer) — *acha o que as strings têm
  em comum.* Prefixos e sufixos repetidos (domínios de e-mail, raízes de URL,
  códigos da mesma família) são escritos uma vez; o resto vira referência curta.
  É o que faz dados com estrutura parecida quase desaparecerem.
- **HCC** (Hierarchical Compositional Coding) — *decide o que vale a pena nomear
  e agrupa repetições.* Escolhe quais trechos viram referência nomeada e colapsa
  repetidos — inclusive sequências quase-iguais (IDs que só mudam no fim). É o
  que mantém a saída pequena **e** inspecionável: os grupos ficam à vista
  (`*3|...`) sem precisar expandir.

Specs técnicas de cada camada: [`docs/algorithms/`](docs/algorithms/).

## Getting started (1 minuto)

```python
from tcf import encode, decode

# Single-column: lista de strings
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
assert decode(text) == ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]

# Multi-column: dict de colunas
table = {
    "id":    ["1", "2", "3"],
    "email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"],
}
text = encode(table)
assert decode(text) == table  # round-trip lossless

# Naturezas (opt-in): CPF/CNPJ/IP comprimidos sem digito verificador/padding
from tcf import SPEC_CPF
text = encode(["111.444.777-35", "529.982.247-25"], nature=SPEC_CPF)
```

`encode` dispatcha por tipo (list → single-column, dict → multi-column);
`decode` roteia pelo shebang.

Tutorial passo-a-passo: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Guias praticos: [`docs/how-to/`](docs/how-to/).

## Estado v1.0 (stable)

- Format `#TCF.6` e API pública **congelados** ([ADR-0017](docs/adr/0017-format-spec-v1-frozen.md))
- Implementação canônica em [`src/tcf/`](src/tcf/); round-trip sempre lossless (`decode(encode(x)) == x`)
- Suíte: **340 passed, 1 xfailed**
- **v2.0 em andamento**: V2-A fallback identity (`#TCF.7`, opt-in `fallback=True`) — [ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)
- Mudanças: [`CHANGELOG.md`](CHANGELOG.md). História M0-M14:
  [`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md)

> O ciclo **v0.5** (formato columnar para LLM benchmark) é acessório e
> vive separado — ver a seção "Benchmark LLM v0.5" mais abaixo.

## Resultados v1.0

**Sem nenhum compressor, o TCF é o formato de _texto_ mais compacto do conjunto.**
Nos 15 datasets sintéticos do [EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/):

| formato (texto puro, sem compressor) | bytes |
|---|---:|
| **TCF** | **3131** |
| CSV | 4872 |
| JSON | 5409 |
| JSONL | 7001 |

~36% menor que CSV e ~42% menor que JSON — **continuando legível**. Núcleo
pinado em testes: D1-D9 = **1523 B** (51.1% do raw), D17a multi-col = **322 B**
(INVARIANT). Real-world multi-coluna (9 tabelas Adult + TPC-H, 136k linhas):
**−33.02% weighted** vs CSV raw.

**E contra gzip / brotli / zstd?** Outra categoria: são compressores binários
*opacos* — precisa descomprimir pra ler qualquer coisa. No ratio puro eles
ganham (no EXP-008, `csv+brotli` = 1742 B contra `tcf+brotli` = 2141 B). O TCF
**troca um pouco de ratio por legibilidade** e se compõe com eles (rodar gzip
por cima do TCF funciona). Tabelas completas:
[reports do EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/reports/).

## First-time setup (dev)

```bash
# Clone + install dev deps
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"

# (recomendado) instalar pre-commit hooks
pre-commit install

# Rodar hooks em todos arquivos (opcional, baseline)
pre-commit run --all-files
```

Hooks configurados (ver [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):
- `ruff` lint + format
- `detect-secrets` (scan)
- basicos: trailing-whitespace, end-of-file-fixer, check-merge-conflict, check-added-large-files
- custom: bloqueia cache dirs (`__pycache__/`, `.pytest_cache/`, etc.) acidentalmente staged

## How to cite

Ver [`CITATION.cff`](CITATION.cff). GitHub renderiza badge "Cite this
repository" na pagina do repo automaticamente.

---

## Benchmark LLM v0.5 (acessorio — projeto paralelo)

> Esta secao resume o ciclo **v0.5** (formato columnar para consumo por LLMs).
> NAO e' o algoritmo TCF v0.6 acima. Todo o material vive separado.

O ciclo v0.5 mediu compreensao de tabelas por LLMs (CSV/JSON/TOON/TCF,
Linha A "LLM le e computa" + Linha B "LLM gera SQL"): 7 modelos comerciais
+ 13 locais, 2 datasets, 2256 registros, 38 findings. Usava o **motor de
niveis** (`EncodeConfig(level=N)`) em [`old/tcf/`](old/tcf/) — ver
[`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md) para a semantica L0–L3.

- **Harness** (runners, llm_eval, scripts): [`llm-benchmark/`](llm-benchmark/)
- **Catalogo de achados** F-Q01..Q38: [`docs/findings/`](docs/findings/)
  + [`docs/FINDINGS_SUMMARY.md`](docs/FINDINGS_SUMMARY.md)
- **Manual / paper v0.5**: [`docs/archive/manual_v05/`](docs/archive/manual_v05/)
  + [`docs/archive/article_v05/`](docs/archive/article_v05/)

Candidato a spin-off (`tcf-llm-tools`) no futuro. Pode re-validar contra v0.6
se Phase 2 for revivida.

---

## Repository layout

```
TCF/
├── src/tcf/                 ← CANONICAL v0.6 API (OBAT+HCC, encode/decode, #TCF.6)
├── old/tcf/                 ← motor v0.5 (niveis L0–L3), congelado-historico (ver LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← labs v0.6 (dirty + clean) — compressao composicional
├── llm-benchmark/           ← benchmark LLM v0.5 (harness: runners + llm_eval) — acessorio
├── tests/                   ← pytest suite (v0.6)
├── datasets/                ← canonical metadata + samples (dados reais em Z:)
├── tickets/                 ← planejamento markdown (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← specs canonicos v0.6 (OBAT, HCC, TCF-format) [reference]
│   ├── adr/                 ← decisoes numeradas, imutaveis
│   ├── theory/              ← fundamentos teoricos [explanation]
│   ├── how-to/, tutorials/  ← Diataxis
│   ├── findings/            ← catalogo cientifico v0.5 LLM (F-Q01..Q38) [historico]
│   ├── workbench/           ← dev timeline, research notes (partes em _archive/)
│   └── archive/             ← material v0.5/v0.1 congelado (manual_v05, article_v05, etc.)
├── config/                  ← storage.json (aponta Z:), api_keys (gitignored)
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

> Para o mapa detalhado, ver [MAP.md](MAP.md). Os diretorios `docs/manual/`
> e `docs/article/` NAO existem — o material v0.5 correspondente esta em
> `docs/archive/manual_v05/` e `docs/archive/article_v05/`.

---

## Tools shipped (v0.6)

O encoder e' a ferramenta principal; auxiliares de suporte (NAO TCF-core):

- **Shaper** (`scripts/shaper/`) — stratified, FK-preserving sampling
  framework. Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`) — uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`) — download/geracao dos datasets canonicos
  (Adult, TPC-H, IBGE, CNPJ, etc.); ver [datasets/README.md](datasets/README.md)

> v1.0 e' **library-only** (sem CLI — `pyproject.toml`). O benchmark LLM v0.5
> (CommercialClient, M-series runners) vive em [`llm-benchmark/`](llm-benchmark/),
> com instrucoes de reproducao no README de la'.

---

## Where to go next

- **I want to use TCF in my pipeline** → API v0.6: `from tcf import encode, decode` ([src/tcf/](src/tcf/)); manual v0.6 pendente. v0.5: [docs/archive/manual_v05/](docs/archive/manual_v05/)
- **I want to read the findings** → [docs/findings/](docs/findings/) (v0.5 LLM, historico)
- **I want to run the LLM benchmark** → [llm-benchmark/](llm-benchmark/) (acessorio v0.5)
- **I want to understand the architecture** → [docs/theory/](docs/theory/)
- **I want to read the paper** → drafts v0.5: [docs/archive/article_v05/](docs/archive/article_v05/) (paper v0.6 pendente)
- **I want to see how it evolved** → [CHANGELOG.md](CHANGELOG.md) +
  [docs/workbench/](docs/workbench/)

---

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Project conceived as part of an academic dissertation (TCC). Datasets:
[UCI Adult Census](https://archive.ics.uci.edu/ml/datasets/adult) and
[TPC-H](https://www.tpc.org/tpch/) (via DuckDB tpch extension).
(Ciclo v0.5) Commercial LLM testing supported by personal credits —
total spend $9.46 USD for 1968 records (75% cache savings).
