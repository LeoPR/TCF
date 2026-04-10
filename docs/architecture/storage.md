# Storage Architecture

Como datasets, derivacoes e archives sao armazenados no projeto TCF.

**Principio:** git guarda scripts e metadados pequenos. Dados grandes
vivem fora do git. Config e gitignored. Tudo reproduzivel via scripts.

## Visao geral (3 camadas)

```
┌───────────────────────────────────────────────────────────┐
│  CAMADA A — GIT (repositorio TCF, no OneDrive)           │
│                                                            │
│  Scripts, metadata, quality reports, perguntas, amostras  │
│  pequenas. Nenhum dado regeneravel grande.                │
└───────────────────────────────────────────────────────────┘
          │
          │ aponta para (via config/storage.json)
          ▼
┌───────────────────────────────────────────────────────────┐
│  CAMADA B — DISCO LOCAL (Z:\tcf-data ou configuravel)    │
│                                                            │
│  external/    raw brutos baixados dos scripts            │
│  interim/     SQLite hub tipado                           │
│  processed/   derivacoes (CSV, JSONL, MD, TCF)            │
└───────────────────────────────────────────────────────────┘
          │
          │ quando dataset e "congelado"
          ▼
┌───────────────────────────────────────────────────────────┐
│  CAMADA C — ARCHIVE (Z:\tcf-data\archives)               │
│                                                            │
│  LZMA ultra-comprimido para backup frio.                  │
│  Libera espaco em disco quando nao em uso.               │
└───────────────────────────────────────────────────────────┘
```

## Camada A: Git

### O que vai para git

| Tipo | Localizacao | Limite |
|------|-------------|--------|
| Scripts | `scripts/` | ilimitado |
| Metadata | `datasets/canonical/{name}/metadata.json` | <50KB |
| Schema/README | `datasets/canonical/{name}/README.md` | <20KB |
| Quality reports | `datasets/quality-reports/{name}.md` | <100KB |
| Perguntas + ground truth | `datasets/questions/{name}.json` | <100KB |
| Amostras pequenas | `datasets/samples/{name}/*.csv` | <50KB direto, <2MB se util |

### O que NAO vai para git

- Dados brutos grandes (regeneraveis via scripts)
- SQLite databases (.db)
- Derivacoes grandes (CSV/JSONL completos de tabelas com >1000 rows)
- Archives LZMA (binario opaco)
- `config/storage.json` (configuracao local do usuario)

### Razao

1. **Git nao e storage.** GitHub tem limite pratico de ~1GB por repo.
2. **Dados regeneraveis nao precisam de versionamento.** O script que
   os gera ja esta versionado.
3. **OneDrive nao e repositorio.** Sincronismo de GBs e desperdicio.
4. **Binarios opacos nao servem para diff.** Zero beneficio em versionar.

## Camada B: Disco local

### Estrutura (Cookiecutter Data Science adaptado)

```
Z:\tcf-data\
├── external\           # raw de terceiros (IMMUTABLE apos download)
│   ├── tpch-sf001\
│   │   ├── region.csv
│   │   ├── nation.csv
│   │   ├── ...
│   │   └── lineitem.csv
│   └── adult-census\
│       └── adult.csv
│
├── interim\            # SQLite hub (converte CSV → DB tipado)
│   ├── tpch-sf001.db
│   └── adult-census.db
│
├── processed\          # derivacoes para consumo
│   ├── tpch-sf001\
│   │   ├── csv\        # CSVs "limpos" a partir do SQLite
│   │   ├── jsonl\      # JSONL tipado
│   │   ├── markdown\   # MD tables
│   │   └── tcf\        # TCF (futuro)
│   └── adult-census\
│       └── ...
│
└── archives\           # backup frio (LZMA ultra)
    ├── tpch-sf001.tar.xz
    └── adult-census.tar.xz
```

### Por que Cookiecutter DS

- **Padrao da industria** adotado em centenas de projetos
- **raw → interim → processed** e um DAG claro
- **Dados raw imutaveis** (read-only apos download)
- Separacao clara de responsabilidades por pasta

Ver [research-notes/2026-04-10-storage-architecture.md](../research-notes/2026-04-10-storage-architecture.md)
para pesquisa completa e justificativa.

### Reproducibilidade

Qualquer usuario com o repositorio TCF pode regenerar a Camada B inteira
executando os scripts em ordem:

```bash
# Setup inicial (uma vez)
cp config/storage.json.example config/storage.json
# editar storage.json para apontar para seu disco

# Download datasets
python scripts/setup_tpch.py
python scripts/setup_adult.py

# Converter para SQLite
python scripts/csv_to_sqlite.py

# Gerar derivacoes
python scripts/derive_formats.py

# Pronto
```

## Camada C: Archive (opcional)

### Quando usar

Quando um dataset esta "congelado" (experimentos concluidos, nao ha mais
alteracao esperada) e voce quer liberar espaco em disco.

### Ratio tipico (LZMA -9e)

| Dataset | Original | LZMA | Ratio |
|---------|----------|------|-------|
| TPC-H SF=0.01 | ~40MB | ~4MB | 10% |
| Adult Census | ~5MB | ~1MB | 20% |
| TPC-H SF=0.1 (projecao) | ~400MB | ~40MB | 10% |

### Tempo

- **Compressao:** lento (~1-5 min para 100MB)
- **Descompressao:** rapido (segundos)

### Comandos

```bash
# Arquivar (libera disco, mantem archive)
python scripts/archive_dataset.py tpch-sf001 --compress

# Restaurar quando precisar
python scripts/archive_dataset.py tpch-sf001 --restore
```

### Caveat

LZMA e para **armazenamento frio**. O TCF encoder **nao** le direto
de .tar.xz. O fluxo e sempre: restore → disco → encoder.

Isso NAO afeta benchmarks — o TCF le do disco descomprimido normalmente.
LZMA e apenas para preservacao de espaco em repouso.

## Config de storage

### Problema

Meu disco Z: nao e o seu disco Z:. Como desacoplar?

### Solucao

**`config/storage.json.example`** (em git, template):

```json
{
  "data_root": "Z:/tcf-data",
  "note": "Copie este arquivo como storage.json e ajuste."
}
```

**`config/storage.json`** (gitignored, cada usuario cria):

```json
{
  "data_root": "Z:/tcf-data"
}
```

**`scripts/_paths.py`** (resolve automaticamente):

```python
from pathlib import Path
import json

def data_root() -> Path:
    config = Path("config/storage.json")
    if config.exists():
        cfg = json.loads(config.read_text(encoding="utf-8"))
        return Path(cfg["data_root"])
    # Fallback: pasta local para dev rapido
    return Path("data-local")

def external_dir(name: str) -> Path:
    return data_root() / "external" / name

def interim_db(name: str) -> Path:
    return data_root() / "interim" / f"{name}.db"

def processed_dir(name: str, fmt: str) -> Path:
    return data_root() / "processed" / name / fmt
```

### Fallback local

Se usuario nao criar `storage.json`, funciona com `./data-local/` dentro
do projeto. Util para dev rapido, mas **nao ideal** para OneDrive (vai
sincronizar). Por isso a config aponta para disco externo por padrao.

## Alternativas consideradas (e rejeitadas)

| Ferramenta | Status | Razao |
|-----------|--------|-------|
| DVC (Data Version Control) | Nao adotado | Overkill para solo dev |
| Git LFS | Nao adotado | Cotas GitHub, complexidade |
| S3/Azure/GCS | Nao adotado | Infra externa, pagamento |
| Oxen.ai | Futuro | Muito novo |
| lakeFS | Nao adotado | Petabyte-scale, overkill |

Ver [research-notes/2026-04-10-storage-architecture.md](../research-notes/2026-04-10-storage-architecture.md)
para analise completa.

## Compatibilidade com `.gitignore`

```gitignore
# Config local (storage.json tem caminhos especificos do usuario)
config/storage.json

# Fallback local (caso usuario nao configure storage)
data-local/

# Dados gerados por scripts (ficam em Camada B)
datasets/canonical/*/*.csv
datasets/canonical/*/*.tsv
datasets/*.db
datasets/sqlite/
datasets/derivations/
```

Metadados, READMEs e amostras pequenas sao whitelist (`!`) para
sobrescrever regras amplas.
