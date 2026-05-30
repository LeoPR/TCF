---
title: T-RECOVER-SCHEMA-MULTI-TABLE — Ferramenta auxiliar de schema multi-tabela (EXTERNO ao TCF)
status: de-prontidao
priority: P2
created: 2026-05-27
updated: 2026-05-27 (escopo corrigido pelo owner: e' ferramenta auxiliar, NAO integrada ao TCF)
blocked-by: []
related:
  - src/tcf/schema.py  (build_schema atual e' per-tabela; este ticket NAO modifica src/tcf)
---

# T-RECOVER-SCHEMA-MULTI-TABLE

## Contexto + ESCOPO (corrigido 2026-05-27)

**Este e' uma ferramenta AUXILIAR EXTERNA ao TCF**, NAO integrada ao
algoritmo de compressao. Vive em `scripts/` ou eventualmente em pacote
separado.

Owner clarificou (2026-05-27) que `build_schema` (welded em src/tcf) e'
**uma coisa**: parte do TCF, analisa schema per-tabela como entrada do
encoder. Esta ferramenta de **multi-tabela com relacionamentos** e' **outra
coisa**: utilitario autonomo que ajuda o usuario a entender/preparar dados
ANTES de usar o TCF, ou totalmente independente de TCF.

Sem relacao direta com o algoritmo. Sem dependencia bidirecional. TCF nao
precisa dela; ela nao precisa do TCF (alem de eventualmente importar o
`TableSchema` como tipo).

## Proposta

Ferramenta de analise de schemas multi-tabela:
- Detecta FK candidates (col_A.values ⊂ col_B.values, cardinalidade alta)
- Identifica colunas compartilhadas entre tabelas (nome+tipo+sample overlap)
- Sugere ordem topologica de processamento (tabelas "mae" -> "filha")

**Caso de uso autonomo**: usuario tem 9 CSVs, quer mapa do relacionamento
entre eles antes de qualquer compressao/analise.

**Caso de uso TCF-adjacent (opcional)**: se quiser, usuario pode usar essa
ferramenta antes de chamar `encode()` em cada tabela. TCF nao se importa
de onde vieram os dados ou em que ordem.

## Estado atual

- **Existe (em src/tcf)**: `build_schema(data) → TableSchema` per-tabela
  (welded Fases 1+2). Permanece intocado.
- **NAO existe**: analise cross-table (este ticket). Sera criado em
  `scripts/schema_multi/` ou pacote separado.

## Plano (futuro)

### Fase 1 — Detector de FK candidate
- `scripts/schema_multi/fk_detect.py` standalone
- Input: dict[table_name, dict[col, list[values]]]
- Output: list[FKCandidate(parent_table, parent_col, child_table, child_col, match_pct)]

### Fase 2 — Detector de colunas compartilhadas
- `scripts/schema_multi/shared_cols.py`
- Cross-table feature matching

### Fase 3 — CLI utility
- `python -m scripts.schema_multi analyze <dir-of-csvs>` produz relatorio
- Markdown/json output; NAO chama TCF

### (Opcional) Fase 4 — Spin-off
- Decidir se vira pacote `tcf-schema-tools` separado pra evitar bloat do
  pacote tcf principal

## Conexao

- **NAO toca** src/tcf/. Permanece em scripts/ ou spin-off.
- Pode importar `TableSchema` do TCF como conveniencia de tipo (opcional)
- NAO bloqueia nem desbloqueia features TCF
- T-RECOVER-LLM-SCHEMA-MODE (relacionado, tambem auxiliar) — eventualmente
  o LLM tool poderia consumir output desta

## Status

**De prontidao** (registrado 2026-05-27, escopo corrigido). Atacar quando
owner decidir; **NAO bloqueia roadmap TCF**.
