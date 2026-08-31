---
title: Arquitetura v0.3 — TCF como nucleo + extras opcionais
date: 2026-04-27
type: research-note
status: PROPOSTA — depende de decisao do usuario em R-tcf-core-revisit
origin: Conversa de reorganizacao pos-reorg de docs
---

# Arquitetura v0.3 — TCF nucleo + extras

Proposta de separacao em camadas com **TCF como nucleo puro** e
funcionalidades auxiliares como **extras opcionais** ou **pacotes irmaos**.

## Estado atual (v0.2)

```
TCF/
├── src/tcf/                  ← encoder/decoder/compression (NUCLEO)
├── scripts/shaper/           ← Shaper sampling (NAO no nucleo, mas no repo)
├── scripts/dataset_reader.py ← driver SQLite local (NAO no nucleo)
├── scripts/csv_to_sqlite.py  ← ETL utilitario
├── experiments/eval/
│   └── llm_eval/
│       ├── ollama_client.py        ← cliente local
│       └── commercial_client.py    ← cliente comerciais
└── ...
```

Tudo no mesmo repo. Funciona, mas confunde:
1. **TCF como produto** (encoder/decoder) vs
2. **TCF como projeto de pesquisa** (Shaper + clients + experimentos)

## Modelos de referencia

### SQLAlchemy (melhor analogia para o DB extractor)

`sqlalchemy` core e neutro a banco. Drivers (`psycopg2`, `pyodbc`,
`pymysql`) sao pacotes separados que o usuario instala. SQLAlchemy
recebe `Engine` ou `Connection` e nao se preocupa com qual e o backend.

```python
from sqlalchemy import create_engine
engine = create_engine("postgresql+psycopg2://...")  # usuario escolhe driver
# sqlalchemy nao traz psycopg2; usuario instala
```

### Pytest + plugins

`pytest` core + plugins (`pytest-cov`, `pytest-asyncio`) instalados
separadamente. Cada um descoberto via entry points.

### Pandas + extras

```bash
pip install pandas[performance]   # pyarrow, numexpr
pip install pandas[plot]          # matplotlib
```

### Hugging Face

`transformers` core + `datasets` + `tokenizers` + `accelerate` —
pacotes irmaos com nomes proprios mas mesma "familia".

## Proposta v0.3 — modelo recomendado

**Hibrido**: pacote core + extras opcionais (estilo Pandas) +
pacotes irmaos para coisas que tem ciclo de vida proprio.

```
PYPI:
  tcf                    ← core: encoder/decoder/compression (foco do paper)
  tcf-extractor          ← driver DB neutral (recebe conexao SQLAlchemy)

GIT-only (nao no PyPI):
  tcf-shaper             ← experimento academico (mantido no repo)
  tcf-experiments        ← runners M-series (mantido no repo)
```

### Por que separar tcf-extractor como pacote

- Usuario comum quer `pip install tcf` e ja codificar
- Usuario avancado precisa coletor: `pip install tcf-extractor`
- Coletor depende de SQLAlchemy + driver de DB do usuario; **nao
  empacota drivers** (psycopg2, pyodbc, etc. ficam por conta do user)
- Lifecycle independente: schema model muda, mas TCF format nao precisa
  bumpar

### Por que NAO separar Shaper

- Shaper e ferramenta de pesquisa — utilidade limitada para usuario
  end-to-end
- Mantendo no repo, fica disponivel para quem quiser reproduzir
  experimentos
- Nao tem demanda externa que justifique manter um pacote PyPI separado
- Citado em paper, mas nao "produto"

## Estrutura proposta (file system)

```
TCF/                          ← repo (rename pendente em R-project-rename)
│
├── packages/                 ← NOVO: cada pasta vira pacote independente
│   ├── tcf/                  ← Core PyPI publishable
│   │   ├── pyproject.toml    ← name = "tcf"
│   │   ├── src/tcf/
│   │   │   ├── __init__.py
│   │   │   ├── encoder.py
│   │   │   ├── decoder.py
│   │   │   ├── compression.py
│   │   │   ├── schema.py
│   │   │   └── cli.py
│   │   └── tests/
│   │
│   └── tcf-extractor/        ← Driver DB neutral PyPI publishable
│       ├── pyproject.toml    ← name = "tcf-extractor"
│       │   ↳ depends: sqlalchemy, tcf>=0.3
│       │   ↳ extras: postgres (psycopg2), mssql (pyodbc), mysql
│       ├── src/tcf_extractor/
│       │   ├── __init__.py
│       │   ├── core.py            ← StructureExtractor(engine)
│       │   ├── adapters/
│       │   │   ├── postgres.py
│       │   │   ├── mssql.py
│       │   │   ├── sqlite.py
│       │   │   └── mysql.py
│       │   └── metadata.py        ← coleta PK/FK/types
│       └── tests/
│
├── experiments/              ← MANTEM (Shaper + runners + manifests)
│   ├── shaper/               ← move de scripts/shaper/
│   ├── eval/
│   └── results/
│
├── datasets/                 ← MANTEM (canonical configs)
├── docs/                     ← MANTEM (estrutura atual)
├── README.md
├── CHANGELOG.md
└── pyproject.toml            ← workspace meta (poetry/uv style)
```

### Por que `packages/` em vez de `src/`?

- Cada pasta tem seu proprio `pyproject.toml`
- Pode publicar separadamente: `cd packages/tcf && python -m build`
- Pode rodar testes do pacote isoladamente: `cd packages/tcf && pytest`
- Padrao monorepo Python (ex: TypeScript nx, Cargo workspaces, Rush.js)

### Workspace tooling

`uv` ou `poetry` workspace para desenvolvimento local:

```toml
# pyproject.toml na raiz
[tool.uv.workspace]
members = ["packages/tcf", "packages/tcf-extractor"]
```

Permite:
- `uv pip install -e packages/tcf` para core
- `uv pip install -e packages/tcf-extractor` para extractor
- Ambos linkados em modo dev sem PyPI

## Camada LLM — onde fica?

**Opcao A**: pacote `tcf-llm` separado
- Cliente Anthropic + OpenAI + Ollama
- Builds de prompt para Linha A / Linha B
- Pydantic schemas (AnswerCell, SqlAnswer)
- Pricing table

**Opcao B**: dentro de `experiments/eval/llm_eval/` (atual)
- Mantido no repo como infraestrutura de pesquisa
- Nao publicado no PyPI

**Recomendacao**: **Opcao B** por enquanto. O codigo LLM e essencial
para reproduzir os experimentos do paper, mas nao e produto autonomo
ainda. Se houver demanda externa pos-paper, promove para Opcao A.

A camada LLM tem **alto acoplamento com o paper** (schemas, prompts,
modelos). Se promover para pacote, vira "TCF for LLM benchmarking" —
escopo diferente do produto core.

## API contract de tcf-extractor (esboco)

```python
from sqlalchemy import create_engine
from tcf_extractor import StructureExtractor

# Usuario instala driver de seu DB:
# pip install tcf-extractor[postgres]  -> psycopg2
# pip install tcf-extractor[mssql]     -> pyodbc
# Etc.

engine = create_engine("postgresql://user@host/dbname")
extractor = StructureExtractor(engine)

# Coleta estrutura
schema = extractor.collect_schema(
    tables=["customers", "orders"],     # ou None = todas
    include_pk=True,
    include_fk=True,
    sample_rows=100,                    # opcional, fk-preserving
)

# schema retorna dict no formato do tcf.metadata
# Pode ser passado direto para tcf.encode_rows ou tcf.encode

from tcf import encode_rows, EncodeConfig
text = encode_rows(
    "customers", schema["customers"]["rows"],
    config=EncodeConfig(level=2, include_stats=True),
)
```

### Pontos chave do contract

1. **Recebe `engine` ou `connection`** (igual SQLAlchemy)
2. **Nao traz drivers** — usuario instala via pip extras
3. **Output e `dict[str, list[dict]]`** ou `pandas.DataFrame` opcional
4. **Sample row e opcional** — pode coletar so schema OU schema+rows
5. **FK-preserving sampling** vem do Shaper (usuario importa
   separadamente se quiser)

## Roadmap proposto

### Fase 1 — split core (sem mover funcionalidade)
- [ ] Criar `packages/tcf/` com encoder atual
- [ ] Mover `src/tcf/` -> `packages/tcf/src/tcf/`
- [ ] Criar `packages/tcf/pyproject.toml`
- [ ] Atualizar imports nos experiments
- [ ] Verificar smoke tests
- [ ] Criar workspace tooling

### Fase 2 — extractor inicial (so Postgres + SQLite)
- [ ] Criar `packages/tcf-extractor/` com skeleton
- [ ] Implementar `StructureExtractor.collect_schema()` para SQLite
- [ ] Implementar adapter Postgres
- [ ] Tests com SQLite in-memory
- [ ] Documentacao + exemplo

### Fase 3 — extractor adapters (incremental)
- [ ] Adapter MSSQL
- [ ] Adapter MySQL
- [ ] Adapter Snowflake (opcional, dependendo de demanda)

### Fase 4 — TCF v0.3 internals (decidido em R-tcf-core-revisit)
- [ ] Stratified STATS, decoder type recovery, etc.
- [ ] Bump para v0.3
- [ ] Apendice A do paper revisto

### Fase 5 — integracao com paper
- [ ] Atualizar Cap 4 (metodologia) com nova arquitetura
- [ ] Atualizar Apendice A (TCF spec) com v0.3
- [ ] Diagrama de arquitetura como Figura 0 do paper

## Decisoes pendentes (input do usuario)

1. **Split agora ou depois do paper?** Tradeoff:
   - Agora: paper descreve a arquitetura final
   - Depois: paper descreve o que existiu durante os experimentos
2. **Workspace tool**: `uv` (mais novo) vs `poetry` (mais maduro)
3. **Nome do extractor**: `tcf-extractor` vs `tcf-driver` vs
   `<rename>-extractor`
4. **Camada LLM separa ou nao**: Opcao A (pacote `tcf-llm`) ou B
   (manter em experiments/)
5. **Quando publicar no PyPI**: pos-paper, junto, ou nunca?

## Riscos

- **Quebrar imports** dos experimentos durante a migracao —
  smoke tests cuidadosos
- **Workspace tooling imaturo**: uv ainda recente; poetry as vezes
  trava em conflicts
- **Apendice A do paper precisa refletir v0.2 OU v0.3**, nao ambos.
  Confundir versao no paper e ruim
- **Manutencao em paralelo de 2 pacotes** se houver fork de codigo
  durante transicao

## Notas para revisar este doc

Caso queira revisitar:
- Snapshot deste arquivo no commit `<ts>`
- Estado atual: src/tcf/ + scripts/shaper/ + experiments/eval/
- Tickets relacionados:
  - [M-architecture-v03](../tickets/open/M-architecture-v03.md)
  - [R-tcf-core-revisit](../tickets/open/R-tcf-core-revisit.md)
  - [R-project-rename](../tickets/open/R-project-rename.md)
- Achados relevantes: F-Q38 (schema_qualifier integration possivel)
