---
title: Schema Qualifier — análise de qualidade de schema antes de passar para TCF/LLM
date: 2026-04-24
type: research-note
status: HIPÓTESE / ROADMAP — não implementado
---

# Schema Qualifier — qualificar dados antes do TCF, ajudar developers e LLM

## Princípio arquitetural pré-existente que motiva esta nota

TCF Core é **ingênuo por design**. Recebe `dict[table, list[dict]]` e codifica.
Não valida FKs, não detecta tabelas órfãs, não opina sobre qualidade. Confia
no desenvolvedor.

Isso é uma escolha **arquitetural correta** porque:
1. Permite que TCF seja usado standalone (qualquer dev com CSV/JSON pode comprimir)
2. Mantém TCF pequeno, testável, sem deps externas
3. Não duplica funcionalidade que existe em ferramentas dedicadas
4. Falha rápida — dado errado entra, saída errada sai (nenhum mascaramento silencioso)

**Mas isso transfere responsabilidade ao desenvolvedor.** Um dev menos
experiente pode:
- Passar tabelas com FK quebrados → TCF comprime ok mas LLM faz JOIN errado
- Esquecer que a tabela X tem dependência implícita com Y → LLM gera SQL incompleto
- Não declarar tipos corretamente → stats viram strings concatenadas

A solução não é fazer TCF "inteligente" — é construir uma **ferramenta auxiliar**
que prepara dados antes do TCF. Esta nota documenta a ideia do **Schema Qualifier**.

## A ideia

```
DB real (sujo, real-world)
       │
       ▼
   Schema Extractor       ← introspecciona via information_schema/pg_catalog/sqlite_master
       │
       ▼
   Schema Qualifier       ← analisa qualidade, emite warnings ★ NOVO
       │
       ▼
   StatsPack + QualityReport
       │
       ├─▶ Caminho 1: tables sintetizadas (com sample rows) → TCF Core (compressão tradicional)
       │
       └─▶ Caminho 2: schema-only payload (sem rows) → LLM
                       (warnings inseridos como hints no prompt!)
```

## O que o Qualifier detecta

### Categoria 1 — Topologia FK

- **Tabelas órfãs** — sem FK entrando ou saindo. Provavelmente lookup tables
  ou tabelas mortas; LLM não deve tentar JOIN com elas
- **FKs danificados** — coluna FK aponta para tabela/coluna inexistente
- **FKs implícitos** — coluna `customer_id` em `orders` mas sem constraint
  declarada; é candidata óbvia mas o dev pode confirmar
- **Self-referencing tables** — sem ciclo declarado, mas FK aponta para
  própria tabela (hierarquias)

### Categoria 2 — Integridade de PK/cardinalidade

- **PK com duplicatas** — coluna marcada PK mas com `count(distinct) < count(*)`
- **PK candidata não declarada** — coluna sem PK mas com cardinalidade total
- **Cardinality skew** — coluna com 99% null, ou 1 valor dominando 95%

### Categoria 3 — Tipos e valores

- **Tipo declarado vs real** — coluna `int` com `"N/A"` em algumas linhas
- **Datas em formato heterogêneo** — `"2024-01-15"` vs `"15/01/2024"` na mesma coluna
- **Nullables não declarados** — coluna marcada `NOT NULL` mas com nulls

### Categoria 4 — Conexões soltas

- **Tabela alcançável apenas via path indireto** — não tem FK direto para
  uma tabela "central"
- **FK redundante** — duas FKs apontando para mesma tabela alvo, possivelmente
  inconsistentes
- **Cardinalidade FK fora do esperado** — FK marcada N:1 mas tem 1:1 ou 1:N

## Como isso ajuda a LLM gerar SQL

**Schemas perfeitos:** zero overhead. Qualifier não emite warnings, payload TCF
fica idêntico ao atual.

**Schemas problemáticos:** TCF formatter inclui um bloco `## Notas de schema`
no prompt:

```
## Notas de schema

- Tabela `legacy_audit` é orfa (sem FK declarado). Nao incluir em JOINs sem confirmacao.
- Coluna `customer_id` em `orders` parece FK para `customers.id` mas nao tem
  constraint. Use `JOIN customers c ON c.id = o.customer_id` para confirmar.
- Coluna `birth_date` em `users` tem 2 formatos: ISO ("2024-01-15") e BR ("15/01/2024").
  Use STRFTIME ou CASE para normalizar.
```

A LLM agora **sabe** das limitações do schema. SQL gerado é mais robusto
porque o modelo foi avisado em vez de adivinhar.

## Validação meta-experimental — auto-checagem dos canonicals

Mesmo TPC-H e Adult Census **devem ser passados pelo qualifier** uma vez que
ele estiver pronto. Razões:

1. **Smoke test do qualifier** — se TPC-H emite muitos warnings em coisas que
   sabemos estarem corretas, qualifier está calibrado mal
2. **Honestidade científica** — não assumir que canonical = perfeito; documentar
   o que de fato foi encontrado
3. **Paper material** — "Aplicamos qualifier em TPC-H: 0 issues. Em Adult Census:
   2 issues (coluna X com `?` como NA, coluna Y com cardinalidade marginal)."

Hipótese específica para auto-validação: Adult Census provavelmente tem mais
issues (coluna `workclass` tem `?` para missing values, coluna `native-country`
tem skew significativa). TPC-H provavelmente passa limpo.

## Conexão com componentes existentes

| Componente | Relação com Qualifier |
|-----------|----------------------|
| TCF Core (#1) | Continua ingênuo. Qualifier roda **antes** e produz tables/payload limpo |
| TCF-LLM Interface (#2) | Pode receber payload com warnings de qualidade no prompt |
| TCF-DB Extractor (#3) | **Hospeda** o Qualifier — é módulo natural deste componente |

## Implementação

Por enquanto: **roadmap apenas**. Construir só após:
1. Etapa 1 da unificação (Shaper FK-aware) — DONE quando feito
2. M-series migrado para canonical via data manager — futuro
3. M9 estendido para Adult Census — futuro

Lugar para o código quando vier: `scripts/db/qualifier.py` (ou similar) como
parte do bundle de ferramentas auxiliares de DB.

## Referências internas

- [components/1-tcf-core.md](../components/1-tcf-core.md) — invariante de ingenuidade do TCF
- [components/3-tcf-db-extractor.md](../components/3-tcf-db-extractor.md) — host natural do qualifier
- [F-Q17](../methodology/F-findings.md) — caso real onde naming collision quebrou JOINs (qualifier teria detectado)
