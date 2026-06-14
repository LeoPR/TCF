# 0022 — V2-A fallback identity welded (abre v2.0, #TCF.7, opt-in)

**Status**: accepted
**Date**: 2026-06-13
**Deciders**: project owner
**Tags**: v2.0, format, fallback, multi-column, low-cardinality, #TCF.7

## Context and Problem Statement

[ADR-0018](0018-v2-format-roadmap.md) registrou V2-A (fallback identity por
coluna) como prioridade #1 do roadmap v2.0: "se o TCF de uma coluna fica maior
que o raw, guarda raw". Garante "nunca pior que raw+delimitadores" e cobre o
ponto cego de baixa-cardinalidade (colunas numericas curtas inflam ate' 2.3x).

O owner decidiu **abrir a v2.0** (perseguir bytes). V2-A foi caracterizado em
9 fontes reais (lab [`2026-06-13-v2a-fallback-expandido`](../../experiments/lab/dirty/2026-06-13-v2a-fallback-expandido/result.md)):
**7.85% weighted**, ganho 0.20–12.48%, RT 9/9 — cumpre o checklist
confirmada-empirica (N>=5 fontes distintas, bytes weighted >= 5%).

Pre-requisito satisfeito: a caracterizacao expos e levou ao fix do bug de RT
do core M10 com string vazia ([T-CODE-EMPTY-FRAG-INDEX-RT](../../tickets/T-CODE-EMPTY-FRAG-INDEX-RT.md))
— o caminho all-TCF que V2-A escolhe-ou-nao agora esta correto.

Problema de design: V2-A muda o formato (`#TCF.6` congelado por [ADR-0017](0017-format-spec-v1-frozen.md)).
Como integrar sem violar a disciplina byte-canonical (D1-D9=1523B, D17a=322B,
snapshots real-world)?

## Decision Outcome

**Weld V2-A como capacidade OPT-IN** (`encode(table, fallback=True)`), multi-col,
emitindo **`#TCF.7 M`** quando usada.

- **Default `fallback=False`** -> saida byte-identica ao v1 (`#TCF.6 M`).
  Segue o padrao do codebase: toda capacidade nova e' opt-in e o default
  preserva o invariante (cf. [ADR-0015](0015-natures-templated-checked-weld.md)
  natures, T-CODE-LAYERED-PIPELINE). Invariantes v1 INTOCADOS.
- **`fallback=True`**: por coluna escolhe `min(TCF, raw)`. Raw = `"\n".join(valores)`,
  usado so' quando ESTRITAMENTE menor E seguro (sem `\n` embutido). Emite
  `#TCF.7 M` sse ALGUMA coluna cai pra raw; senao `#TCF.6 M` (byte-identico).
- **Marcador**: par meta `!<size>=<name>` (`!` ANTES do size). Nao colide com
  nomes (size e' digito; `!` so' aparece em `#TCF.7`). Melhor que o `!name` do
  proto (que exigiria restringir nomes).
- **Decoder**: le `#TCF.6` e `#TCF.7` automaticamente; o `!` por par diz o modo
  (self-describing, sem flag no decode).

### Por que opt-in e nao default-on

Default-on tornaria `#TCF.7` a saida de qualquer tabela com coluna que infla,
mudando invariantes pinados (ex: D17a=322B) e a saida observavel de tabelas
pequenas. Isso e' uma decisao de RELEASE (bump de pacote 2.0.0, flip de default,
migration doc), separavel do weld da capacidade. O weld entrega V2-A no core
(testado, documentado, reversivel); flipar o default fica como decisao futura
do owner.

## Format (v2 / #TCF.7)

    #TCF.7 M
    # <size1>=<name1>,!<size2>=<name2>,...
    <body1><raw_body2>...

`!<size>=<name>` = coluna raw (body = `"\n".join(valores)`). Sem `!` = TCF
(M10 normal). Bodies length-delimited por size (byte-precise), igual v1.

## Pros and Cons

**Pros**:
- Ganho real-world (0.2–12.5% por dataset; 7.85% weighted nas 9 fontes), com
  piso forte "nunca pior que raw".
- Zero risco pro v1: default preserva todos os invariantes byte-canonical.
- Backward-compat total: decoder v2 le v1; encoder emite v1 quando nao ha ganho.
- Reversivel; abre o caminho v2.0 sem comprometer release labeling.

**Cons / limites**:
- Single-col fora de escopo (sem header pra marcar modo) — follow-up.
- Raw assume sem `\n` embutido (mesma premissa "dados felizes" do TCF).
- `#TCF.7` nao e' legivel por decoders v1 (esperado — e' o ponto do bump).

## Relation to other ADRs

- **ADR-0017** (format frozen v1.0): `#TCF.6` permanece congelado byte-identico.
  `#TCF.7` e' ADITIVO e opt-in; nao altera nenhuma saida `#TCF.6` existente.
- **ADR-0018** (roadmap v2.0): V2-A **welded**. V2-B (dicionario), V2-C (lossy),
  V2-D (strip sufixo) seguem como roadmap (este ADR nao os implementa).

## Consequences

- v2.0 ABERTA pela primeira capacidade (V2-A). Proximos candidatos do ADR-0018
  agora tem precedente de formato (#TCF.7 + marcadores opt-in).
- Decisoes de release PENDENTES (owner, nao bloqueiam o weld): flip de default
  fallback on; bump `tcf` 1.0.0 -> 2.0.0; migration doc v1->v2; single-col
  fallback.

## Verification

- `tests/test_multi_col_rt.py::TestV2AFallback` (8 casos: opt-in, #TCF.7 quando
  beneficia, #TCF.6 quando nao, byte-identico no default, raw com vazios,
  self-describing, marcador, single-col ignora).
- Suite completa: **340 passed, 1 xfailed**. Byte-canonical preservado
  (D1-D9=1523B, D17a=322B, snapshots real-world — todos no default).
- Caracterizacao 9 fontes: 7.85% weighted, RT 9/9.

## Links

- [Lab 2026-06-13-v2a-fallback-expandido](../../experiments/lab/dirty/2026-06-13-v2a-fallback-expandido/result.md)
- [ADR-0018 roadmap v2.0](0018-v2-format-roadmap.md)
- [ADR-0017 format frozen v1.0](0017-format-spec-v1-frozen.md)
- [T-CODE-EMPTY-FRAG-INDEX-RT](../../tickets/T-CODE-EMPTY-FRAG-INDEX-RT.md) (pre-req)
