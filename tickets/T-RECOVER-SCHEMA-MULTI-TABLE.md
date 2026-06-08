---
title: T-RECOVER-SCHEMA-MULTI-TABLE — Gadget auxiliar de schema multi-tabela (alertas, NAO conserta)
status: de-prontidao
priority: P2
created: 2026-05-27
updated: 2026-05-27 (escopo refinado: gadget auxiliar so' alerta, NUNCA arruma; usa SideOutputs)
blocked-by: []
related:
  - src/tcf/side_outputs.py  (framework de "efeito colateral" que esta ferramenta consome)
  - src/tcf/schema.py  (build_schema per-tabela; permanece intocado)
---

# T-RECOVER-SCHEMA-MULTI-TABLE — Gadget auxiliar

## Contexto + ESCOPO (refinado 2026-05-27)

**Gadget AUXILIAR EXTERNO ao TCF**, NAO integrado, **so' EMITE ALERTAS,
nunca conserta dados**. Vive em `scripts/` ou eventualmente em pacote
separado.

Owner reforcou (2026-05-27):
> "TCF supoe dados muito sadios e felizes. Nao e' responsabilidade
> dele ficar melhorando ou entrar no merito do porque uma data esta
> invertida ou com 32 de fevereiro. (...) Uma ferramenta previa pra
> chegar dados de forma sadia e' uma opcao que o dev ou arquiteto
> podem ter. (...) Esses tools tambem nao tem o compromisso de arrumar
> absolutamente nada."

## Proposta — gadget pequeno e focado

Ferramenta de **analise/alerta** de schemas multi-tabela. Output: relatorio
de qualidade + sugestoes; **nunca dados transformados**.

Detecta e ALERTA sobre:
- **Integridade**: FK candidates (col_A.values ⊂ col_B.values com %)
- **Relacionamentos**: colunas compartilhadas entre tabelas
- **Formato**: datas com formatos misturados, ISO vs BR vs US
- **Anomalias**: valores impossiveis (32 de fev, idades negativas, etc)
- **Qualidade**: cardinality, completude (% nulls), distribuicao

Tudo emitido como **alertas consistentes** pro usuario decidir o que fazer.
**Nenhuma transformacao automatica**.

Resultado downstream: usuario aplica fixes manuais OU aceita os warnings;
quando esse dado limpo chega no TCF, TCF comprime melhor.

## Integracao com SideOutputs (framework existente)

`SideOutputs` (em src/tcf/side_outputs.py) ja' captura **efeito colateral**
do encode: column_features (n_rows, n_unicas, cardinality, is_numeric,
sample), cadence_info, etc. Esses dados sao computados de qualquer jeito
durante encode — **gratis**.

Este gadget pode:
- **Consumir** SideOutputs em paralelo: quando usuario roda encode pra
  proof, o gadget extrai os stats e emite alertas (sem custo adicional)
- **Expandir** SideOutputs com campos de qualidade (futuro, opt-in):
  format_inconsistencies, distribution_warnings, anomaly_flags — mantendo
  filosofia "zero custo, so' o que ja' compute".

## Estado atual

- **Existe (em src/tcf)**: `build_schema(data) → TableSchema` per-tabela
  (welded Fases 1+2). Permanece intocado.
- **Existe**: SideOutputs como framework de efeito colateral.
- **NAO existe**: analise cross-table + alertas de qualidade. Sera criado
  em `scripts/schema_gadget/` ou pacote separado.
- **DESIGN DOC (2026-06-03)**: [`docs/theory/schema-gadget-design.md`](../docs/theory/schema-gadget-design.md)
  — define fronteira (gadget vs build_schema core), catalogo de detectores
  por custo (zero/barato-gated/caro), 5 fases, e o norte de pushdown
  (RLE-as-groupby) + sinalizacao do cenario SQL-like.

## Plano (futuro)

### Fase 1 — Detector de FK candidate ✅ FEITA (2026-06-03)
- `scripts/schema_gadget/fk_detect.py` standalone — `detect_fk_candidates()`
- Input: dict[table_name, dict[col, list[values]]]
- Output: `FKCandidate` com overlap, n_orphans, name_match, **confidence**
  (alta/media/baixa). ALERT-ONLY (não muta entrada; testado).
- **Validado em TPC-H** (9 FKs reais, descobertas por VALOR sem ler
  metadata.fk): `min_confidence='alta'` → **recall 9/9, 0 falsos positivos**;
  default gradua os 39 candidatos (30 coincidências numéricas marcadas
  `baixa`). Também acha FK cross-table de nome diferente (br-identidades
  socio_cpf → pessoas.cpf, overlap 1.0).
- **Aprendizado**: overlap puro em INTEIROS DENSOS pequenos gera FP por
  coincidência numérica (l_quantity cai no range de p_partkey); o sinal de
  NOME compatível + cardinalidade desambigua. Daí a graduação de confiança.
- Testes: `tests/test_schema_gadget_fk.py` (7, CI-friendly, sem Z:).

### Fase 2 — Date/format consistency checker ✅ FEITA (2026-06-08)
- `scripts/schema_gadget/date_check.py` — `check_dates(tables)`.
- **Auto-detecta** colunas que parecem data (>=70% do sample casa um formato)
  e emite: `impossible_date` (calendário-inválido: mês>12, 32-fev, dia/mês=0,
  29-fev não-bissexto), `format_mix` (ISO/BR/US/compact misturados),
  `suspicious_date` (fora de [1900..2100]).
- **NÃO é zero-custo** (ao contrário da Fase 3): scan dedicado que parseia
  TODOS os valores com conhecimento de calendário. Declarado + toggleável
  (`check_dates_enabled` no report). Parser próprio (regex stdlib) pra não
  herdar a permissividade do dateutil. Type-safe (DatasetReader devolve int).
- **Validado por corrupção controlada** (fatia mínima do T-DATA-3): baseline
  real limpo (tpch o_orderdate, br-identidades data_cadastro) → **0 alertas**;
  mesma coluna com 3 impossíveis + 2 BR + 1 futuro injetados → pega
  **exatamente** os 6 defeitos. Precisão (0 FP no limpo) + recall confirmados.
- Testes: `tests/test_schema_gadget_dates.py` (12, CI-friendly). Integrado
  no report/CLI (seção "Alertas de data"). Desbloqueou sem esperar T-DATA-3
  (corrupção inline basta pra validar).

### Fase 3 — SideOutputs hook ✅ FEITA (2026-06-03)
- `scripts/schema_gadget/sideouts_quality.py` — `analyze_quality(schema, expected_unique=...)`
- Consome `TableSchema` (build_schema) e emite `QualityAlert` ZERO-CUSTO
  (só lê o que o encode já computou — confirmado em 7 datasets).
- **3 detectores** (após validação adversarial — workflow 7 datasets):
  - `constant` (1 valor único) — único com TP real + 0 FP; mantido
  - `duplicate_key` (PK **single-column** com repetição) — pula PK composta
  - `type_drift` (sample maioria-numérico com minoria não-numérica, ex 'N/A')
- **`useless_id` REMOVIDO**: validação adversarial deu 12/12 falsos positivos
  em tpch (disparava em qualquer string all-distinct: nomes, comentários).
- **Aprendizado (verificação adversarial)**: detector ingênuo dava 94% ruído
  em tpch (15/16 FP). Causas: (a) useless_id não distingue surrogate de chave
  natural; (b) type_drift original era código morto (is_numeric=True proíbe
  não-numérico no mesmo sample) → reescrito como fração-numérica; (c)
  duplicate_key disparava em cada componente de PK composta. Pós-fix: tpch
  16→1 alert (só o TP), **0 FP**.
- **Fora de escopo (não zero-custo, declarado)**: null/empty count, length
  stddev, drift no tail (>sample[:20]), format-mix, datas impossíveis — todos
  exigiriam acumulador no analyze_column (toca pre-pass, gated T-REGRESSION).
- Testes: `tests/test_schema_gadget_quality.py` (13, CI-friendly).

### Fase 4 — CLI / relatório unificado ✅ FEITA (2026-06-08)
- `scripts/schema_gadget/report.py` (`analyze_tables` / `analyze_dataset`) +
  `__main__.py` (CLI). Orquestra FK detect (Fase 1) + quality (Fase 3) num
  relatório **markdown ou JSON**. ALERT-ONLY (read-only, nunca modifica).
- CLI: `python -m schema_gadget {list|analyze <dataset>}` com `--json`,
  `--rows N`, `--fk-confidence baixa|media|alta`.
- **Validado nos hubs reais**: `analyze tpch-sf001 --fk-confidence alta` →
  exatamente os 9 FKs reais + 1 constant (`o_shippriority`), **0 ruído**.
  `list` enumera os 6 hubs em Z:. JSON parseável.
- Testes: `tests/test_schema_gadget_report.py` (8, CI-friendly via
  `analyze_tables` inline, sem Z:). Suite total 308 passed.

### (Opcional) Fase 5 — Spin-off
- Decidir se vira pacote `tcf-quality-gadget` separado

## Estado geral (2026-06-08)

Gadget **completo end-to-end**: Fases 1 (FK), 2 (date/format), 3 (quality),
4 (CLI/relatório) FEITAS. Fase 5 (spin-off `tcf-quality-gadget`) é opcional.
Usável: `python -m schema_gadget analyze <dataset>` → relatório markdown/JSON
com FK candidates + qualidade zero-custo + datas. ALERT-ONLY, `src/tcf`
intocado. Total ~40 testes CI-friendly. T-DATA-3 (fixtures de borda
versionados) deixou de ser bloqueador — corrupção controlada inline valida.
**Ticket pode ser marcado closed-done** (gadget funcional); T-DATA-3 segue
deferred pra fixtures persistentes se/quando quiser regressão em disco.

## Conexao

- **NAO toca** src/tcf/. Permanece em scripts/ ou spin-off.
- Pode importar `TableSchema` + `SideOutputs` do TCF (consumidor, nao
  modificador)
- NAO bloqueia nem desbloqueia features TCF
- T-RECOVER-LLM-SCHEMA-MODE — outro gadget auxiliar, irmao

## Filosofia

- **TCF supoe dados felizes**: este gadget e' opt-in pra quem precisa
  validar antes
- **So' alerta, NUNCA conserta**: dev/arquiteto decide o que fazer
- **Gadget pequeno e focado**: nao e' platform play, e' utilitario modular
- **Zero custo via SideOutputs**: aproveita stats que TCF ja' compute

## Status

**De prontidao** (registrado 2026-05-27, escopo refinado). Atacar quando
owner decidir; **NAO bloqueia roadmap TCF**.
