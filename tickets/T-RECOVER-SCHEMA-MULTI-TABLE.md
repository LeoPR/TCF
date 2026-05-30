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

## Plano (futuro)

### Fase 1 — Detector de FK candidate
- `scripts/schema_gadget/fk_detect.py` standalone
- Input: dict[table_name, dict[col, list[values]]]
- Output: relatorio de FKCandidates com confianca

### Fase 2 — Date/format consistency checker
- `scripts/schema_gadget/date_check.py`
- Detecta formatos misturados, datas impossiveis (32/02), futuros suspeitos

### Fase 3 — SideOutputs hook
- `scripts/schema_gadget/sideouts_quality.py`
- Le SideOutputs de um encode (proof run) e emite alertas:
  - "coluna X tem cardinality=1.0 e n=5 — pode ser ID inutil"
  - "coluna Y has is_numeric=True mas 3 samples falharam parse"
  - "tabelas A e B compartilham coluna 'user_id' com 87% overlap"

### Fase 4 — CLI
- `python -m scripts.schema_gadget analyze <dir-of-csvs>` → relatorio
  markdown/json. **NAO modifica nada**.

### (Opcional) Fase 5 — Spin-off
- Decidir se vira pacote `tcf-quality-gadget` separado

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
