---
title: Componente 3 — TCF-DB Extractor
date: 2026-04-23
type: component
status: VISION — roadmap, sem código ainda
---

# 3. TCF-DB Extractor — de DB real para TCF mínimo

## O que é (objetivo)

Uma ferramenta que, dado um banco de dados relacional real (SQLite, PostgreSQL,
MySQL), extrai o **mínimo de metadata necessário** para representar seu schema
em TCF, e combina isso com perguntas de BI do usuário para executar consultas
**no próprio banco** — sem copiar ou reproduzir os dados.

Diferença vs. experimentos atuais: M-series usa fixtures sintéticas controladas
no memória. Este componente testa o pipeline de produção realista — **DB do
cliente, pergunta do usuário, resposta via TCF+LLM+SQL**.

## Pipeline conceitual

```
DB real (Postgres/MySQL/SQLite)
    │
    ▼
[Schema Introspector]   ← lê information_schema, pg_catalog, sqlite_master
    │
    ▼
[Schema Qualifier]      ← analisa qualidade: orfa, FK soltos, tipos heterogeneos
    │                     emite warnings que viram hints no prompt da LLM
    │                     (ver research-note 2026-04-24-schema-qualifier.md)
    ▼
Schema TCF + StatsPack + QualityReport
    │
    ▼
+ Pergunta BI do usuário (NL)
    │
    ▼
[LLM com prompt TCF-schema + warnings]
    │
    ▼
SQL gerado (informado das limitacoes do schema)
    │
    ▼
Executar NO DB ORIGINAL (mesmo engine, mesmos dados)
    │
    ▼
Resultado
```

## Por que importa

1. **Prova o valor prático do TCF:** em LLM produção, usuário tem DB, não CSV
2. **Validação externa:** testa em schemas reais (não sintéticos), com
   nomes de colunas em linguagem natural, FK complexos, tipos variados
3. **Vantagem competitiva vs. alternativas:** a maioria de text-to-SQL
   assume dump SQL; TCF minimal schema cabe em contexto de LLM pequeno
4. **Bridge pesquisa→aplicação:** Linha B (schema carrier) só tem sentido
   em produção se o schema pode ser extraído de forma geral

## Design preliminar

### Módulo 1 — Schema Introspector

```python
from tcf_db import introspect

schema = introspect.from_dsn("postgresql://user@host/db")
# Returns: TableSchema list with columns, types, FKs, indexes, row counts
```

**Fontes por engine:**
- PostgreSQL: `information_schema.tables`, `pg_catalog.pg_constraint`, `pg_stats`
- MySQL: `information_schema.tables`, `information_schema.key_column_usage`
- SQLite: `sqlite_master`, `PRAGMA foreign_key_list(table)`, `PRAGMA table_info(table)`

### Módulo 2 — Schema Qualifier (NOVO — ver research-note)

```python
from tcf_db import qualify

report = qualify.schema(schema)
# Returns: QualityReport with orphan_tables, dangling_fks, implicit_fks,
#          type_heterogeneity, cardinality_issues, etc.
```

**Detecta:**
- Tabelas órfãs (sem FK entrando/saindo)
- FKs danificados (apontam para alvo inexistente)
- FKs implícitos não-declarados (coluna parece FK por nome)
- PK com duplicatas; PK candidata não-declarada
- Tipos heterogêneos (datas em formatos diferentes na mesma coluna)
- Cardinality skew (99% null, 1 valor dominando 95%, etc.)

**Saída integra-se ao prompt da LLM:**
```
## Notas de schema
- Tabela `legacy_audit` é orfa. Nao incluir em JOINs sem confirmacao.
- Coluna `customer_id` em `orders` parece FK para `customers.id` mas sem constraint.
```

**Validação meta:** rodar qualifier sobre TPC-H e Adult Census para
calibrar (TPC-H deve passar limpo; Adult Census tem peculiaridades como `?`
para missing).

Documentação completa em
[../research-notes/2026-04-24-schema-qualifier.md](../research-notes/2026-04-24-schema-qualifier.md).

### Módulo 3 — TCF Schema Generator

```python
from tcf_db import build_schema_payload

tcf_schema = build_schema_payload(schema, sample_rows=3, include_stats=True)
```

Gera payload TCF **só de schema** (sem dados completos):
- Nomes de tabelas e colunas
- Tipos SQL mapeados para tipos TCF
- Cardinalidades estimadas (COUNT, DISTINCT COUNT)
- FK explícitos com hints
- 3 valores de exemplo por coluna (`SELECT ... LIMIT 3`)
- STATS pré-computados via agregações SQL (para colunas numéricas)

Isso é equivalente ao `build_payload_stats_fewshot` atual, mas alimentado
por DB real em vez de fixtures.

### Módulo 4 — Query Executor

```python
from tcf_db import ask

result = ask(schema, "Quantos clientes distintos compraram em março?",
             model="qwen3:14b", safe_sql="auto")
# Returns: {"sql": "...", "result": 42, "elapsed_ms": 2100}
```

Reusa a infra de Linha B:
- `llm_eval/ollama_client.py` para chamada LLM
- Prompt template com schema TCF + few-shot + style hints
- Executa SQL no **DB original**, não em SQLite local
- Retorna SQL + resultado + metadata

### Safe-SQL auto-selection

Usa F-Q23: em vez de aplicar todos os flags, detecta padrão da pergunta:
- Contém "quantos X têm mais de N Y"? → ativa `safe_having`
- Pede nome de entidade? → ativa `safe_name_join`
- Etc.

Classifier simples (rule-based ou LLM auxiliar) decide qual flag usar.

## Roadmap de implementação

| Milestone | Escopo | Status |
|-----------|--------|--------|
| M_db0 | Design spec + interface | Em esboço (este doc) |
| M_db1 | SQLite introspector (mais simples) | Não iniciado |
| M_db2 | Schema Qualifier (calibrar em TPC-H/Adult) | Não iniciado |
| M_db3 | Schema → TCF payload generator (com warnings) | Não iniciado |
| M_db4 | Query executor + safe-sql auto | Não iniciado |
| M_db5 | Validar em DB público (Chinook, Northwind) | Não iniciado |
| M_db6 | PostgreSQL/MySQL introspectors | Futuro |
| M_db7 | Benchmark contra text-to-SQL state-of-the-art | Pré-paper |

## Decisões de design em aberto

1. **Sampling de dados:** incluir N rows como exemplo ajuda LLM (como nos
   experimentos atuais) ou é preferível só schema + stats? Hipótese: depende
   da pergunta; `safe-sql-with-samples` vs `safe-sql-schema-only`.

2. **Privacy:** dados de exemplo podem vazar PII. Precisa de modo anonymized
   (hash/replace de strings, buckets para numéricos).

3. **Tamanho de schema:** DBs reais têm 50+ tabelas. TCF schema payload
   precisa priorizar (por relevância à pergunta?) para caber no contexto.

4. **Execução:** read-only SQL apenas; bloquear UPDATE/DELETE/DROP no
   executor; caps de timeout, rows, memory.

5. **Metadata caching:** introspection é cara em DBs grandes; cache de
   schema com invalidation via DDL hooks?

## Relação com outros componentes

- **TCF Core** provê o formato de schema (não muda)
- **TCF-LLM Interface** provê as estratégias de prompt, fewshot, safe-sql
- **TCF-DB Extractor** conecta tudo com dados reais do usuário

Este componente **é o que transforma TCF de pesquisa em produto**.

## Status

Pre-design. Sem código. Documentado aqui como vision para quando a pesquisa
em Linha B estiver madura (possivelmente pós-paper).
