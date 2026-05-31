---
title: Multi-column scaling — port pra canonical M10 + real-world
type: dirty-experiment
status: in-progress
tags: [tcf, multi-column, scaling, canonical, real-world]
created: 2026-05-23
predecessor: EXP-011-multi-column-basic
related:
  - docs/adr/0004-multi-column-header-compacto.md
  - docs/adr/0011-pacote1-weld-canonical.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md
---

# Multi-column scaling — port canonical + real-world

## Contexto

EXP-011 (2026-05-17) validou multi-column basico em D17a (13 rows x 4 cols)
usando `encode_column` do EXP-010 (delta_aware prototype, antes do M10).

Desde entao:
- 2026-05-22: Pacote 1 welded canonical (ADR-0011, M9 → M10, -5.70% em D1-D9)
- Real-world Adult Census + TPC-H validados single-column (EXP-012/013/014)
- Multi-column NUNCA testado em real-world

## Pergunta

1. `multi_col.py` portado pra `from tcf import encode, decode` preserva
   RT em D17a e mantem ou melhora bytes?
2. Multi-column escala em real-world (Adult Census 14 cols x 32k rows,
   TPC-H tables 4..16 cols x 5..60k rows)?
3. Header overhead (`#TCF.6 M` + `# s=n,...`) e' negligenciavel ou
   dominante em datasets reais?

## Hipotese

**H1**: Port canonical preserva RT em D17a (M10 e M9 ambos byte-canonical),
bytes iguais ou levemente menores (M10 captura mais padroes que M9).

**H2**: Multi-column em real-world e' viavel sem regressao significativa
vs concatenacao single-column.

**H3**: Header overhead < 1% pra datasets reais (>1k rows).

## Plano

### Fase 1 — Port D17a
- Criar `multi_col_canonical.py` usando `from tcf import encode, decode`
- Validar D17a: RT OK + comparar bytes vs EXP-011 (322B baseline)
- Output: `outputs/d17a-canonical.tcf` + report parcial

### Fase 2 — Real-world Adult Census
- Carregar via `DatasetReader("adult-census")` tabela `adult` (14 cols x 32k rows)
- Multi-encode + RT + medir header overhead
- Comparar com single-encoding (concat tudo em 1 coluna gigante)
- Stringify valores (TCF opera em strings)

### Fase 3 — Real-world TPC-H tables
- Tabelas pequenas: nation (4 cols x 25 rows), region (3 cols x 5 rows)
- Tabelas medias: customer (8 cols x 1500 rows), supplier (7 cols x 100 rows)
- Tabelas grandes: orders (9 cols x 15k rows), lineitem (16 cols x 60k rows)
- Medir scaling em ambos eixos (cols x rows)

### Fase 4 — Sintese
- Tabela: dataset, n_rows, n_cols, raw_bytes, multi_bytes, single_bytes,
  header_overhead%, RT
- Decidir: welding pra src/tcf? (criterio: real-world ganho consistente,
  RT 100%, header overhead < 5%)

## Criterio de aceite

- D17a: RT OK + bytes <= 322B (EXP-011 baseline)
- Real-world: RT 100% em pelo menos 4 tabelas (adult + 3 TPC-H)
- Multi-col vs single-col: ganho > 0% weighted ou explicacao clara da
  regressao
- Header overhead < 5% real-world (>1k rows)

## Limitacoes

- Datasets sao tratados como `dict[str, list[str]]` (stringify SQL types).
  Real-world inclui NULL, decimals, datetimes; conversao str() padrao.
- TPC-H lineitem 60k rows pode ser lento (HCC O(N^1.42)).
- Sem cross-column ou ordering otimizations (O-FMT-01..06 adiadas).

## Conexao

- [EXP-011 base](../../clean/EXP-011-multi-column-basic/) — single dataset sintetico
- [ADR-0011 weld canonical](../../../../docs/adr/0011-pacote1-weld-canonical.md)
- [futuras-otimizacoes-formato.md](../notas/futuras-otimizacoes-formato.md) — O-FMT-* registry
