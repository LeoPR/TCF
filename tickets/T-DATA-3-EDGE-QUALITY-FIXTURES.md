---
title: T-DATA-3-EDGE-QUALITY-FIXTURES — Plano de dados de borda/defeituosos para os gadgets de qualidade/schema (planejamento, NAO implementar agora)
status: deferred
priority: P3
created: 2026-06-01
updated: 2026-06-01
blocked-by: [T-RECOVER-SCHEMA-MULTI-TABLE]
related:
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md   (gadget alvo: so' alerta, NUNCA arruma)
  - tickets/T-RECOVER-LLM-SCHEMA-MODE.md
  - src/tcf/side_outputs.py                    (canal zero-cost; campos anomaly_flags planejados)
  - src/tcf/column_features.py                 (analyze_column — onde sinais zero-cost nascem)
  - experiments/lab/dirty/2026-05-24-cpf-templated-checked/  (gerador de corrupcao existente)
---

# T-DATA-3-EDGE-QUALITY-FIXTURES — Dados de borda (PLANO)

## Escopo e disclaimer

**Planejamento apenas** (owner pediu explicitamente: "ter alguns dados de
borda com algum problema, faltando ou com defeito seriam interessantes...
(não agora) mas já veja nos planejamentos"). Este ticket cataloga os dados
defeituosos pra testar os **gadgets auxiliares de qualidade/schema**
(T-RECOVER-SCHEMA-MULTI-TABLE), que **so' ALERTAM, NUNCA arrumam**. NAO e'
pra testar o TCF-core (TCF supoe "dados felizes"). Os gadgets ainda nao
existem — este plano so' executa quando eles entrarem.

## Principio metodologico (obrigatorio)

- **Detect-never-fix**: cada fixture testa um DETECTOR/alerta; nenhum
  transforma dado. O lab CPF (sub-exp 03) ja' provou que elide+regen de
  digito errado causa corrupcao silenciosa — corrupto vai pra fallback
  literal `_`, NUNCA e' "consertado".
- **Ecological vs stress**: todo fixture e' STRESS/artificial, gerado por
  **corrupcao controlada de um baseline canonico SADIO** (ibge/TPC-H/adult/
  wine/online-retail/CPF-uniform). Sempre shippar: (a) copia limpa do
  baseline pra diff, (b) manifesto de corrupcao (row, valor original, valor
  injetado, classe de defeito), (c) gerador citando framework academico
  (Myers / DeMillo mutation / Beizer BVA / Rahm&Do / Miller fuzzing) + stats
  ISO/IEC 25012. **Vies declarado** no README — NUNCA usar pra
  `confirmada-empirica`.
- **Armazenamento**: corrompido grande -> `Z:/tcf-data/processed/` ou
  `datasets/synthetic/edge/` (gitignored onde grande); so' referencia leve +
  manifesto versionados (espelha convencao canonical).

## Catalogo de defeitos (11 classes)

| Classe | Baseline a corromper | Mapeia p/ gadget | Zero-cost via SideOutputs? | Severidade |
|---|---|---|---|---|
| duplicate_primary_key | ibge id / TPC-H *_key | Fase 3 (cardinality<1.0 em PK) | **SIM** (cardinality ja' computada) | high |
| type_drift (valor nao-numerico em col numerica) | wine/beijing/tpch float | Fase 3 (is_numeric mismatch) | **Quase** (is_numeric ja' roda; falta sink) | medium |
| missing_values_pattern (sentinelas '', NULL, NaN, \N) | ibge (8 cols non-null) | Fase 3 completude % | Parcial (n_rows free; falta null-count) | medium |
| length_variance_anomaly | online-retail StockCode / tpch c_phone | Formato/Qualidade | Parcial (avg_len free; falta stddev) | low |
| format_inconsistency (datas ISO/BR/US mistas; sigla<->nome ibge quebrado) | tpch o_orderdate / ibge uf | Fase 2 date_check | Parcial (length-variance proxy) | medium |
| fk_orphan (+ overlap 88-99% + bait nome-coincidente) | TPC-H star+chain | Fase 1 fk_detect | NAO (precisa interseccao cross-table) | high |
| out_of_range_impossible (idade -5/999, discount 0.50, uf 'XX') | adult age / tpch / wine | Fase 2 anomalias | NAO (precisa dominio por coluna) | high |
| impossible_date (2026-02-30, mes-13, ship>receipt) | TPC-H datas correlacionadas | Fase 2 date_check | NAO (validacao calendario) | high |
| malformed_identifier_bad_check_digit (CPF/CNPJ dv errado) | gerador lab CPF / br-identidades | nature_stats (Checked) | So' com nature opt-in ativa | high |
| encoding_issue (mojibake, BOM, NFC/NFD misto) | ibge municipio (acentuado) | Anomalias | NAO (scan byte-level dedicado) | low |
| (cross-table relationships / shared cols) | TPC-H multi-tabela | Fase 1/3 | NAO (cross-table) | medium |

## Faseamento (quando os gadgets existirem)

1. **PRIMEIRO — sinais genuinamente zero-cost (hoje em ColumnFeatures)**:
   duplicate_primary_key (cardinality<1.0 em PK esperada) + type_drift
   (is_numeric mismatch). So' **expor** campos ja' computados.
   > **Cuidado (achado do critico)**: adicionar acumuladores NOVOS
   > (null-count, length-stddev) a `analyze_column` **TOCA o pre-pass** ->
   > guardado pelo gate T-REGRESSION-REAL-WORLD. NAO e' "de graca"; tratar
   > como mudanca gated (passa os DOIS suites) + opt-in (preservar invariante
   > ADR-0014 "zero overhead sem side_outputs=").
2. **SEGUNDO — FK detector** (Fase 1 gadget) + fixture fk_orphan (corromper
   TPC-H). Rodar contra TPC-H LIMPO primeiro (deve dar 0 orfas) -> baseline.
3. **TERCEIRO — date/format checker** (Fase 2) + impossible_date +
   format_inconsistency (precisam conhecimento de dominio).
4. **QUARTO — out_of_range + encoding** (mais baixo: dominio per-coluna /
   fora do escopo TCF). Calibracao de thresholds de severidade.
- **Cross-cutting**: bad-check-digit reusa gerador CPF do lab + mod-11 ja'
  implementado; zero-cost SO' com nature opt-in ativa. NAO bloquear roadmap
  do gadget em dataset CPF real (nao existe) — manter declared-stress.

## Criterio de aceite (quando ativado)

- [ ] Cada fixture: baseline limpo + manifesto + gerador com citacao
      framework + stats ISO 25012
- [ ] Gadget roda contra baseline LIMPO primeiro (0 falsos positivos) antes
      do corrompido
- [ ] Nenhum fixture muta/conserta dado (so' alerta)
- [ ] READMEs com vies declarado; nada disso alimenta `confirmada-empirica`
- [ ] Fixtures-FK mantidos SEPARADOS da garantia no-orphan do shaper
      (concerns diferentes: detector vs sampler)

## Riscos / questoes abertas

1. **Campos SideOutputs planejados** (anomaly_flags, format_inconsistencies,
   distribution_warnings, nature_stats) ainda NAO existem em
   `side_outputs.py`; ColumnFeatures nao tem null-count/stddev/min-max/freq.
   Forma exata (sempre-on barato vs opt-in) e' decisao pendente e gateia a
   Fase 1.
2. **Thresholds de severidade indefinidos** (que % overlap = FK candidate?
   que variancia de length = alerta?). Fixtures devem varrer N% (0/1/5/20/
   100%) pra calibrar; cut-points finais = decisao do owner.
3. **Baselines ja' com markers reais**: adult ('?') e beijing ('NA') ja' tem
   missing markers — pra completude usar ibge (8 cols non-null, baseline 1.0).
4. **Onde versionar**: fixtures minusculos (n<=10, estilo D-series) talvez
   git-tracked; copias corrompidas grandes de TPC-H = regeneravel-only em Z:.
   Decisao do owner.

## Conexoes

- Bloqueado por: T-RECOVER-SCHEMA-MULTI-TABLE (gadget nao existe ainda)
- Reusa: gerador de corrupcao em
  `experiments/lab/dirty/2026-05-24-cpf-templated-checked/`
- Filosofia: CLAUDE.md "gadgets so' alertam, NUNCA arrumam" + "dados felizes"
- Origem: design workflow 2026-06-01 (taxonomia de tipos de dados)
