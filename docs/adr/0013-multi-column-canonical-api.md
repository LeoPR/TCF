# 0013 — Multi-column canonical API welded em src/tcf

**Status**: accepted + welded
**Date**: 2026-05-23
**Deciders**: project owner
**Tags**: welding, multi-column, canonical, api, encode_table, header-format

## Context and Problem Statement

EXP-011 (2026-05-17) validou multi-column basico em D17a sintetico
(13 x 4) usando `encode_column` do EXP-010 prototype (M9 era).

Desde entao:
- 2026-05-22: Pacote 1 canonical welded em src/tcf (M9 → M10, ADR-0011)
- 2026-05-23: T-EXP-MULTI-COL-SCALING port multi_col.py pra canonical M10
  + real-world validation (9 tabelas Adult Census + TPC-H tier 1+2,
  136k linhas, RT 9/9, -33.02% weighted vs raw, -31.46% vs single concat)

Lacuna: multi-column ainda nao tinha API publica em src/tcf. Owner
aprovou welding apos validacao real-world completa (inclusive lineitem
60k em Fase 4).

## Considered Options

### Opcao A — `encode_table(dict)` + `decode_table(text)` separados

Adiciona funcoes novas a API publica:

```python
from tcf import encode, decode, encode_table, decode_table
```

- `encode(values)` → single-column (M10 canonical, ADR-0011)
- `encode_table(table)` → multi-column (este ADR)

Pros:
- Explicit > implicit (Zen of Python)
- Type-safe sem runtime checks
- API clara: nome indica numero de colunas
- Backward compat trivial (encode/decode intocados)
- Continuidade com EXP-011 / sub-exp dirty (mesmo nome)

Contras:
- API publica tem 2 pares de funcoes (encode/decode + encode_table/decode_table)

### Opcao B — `encode(values | dict)` overload

```python
encode(["a", "b", "c"])           # single-col
encode({"id": [...], "name": ...}) # multi-col
```

Pros:
- DRY (1 funcao para tudo)

Contras:
- Type check em runtime (`isinstance(values, dict)`)
- Documentacao ambigua (signature dupla)
- Return type ambiguo (str vs (str, dict))
- Quebra contrato existente de `encode` (que retorna str sem info)

### Opcao C — `encode_columns(table)` (nome O-FMT-05 antigo)

Nome plural "columns" pra distinguir.

Pros:
- Mais descritivo "multi-column"

Contras:
- Plural inconsistente com `encode` singular
- O-FMT-05 era v0.5 era (legacy), nome ja' tinha sido descartado

## Decision Outcome

**Opcao A — `encode_table` + `decode_table` separados**.

Razoes:
1. Explicit > implicit (filosofia Python + projeto)
2. Type-safe sem branching runtime
3. Continuidade com sub-exp dirty (port direto)
4. API publica permanece estavel (encode/decode intactos)
5. Validado empiricamente em real-world antes do welding (criterio
   metodologico TCF: nao welder sem real-world test)

## Implementacao

### Novo modulo `src/tcf/multi.py`

API:
```python
def encode_table(table: dict[str, list[str]]) -> tuple[str, dict]:
    """Encode multi-column. Returns (tcf_text, info_dict)."""

def decode_table(tcf_text: str) -> dict[str, list[str]]:
    """Decode multi-column TCF text."""
```

Internamente itera por coluna chamando `tcf.encode` / `tcf.decode`.

### Header format (welded de ADR-0004, EXP-011)

```
#TCF.6 M
# <size1>=<name1>,<size2>=<name2>,...
<body1><body2>... (concatenado, byte-precise por size)
```

- Magic + flag: `#TCF.6 M` (8 bytes + LF)
- Meta line: pares `size=name` (size em bytes UTF-8 do body) separados
  por virgula
- Bodies concatenados sem delimitador (sizes garantem separacao via
  byte-count)

### NULL handling

`None -> ""` (empty string). Justificativa:
- TCF opera em strings (camada acima ja' faz type conversion)
- Empty string e' valor valido em real-world (e.g., optional fields)
- POC validou em Adult Census (~25% NULL em CustomerID) e TPC-H sem
  problemas observaveis
- Risco: colisao com empty string legitima, mas TCF nao tem semantica
  de "NULL distinto" - quem precisa pode wrap em encoder customizado

### Restricoes

- Nomes de coluna nao podem conter `,` ou `=` (caracteres reservados
  do header). Levanta `ValueError` se violado.
- Todas colunas devem ter mesmo numero de valores. Levanta `ValueError`.

### Atualizacoes a `src/tcf/__init__.py`

```python
from tcf.encoder import encode
from tcf.decoder import decode
from tcf.multi import encode_table, decode_table

__all__ = ["encode", "decode", "encode_table", "decode_table"]
```

## Consequences

**Positivas**:
- API publica multi-column disponivel sem importar from sub-exp
- D17a 322B baseline preservado (byte-canonical com EXP-011)
- Real-world validation completa (RT 9/9, -33% weighted vs raw)
- Welding seguindo metodologia TCF (criterio real-world antes de src/)

**Negativas/risco**:
- API agora tem 4 funcoes publicas (era 2). Users precisam aprender
  diferenca encode/encode_table.
- NULL -> "" pode causar collision (documentado como limitacao;
  encoders customizados podem wrap)
- HCC tempo lineitem 60k = 16.6 min (gargalo conhecido, Cython/Rust
  H-PERF-06 adiado).

## Validacao byte-canonical

- D17a sintetico: 322 bytes (INVARIANT, == EXP-011 baseline)
- D17a RT: OK
- Real-world Adult Census + TPC-H tier 1+2 (9 tabelas): RT 9/9
- Real-world bytes weighted: -33.02% vs raw, -31.46% vs single-col concat

Tests adicionados em `tests/test_multi_col_rt.py` com D17a 322B como
invariant (CI-friendly, sem requires_data marker).

## Links

- [ADR-0004 — Multi-column header compacto](0004-multi-column-header-compacto.md)
  (welded predecessor; este ADR confirma header format)
- [ADR-0011 — Pacote 1 weld canonical (M9 → M10)](0011-pacote1-weld-canonical.md)
  (single-col canonical, base do multi)
- [EXP-011 multi-column basic](../../experiments/lab/clean/EXP-011-multi-column-basic/)
- [T-EXP-MULTI-COL-SCALING](../../tickets/T-EXP-MULTI-COL-SCALING.md)
- [sub-exp dirty 2026-05-23-multi-column-scaling](../../experiments/lab/dirty/2026-05-23-multi-column-scaling/)
