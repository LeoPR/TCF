# TCF · Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.7.0%20(pré--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.6%20%2F%20.7-blue)

> **E se desse pra transmitir a mesma tabela com bem menos bytes,
> sem virar um arquivo binário que ninguém mais consegue abrir e ler?**

Um cadastro pequeno, nos três formatos (bytes reais, saída de verdade):

**JSON** *(480 B)*: repete o nome de cada campo em toda linha.

```json
[ { "nome": "Ana Souza",  "email": "ana@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium" },
  { "nome": "Bruno Lima", "email": "bruno@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium" }, … ]
```

**CSV** *(213 B)*: tira os nomes repetidos, uma linha por registro.

```
nome,email,cidade,plano
Ana Souza,ana@acme.com.br,Sao Paulo,Premium
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium
```

**TCF** *(177 B, formato 0.7, saída real do `encode`)*: o que se repete vira referência.

```
#TCF.7 M
!44=nome,42=email,28=cidade,plano
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
```

**Como ler:**

- Linha 1, shebang: `#TCF.7 M` é o formato 0.7, multi-coluna.
- Linha 2, meta das colunas (`tamanho=nome`).
  O `!` marca uma coluna guardada **crua** (quando o raw fica menor que o TCF).
  A última (`plano`) não leva tamanho: vai até o fim.
- Os corpos vêm concatenados, **delimitados por tamanho, não por quebra de linha**.
  Por isso a coluna crua `nome` (`…Diego Rocha`) emenda direto no e-mail (`an*a*…`).
- No corpo: `*3|Sao Paulo` é *"Sao Paulo, 3×"* (repetição).
  `^1` é *"igual à linha 1"* (substituição).
- Na coluna de **e-mail** o TCF vai mais fundo (prefixo único + domínio comum referenciado).
  É onde mais economiza, e onde o texto fica mais denso.

JSON repete a estrutura inteira.
CSV repete os valores.
O **TCF fatora o que se repete** e referencia o resto, continuando **texto ASCII que você abre e lê**.

Mas quanto mais fundo ele fatora (veja o e-mail), mais denso o texto fica.
*Legível não quer dizer óbvio à primeira vista.*

Em tabelas grandes a diferença cresce: ver [Resultados](#resultados).

## O que é o TCF

Um formato **textual** e **sem perdas** (`decode(encode(x)) == x`) para tabelas de strings.

Comprime parecido com um zip/gzip, mas com uma diferença: o resultado **continua texto ASCII que você abre e inspeciona**, sem descomprimir.
Não fica tão óbvio quanto o original (quanto mais o TCF fatora, mais denso o texto), mas nunca vira um blob opaco.
Cada coluna passa por um pipeline próprio.

É essa a faixa que o TCF ocupa: **compacto como um compressor, inspecionável como texto**.
(Precisa de ratio máximo? Dá pra rodar gzip/brotli por cima: eles se compõem.)

## Como ele faz isso: OBAT + HCC

Duas camadas, explicadas pelo propósito (specs: [`docs/algorithms/`](docs/algorithms/)).

**OBAT** (Online Bidirectional Affix Tokenizer) *acha o que as strings têm em comum.*
Para cada valor, procura o maior prefixo **e** sufixo compartilhado com os anteriores (domínios de e-mail, raízes de URL, códigos da mesma família).
Escreve o trecho uma vez e referencia o resto.

É um **front-coding bidirecional**: generaliza o front-coding clássico de dicionários de strings (Witten et al.; HTFC/RPDac, Brisaboa et al.).
O "bidirecional" é o que captura o **sufixo** comum (`@acme.com.br`), não só o prefixo.

A busca por afixos é da família das **árvores de prefixo/sufixo**: tries, **Patricia/radix tree** (Morrison 1968), suffix trees.
Na prática o OBAT acelera essa busca com um **índice de trigramas**, que derruba o custo de O(N²) ingênuo para ~O(N^1.42) (sub-quadrático, quase-linear).
*(Trocar o índice por uma Patricia trie é candidato futuro: [exploração](docs/theory/patricia-trie-exploration.md).)*

**HCC** (Hierarchical Compositional Coding) *decide o que vale a pena nomear e agrupa repetições.*
Pega os tokens do OBAT, fatora composições recorrentes em **referências nomeadas reutilizáveis** (operador `~`) e colapsa repetidos (RLE, inclusive sequências quase-iguais, tipo IDs que só mudam no fim).

Como referência aponta para referência, o resultado é um **grafo acíclico (DAG) de fragmentos**: na prática uma *gramática* / straight-line program do conteúdo.
É o espírito do **Re-Pair** (Larsson & Moffat 1999) e do **Sequitur** (Nevill-Manning & Witten 1997), mas operando sobre os **tokens** do OBAT (não sobre bytes) e com operadores próprios (`~` cria nó nomeado, `,` só concatena).

É o que mantém a saída pequena **e** inspecionável: os grupos `*N|...` ficam à vista.

**Velocidade.**
O lado caro é o **encode** (a busca de afixos do OBAT), trazido a quase-linear pelo índice de trigramas (mais o acelerador Cython opcional).
O **decode** é uma **passada linear única**: só expande as referências (lookups O(1)) e os grupos RLE, sem nenhuma busca.
Rápido e previsível.

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

`encode` dispatcha por tipo (list → single-column, dict → multi-column).
`decode` roteia pelo shebang.

Tutorial passo-a-passo: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Guias praticos: [`docs/how-to/`](docs/how-to/).

## Formato 0.7 (default): onde os bytes vão

O `encode` multi-coluna sai em **0.7 / `#TCF.7`** por default ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
Duas coisas, ambas automáticas (sem flag):

- **Fallback por coluna.**
  Guarda a coluna em raw quando o raw fica menor que o TCF ("nunca pior que raw").
  Marcada com `!` no meta ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)).
- **Header mínimo.**
  O flag `M` no shebang já declara que vêm colunas, então o meta dispensa o prefixo `# `.
  E a última coluna não leva tamanho, vai até o fim ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)).

```python
text = encode(table)        # 0.7 / #TCF.7, é o default, sem flags

# knobs opt-out (default True) — pra modificar o comportamento / inspecionar:
text = encode(table, fallback=False, min_header=False)  # força o legado #TCF.6
text = encode(table, min_header=False)                  # #TCF.7 com header verboso
text = encode(table, min_len=5)                         # override do min_len do OBAT (default: auto)
```

No cadastro de 4 colunas do topo, comparado ao formato legado `#TCF.6`:

| formato | meta line | bytes |
|---|---|---:|
| **0.7 / `#TCF.7`** (default) | `!44=nome,42=email,28=cidade,plano` | **177** |
| `#TCF.6` (legado) | `# 45=nome,42=email,28=cidade,20=plano` | 182 |

O ganho é proporcionalmente maior em **payloads pequenos** (o header de tamanho fixo domina).

Pré-1.0, o encoder só escreve o formato mais novo.
O `#TCF.6` legado ainda é **lido** pelo decoder, e `git checkout` reproduz a era 0.6 ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
Ganhos de *body* em tabelas grandes (dicionário low-card, strip de sufixo) ficam no [roadmap](docs/adr/0018-v2-format-roadmap.md).

## Estado (pré-1.0)

- **Pré-1.0** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
  Os minors do formato (`#TCF.4/.5/.6/.7`) são iterações de desenvolvimento rumo a um **1.0 sólido**, sem compat rígida entre eles (git reproduz versões antigas).
  v2.0 fica pra depois.
- Implementação canônica em [`src/tcf/`](src/tcf/).
  Round-trip sempre lossless (`decode(encode(x)) == x`).
- Default **0.7 / `#TCF.7`**: fallback ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)) + header mínimo ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)), ver seção acima.
  O `#TCF.6` legado é lido pelo decoder.
- Suíte: **348 passed, 1 xfailed**.
  Baselines de byte = guardas de regressão, re-pináveis em mudança intencional ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
- Mudanças: [`CHANGELOG.md`](CHANGELOG.md).
  História M0-M14: [`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md).

> O ciclo **v0.5** (formato columnar para LLM benchmark) é acessório e vive separado.
> Ver a seção "Benchmark LLM v0.5" mais abaixo.

## Resultados

**Sem nenhum compressor, o TCF é o formato de _texto_ mais compacto do conjunto.**
Nos 15 datasets sintéticos do [EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/):

| formato (texto puro, sem compressor) | bytes |
|---|---:|
| **TCF** | **3131** |
| CSV | 4872 |
| JSON | 5409 |
| JSONL | 7001 |

~36% menor que CSV e ~42% menor que JSON, continuando legível.

Núcleo pinado em testes: D1-D9 = **1523 B** (51.1% do raw, single-col); D17a multi-col = **307 B** (0.7; legado `#TCF.6` = 322 B).
Real-world multi-coluna (9 tabelas Adult + TPC-H, 136k linhas): **−33.02% weighted** vs CSV raw.

**E contra gzip / brotli / zstd?**
Outra categoria: são compressores binários *opacos* (precisa descomprimir pra ler qualquer coisa).
No ratio puro eles ganham (no EXP-008, `csv+brotli` = 1742 B contra `tcf+brotli` = 2141 B).
O TCF **troca um pouco de ratio por legibilidade** e se compõe com eles (rodar gzip por cima do TCF funciona).

Tabelas completas: [reports do EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/reports/).

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

## Benchmark LLM v0.5 (acessorio, projeto paralelo)

> Esta secao resume o ciclo **v0.5** (formato columnar para consumo por LLMs).
> NAO e' o algoritmo TCF v0.6 acima. Todo o material vive separado.

O ciclo v0.5 mediu compreensao de tabelas por LLMs (CSV/JSON/TOON/TCF,
Linha A "LLM le e computa" + Linha B "LLM gera SQL"): 7 modelos comerciais
+ 13 locais, 2 datasets, 2256 registros, 38 findings.
Usava o **motor de niveis** (`EncodeConfig(level=N)`) em [`old/tcf/`](old/tcf/).
Ver [`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md) para a semantica L0–L3.

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
├── experiments/lab/         ← labs v0.6 (dirty + clean): compressao composicional
├── llm-benchmark/           ← benchmark LLM v0.5 (harness: runners + llm_eval), acessorio
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
> e `docs/article/` NAO existem; o material v0.5 correspondente esta em
> `docs/archive/manual_v05/` e `docs/archive/article_v05/`.

---

## Tools shipped (v0.6)

O encoder e' a ferramenta principal; auxiliares de suporte (NAO TCF-core):

- **Shaper** (`scripts/shaper/`): stratified, FK-preserving sampling framework.
  Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`): uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`): download/geracao dos datasets canonicos
  (Adult, TPC-H, IBGE, CNPJ, etc.); ver [datasets/README.md](datasets/README.md)

> Pré-1.0: **library-only** (sem CLI; ver `pyproject.toml`).
> O benchmark LLM v0.5 (CommercialClient, M-series runners) vive em
> [`llm-benchmark/`](llm-benchmark/), com instrucoes de reproducao no README de la'.

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
(Ciclo v0.5) Commercial LLM testing supported by personal credits;
total spend $9.46 USD for 1968 records (75% cache savings).
