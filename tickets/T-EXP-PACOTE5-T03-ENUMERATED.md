---
title: T-EXP-PACOTE5-T03-ENUMERATED — Pacote 5: enumerated nature canonical
status: closed
resolution: no-go-m10-suficiente
priority: P2
created: 2026-05-23
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - tickets/META-TYPE-ENCODERS.md
  - experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md
  - experiments/lab/dirty/2026-05-23-pacote5-t03-enumerated/
  - tickets/T-CODE-PACOTE1-WELD-CANONICAL.md
  - docs/adr/0011-pacote1-weld-canonical.md
---

# T-EXP-PACOTE5-T03-ENUMERATED — Enumerated canonical (Pacote 5)

## Contexto / motivacao

Reflexao 2026-05-23 sobre naturezas numericas (nota
`notas/naturezas-numericas-2026-05-23.md`) identificou **natureza #7
(classes/enumerated)** como candidato Pacote 5.

TCF M10 atual ja' captura colunas low-card via:
- Dedup (atoms unicos)
- HCC seq-RLE (`*N|linha` para repetidos consecutivos)

Mas NAO tem encoder enumerated EXPLICITO (dict + indices). Hipotese:
encoder enumerated dedicado pode comprimir colunas low-card melhor
que dedup + RLE atual.

Candidatas reais em TPC-H:
- `l_discount` (~11 valores unicos em [0.00..0.10] step 0.01)
- `l_returnflag` (3 valores: A, N, R)
- `l_linestatus` (2 valores: F, O)
- `l_shipinstruct` (4 valores)
- `l_shipmode` (7 valores)

Adult Census:
- `sex` (2 valores)
- `race` (5 valores)
- `class` (2 valores)
- `workclass`, `marital-status`, `relationship` (poucos valores)

## Hipotese / pergunta

**H-ENUM-01**: Em real-world Adult+TPC-H, qual o ganho potencial de
encoder enumerated explicito vs M10 atual (dedup + seq-RLE)?

Sub-questoes:
- Quanto bytes/row TCF M10 atual consome em colunas low-card?
- Qual e' o lower bound teorico (1 byte/row + dict overhead)?
- Diferenca justifica encoder dedicado?

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-23-pacote5-t03-enumerated/`

### Sub-exp 01 — caracterizacao + estimativa ganho

Pra cada coluna low-card (card < 0.05) em Adult+TPC-H:
1. Bytes atual TCF M10 (`tcf.encode`)
2. Bytes lower bound teorico:
   - dict overhead: sum(len(v) for v in unicas) + N seps
   - body: n_rows * ceil(log10(N+1)) chars
3. Bytes encoder enumerated estimado:
   - dict inline + N atoms
   - body com bare digits (sem escape) + seps
4. Diff M10 vs enumerated = ganho potencial

**Criterio go**: ganho weighted real-world >= 5% sobre colunas low-card.

### Sub-exp 02 (condicional) — prototype encoder enumerated

Se go: fork dirty implementando encoder enumerated:
- Detect heuristica (card < threshold + dedup retornaria poucos atoms)
- Sintaxe especial no body para enumerated col
- Decoder espelho

### Sub-exp 03 (condicional) — welding canonical

Se ganho confirmado e RT 100%:
- ADR-0012 (novo encoder + nova natureza canonical)
- Welding em src/tcf (aprovacao owner obrigatoria)

## Criterio de aceite (KR)

- [ ] Sub-exp 01 com tabela ganho por coluna
- [ ] Decisao go/no-go documentada (>= 5% weighted)
- [ ] (se go) Sub-exp 02 prototype + RT 100%
- [ ] (se welding) ADR-0012 + welding canonical aprovado

## Riscos

1. **M10 ja' captura via RLE**: low-card cols com runs longos
   (sorted) sao bem comprimidos hoje. Ganho marginal possivel.
2. **Real-world mistura**: l_returnflag em TPC-H esta intercalado
   (A, N, R repetidos mas nao em runs longos). RLE captura parcial.
3. **Welding complexo**: adicionar nova natureza no encoder canonical
   muda sintaxe HCC — decisao arquitetural.

## Conexoes

- [Reflexao naturezas numericas](../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
- [META-TYPE-ENCODERS T03](META-TYPE-ENCODERS.md)
- [Taxonomia natureza enumerated](../docs/theory/data-natures-taxonomy.md)
- [ADR-0011 Pacote 1 canonical](../docs/adr/0011-pacote1-weld-canonical.md)

## Updates datados

### 2026-05-23 — abertura

Ticket criado seguindo convencao YAML frontmatter. Reabre escopo de
META-TYPE-ENCODERS (T03) com criterio atingido (Pacote 1 + ADR-0008 +
ADR-0010 + ADR-0011 cobrem numericos high-card mas nao low-card explicito).

Pre-requisito atendido: ColumnFeatures (H-DA-11c) ja' tem
`cardinality` e `n_unicas` pra usar como features de detect_enumerated.

Fase 1 (caracterizacao) e' decisor — se ganho < 5%, encerrar lab.

### 2026-05-23 — Fase 1 caracterizacao: NO-GO (M10 ja' captura bem)

Sub-exp 01 mediu 37 colunas low-card (card < 0.05) em D1-D9 + Adult +
TPC-H, comparando bytes M10 atual vs lower bound enumerated explicit.

**Agregados**:
- Low-card real-world total: M10=311,434B vs enum LB=331,749B
  → **M10 vence por -6.52%** (encoder explicit seria PIOR)
- Weighted real-world total (todas cols): **-2.28%** (regressao)

**Padroes identificados**:
- M10 dominante em low-card com runs adjacentes (sorted/grouped):
  - l_linestatus (2 valores, 5000 rows): M10=4137B vs enum=10002B → M10 -141.77%
  - l_returnflag (3 valores, 5000 rows): M10=8075B vs enum=10004B → M10 -23.89%
  - adult class (2 valores, 5000 rows): M10=8229B vs enum=10009B → M10 -21.63%
- Enum ganha em cols com valores LONGOS sem runs:
  - c_mktsegment (5 valores, 1500 rows, ~12 chars/valor): +30.20%
  - relationship Adult (6 valores, "Husband" etc.): +27.18%
  - l_quantity (50 valores, 5000 rows): +20.30%

**Aprendizado meta**: TCF M10 ja' e' encoder enumerated implicito
EFICIENTE via `dedup + HCCSeqRLE`. Encoder explicit teria ganho
marginal SELETIVO em colunas com valores longos sem runs adjacentes,
mas perda global em colunas com poucos valores curtos + runs.

Mesmo padrao do Pacote 2 (escape deduction): hipotese promissora
conceitualmente refutada em medicao empirica. Anti-incidente checklist
do CLAUDE.md (5 perguntas) aplicado corretamente — sub-exp 01
caracterizacao impediu welding de encoder com ganho marginal/negativo.

**Resolution**: no-go-m10-suficiente. Lab fechado, META-TYPE-ENCODERS
T03 NAO reaberto (criterio empirico nao atingido).

**Direcao alternativa**: encoder enumerated CONDICIONAL (heuristica
para detectar quando vale a pena: valores longos + sem runs) poderia
ser exploration futura, mas overhead de heuristica + 2 encoders
provavelmente nao vale ~2-3% ganho seletivo.
