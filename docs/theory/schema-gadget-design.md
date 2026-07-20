---
title: Design — Schema/Quality Gadget (T-RECOVER-SCHEMA-MULTI-TABLE)
type: explanation
status: design-draft
created: 2026-06-03
related:
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md
  - tickets/T-DATA-3-EDGE-QUALITY-FIXTURES.md
  - src/tcf/schema.py        # build_schema CORE — NAO e' o gadget
  - src/tcf/side_outputs.py  # canal zero-custo que o gadget consome
  - docs/adr/0018-v2-format-roadmap.md  # V2-J/K/L: perspectivas do framework
---

# Design — Schema/Quality Gadget

> **Status: rascunho de design.** Define O QUE o gadget é, sua fronteira e
> fases — antes de qualquer código. Não implementa nada.

## 1. Posição (o que É e o que NÃO É)

O gadget é uma ferramenta **auxiliar, externa ao TCF-core**, que **só
detecta e alerta — nunca arruma** (filosofia "dados felizes" do AGENTS.md).
Vive em `scripts/schema_gadget/` (spin-off recomendado quando crescer).

**Distinção crítica de nome (existem 4 `schema.py` no repo):**

| Coisa | Onde | É o gadget? |
|---|---|---|
| `build_schema(data) → TableSchema` | `src/tcf/schema.py` (CORE, welded) | **NÃO** — é core, per-tabela, fica |
| **Schema/Quality Gadget** | `scripts/schema_gadget/` (não existe ainda) | **SIM** — cross-table, alert-only |

O `build_schema` core já produz, **por tabela**, via SideOutputs (zero-custo):
`ColumnSchema(name, n_rows, n_unicas, avg_len, cardinality, is_numeric,
cadence_detected, cadence_rule, min_len, body_bytes, seq_rle_runs_count,
sample, natures)` + `TableSchema(n_rows, n_cols, columns, total_bytes,
header_bytes, body_bytes, is_multi_col)`.

O gadget **consome** isso e adiciona o que o core **não** faz: análise
**cross-table** + alertas de qualidade. Não modifica `src/tcf/`.

## 2. Princípios (invioláveis)

1. **Detecta, nunca arruma.** Output = relatório/sinal. O dev/arquiteto
   decide o que fazer. (Provado necessário: no lab CPF, "consertar" um
   dígito verificador errado = corrupção silenciosa.)
2. **Paralelo e zero-custo onde possível.** Consome o que o TCF já computa
   (SideOutputs). Não força recomputação cara sem necessidade.
3. **Não toca o core.** Importa `build_schema`/`SideOutputs` como
   **consumidor**; nunca modifica `src/tcf/`.
4. **Honesto sobre custo.** Cada detector declara se é zero-custo (já em
   SideOutputs), barato (acumulador no pass O(N) — mas isso TOCA o pre-pass,
   gated por T-REGRESSION-REAL-WORLD), ou caro (scan dedicado cross-table).

## 3. O que detecta (catálogo) — por custo

### Zero-custo hoje (já em ColumnSchema/SideOutputs — só expor)
- **duplicate_primary_key / useless-id**: coluna esperada-única com
  `cardinality < 1.0` → chaves duplicadas; `cardinality ≈ 0` → coluna inútil.
- **type_drift**: `is_numeric=True` mas valores não-numéricos no sample.

### Barato (acumulador no analyze_column — GATED, toca pre-pass)
- **missing_values / completude**: contagem de nulos/vazios (não é campo
  atual; exige somar no pass O(N) → gate real-world).
- **length_variance_anomaly**: stddev de comprimento numa coluna "uniforme"
  (só temos avg_len hoje).

### Caro (scan dedicado do gadget — NÃO zero-custo)
- **fk_orphan / fk_candidate** (cross-table): `col_A.values ⊂ col_B.values`
  com %. Precisa interseção de conjuntos entre tabelas. **Núcleo da Fase 1.**
- **format_inconsistency**: datas ISO vs BR vs US misturadas numa coluna.
- **impossible_value / impossible_date**: 32-fev, idade negativa, ship>receipt.
  Exige conhecimento de domínio/calendário.
- **bad_check_digit** (CPF/CNPJ): zero-custo SÓ quando uma nature opt-in está
  ativa (mod-11 já recomputado); senão, scan dedicado.

Fixtures de teste para cada classe: ticket T-DATA-3 (deferred, alimenta este).

## 4. Fases (do ticket, refinadas)

1. **Fase 1 — FK detector** ✅ (`fk_detect.py`): overlap de valores +
   confiança graduada (nome+cardinalidade). Validado TPC-H 9/9, 0 FP em alta.
2. **Fase 2 — date/format checker** ✅ (`date_check.py`): auto-detecta
   colunas-data; impossible_date/format_mix/suspicious_date. NÃO zero-custo
   (scan dedicado, calendário). Validado por corrupção controlada (0 FP no
   real limpo, recall total no corrompido).
3. **Fase 3 — SideOutputs hook** ✅ (`sideouts_quality.py`): alertas
   zero-custo (constant, duplicate_key single-PK, type_drift fração-numérica).
   Validação adversarial removeu useless_id (94% ruído).
4. **Fase 4 — CLI** (`python -m scripts.schema_gadget analyze <dir>`):
   relatório markdown/json. **Nunca modifica nada.**
5. **(Opcional) Fase 5 — spin-off** `tcf-quality-gadget`.

## 5. Visão de fundo — perspectivas do mesmo framework (registrado, não-agora)

O owner registrou (ADR-0018 V2-J/K/L; docs/theory) que **online, disco e
remoto são perspectivas de UM framework**, ligadas pela mesma relação
encode/decode ("mandar remoto == mandar pro disco; disco é memória remota").

O gancho relevante para ESTE gadget: **computar sem descomprimir (pushdown).**
Um `RLE *N|linha` é um **groupby natural** — uma camada acima pedindo
contagem/agrupamento/estatística **não precisa descomprimir**: a forma
armazenada já dá agrupamento + estatística, economizando decode, memória
intermediária e reanálise. O mesmo vale para `A..B` (ranges) e
`*N+delta|template` (seq-RLE).

Implicação de design (para quando evoluir): o gadget — e uma futura camada
SQL-like de recuperação rápida com filtros — devem **ler os agrupamentos
direto da estrutura comprimida** (via `seq_rle_runs`/RLE no body) em vez de
materializar. "Perder" compressão às vezes vale a pena dependendo da
operação-alvo no decode. Isto NÃO é escopo da Fase 1; fica como norte.

> ⚠️ **Sinalização (pedido do owner): o que beneficia um cenário SQL-like
> de recuperação rápida com filtro.** Hoje, o que já está alinhado a isso:
> (a) `seq_rle_runs` em SideOutputs expõe os grupos sem expandir; (b) RLE
> `*N|` e ranges `A..B` no body são pushdown-friendly; (c) `build_schema`
> dá cardinality/is_numeric por coluna (seleção de plano sem ler dados).
> O que FALTARIA para um "mini-SQL": um índice de offset por coluna
> (V2-K disk/column-pruning, ADR-0018) e um leitor que opere no body
> comprimido. Marcar qualquer trabalho futuro que avance nisso.

## 6. Fora de escopo (explícito)

- Não corrige dados (nunca).
- Não altera `src/tcf/`.
- Não implementa a camada SQL-like agora (é norte, não Fase 1).
- Fixtures de defeito: ticket T-DATA-3 (separado, deferred).

## 7. Próximo passo

Aprovado o design → Fase 1 (`fk_detect.py`) validado em TPC-H. Decisão de
adicionar campos zero-custo ao SideOutputs (Fase 3) é separada e mais
sensível (toca core opt-in) — avaliar depois da Fase 1.
