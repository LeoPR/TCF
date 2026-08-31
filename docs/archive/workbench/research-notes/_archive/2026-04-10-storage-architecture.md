# Pesquisa 2026-04-10: Arquitetura de Storage e Boas Praticas de Data Engineering

Consolidacao da pesquisa sobre:
1. Onde armazenar datasets grandes
2. Estrutura de projeto de data engineering moderna
3. Separacao de git / OneDrive / disco local
4. Compressao para archiving (LZMA)
5. Telemetria honesta em benchmarks
6. Red flags de overengineering

---

## 1. Consenso da industria — Cookiecutter Data Science

Fonte: [cookiecutter-data-science.drivendata.org](https://cookiecutter-data-science.drivendata.org/)
e [drivendataorg/cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science)

E o padrao de facto para projetos de data science reproduziveis. Adotado
em centenas de projetos academicos e empresariais.

### Principios confirmados

**1. `data/` no .gitignore por padrao.** Pequenos datasets estaveis podem
ser versionados, mas a regra e: dados nao vao pro git.

**2. Dados raw sao IMUTAVEIS.** "It's okay to read and copy raw data to
manipulate it into new outputs, but never okay to change it in place."

**3. Fluxo unidirecional:**
```
data/raw/      (original dump, imutavel)
  ↓
data/interim/  (transformacoes intermediarias)
  ↓
data/processed/ (final, canonical para uso)
```
Nunca volta. Cada passo e um no num DAG de analise.

**4. `data/external/`** para datasets de terceiros (TPC-H, Adult na nossa tradução).

**5. Analise como DAG.** Cada etapa e um no. Sem loops. Permite re-execucao
forward ou trace backward.

**6. Config separada do codigo.** `.env` gitignored, carregado via `python-dotenv`
ou similar. Nunca hardcode credenciais ou caminhos de storage.

**7. Storage externo para datasets grandes.** Template oferece integracao
opcional com S3, Azure Blob, GCS durante setup. Confirma que **dados
grandes NAO vao para o git**.

### Estrutura adaptada para TCF

```
data/              # ou Z:\tcf-data\ (configuravel)
├── external/      # raw de terceiros: TPC-H, Adult (download via scripts)
├── interim/       # SQLite tipado (hub intermediario)
└── processed/     # derivacoes: CSV/JSONL/MD/TCF prontas
```

---

## 2. Alternativas consideradas e rejeitadas

### DVC (Data Version Control)

Fonte: [dvc.org](https://dvc.org/), [comparacao lakefs](https://lakefs.io/blog/dvc-vs-git-vs-dolt-vs-lakefs/)

**Pros:**
- Versiona dados junto com git (metadados no git, dados em backend remoto)
- Suporta S3, Azure, GCS, local, SSH
- Integra com HuggingFace, Kaggle
- Pipelines reproduziveis

**Contras para nosso caso:**
- Dependencia extra (DVC CLI, config)
- Curva de aprendizado
- Overengineering para projeto solo
- Complexidade quando nao ha multiplos colaboradores

**Decisao:** **nao adotar agora**. Documentar como opcao futura se o projeto
crescer para multiplos colaboradores ou precisar versionar resultados.

### Git LFS (Large File Storage)

**Pros:**
- Integrado ao GitHub
- Mais simples que DVC

**Contras:**
- Cotas de banda no GitHub (pagam se passar)
- Nao feito para data science
- Binarios opacos
- Complica `git clone` (requer LFS instalado)

**Decisao:** **nao adotar**. Limitacoes de banda + complexidade sem beneficio.

### Oxen.ai

Mencionado em [ghost.oxen.ai/the-best-ai-data-version-control-tools/](https://ghost.oxen.ai/the-best-ai-data-version-control-tools/)
como alternativa moderna a DVC/git-lfs, performance superior.

**Decisao:** interessante mas muito novo, pouco testado. **Futuro**.

### lakeFS

Control plane sobre storage centralizado, branching de petabytes.

**Decisao:** **overkill absoluto** para nosso escopo.

### Dolt

Database versionado como git.

**Decisao:** muito especifico, nao se alinha com CSV/JSONL/TCF.

---

## 3. Solucao escolhida — hibrido simples de 3 camadas

### Camada A — Git (repositorio TCF no OneDrive)

**Criterio:** pequeno, estavel, util para reprodutibilidade.

| Tipo | Size limit | Exemplos |
|------|------------|----------|
| Scripts | ilimitado | `scripts/setup_tpch.py` |
| Metadata | <50KB | `metadata.json` (schema, PK/FK, tipos) |
| Quality reports | <100KB | `quality-reports/tpch-sf001.md` |
| Perguntas + ground truth | <100KB | `questions/tpch-sf001.json` |
| Amostras pequenas | <50KB direto | `samples/tpch-sf001/nation.csv` (25 rows) |
| Amostras medias | <2MB se util | `samples/tpch-sf001/lineitem-sample.csv` (100 rows) |

### Camada B — Disco local espacoso (Z:\tcf-data)

**Criterio:** tudo que e grande ou regeneravel.

```
Z:\tcf-data\
├── external\           # raw download (imutavel apos download)
│   ├── tpch-sf001\
│   │   ├── region.csv
│   │   ├── nation.csv
│   │   └── ...
│   └── adult-census\
│       └── adult.csv
├── interim\            # SQLite hub tipado
│   ├── tpch-sf001.db
│   └── adult-census.db
├── processed\          # derivacoes prontas
│   ├── tpch-sf001\
│   │   ├── csv\
│   │   ├── jsonl\
│   │   ├── markdown\
│   │   └── tcf\        # futuro
│   └── adult-census\
└── archives\           # backup frio LZMA
    ├── tpch-sf001.tar.xz
    └── adult-census.tar.xz
```

**Nao sincroniza com OneDrive.** Nao vai pro git. Regeneravel via scripts.

### Camada C — Archive LZMA (Z:\tcf-data\archives)

**Quando:** dataset "congelado" (nao mais editado, concluido).

```bash
# Arquivar (free up disk)
python scripts/archive_dataset.py tpch-sf001 --compress
# Gera: archives/tpch-sf001.tar.xz (~10-15% do original)
# Apaga: external/ interim/ processed/ do dataset

# Restaurar quando precisar
python scripts/archive_dataset.py tpch-sf001 --restore
```

**Numeros esperados (LZMA -9e):**
- Texto tabular: 15-25% do original
- Dados TPC-H (muito repetitivo): 8-12%
- Adult: 15-20%

**Caveat:** compressao e lenta (1-5 min para 100MB), descompressao rapida.

---

## 4. Config resolucao de caminhos

Problema: meu disco Z: nao e o seu disco Z:. Como desacoplar?

### Solucao

**`config/storage.json.example`** (em git, template):
```json
{
  "data_root": "Z:/tcf-data",
  "note": "Copie este arquivo como storage.json e ajuste para seu ambiente.",
  "fallback": "Se nao tiver disco extra, use 'data-local' (dentro do projeto)"
}
```

**`config/storage.json`** (gitignored, cada usuario cria o seu):
```json
{
  "data_root": "Z:/tcf-data"
}
```

**`src/tcf/paths.py`** (ou `scripts/_paths.py`):
```python
from pathlib import Path
import json

def data_root() -> Path:
    """Resolve o root do storage baseado no config local."""
    config = Path("config/storage.json")
    if config.exists():
        cfg = json.loads(config.read_text(encoding="utf-8"))
        return Path(cfg["data_root"])
    # Fallback: pasta local (para dev rapido sem disco extra)
    return Path("data-local")

def external_dir(name: str) -> Path:
    return data_root() / "external" / name

def sqlite_path(name: str) -> Path:
    return data_root() / "interim" / f"{name}.db"

def processed_dir(name: str, format: str) -> Path:
    return data_root() / "processed" / name / format
```

**Vantagens:**
- Desacopla codigo do storage local
- Usuario escolhe onde pisar
- Fallback funciona mesmo sem config (dev instantaneo)
- Zero dependencias externas

---

## 5. Telemetria honesta em benchmarks

### Problema

Benchmarks sem isolamento de fases sao enganosos. Exemplo:

```
"TCF encode levou 3 segundos"
```

Realmente 3s? Ou foi 100ms de encode e 2.9s lendo do disco?
Ou foi 500ms de parse CSV + 2.4s descomprimindo gzip + 100ms encode?

### Solucao

Modulo central de timing (ver [ticket 11-T-telemetry](#proposta-tickets-11)):

```python
# src/tcf/timing.py
from contextlib import contextmanager
import time

class Timings:
    """Coletor de tempos por fase, em nanossegundos (perf_counter_ns)."""

    def __init__(self):
        self.events: dict[str, int] = {}

    @contextmanager
    def measure(self, name: str):
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            self.events[name] = time.perf_counter_ns() - t0

    def to_dict(self, unit: str = "ms") -> dict[str, float]:
        div = {"ns": 1, "us": 1000, "ms": 1_000_000, "s": 1_000_000_000}[unit]
        return {k: round(v/div, 3) for k, v in self.events.items()}
```

### Uso

```python
t = Timings()

with t.measure("io_read"):
    raw = path.read_bytes()

with t.measure("decompress"):
    data = lzma.decompress(raw) if compressed else raw

with t.measure("parse_csv"):
    rows = list(csv.DictReader(io.StringIO(data.decode())))

with t.measure("tcf_encode"):       # ← isolado
    tcf_text = tcf.encode(rows, config)

# No manifest
result["timings_ms"] = t.to_dict()
# Exemplo: {"io_read": 2.1, "decompress": 0.0, "parse_csv": 45.3, "tcf_encode": 12.7}
```

### No paper

Reportar **`tcf_encode` isolado**. Mencionar `io + parse` como baseline
comum a todos os formatos (CSV, JSONL, TOON, TCF pagam igual por isso).

---

## 6. Sobre tolerancia de compressao (observacao do usuario)

Observacao do usuario: *"tolerancias que os compressores tem em que se
nao comprimir nada, so registra e deixa do dado como esta"*.

### Analogia com outros formatos

- **Deflate/gzip:** tem "stored blocks" — dados sem compressao quando
  compressao nao ajuda. Cabecalho + dados literais.
- **LZMA:** tem "literal runs" para bytes que nao se comprimem.
- **Zstd:** "uncompressed mode" para blocos incompreensiveis.

### Aplicacao ao TCF

Um encoder inteligente detectaria:

**Por dataset:**
- Dataset com <10 rows? → L0 sempre (niveis maiores nao ajudam)
- Dataset com 100% valores unicos? → L0 sempre (RLE nao economiza)

**Por coluna:**
- Coluna com cardinalidade 100%? → deixa expanded mesmo em L2
- Coluna onde RLE resulta maior que expanded? → fallback para expanded
- Coluna de uuids/hashes? → sempre expanded, dict pouco ajuda

**Registrar no header:**
```
# TCF v0.3 level=2 auto_fallback=true
## data n=5000 sorted_by=category
# column_strategy: category=rle_dict, id=expanded, uuid=expanded, total=rle
```

**Decisao:** registrar como ideia para **futuro** (quando revisitar encoder).
Por enquanto L0-L3 sao manuais. Auto-detect vem como L-auto num v0.3.

---

## 7. Red flags de overengineering

| Feature | Decisao | Razao |
|---------|---------|-------|
| DVC | **Nao** | Overkill para projeto solo |
| Git LFS | **Nao** | Limitacoes GitHub, complexidade |
| S3/cloud storage | **Nao** agora | Infra externa, pagamento |
| Docker/VMs | **Nao** | Complexidade sem retorno |
| CI/CD pipelines | **Nao** | Prematuro |
| Data catalog formal | **Nao** | Overkill |
| Kafka/streaming real | **Nao** | Scope e batch |
| Airflow/Prefect | **Nao** | Scripts simples bastam |
| SQLAlchemy ORM | **Nao** | stdlib sqlite3 ja resolve |
| Pydantic para schemas | **Talvez** | Uteis, mas dataclasses chegam |
| pre-commit hooks | **Opcional** | Se leve, util |
| Makefile/Taskfile | **Opcional** | Conveniencia, nao bloqueante |
| Great Expectations | **Nao** agora | Nosso quality report manual e mais simples |

### Green flags (adotamos)

- Cookiecutter DS structure (padrao provado)
- Config em arquivo gitignored
- Raw imutavel
- Python stdlib quando possivel
- Fallback local para quem nao tem disco extra
- Scripts idempotentes (roda varias vezes sem quebrar)
- Telemetria por fase (isolamento de tempo)

---

## 8. Estrutura proposta de docs/

Voce disse: *"docs seja a Meca, o compendio de tudo"*.

### Proposta

```
docs/
├── README.md                    ← entry point (substitui quase todos os .md da raiz)
│
├── architecture/                ← arquitetura do projeto
│   ├── overview.md              ← substituir ARCHITECTURE.md atual
│   ├── storage.md               ← NOVO (esta pesquisa)
│   ├── telemetry.md             ← NOVO (timing honesto)
│   └── source-map.md            ← mover SOURCE_MAP.md atual
│
├── datasets/                    ← NOVO: manuais por dataset
│   ├── tpch-sf001.md            ← como obter, usar, schema, licenca
│   ├── adult-census.md
│   └── poor-reference.md        ← historico do retail_sales
│
├── methodology/                 ← metodologia experimental
│   ├── experimental-design.md   ← EXPERIMENT_DESIGN.md atual
│   └── tests.md                 ← TESTS.md atual
│
├── article/                     ← paper (ja existe, mantem)
│   ├── README.md
│   ├── 00-innovations.md
│   └── ...
│
├── research-notes/              ← pesquisas datadas (ja existe, mantem)
│   ├── 2026-04-10-canonical-datasets.md
│   ├── 2026-04-10-critical-review.md
│   ├── 2026-04-10-compression-tokens-streaming.md
│   └── 2026-04-10-storage-architecture.md  ← ESTE arquivo
│
└── reference/                   ← NOVO: glossarios
    ├── glossary.md              ← termos do projeto
    └── format-cheatsheet.md     ← referencia rapida de formatos
```

### Raiz do projeto (enxuta, "cara de github")

```
TCF/
├── README.md             ← pitch + quick start + link para docs/
├── LICENSE               ← MIT
├── pyproject.toml        ← deps + metadata
├── .gitignore
├── .github/              ← GitHub-specific (issue templates, actions)
├── config/               ← configs (gitignored na maior parte)
├── src/                  ← codigo da biblioteca
├── tests/                ← testes
├── experiments/          ← runners cientificos
├── scripts/              ← scripts utilitarios
├── docs/                 ← Meca (compendio)
├── tickets/              ← tickets
├── data-local/           ← placeholder com .gitkeep (fallback se nao tem Z:)
└── archive/              ← historico v01 (mantem para rastreabilidade)
```

### Arquivos a mover para `docs/`

| De | Para | Motivo |
|----|------|--------|
| `docs/ARCHITECTURE.md` | `docs/architecture/overview.md` | padronizar |
| `docs/SOURCE_MAP.md` | `docs/architecture/source-map.md` | arquitetura |
| `docs/ARTICLE.md` | `docs/article/README.md` | ja existe similar |
| `docs/TESTS.md` | `docs/methodology/tests.md` | metodologia |
| `docs/EXPERIMENT_DESIGN.md` | `docs/methodology/experimental-design.md` | metodologia |

`README.md` raiz: reescrever com pitch curto + links para `docs/`.

---

## 9. Consolidacao das decisoes

1. **Storage principal:** `Z:\tcf-data\` (configuravel via `config/storage.json`)
2. **Git:** so scripts, metadata, reports, perguntas, amostras pequenas
3. **Estrutura:** Cookiecutter DS (`external/`, `interim/`, `processed/`)
4. **Archive:** LZMA ultra para backup frio (futuro, nao bloqueante)
5. **Config:** `config/storage.json` (gitignored) + `.example` em git
6. **Telemetria:** modulo `src/tcf/timing.py` para fases isoladas
7. **Docs:** reorganizacao para subpastas, `docs/` e a Meca
8. **Rejeitado:** DVC, Git LFS, S3, Docker, CI/CD (overengineering)

---

## 10. Referencias

### Project structure
- [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/)
- [Cookiecutter DS opinions](https://cookiecutter-data-science.drivendata.org/opinions/)
- [drivendataorg/cookiecutter-data-science GitHub](https://github.com/drivendataorg/cookiecutter-data-science)

### Data versioning alternatives
- [DVC docs](https://dvc.org/)
- [lakeFS comparison: DVC vs git-lfs vs Dolt vs lakeFS](https://lakefs.io/blog/dvc-vs-git-vs-dolt-vs-lakefs/)
- [Oxen.ai](https://ghost.oxen.ai/the-best-ai-data-version-control-tools/)
- [Git LFS + DVC guide](https://medium.com/@pablojusue/git-lfs-and-dvc-the-ultimate-guide-to-managing-large-artifacts-in-mlops-c1c926e6c5f4)

### Best practices 2025
- [15 Data Engineering Best Practices — lakeFS](https://lakefs.io/blog/data-engineering-best-practices/)
- [dbt Labs — Best practices for modern data engineering](https://www.getdbt.com/blog/data-engineering)
- [10 Best Practices — Mind Grid Academy](https://mindgridacademy.com/10-best-practices-every-data-engineer-should-know-in-2025/)

### Compressao
- [Python lzma stdlib](https://docs.python.org/3/library/lzma.html)
- [Python zlib stdlib](https://docs.python.org/3/library/zlib.html) (compressobj para streaming)

---

## 11. Proxima acao

Apos este documento ser comitado, atualizar:
1. Tickets 02-10 para refletir storage em Z: com fallback
2. Criar `11-T-telemetry.md` (modulo de timing central)
3. Reorganizar `docs/` conforme proposta (moves + novos arquivos)
4. Reescrever `README.md` raiz (enxuto)
5. Commit + push

Nao implementar codigo ainda — so reestruturar docs e tickets.
Implementacao vem apos alinhamento final com o usuario.
