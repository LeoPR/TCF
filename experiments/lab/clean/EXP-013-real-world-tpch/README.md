---
title: EXP-013 — Real-world test em TPC-H (multi-table)
type: clean-experiment
status: active
tags: [tcf, real-world, multi-column, multi-table, tpch, scale]
created: 2026-05-18
updated: 2026-05-18
predecessor: EXP-012-real-world-adult-census
related:
  - scripts/shaper/README.md
  - scripts/dataset_reader.py
  - docs/adr/0006-empty-string-decode-fix.md
---

# EXP-013 — Real-world test em TPC-H (8 tabelas)

**Data**: 2026-05-18
**Tipo**: experimento clean
**Estado**: ativo
**Predecessor**: EXP-012 (Adult Census, 1 tabela)

## Pergunta cientifica

Pipeline EXP-011 generaliza pra TPC-H **8 tabelas** com tipos
variados? Especificamente:
- RT byte-canonical OK em todas tabelas?
- Como varia ratio TCF/raw entre tabelas (categorica vs numerica)?
- Performance em tabela maior (lineitem 60k)?
- Bug empty-string (ADR-0006) realmente fixou pra real-world?

## Infra utilizada

- **`scripts/dataset_reader.py`** — `DatasetReader("tpch-sf001")`
- **`Z:/tcf-data/interim/tpch-sf001.db`** — SQLite hub
- **EXP-011** `multi_col.encode_table` (welded EXP-010)
- **ADR-0006 fix** aplicado (empty strings funcionam)

## Tabelas TPC-H SF=0.01

| Tabela | Rows | Cols | Caracter |
|---|---:|---:|---|
| region | 5 | 3 | nation regions |
| nation | 25 | 4 | country names + key |
| supplier | 100 | 7 | suppliers info |
| customer | 1500 | 8 | customers (text + numeric) |
| part | 2000 | 9 | parts (mix) |
| partsupp | 8000 | 5 | join table part+supplier |
| orders | 15000 | 9 | order headers (date + numeric) |
| lineitem | 60175 | 16 | order details (BIG) |

Total: ~87k rows, 61 col-instances.

## Plano

Por tabela:
1. Carrega N rows via `DatasetReader.rows(table, limit=N)`
2. Converte `list[dict]` → `dict[col, list[str]]`
3. `encode_table(cols)` → bytes
4. `decode_table(text)` → verifica RT
5. Mede: bytes raw CSV, bytes TCF, ratio, runtime

Volume strategy: full rows pra tabelas <= 5000; cap em 5000 pras
maiores (orders, lineitem). EXP-012 mostrou encode O(N²) — 5000
rows leva ~30s; lineitem full seria proibitivo.

## Aceite

- **RT 8/8 tabelas OK** (obrigatorio) — **NAO atingido**, 3/8 OK; revelou bugs canonical
- **Ratio TCF/raw < 100%** em ao menos 6 tabelas (compressao real) — parcial
- **Per-tabela stats documentadas** — sim

## Achados criticos durante EXP-013

EXP-013 revelou MULTIPLOS bugs no decoder canonical
(`src/tcf/composicional/syntax.py`):

1. **Bug empty-string** (FIXADO): empty body line skipada via
   `not linha`. Ver [ADR-0006](../../../../docs/adr/0006-empty-string-decode-fix.md).
2. **Bug whitespace** (FIXADO em mesmo lugar): `.strip()` removia
   leading/trailing whitespace de literais. TPC-H comments frequentemente
   tem trailing space.
3. **Bug comma in literal** (NAO FIXADO, REGISTRADO):
   literais contendo `,` corrompem no decode. Ex: `'pending, bold reques'`
   → `'pending bold reques'`. Causa: `,` e' separator em refs mas
   `_escape_lit` NAO escapa `,` em literais.
4. **KeyError downstream** (NAO FIXADO): KeyError em `part` (2800),
   `orders` (5620), `lineitem` (11072). Provavelmente downstream do
   bug #3 (parser confuso por commas mal-tratadas).

**Decisao**: nao tentar mais fixes apressados em canonical. Bug #3
requer analise profunda do _escape_lit + _parse_decl. Registrar
como issue/ADR futuro.

## Hipoteses derivadas

- **H-RW-07**: tabelas categoricas (region, nation) com poucas
  uniques tem ratio MUITO baixo (alta repeticao -> seq-RLE explode)
- **H-RW-08**: lineitem com 16 cols varia muito (datetime + decimal
  + text); ratio similar a Adult Census (~38-42%)
- **H-RW-09**: pipeline aguenta 5000 rows × 16 cols (lineitem
  amostrado) sem travamento (encode <60s)

## See also

- [EXP-012 Adult Census](../EXP-012-real-world-adult-census/) — predecessor
- [shaper README](../../../../scripts/shaper/README.md)
- [ADR-0006 empty-string fix](../../../../docs/adr/0006-empty-string-decode-fix.md)
