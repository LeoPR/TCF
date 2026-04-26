---
title: Assembly Overview — peças, fluxos e empacotamento
date: 2026-04-25
type: architecture
status: REFERÊNCIA — análise do estado atual e roadmap
---

# Assembly Overview — como as peças se encaixam

Este documento responde a três perguntas estruturais:

1. **O que já existe e o que falta?**
2. **Como as peças se montam para o desenvolvedor (mundo real) e para nós (experimentos)?**
3. **Qual é a fronteira de empacotamento de cada peça?**

Serve para evitar duplicação acidental e para guiar o que ainda precisa ser
construído.

---

## 1. Inventário — o que existe hoje

### Implementado e funcional

| Peça | Localização | Estado | Faz | Não faz |
|------|------------|--------|-----|---------|
| **TCF Core** | `src/tcf/` | ATIVO | encode/decode L0-L3, reversível, stdlib only | Conhecer DB, Shaper, LLM |
| **DatasetReader** | `scripts/dataset_reader.py` | ATIVO | API de leitura SQLite uniforme | Sample, format, opinar |
| **Shaper** | `scripts/shaper/` | ATIVO | extração estratificada FK-aware | Conhecer TCF, formatar prompt |
| **Synthetic generators** | `tests/fixtures/synthetic_v2.py`, `synthetic_domains.py` | ATIVO | gerar `(tables, meta)` reproduzível | I/O externo, format |
| **data_sources** | `experiments/eval/data_sources.py` | ATIVO | orchestrator-level data gateway (synthetic/canonical) | Construir payload, chamar LLM |
| **Payload builders** | `experiments/eval/run_m*.py::build_payload_*` | ATIVO (espalhado) | montar prompt: schema + stats + fewshot | Acessar dados, sample |
| **LLM client** | `experiments/eval/llm_eval/ollama_client.py` | ATIVO | HTTP para Ollama | Orquestrar |
| **Orquestrador (test runners)** | `experiments/eval/run_m*.py` | ATIVO (M1-M9) | coordenar load → payload → LLM → score → manifest | Conhecer internals dos componentes |
| **csv_to_sqlite + setup_*** | `scripts/` | ATIVO | ETL: external CSV → interim SQLite | Sample, format |

### Não implementado (roadmap)

| Peça | Local sugerido | Status | O que faria |
|------|---------------|--------|------------|
| **Schema Introspector** | `scripts/db/introspector.py` | ROADMAP | conectar em DB real, ler `information_schema`/`pg_catalog`/`sqlite_master`, devolver schema + stats + samples (sem rows completos) |
| **Schema Qualifier** | `scripts/db/qualifier.py` | ROADMAP | analisar schema dict, emitir warnings (órfãs, FKs soltos, tipos heterogêneos) |
| **TCF LLM-mode helper** | `src/tcf/llm.py` ou helper dedicado | A DECIDIR | API de alto nível: `format_for_llm(schema, stats, warnings, question)` → prompt string |

**Observação importante:** "TCF LLM mode" hoje **já existe parcialmente** —
está nos `build_payload_*()` espalhados pelos runners. O que falta é
**unificar** isto em uma API estável que o desenvolvedor chame, em vez de
cada experimento implementar a sua versão.

---

## 2. Esclarecimento crítico: Shaper e Orquestrador são EXPERIMENTAIS

Esta era a fonte da confusão. Marcando explicitamente:

| Peça | Quem usa | Por quê |
|------|----------|---------|
| **TCF Core** | Dev e nós | Compressão e formatação para LLM |
| **Schema Introspector** (futuro) | Dev e nós | Ler estrutura de DB real |
| **Schema Qualifier** (futuro) | Dev e nós | Avaliar qualidade do schema |
| **DatasetReader** | Nós (e dev se quiser) | API SQLite — útil mas não obrigatório para dev |
| **Shaper** | **SÓ NÓS** | Sample estratificado para experimentos. Dev tem dados próprios e faz seu próprio query/filter. |
| **data_sources.py** | **SÓ NÓS** | Gateway de orquestrador para escolher synthetic vs canonical. Dev não tem essa dualidade. |
| **run_m*.py (orquestrador)** | **SÓ NÓS** | Coordenação para experimentos com seeds, manifests, scoring. Dev escreve sua própria app. |

**Resumindo:** o desenvolvedor não tem orquestrador, não tem Shaper, não
tem data_sources. Ele tem **sua aplicação** (que é o orquestrador dele,
escrito por ele) e usa as peças neutras: TCF Core, Schema Introspector,
Schema Qualifier.

Para nós, Shaper é "filtro de redimensionamento horizontal+vertical sobre
dados controlados". Em modo passthrough (volume=None), Shaper apenas
entrega tudo. Mas ele está sempre no caminho — é como uma tampa
parametrizável.

---

## 3. Esclarecimento: TCF LLM-mode vs Schema Introspector

Você perguntou se esses dois se sobrepõem. Não — são **etapas sequenciais
complementares**:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌─────────┐
│  DB do dev   │ →  │  Schema      │ →  │  Schema          │ →  │  TCF    │
│  (Postgres,  │    │  Introspector│    │  Qualifier       │    │  LLM    │
│   MySQL,     │    │  (lê info_   │    │  (analisa,       │    │  mode   │
│   SQLite)    │    │   schema)    │    │   warnings)      │    │  format │
└──────────────┘    └──────────────┘    └──────────────────┘    └────┬────┘
                          │                     │                    │
                          ▼                     ▼                    ▼
                    schema_dict           schema_dict +           prompt
                    com tipos, FKs,       warnings (orphan,       string
                    cardinalidade,        dangling FK,            (LLM-pronto)
                    samples curtos        type-hetero)
                    (sem rows!)
```

**Schema Introspector:**
- **Input:** conexão com DB real
- **Output:** `dict` estruturado com schemas, FKs, tipos, cardinalidades, alguns samples
- **Não faz:** decidir se está bom, formatar texto

**Schema Qualifier:**
- **Input:** o `dict` do Introspector
- **Output:** mesmo `dict` + lista de warnings
- **Não faz:** I/O, formato

**TCF LLM-mode (helper):**
- **Input:** schema_dict + warnings + pergunta do usuário (todos opcionais conforme o caso de uso)
- **Output:** string de prompt pronta para enviar à LLM
- **Não faz:** chamar LLM, executar SQL

**O dado real (rows) NÃO passa por essa cadeia no caso de "LLM-mode".** Só
schema + stats + warnings circulam. Isso é o que diferencia do caso de
compressão (onde rows passam).

---

## 4. Os modos de TCF Core

Hoje, na prática, TCF Core opera em UM modo (compressão), e o "modo LLM"
está implementado fora dele (nos payload builders). A questão é:
**unificar ou manter separado?**

### Proposta: TCF Core continua só compressão; LLM-mode helper é separado

```
┌────────────────────┐    ┌───────────────────────┐
│   TCF Core         │    │   TCF LLM-mode helper │
│   (src/tcf/)       │    │   (a definir)         │
│                    │    │                       │
│   encode L0-L3     │    │   format_for_llm()    │
│   decode           │    │   ├─ usa TCF Core L0  │
│                    │    │   │  para representar │
│   Reversível       │    │   │  o schema         │
│   Stdlib only      │    │   ├─ adiciona stats   │
│                    │    │   ├─ adiciona warnings│
│   INPUT:           │    │   ├─ adiciona pergunta│
│   tables + meta    │    │   └─ output: prompt   │
│   OUTPUT:          │    │                       │
│   texto TCF        │    │   INPUT: schema_dict  │
│                    │    │   + warnings + Q      │
└────────────────────┘    │   OUTPUT: prompt str  │
                          └───────────────────────┘
```

Por que separar:
- TCF Core fica pequeno, testável, sem deps externas (invariante já documentada)
- LLM-mode pode evoluir (adicionar fewshot, safe-sql hints, etc.) sem inchar TCF Core
- Em distribuição: dev pode pegar só TCF Core (compressão) sem precisar do LLM helper

**Hoje:** os `build_payload_*()` em `experiments/eval/run_m*.py` cumprem
esse papel mas estão acoplados aos experimentos. **Falta extrair** isto
para um módulo público do dev.

---

## 5. Os 4 fluxos completos (dev e nós)

### 5.1 Fluxo Dev — Caso A: TCF compressor puro (round-trip)

```
[Dados do dev]
      │
      ▼
APP DO DEV  ─────►  TCF.encode()  ─────►  texto TCF (transmite/armazena)
                                                │
                                                ▼
                                          TCF.decode()  ─────►  tables (uso)
```

**Componentes usados:** apenas TCF Core.
**Status:** funciona hoje.

### 5.2 Fluxo Dev — Caso B: TCF + Qualifier (com hygiene)

```
[Dados do dev]
      │
      ▼
APP DO DEV  ─►  Schema Qualifier (warnings)  ─►  TCF.encode()  ─►  texto TCF
                       │                                                 │
                  log/warning para dev                                   ▼
                                                              TCF.decode() ─► tables
```

**Componentes usados:** TCF Core + Schema Qualifier.
**Status:** Qualifier é roadmap; resto funciona.

### 5.3 Fluxo Dev — Caso C: TCF como bridge LLM-SQL (schema-only)

```
[DB do dev]
      │
      ▼
APP DO DEV  ─►  Introspector  ─►  Qualifier  ─►  TCF LLM-mode  ─►  prompt
                    │                                                    │
                schema_dict                                               ▼
                (sem rows!)                                            LLM externa
                                                                          │
                                                                          ▼
                                                                       SQL gerado
                                                                          │
                                                                          ▼
                                                              APP DO DEV executa
                                                              no DB original
```

**Componentes usados:** Introspector + Qualifier + TCF LLM-mode helper +
LLM client (do dev) + executor (do dev).
**Status:** todos os 3 do meio são roadmap.

### 5.4 Fluxo Nosso (experimentador)

Os mesmos 3 caminhos acima, mas com:

- **Fontes:** canonical via Shaper (não DB do dev) OU synthetic generators
- **Quem coordena:** `run_m*.py` (orquestrador experimental) em vez de "app do dev"
- **Extras:** scoring, manifests, ground truth, comparação com baseline

```
[Z:/tcf-data canonical]  ou  [synthetic_v2/domains]
                  │
                  ▼
          data_sources.load_dataset()
                  │
                  ▼ (com Shaper FK-aware ou direto)
              tables, meta
                  │
                  ▼
ORQUESTRADOR (run_m*.py)
       │
       │ ├─► caso A: TCF.encode() para benchmark de compressão
       │ ├─► caso B: + Qualifier antes (quando tivermos)
       │ └─► caso C: payload builder (proto-TCF-LLM-mode)
       │           ↓
       │       prompt
       │           ↓
       │       LLM client (Ollama)
       │           ↓
       │       SQL
       │           ↓
       │       SQLite (in-memory) executa
       │           ↓
       │       resultado
       │           ↓
       │       score vs ground truth
       │           ↓
       │       manifest.jsonl
       │
       └─► fim da combinação
```

**Componentes usados:** TUDO. Shaper é nosso, payload builder é nosso,
manifest é nosso. Dev não vê nada disso.

---

## 6. O que falta para fechar os pacotes

### Pacote 1: TCF Core (já existe)
- ✅ Implementado em `src/tcf/`
- ✅ Stdlib only, ingênuo
- ✅ Pode ser distribuído como `pip install tcf` independente
- **Falta:** nada no escopo desta análise

### Pacote 2: TCF DB Tools (a criar)
Inclui Schema Introspector + Schema Qualifier + TCF LLM-mode helper.
- ❌ Schema Introspector: ler DB → schema_dict
- ❌ Schema Qualifier: schema_dict → schema_dict + warnings
- ❌ TCF LLM-mode helper: schema + warnings + Q → prompt
- **Decisão:** vivem juntos como `tcf_db` ou separados? Sugestão: **juntos** —
  são complementares, têm uso correlato (pipeline DB → LLM)

### Pacote 3: Experimental tools (nosso, não publicado)
- ✅ Shaper + DatasetReader (em `scripts/`)
- ✅ data_sources.py (em `experiments/eval/`)
- ✅ run_m*.py (em `experiments/eval/`)
- **Falta:** nada — funciona como está. Não precisa virar pacote distribuível.
  Eventualmente, **Shaper pode ser extraído** se houver interesse externo
  (ver [research-notes/2026-04-25-shaper-as-standalone-tool.md](../research-notes/2026-04-25-shaper-as-standalone-tool.md)).

---

## 7. Mapa de decisão para próximas etapas

Em ordem sugerida, depois de validar que esta análise está correta:

### Etapa 3 — Extrair payload builder para `tcf_llm` (módulo)
Razão: hoje cada `run_m*.py` tem o seu `build_payload_*()`. Há
duplicação. Extrair para um módulo único e usar o módulo em todos os
runners.

Nota: ainda fica em `experiments/eval/llm_eval/` (não em `src/tcf/`)
porque pode crescer com fewshot, safe-sql hints, warnings — tudo isso
não é "core" do TCF.

### Etapa 4 — Implementar Schema Introspector (SQLite primeiro)
Razão: começar pelo mais simples (SQLite) para validar a abstração.
Depois Postgres, MySQL.

### Etapa 5 — Implementar Schema Qualifier
Razão: roda sobre o output do Introspector. Validar inicialmente com
TPC-H e Adult Census.

### Etapa 6 — Validação meta-experimental
Rodar Qualifier sobre TPC-H/Adult Census, ver se emite warnings em
schemas conhecidamente bons.

### Etapa 7 — TCF-DB Extractor (componente 3) ganha implementação
Tudo integrado: dev pode pegar `tcf_db` e rodar o caminho completo
(Caso C) sobre seu DB.

---

## 8. Perguntas em aberto

1. **`tcf_llm` extraído ou mantido em experiments/?**
   Sugestão: extrair para `experiments/eval/llm_eval/payload_builder.py` agora
   (uniformiza), e considerar empacotar como `pip install tcf-llm` depois
   junto com `tcf-db`.

2. **Schema Qualifier é parte de `tcf_db` ou separado?**
   Sugestão: parte do `tcf_db`. Eles formam um pipeline único.

3. **Schema Introspector suporta múltiplos dialetos desde o início ou só SQLite?**
   Sugestão: SQLite primeiro (mais simples), arquitetura aberta para
   plugar Postgres/MySQL.

4. **Shaper extraído como tool independente?**
   Sugestão: pós-paper, conforme research-note. Por ora, fica em scripts/.

---

## 9. TL;DR para você analisar

- **Quase tudo já existe.** TCF Core, Shaper, DatasetReader, data_sources,
  payload builders (espalhados), runners — tudo funcional.
- **Falta para o desenvolvedor:** Schema Introspector + Schema Qualifier +
  TCF LLM-mode helper unificado. Os três formam o pacote `tcf_db`.
- **Para nós, NÃO falta nada essencial.** Etapa 1+2 fechou a unificação
  experimental.
- **Confusão resolvida:** Shaper, data_sources e orquestrador são SÓ
  experimentais. Dev tem sua app + chama TCF/Introspector/Qualifier
  diretamente.
- **TCF LLM-mode vs Introspector:** etapas sequenciais, não overlap.
  Introspector pega schema do DB; TCF LLM-mode formata schema+warnings
  para o prompt.

Sugestão de leitura:
1. Esta análise (você está aqui)
2. [data-pipeline.md](data-pipeline.md) — fluxo experimental atual (já rodando)
3. [components/3-tcf-db-extractor.md](../components/3-tcf-db-extractor.md) —
   visão do componente desenvolvedor
4. [research-notes/2026-04-24-schema-qualifier.md](../research-notes/2026-04-24-schema-qualifier.md) —
   detalhe do Qualifier

---

## Anexo A — Cenário 1 (CSV/JSON → TCF) e a decisão "Opção D"

### Contexto

Cenário básico do desenvolvedor: tem dados em CSV/JSON/outros, quer
**comprimir e descomprimir via TCF** — round-trip puro, sem LLM.

### Estado atual investigado (2026-04-25)

TCF Core (`src/tcf/encoder.py`) tem **3 entry points** em camadas:

| API | Aceita | Status |
|-----|--------|--------|
| `encode_columns(name, dict[str, list[str]], config)` | colunas em memória | CORE PURO — sem IO, sem parsing, sem filesystem |
| `encode_rows(name, list[dict], config)` | linhas em memória | conveniência — transpõe linhas → colunas |
| `encode(meta_path, data_dir, config)` | CSV em disco + metadata.json | LEGACY — único ponto onde TCF "entende" um formato externo |

Decoder (`src/tcf/decoder.py`):
- `decode(text)` retorna `dict[table, list[dict]]` — entrega Python puro

Outros formatos (JSON, JSONL, Markdown, TOON):
- **Não há helpers** em `src/tcf/`
- Writers existem em `scripts/writers/` mas são **fora do TCF Core**
  (usados apenas em `derive_formats.py` para gerar comparativos)

### Histórico verificado

Não há remoção de funcionalidade no git (`git log --diff-filter=D src/tcf/`).
O commit `2e990d5` (13/abril) refatorou em 3 camadas mas **adicionou**
APIs puras (`encode_columns`/`encode_rows`); manteve `encode()` legacy.

Se houve discussão sobre adicionar JSON nativo, foi informal e não virou
código.

### Decisão registrada: Opção D (manter ingenuidade + cookbook)

**TCF Core não cresce para entender mais formatos.** O usuário com JSON,
JSONL, Pandas, Parquet etc. parseia em 1-3 linhas e passa para
`encode_rows()`. Documentação fornece o cookbook.

**Razão:** o invariante "TCF é ingênuo" tem motivo prático — cada formato
suportado nativamente arrasta dívidas (encoding, dialects, malformed data).
Hoje o `encode()` legacy já carrega isso para CSV. Adicionar JSON nativo
dobra a superfície sem ganho científico real.

### Inventário de coisas que precisam mudar para alinhar com Opção D

**Não muda código** — só vocabulário, ordem de apresentação e cookbook.

#### Tier 1 — Documentação (alta prioridade, baixo risco)

| Arquivo | Mudança |
|---------|---------|
| `README.md` (raiz) | Inverter ordem: `encode_columns`/`encode_rows` como API primária; `encode()` legacy como apêndice. Hoje features CSV+metadata.json no quick start, o que sugere falsamente que TCF "entende CSV" |
| `docs/architecture/overview.md` | Mesmo ajuste — exemplo CLI atual sugere CSV-first |
| `docs/architecture/boundaries.md` | Atualizar diagrama do encoder para mostrar 3 camadas, `encode()` legacy explícito |
| `docs/architecture/data-pipeline.md` | No bloco "TCF Core" do diagrama, mostrar `encode_columns/rows` como entry, não `encode(meta_path, data_dir)` |
| `docs/components/1-tcf-core.md` | Adicionar seção "API e formatos de entrada" depois da spec, antes da invariante |
| `src/tcf/cli.py` (docstring) | Header atual diz `encode CSV + metadata.json -> TCF` — ajustar para `encode (legacy CSV mode) -> TCF` |
| `src/tcf/encoder.py` (docstring de `encode()`) | Já diz "Legacy convenience wrapper" ✓ — só verificar consistência |

#### Tier 2 — Cookbook unificado (criar uma vez, linkar de todo lado)

Criar `docs/components/1-tcf-core-cookbook.md` (ou seção dentro de
`1-tcf-core.md`) com snippets para cada formato comum:

```python
# CSV (sem metadata.json, sem JOIN automático)
import csv
with open("file.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
text = encode_rows("my_table", rows)

# JSON (lista de objetos)
import json
rows = json.load(open("file.json"))
text = encode_rows("my_table", rows)

# JSONL (NDJSON)
with open("file.jsonl") as f:
    rows = [json.loads(line) for line in f]
text = encode_rows("my_table", rows)

# Pandas
text = encode_rows("my_table", df.to_dict("records"))

# Polars
text = encode_rows("my_table", df.to_dicts())

# Parquet (via pandas)
import pandas as pd
text = encode_rows("my_table", pd.read_parquet("f.pq").to_dict("records"))

# SQL query result (via cursor)
cur.execute("SELECT * FROM t LIMIT 100")
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]
text = encode_rows("my_table", rows)
```

Cada snippet é 2-3 linhas. Honra a ingenuidade.

#### Tier 3 — Decisão sobre CLI (decidir antes de mexer)

CLI atual: `python -m tcf encode --meta X --data-dir Y` — só aceita CSV +
metadata.json. **Pergunta em aberto:**

- (a) Manter como está (CSV legacy é a única CLI; doc diz que API
  Python é a forma moderna)
- (b) Adicionar `python -m tcf encode-jsonl file.jsonl --name t` (e
  similares) — vai contra Opção D porque adiciona parsers nativos
- (c) Refatorar CLI para `python -m tcf encode --from csv|jsonl|json
  --input file --name t` — adiciona parsing, vai contra D
- (d) Deprecar CLI complexa, apontar para Python API + `python -c
  "from tcf import encode_rows; ..."` — minimal, mais consistente com D

**Sugestão:** **(a) manter**. CLI legacy continua útil para o caso CSV
(que já é suportado); para JSON/Pandas/outros, README diz "use a API
Python, é 3 linhas".

#### Tier 4 — Futuro do `encode()` legacy (decidir antes de mexer)

`encode(meta_path, data_dir)` é o único ponto onde TCF "entende CSV".
Opções:

- (a) Manter como wrapper conveniente — não adiciona, não remove
- (b) Marcar como deprecated (DeprecationWarning) e remover em v0.3
- (c) Mover para `scripts/tcf_csv_helper.py` ou similar — sai do core

**Sugestão para discussão futura:** (a) por enquanto. Se a base de usuários
do CSV-mode for pequena (apenas nosso quick start no README), considerar
(b)/(c) numa versão major.

### Checklist de execução (quando decidir fazer)

Tudo abaixo é commit único, baixo risco, zero código novo:

- [ ] Inverter ordem em `README.md` (Python API → Legacy CSV CLI)
- [ ] Inverter ordem em `docs/architecture/overview.md`
- [ ] Atualizar diagrama do encoder em `boundaries.md` (3 camadas)
- [ ] Ajustar bloco TCF em `data-pipeline.md` (mostrar `encode_columns/rows`)
- [ ] Adicionar seção "API e entrada de dados" em `1-tcf-core.md`
- [ ] Criar/anexar cookbook (CSV, JSON, JSONL, Pandas, Polars, SQL, Parquet)
- [ ] Ajustar header de `cli.py` para deixar claro que é legacy CSV mode
- [ ] Verificar consistência em `__init__.py` (já está OK)

### Não fazer (consequências da Opção D)

- Não criar `encode_csv_file()`, `encode_json_file()`, `encode_jsonl_file()`
- Não adicionar `--from json|jsonl` à CLI
- Não importar `pandas`, `polars`, `pyarrow` em `src/tcf/`
- Não criar pacote `tcf-io` ou `tcf-readers`

Se um usuário pedir suporte nativo a JSON/Pandas, a resposta é o cookbook
(3 linhas) + invariante (TCF Core fica pequeno e estável).

---

## Anexo B — Cenário 2 (TCF + Schema Qualifier opcional)

### Contexto

Dev tem 2-3 tabelas em CSV/JSON, já parseou para `dict[table, list[dict]]`,
quer **inserir uma camada de Schema Qualifier antes do TCF** para detectar
inconsistências (FKs soltos, dados vazios demais, outliers, etc.) sem
bloquear o fluxo. Saída do Qualifier é **bypass + log paralelo**.

### Análise crítica — está alinhado com o projeto?

**Sim, e ainda corrige uma ambiguidade que tinhamos.** Antes, em
`research-notes/2026-04-24-schema-qualifier.md` e
`components/3-tcf-db-extractor.md`, o Qualifier estava descrito como
**módulo dentro do TCF-DB-Extractor** — sequencial após o Schema Introspector.
Sua descrição agora generaliza: o Qualifier opera sobre **qualquer
`dict[table, list[dict]] + meta`**, não só sobre saída do Introspector.

Isto é **mais correto**. O Qualifier é uma **camada genérica** com:
- **Input:** o mesmo formato que TCF aceita (`tables, meta`)
- **Output (data path):** bypass exato — entrega `tables, meta` idênticos
- **Output (side channel):** `WarningReport` em log/variável/arquivo

Resultado: pode rodar **antes de TCF** independente de onde os dados vieram
(CSV via cookbook, JSON, Introspector, Shaper, qualquer coisa).

### Por que esse design é elegante

1. **Composability via input/output unificado** — Qualifier e TCF aceitam
   o mesmo shape (`tables, meta`). Não precisa adapters entre as etapas.
   Pode chamar `tcf.encode_rows(name, qualifier.check(rows).tables[name])`
   ou ignorar Qualifier completamente.

2. **Bypass como default** — não bloqueia nem corrompe pipeline. Dev
   decide o que fazer com warnings (ignorar, logar, mostrar ao usuário,
   abortar build). Qualifier nunca decide por ele.

3. **Side channel para warnings** — TCF Core fica limpo (não conhece
   warnings). Orquestrador decide injetar warnings no prompt LLM (caso C)
   ou no log do dev (caso A/B).

4. **Lib utils compartilhadas** — TCF Core já tem detecção de tipo,
   cardinalidade, stats por coluna (em `src/tcf/encoder.py`:
   `_detect_column_type`, stats numéricas). Qualifier reusa isso.
   **Direção segura:** Qualifier importa de TCF; TCF não importa Qualifier.

### Diagrama atualizado

```
            tables, meta (input — Python dict puro)
                       │
                       ▼
              ┌──────────────────────┐
              │  Schema Qualifier    │   (CAMADA OPCIONAL,
              │  (camada genérica)   │    gateway entre fonte
              │                      │    e TCF)
              │  - detecta órfãs     │
              │  - FKs soltos        │
              │  - tipos heterogên.  │
              │  - outliers (futuro) │
              │  - junções suspeitas │
              └────┬───────────┬─────┘
                   │           │
        bypass:    │           │  side channel:
        igual ao   │           │  WarningReport
        input      │           │  (log/var/file)
                   │           │
                   ▼           └──► consumido pelo
              tables, meta          orquestrador/dev
                   │
                   │ (entra no TCF como se Qualifier não existisse)
                   ▼
        ┌───────────────────────┐
        │      TCF Core         │   modo compressão:
        │   encode/decode       │   tables → texto comprimido
        └───────────────────────┘
                  ou
        ┌───────────────────────┐
        │  Payload Builder      │   modo LLM:
        │  (orquestrador)       │   tables + warnings + pergunta
        │  - usa TCF L0         │   → prompt
        │  - injeta warnings    │
        │  - injeta pergunta    │
        └───────────────────────┘
```

### O ponto da "saída pro formato TCF" — clarificação

Você falou: *"a saída dele também é pro formato TCF"*. Tem duas leituras
possíveis e a primeira é a correta:

- **(✓ correta)** Saída em formato compatível com **input do TCF** —
  `dict[table, list[dict]] + meta`. É o mesmo shape Python que TCF aceita.
  "Qualifier emite o mesmo formato de input que TCF aceita" — composabilidade.

- **(✗ incorreta)** Saída no formato TEXTUAL TCF (L0-L3 comprimido).
  Qualifier não comprime — só verifica. Quem comprime é o TCF Core.

Anotação para evitar confusão futura.

### Posição na arquitetura geral

Qualifier é **a 4ª peça neutra** (não-experimental) ao lado de:
- TCF Core (compressão/codec)
- Schema Introspector (DB → tables/meta) — futuro
- TCF LLM-mode helper (tables/warnings/Q → prompt) — futuro

Todas elas:
- Aceitam ou produzem `dict[table, list[dict]] + meta` (formato comum)
- Não conhecem Shaper, data_sources, orquestrador
- Podem ser usadas standalone pelo dev

### Sobre evolução futura (correções lógicas)

Você mencionou: *"eventualmente ele poderia fazer algumas correções lógicas
se o desenvolvedor quiser"*.

**Sugestão arquitetural:** se Qualifier começar a corrigir, ele vira ETL.
Isso é uma responsabilidade diferente.

Manter Qualifier como **somente leitura** (warnings) e criar uma peça
separada `Schema Repair` (ou `Data Cleaner`) que toma `(tables + warnings)`
e produz `tables_corrigido`. Seria uma 5ª peça neutra, opcional, depois do
Qualifier:

```
tables ──► Qualifier ─► tables (bypass) ──► [Repair opcional] ──► TCF
                  │                          ▲
                  └─► warnings ──────────────┘
```

Isto preserva o princípio "uma peça, uma responsabilidade".

### Lib utils que Qualifier pode reusar do TCF Core (mapeamento concreto)

| Util em `src/tcf/encoder.py` | Uso pelo Qualifier |
|------------------------------|---------------------|
| `_detect_column_type(values)` | detectar tipos heterogêneos (declarado != real) |
| Cardinality counting (set + len) | PK com duplicatas, candidatos a PK |
| Stats numéricas (min/max/mean) | outliers |
| Null counting | "dados vazios demais" |
| `_fk_hint(col, table_names)` heuristic | FKs implícitos (col `id_X` sem constraint) |

**Caminho de extração futuro:** mover essas utils de
`src/tcf/encoder.py` para `src/tcf/_column_utils.py` (módulo privado mas
importável internamente). Qualifier (em `scripts/db/qualifier.py` ou onde
for) importa de lá. TCF não importa Qualifier — direção segura.

### Inventário de mudanças para implementar Qualifier (futuro)

Tudo é trabalho de criação, baixo risco no que já existe.

#### Novo

- [ ] `src/tcf/_column_utils.py` — extrair utils que serão compartilhadas
- [ ] `scripts/db/qualifier.py` — implementação core (input → bypass + warnings)
- [ ] `scripts/db/__init__.py` — pacote
- [ ] Tests em `tests/test_qualifier.py` cobrindo os 5+ tipos de warning
- [ ] Doc `docs/components/qualifier.md` (ou seção em 3-tcf-db-extractor)

#### Modificações (mínimas)

- [ ] `src/tcf/encoder.py` — refatorar para usar `_column_utils` (sem
  mudar comportamento; verificável por roundtrip)
- [ ] Atualizar `data-pipeline.md` para mostrar Qualifier opcional na cadeia
- [ ] Atualizar `assembly-overview.md` removendo "futuro" do Qualifier
- [ ] Atualizar `components/3-tcf-db-extractor.md` esclarecendo que Qualifier
  é peça neutra (pode ser usada sem o Extractor)
- [ ] Atualizar `research-notes/2026-04-24-schema-qualifier.md` com generalização
  (Qualifier não depende de DB — opera sobre qualquer tables/meta)

### Não fazer (consequências da decisão)

- Não mover Qualifier para dentro de `src/tcf/` — TCF Core continua ingênuo
- Não fazer Qualifier corrigir dados (vira `Schema Repair` separado se for o caso)
- Não acoplar Qualifier ao Introspector — eles são peças independentes
- Não passar warnings para `tcf.encode_*()` — TCF nunca recebe warnings
  (warnings vão para orquestrador via side channel)

### Resposta direta às suas perguntas

> *"Veja se faz sentido"*
Faz total sentido e melhora a arquitetura — generaliza Qualifier de
"módulo do Introspector" para "camada neutra opcional".

> *"Estou fugindo do projeto?"*
Não. Está exatamente alinhado com o que documentamos em
`research-notes/2026-04-24-schema-qualifier.md` e nos casos A/B/C do fluxo
dev em `assembly-overview.md` seções 5.1 a 5.4.

> *"Manter assim é bom porque dá pra reaproveitar lib utils comuns"*
Confirmado — mapeamento concreto de utils está acima. Direção da
dependência é Qualifier → TCF (não o contrário), preservando invariante.

---

## Anexo C — Cenário 3 (DB real → Schema Extractor → TCF LLM-mode)

### Contexto

Dev tem **um banco de dados real** (ou conjunto grande de arquivos) e
**não conhece toda a estrutura**. Precisa de uma ferramenta que:

1. Conecte no DB
2. Vasculhe estruturas (tabelas, colunas, tipos, PK, FK declarados,
   índices, cardinalidades)
3. Produza um apanhado de schemas + estatísticas + conexões lógicas
4. Funcione **mesmo em DBs mal-modelados** (sem PK/FK declarados),
   apenas extraindo o que é fato observável — sem inferir

Esta peça é o **Schema Extractor** (até agora chamado em outros docs de
**Schema Introspector** — ver "Nota de nomenclatura" abaixo).

### Análise crítica — está alinhado com o projeto?

**Sim, e adiciona precisão a algo que estava implícito.** Concretamente:

1. **Extractor é peça neutra independente** — não é módulo do
   TCF-DB-Extractor (componente 3); é uma peça que **o componente 3
   compõe**. Mesma lógica do Qualifier no Anexo B.

2. **Distinção entre fato e opinião** — Extractor produz **fatos
   observáveis** (`pedidos` tem coluna `id_usuario INT NOT NULL`).
   Qualifier produz **opiniões/warnings** ("`id_usuario` parece FK
   implícito mas não tem constraint declarada"). Separação correta.

3. **DB mal-modelado é caso real, não exceção** — em produção, a maioria
   dos DBs tem inconsistências. Tratar isso como cenário de primeira
   classe é mais honesto cientificamente.

4. **Não inferir relações sem evidência** — seu exemplo
   (Usuarios/Produtos/Pedidos sem keys) é correto: sem PK/FK declarados
   e sem nomes que sugiram FK, o Extractor não tem como ligar tabelas.
   Resultado: 3 tabelas "órfãs" no relatório. Qualifier pode emitir
   warning de "FK implícito por nome" se aplicável (ex: `id_usuario`),
   mas como sugestão, não conclusão.

### A invariante de uso que você levantou

Você concluiu corretamente: **TCF compressão não se aplica neste cenário,
só TCF LLM-mode.** Razão: não há rows completos para comprimir — só
schema + stats.

Vale registrar como **invariante de uso explícita**:

> Quando o pipeline começa em "DB sem extração de rows completos", TCF
> Core nunca é usado em modo compressão. Apenas o caminho LLM-mode
> (formatação de payload) faz sentido.

### Exceção parcial — "samples" não são "dados completos"

Você mencionou: *"dependendo do sistema, até daria pra tirar alguns
dados básicos para auxiliar na query da LLM"*.

Isso é exatamente o que o sistema atual já faz no LLM-mode:

```
### vendas (509 rows)
  pessoa TEXT, cardinality=24, samples=[Ana, Bruno, Carla]
  total REAL, range=[9.01, 759.8], mean=289.68, cardinality=412
```

**3 valores por coluna** chegam ao LLM como exemplos — não como dataset.
Eles servem para o modelo entender o **tipo de valor** ("essa coluna tem
nomes brasileiros, não números de produto"). Privacidade e volume são
preservados.

Vale formalizar isso como **3 categorias** distintas:

| Categoria | O que é | Volume | Onde aparece | Para quê |
|-----------|---------|--------|--------------|----------|
| **Dados completos (rows)** | Todos os valores de todas as linhas | N rows × M cols | TCF compressão | Round-trip exato |
| **Stats** | min/max/mean/cardinality/null count por coluna | constante (~5 nums/col) | TCF LLM-mode | Dar contexto numérico ao modelo |
| **Samples** | 3 valores ilustrativos por coluna | 3 × M cols | TCF LLM-mode | Dar contexto semântico ao modelo |

No Cenário 3, **rows completos não passam**. Stats + samples sim.

### Pipeline atualizado para Cenário 3

```
   DB do dev (Postgres/MySQL/SQLite)
            │
            │  scripts/db/introspector.py (futuro)
            │  - lê information_schema/pg_catalog/sqlite_master
            │  - lê PK/FK declarados
            │  - calcula cardinalidades, null rates, min/max
            │  - extrai samples (3 valores/coluna via SELECT LIMIT 3)
            │  - NÃO extrai rows completos
            ▼
   schema_pack: dict[table, {columns, types, pk, fk, stats, samples}]
            │
            │  (peça opcional — bypass + side channel)
            ▼
   ┌─────────────────────────┐
   │  Schema Qualifier       │
   │  - sobre schema_pack    │
   │  - emite warnings:      │
   │    * tabelas órfãs      │
   │    * FKs implícitos     │
   │    * tipos heterogêneos │
   │    * cardinalidade      │
   │      suspeita           │
   │  - bypass do schema_pack│
   └────┬────────────┬───────┘
        │            │
        │ bypass     └────► WarningReport
        │
        ▼
   schema_pack (igual)
            │
            │  (orquestrador junta com pergunta NL)
            ▼
   ┌──────────────────────────────────┐
   │   TCF LLM-mode helper (futuro)   │
   │   - usa TCF L0 para formatar     │
   │     schema_pack como texto       │
   │   - injeta warnings              │
   │   - injeta pergunta NL do usuário│
   │   → output: prompt string        │
   └──────────────────┬───────────────┘
                      │
                      ▼
                LLM externa
                      │
                      ▼
                  SQL gerado
                      │
                      ▼
   Orquestrador (app do dev) executa SQL no DB original
```

### Casos de qualidade do DB

| Qualidade do DB | Extractor produz | Qualifier emite | Resultado prático |
|----------------|------------------|-----------------|-------------------|
| Bem-modelado (PK/FK declarados, tipos consistentes) | schema_pack rico | poucos/nenhum warning | LLM gera SQL com JOIN explícito, alta accuracy esperada |
| Médio (alguns FKs implícitos, alguns NULLs) | schema_pack ok | warnings de FK implícito | LLM informada das incertezas; SQL mais defensivo |
| Mal-modelado (sem keys, tabelas órfãs) | schema_pack com tabelas isoladas | muitos warnings; "órfã: X" | LLM sabe que não pode fazer JOIN entre X e Y |
| Patológico (sem keys nem nomes sugestivos) | 3 tabelas isoladas | warnings de "sem relação observável" | LLM responde "não consigo correlacionar X e Y" — comportamento esperado e honesto |

### Nota de nomenclatura — Extractor vs Introspector

Em docs anteriores chamei essa peça de **Schema Introspector** (em
`research-notes/2026-04-24-schema-qualifier.md` e
`components/3-tcf-db-extractor.md`).

Você usou **Schema Extractor** neste cenário. As duas palavras descrevem
a mesma coisa, mas têm conotações sutis:

- **Introspector:** sugere via system tables (`information_schema`,
  `pg_catalog`, `sqlite_master`) — termo técnico de DB
- **Extractor:** mais geral, sugere "tira informação de algum lugar"

**Sugestão para alinhamento:** padronizar como **Schema Introspector**
quando estamos falando do módulo técnico (sabe ler system tables).
"Extractor" pode ser sinônimo coloquial — ambas terminologias funcionam.

Aguardando confirmação ou contraproposta sua para definir nos docs.

### Composição: Componente 3 (TCF-DB Extractor) é a soma das peças

Importante: o **componente 3** documentado em
`docs/components/3-tcf-db-extractor.md` é o **pacote integrado** que
junta:

- Schema Introspector (Cenário 3 sem Qualifier)
- Schema Qualifier (Anexo B + Cenário 3 com warnings)
- TCF LLM-mode helper (formata payload)
- Query Executor (roda SQL no DB original)

Cada peça **funciona standalone** (dev pode usar só Introspector se quer
ver estrutura). O componente 3 é a **conveniência** de ter tudo
empacotado para o caso "DB → pergunta NL → resultado".

Diagrama mental:
```
TCF-DB Extractor (componente 3, pacote conveniência)
   ├── Schema Introspector
   ├── Schema Qualifier (opcional, importa de Introspector ou outra fonte)
   ├── TCF LLM-mode helper
   └── Query Executor
```

Cada peça tem doc próprio; componente 3 documenta a **integração**.

### Inventário de mudanças para implementar Cenário 3

Sobreposição parcial com Anexo B (Qualifier).

#### Novo (acima do Anexo B)

- [ ] `scripts/db/introspector.py` — interface comum + impl SQLite
  primeiro, Postgres/MySQL depois
- [ ] `scripts/db/__init__.py` — pacote (compartilhado com Qualifier)
- [ ] Tests em `tests/test_introspector.py` (sample DB SQLite)
- [ ] Doc `docs/components/introspector.md` (ou seção em 3-tcf-db-extractor)

#### Decisões em aberto antes de implementar

1. **Dialect support inicial:** SQLite primeiro? Sugestão: sim, é o que
   já temos rodando em `Z:/tcf-data/interim/`.
2. **Sample size:** 3 por coluna como hoje? Sugestão: parametrizável,
   default 3.
3. **Como tratar BLOBs/TEXT longos:** truncar em N chars ou skip?
   Sugestão: skip se tamanho > limite configurável.
4. **Privacy mode:** opção para hash/anonymize samples? Sugestão:
   futuro, fora do MVP.
5. **Caching:** introspection é caro em DBs grandes — cachear schema_pack?
   Sugestão: futuro.

### Não fazer (consequências)

- Não ler rows completos no Cenário 3 (defeito o propósito)
- Não inferir relações sem evidência (Extractor reporta fato; Qualifier
  pode sugerir, nunca afirmar)
- Não comprimir schema_pack via TCF compressão (não é o uso correto)
- Não acoplar Introspector ao Qualifier (peças independentes)

### Resposta direta às suas perguntas

> *"Esse mecanismo poderia comprimir de fato? Só poderia ser usado para LLM, certo?"*
Correto. Sem rows completos, TCF compressão não tem o que comprimir.
Apenas TCF LLM-mode (formatação de payload) faz sentido.

> *"Não ter dados é um pouco de exagero porque, dependendo do sistema, até daria pra tirar alguns dados básicos"*
Sim — esses são os **samples** (3 valores/coluna), categoria diferente
de "rows completos". Já estão na arquitetura.

> *"Para o TCF no modo LLM ele é mais útil como schemático certo?"*
Correto. TCF LLM-mode opera principalmente sobre schema + stats +
samples. Rows completos são opção (caso A/B), não necessidade.

---

---

## Anexo D — Cenário 4 (Shaper / Sampler — peça experimental)

### Contexto

**Shaper é nossa peça**, não do desenvolvedor. Serve para modular
**quantidade** e **complexidade** de datasets canônicos para experimentos.

Datasets canônicos cobrem domínios diferentes: comercial (TPC-H),
demográfico (Adult), financeiro, ERP, CRM, didático. O Shaper produz
amostras **estatisticamente estratificadas** — não aleatórias 10%, mas
proporcionais que mantêm representatividade mesmo com JOINs.

Também reduz **complexidade**: do dataset com N tabelas para subset com
2-3 tabelas (níveis `minimal`, `core`, `chain`, `full` já definidos).

### O eixo horizontal × vertical (confirmação da sua intuição)

Sua proposta foi: *"a gente força os formatos horizontais, e o shaper cuida
mais da parte vertical (estratificação de linhas)"*.

**Está correta e é exatamente o que implementamos hoje.** Formalizando:

| Dimensão | O que define | Quem decide | Como |
|----------|-------------|-------------|------|
| **Horizontal** (schema) | quais tabelas, quais colunas, quais joins | Nós (pesquisadores) | `schema=["partsupp","part","supplier"]` ou `schema_levels[name]["chain"]` |
| **Vertical** (rows) | quantas linhas, qual ordem, estratificação | Shaper (mecanicamente) | strategies `volume`, `fk_preserving`, `stratify`, `ordering` |

Resultado: **Shaper é "burro mas parametrizado"**. Não tenta adivinhar
nada. Recebe configuração horizontal + parâmetros verticais, e executa.

Isso responde sua pergunta diretamente:

> *"Vale a pena deixar genérico e inteligente, ou fazer análise externa
> e Shaper só executar?"*

**Resposta: Shaper só executa.** A "análise" (que tabelas, qual chave de
estratificação) é nossa, codificada em `CANONICAL_PROFILES` em
`experiments/eval/data_sources.py` e `SCHEMA_LEVELS` em
`scripts/shaper/strategies/schema.py`.

### Estado atual do Shaper

#### Estratégias implementadas e funcionais

| Estratégia | Status | O que faz |
|-----------|--------|-----------|
| `schema_filter` | ✅ ATIVO | Restringe ao subset de tabelas pedido (horizontal) |
| `fk_preserving` | ✅ ATIVO | Sample fact + filtra dims preservando FK integrity (vertical com integridade) |
| `volume` | ✅ ATIVO | Sample N rows ou fração — só executa quando `fk_preserving=False` |
| `ordering` | ✅ ATIVO | natural / random:seed / sorted:col / reverse:col |

#### Todas as estratégias implementadas (audit 2026-04-26)

| Estratégia | Status | Notas |
|-----------|--------|-------|
| `stratify` | ✅ ATIVO (2026-04-25) | Proportional allocation Neyman-style + min-1 por grupo |
| `compressibility` | ✅ ATIVO (audit 2026-04-26) | Score por raridade categorical (-log2 freq), filtra por quantil; cache em disco |
| `join` | ✅ ATIVO (audit 2026-04-26) | normalized (default) ou flat (denormaliza via FK metadata) |

`stratify` foi implementado em 2026-04-25. Validação:
- Adult Census volume=20 com `stratify_by='class'`: random std=9.7 (range 10-45%)
  → stratify std=0.0 (consistente em 23.9-25%, próximo da população real)
- Edge case 16 grupos `education`: cada grupo aparece com ≥1 row mantendo dominância dos majoritários
- TPC-H regressão zero (mesmos 66/94/100 quando stratify_by=None)

### A "inteligência" do Shaper vem da configuração, não do código

**Por dataset, definimos antes de qualquer experimento:**

1. **Schema levels** — quais tabelas formam `minimal`/`core`/`chain`/`full`
   (em `scripts/shaper/strategies/schema.py::SCHEMA_LEVELS`)
2. **Fact table** — qual é a tabela onde a maior parte das FKs aponta
   (em `experiments/eval/data_sources.py::CANONICAL_PROFILES`)
3. **Stratify column** (futuro, quando implementar) — qual coluna mantém
   representatividade quando reduzimos volume

Exemplo TPC-H já configurado:

```python
# scripts/shaper/strategies/schema.py
SCHEMA_LEVELS = {
    "tpch-sf001": {
        "minimal": ["customer"],
        "core":    ["customer", "orders"],
        "chain":   ["customer", "orders", "lineitem"],
        "full":    ["region", "nation", ...],  # 8 tabelas
    },
}

# experiments/eval/data_sources.py
CANONICAL_PROFILES = {
    "tpch-sf001": {
        "schema": ["partsupp", "part", "supplier"],
        "fact_table": "partsupp",
    },
}
```

**Isso é a análise externa que você mencionou.** Não está no Shaper —
está em arquivos de configuração que **nós** criamos para cada dataset.

Para um dataset novo (ex: Northwind), passos:
1. Rodar Schema Introspector (futuro) ou ler manualmente metadata
2. Decidir quais subsets fazem sentido por nível
3. Adicionar entrada em `SCHEMA_LEVELS` e `CANONICAL_PROFILES`
4. Pronto — Shaper já sabe o que fazer

### Conexão Shaper → Qualifier (nosso uso meta)

Você sugeriu: *"ele mesmo pode passar depois pelos filtros do
qualificador por exemplo, para ver se tem algo errado"*.

**Ótima ideia para validação meta-experimental.** Pipeline:

```
canonical DB → Shaper (subset) → Qualifier (verifica subset)
                                     │
                                     ▼
                                WarningReport
                                (subset pode ter perdido representatividade,
                                 quebrado FK na samplagem, criado órfãs, etc.)
```

Casos onde isso seria útil:
- Validar que `fk_preserving` realmente preservou todos os FKs
- Detectar se sample volume=10 deixou alguma dim com 0 rows
- Detectar se stratify_by produziu distribuição diferente da fonte
- Smoke test: warnings em subset não devem aparecer se canonical estava ok

Anota como uso meta-experimental — não bloqueia nada, mas é insurance.

### Sobre "uso prático fora de experimento"

Você disse: *"tudo isso só serve para o experimento e imagino que não
tem uma utilidade prática"*.

**Concordo no escopo do paper TCF.** Mas vale registrar que Shaper isolado
tem usos potenciais fora de experimentos:

| Uso fora de pesquisa | Aplicabilidade |
|---------------------|----------------|
| Gerar dataset de dev/test a partir de produção | Sim — sample estratificado mantém edge cases |
| Anonimização parcial (dev recebe sample, não dump) | Possível — combinado com Privacy mode |
| Smoke test de migrações de schema | Possível — sample pequeno mas representativo |
| Demo dataset para clientes/parceiros | Sim — extrair vertical menor mantendo cardinalidade |

Mas esses são casos potenciais — **não estão no escopo atual**. Documentado
no [research-notes/2026-04-25-shaper-as-standalone-tool.md](../research-notes/2026-04-25-shaper-as-standalone-tool.md).

### Os dois caminhos da sua pergunta — análise

| Caminho | Descrição | Custo | Risco | Recomendação |
|---------|-----------|-------|-------|--------------|
| **A. Genérico e inteligente** | Shaper recebe DB desconhecido e adivinha estratificação (auto-detecta fact table, stratify column, complexity levels) | Alto — heurísticas frágeis, ML para auto-detect | Adivinhação errada produz amostras enviesadas; difícil debug | **Não recomendado** para o escopo atual |
| **B. Configurado externamente** | Nós analisamos o canonical, codificamos em config; Shaper só executa | Baixo — já implementado | Adicionar dataset novo requer ~1 hora de análise manual | **Recomendado e atual** |

**Justificativa B:**
- Auto-detect tem precedente ruim em ferramentas de DB (ex: SQL ORMs que
  adivinham FK quase sempre acertam mas erros são caros)
- Para datasets canônicos, a análise manual é trivial (TPC-H tem
  documentação de 1999)
- Pesquisador deve **conhecer** os dados que está usando — auto-detect
  esconde decisões que precisam ser explícitas no paper
- Caminho A pode ser **paper futuro** (Shaper inteligente como contribuição
  separada), mas hoje é overkill

### Inventário de mudanças para fechar o Shaper

#### Implementar (prioridade média, futuro)

- [ ] `stratify` strategy — sampling proporcional por chave
- [ ] `compressibility` strategy — filtra por faixa de cardinalidade
- [ ] `join` strategy — flat vs normalized output

#### Validação meta (depois de Qualifier existir)

- [ ] Pipeline de validação: Shaper → Qualifier → relatório
- [ ] Test que verifica zero warnings em canonical bem-formado
- [ ] Test que verifica warnings esperados quando volume=10 quebra FKs

#### Sem ação (status quo OK)

- ✅ FK-preserving — já funciona (Etapa 1)
- ✅ Configuração externa via SCHEMA_LEVELS + CANONICAL_PROFILES
- ✅ data_sources.py como entry point unificado

### O que NÃO fazer

- Não fazer Shaper "inteligente" (auto-detect fact, auto-stratify) — vai
  contra a separação config-vs-execução e adiciona variáveis ocultas no paper
- Não acoplar Shaper ao Qualifier (são peças independentes; orquestrador
  combina)
- Não usar Shaper para dados de não-pesquisa por enquanto (escopo do paper)
- Não tentar generalizar para "qualquer DB do dev" — Shaper é para datasets
  canônicos onde temos análise prévia

### Resposta direta às suas perguntas

> *"Vale a pena deixar genérico e inteligente?"*
Não no escopo atual. Manter config-driven (Caminho B).

> *"Como e quem analisa os dados previamente?"*
Nós, manualmente, codificando em `SCHEMA_LEVELS` (per-dataset, em
strategies/schema.py) e `CANONICAL_PROFILES` (em data_sources.py).

> *"Como ele estratifica?"*
Hoje: por volume + FK-preserving (já implementado). Futuro:
`stratify` strategy (placeholder hoje) implementará sampling
proporcional por chave configurável.

> *"Forçar horizontal, Shaper cuida do vertical"*
**Confirmado.** É o design atual e está correto.

---

---

## Anexo E — Cenário 5 (Notação de grafo para schema + plano de validação em escala)

Você chamou de "uma coisinha", mas tem duas coisas substantivas aqui:
uma **nova hipótese de formato de payload** e uma **fase de validação em escala** que organiza todo o trabalho. Vou tratar separadamente.

### Parte 1 — Notação de grafo para FKs do schema

#### O formato que você descreveu

```
casa -> carro
casa -> quarto
carro -> rodas
quarto -> cama
quarto -> guarda roupa
```

Esse é tecnicamente conhecido como **edge list** (notação minimalista) ou
**DOT language** (Graphviz, com wrapper `digraph { ... }`). Outras
variantes próximas:
- **Mermaid** — usado em docs modernas (`A --> B`)
- **TGF** (Trivial Graph Format) — formato muito simples de grafo
- **Cypher / Neo4j** — `(a)-[:rel]->(b)`

Para schema, a versão mais útil seria:

```
# Schema graph (FK relationships)
pedidos.id_cliente -> clientes.id
pedidos.id_produto -> produtos.id
itens.id_pedido    -> pedidos.id
```

Ou ainda mais minimalista:
```
pedidos -> clientes
pedidos -> produtos
itens -> pedidos
```

#### A hipótese de teste

**LLMs entendem schema melhor com notação de grafo do que com FK inline?**

Hoje TCF entrega FK inline na coluna:
```
### pedidos (509 rows)
  id_cliente INTEGER [FK -> clientes.id], range=[1, 50]
  id_produto INTEGER [FK -> produtos.id], range=[1, 100]
  total REAL, range=[10.50, 980.00]
```

Com notação de grafo, FKs ficariam **centralizadas no topo**:
```
## Schema graph
pedidos.id_cliente -> clientes.id
pedidos.id_produto -> produtos.id

### pedidos (509 rows)
  id_cliente INTEGER, range=[1, 50]
  id_produto INTEGER, range=[1, 100]
  total REAL, range=[10.50, 980.00]
```

#### Análise crítica

**Argumentos a favor:**
- LLMs são treinadas em bilhões de linhas de docs Markdown/Mermaid/Graphviz
  (provável familiaridade com `A -> B`)
- Centraliza topologia FK em um bloco — modelo "vê o mapa" antes dos detalhes
- Reduz redundância em schemas grandes (FK aparece 1x, não em cada coluna)
- Compatível com notações visuais existentes (devs podem renderizar com Graphviz)

**Argumentos contra:**
- Em schemas pequenos (3 tabelas) pode ser overhead vs FK inline
- LLM precisa correlacionar grafo separado + coluna (2 lookups vs 1)
- Adiciona variável ao paper (mais um eixo experimental)

**Onde se encaixa:**
- É um **variante de payload formatting**, não mudança no TCF Core
- Se encaixa em "TCF LLM-mode helper" (futuro)
- Pode ser testado como ablação tipo M-series:
  - Variant: `schema_inline` (atual)
  - Variant: `schema_graph` (FKs no topo, colunas sem `[FK]`)
  - Variant: `schema_both` (FKs no topo + inline — redundância proposital)

#### Sugestão de experimento (M10 ou similar, futuro)

```
3 modelos × 3 variantes (inline/graph/both) × 7 questions × 3 seeds = 189 combos
```

Hipóteses de resultado:
- **H1:** `schema_graph` ≥ `schema_inline` em queries L3 (subquery, JOIN
  multi-tabela) — modelo se beneficia de "ver o mapa"
- **H2:** `schema_graph` ≤ `schema_inline` em queries L1 (sem JOIN) —
  overhead sem ganho
- **H3:** `schema_both` é o melhor mas custo de tokens é maior — pareto
  trade-off

Variável bonus para investigar: **dialeto de grafo importa?**
- DOT (`A -> B`)
- Mermaid (`A --> B`)
- Edge list simples (`A B` sem seta)

#### Não fazer agora

Esta hipótese vai para o **roadmap de experimentos futuros** (Parte 2
abaixo). Não há urgência arquitetural. É um payload variant.

---

### Parte 2 — Plano de validação em escala

Você descreveu o que vem **depois de fechar a arquitetura**:

> *"Voltar tudo que fizemos repetir os experimentos em várias escalas,
> melhorar os resultados, ou ao menos ver os índices de confiança de
> resultados variados, com o shaper bem 'elástico'... testar os modos
> de compressão, velocidade, comparar com outros formatos... além das
> versões com tamanhos e complexidades diferentes do banco também para
> ver o quanto a LLM consegue gerar consultas... além da questão do
> grafo."*

**Isto é a fase de validação rigorosa do paper.** Vale registrar como
plano explícito.

#### Eixos a varrer

| Eixo | Variantes a testar |
|------|--------------------|
| **Compressão TCF** | L0, L1, L2, L3 |
| **Compressão clássica** | gzip, brotli, zstd, lz4 (sobre CSV, JSON, TCF) |
| **Compressão HTTP** | content-encoding: gzip, br, deflate |
| **Formato base** | CSV, JSONL, Markdown, TOON, TCF (todos os L) |
| **Scale (vertical)** | 50, 100, 200, 500, 1000, 5000 rows |
| **Schema complexity (horizontal)** | minimal (1 tabela), core (2), chain (3-4), full (8+) |
| **Notação de schema** | inline, graph (DOT/Mermaid), both |
| **Modelos** | Locais (qwen3, phi4, qwen2.5-coder) + comerciais (Claude, GPT-4o) |
| **Seeds** | mínimo 5 para CI estreito |

#### Métricas a coletar

| Métrica | Por quê |
|---------|---------|
| Accuracy SQL gerada | Qualidade do output LLM |
| Bytes (raw + comprimido) | Eficiência de transporte |
| Tokens (no prompt) | Custo direto LLM |
| Tempo encode/decode | Performance do TCF |
| Tempo LLM (latência) | UX e custo |
| Wilson CI por (variant × question) | Significância estatística |
| Pareto: accuracy × tokens | Trade-off principal do paper |

#### Plano de execução em fases (depois da arquitetura fechar)

**Fase V1 — Replicação básica em escala:**
- Reproduzir M3 cross-domain em escalas 50/100/500/1000
- 3 modelos locais × 3 domínios × 7 questions × 3 seeds × 4 escalas = 756 combos
- Objetivo: validar que F-Q16 (cross-domain) é robusto a escala

**Fase V2 — Compressão classics:**
- Benchmark: TCF L0-L3 vs CSV+gzip vs JSON+gzip vs Markdown+gzip vs TOON
- Sobre 2 datasets canônicos (TPC-H, Adult) em 3 escalas
- Métricas: bytes raw, bytes gzip, tokens
- Objetivo: posicionar TCF na fronteira Pareto

**Fase V3 — Notação de schema (Parte 1 deste anexo):**
- Variantes: inline / graph / both
- 3 modelos × 3 dimensões de complexidade schema × 7 questions × 5 seeds
- Objetivo: testar H1/H2/H3 do experimento M10

**Fase V4 — Modelos comerciais (já no roadmap como M8 expandido):**
- Claude Haiku/Sonnet, GPT-4o-mini/GPT-4o
- Validar accuracy em commercial-grade
- Objetivo: credibilidade do paper

**Fase V5 — Final integration test:**
- Rodar pipeline completo: canonical DB → Shaper → Qualifier → TCF LLM-mode
  → Modelo → SQL → executar no DB original → validar resultado
- Objetivo: prova de end-to-end funciona

#### Pré-requisitos antes de começar V1-V5

Lista das peças que precisam estar prontas antes da validação em escala:

- [ ] Stratify strategy implementada no Shaper (Anexo D)
- [ ] Schema Qualifier implementado (Anexo B + C)
- [ ] Schema Introspector implementado (Anexo C)
- [ ] TCF LLM-mode helper extraído (Anexo A passo Tier 2)
- [ ] Pelo menos 2 datasets canônicos prontos (já temos: TPC-H + Adult)
- [ ] M9 estendido para Adult Census (precisa profile no data_sources)

#### Custo estimado

Conservador, ~3000 combos × ~10s/call = ~10 horas de LLM local.
Comerciais (V4): ~$50-100 em API costs.
Tempo de engenharia: ~2-3 semanas para V1-V5 completos.

#### O que NÃO fazer agora

- Não começar V1 antes da arquitetura fechar (Anexos A-D + Schema Qualifier
  + Introspector)
- Não rodar V5 antes de V1-V3 (depende de tudo estar provado primeiro)
- Não comprometer com escala fixa antes de smoke test (validar 1 escala
  primeiro, expandir conforme resultado)

#### Cronograma sugerido (high-level)

```
Hoje                 →  Anexo E fechado, plano registrado
+1-2 semanas         →  Implementar Anexos A (cookbook docs) + B (Qualifier)
+2-3 semanas         →  Implementar Anexo C (Introspector) + extrair LLM-mode
+3-4 semanas         →  Stratify strategy + M9 expandido
+4-6 semanas         →  Fase V1 (replicação em escala)
+6-8 semanas         →  Fases V2 + V3 (compressão + grafo)
+8-10 semanas        →  Fase V4 (comerciais) + V5 (integration)
+10-12 semanas       →  Paper draft com todos os números
```

Estimativas conservadoras. Course-correção esperada.

### Resposta direta à sua pergunta

> *"O que acha?"*

**Da notação de grafo:** ideia válida, vai pro roadmap como variante de
payload formatting (M10 futuro). Não bloqueia nada agora; pode produzir
finding interessante para o paper se H1 se confirmar.

**Do plano em escala:** **muito necessário**. Hoje temos confirmações em
N=189 (M3) e N=63 (M9) — bom para significância de achado individual,
mas o paper precisa de ablações em **múltiplas dimensões** para
robustez. V1-V5 cobre exatamente isso.

**Conexão com tudo que documentamos:** o plano em escala valida
arquiteturalmente os componentes (TCF Core, Shaper, Qualifier, Introspector,
LLM-mode helper) através de uso intensivo. Ou seja: arrumar a arquitetura
**não é só limpeza**; é pré-requisito para a validação em escala não
ficar travada por gambiarras.

---

## Revisão final pendente

Anexos A-E cobrem os 5 cenários que você descreveu (mais o plano de validação
em E.2). **Pronto para revisão final do documento.**

Sugestão: você revisa os anexos, identificamos use cases faltantes (se
houver), e depois decidimos por onde começar a execução. Candidatos
naturais para próxima ação:

1. **Tier 1 do Anexo A** — atualizar docs com Opção D (cookbook, ordem
   Python-API-first). Baixo risco, alta organização.
2. **Implementar `stratify` no Shaper** (Anexo D) — destrava experimentos
   de proporcionalidade.
3. **Estender M9 para Adult Census** — segundo dataset canonical, validação
   adicional do Pipeline B.

Sua escolha define ritmo do projeto.
