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
