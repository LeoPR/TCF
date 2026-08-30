---
title: "BUG-MENSAGEM-COLUNA-VAZIA-MISTA: fail-loud omite o nome válido vazio"
type: bug
status: closed-fixed
priority: P3
severity: "diagnóstico: o erro identifica colunas nomeadas, exceto o nome vazio"
created: 2026-08-29
updated: 2026-08-30
gate: "correção em src/tcf só com aprovação explícita do owner (I5)"
blocked-by: []
related:
  - src/tcf/hierarchical.py
  - docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md
  - experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/
  - tickets/T-QA-083-REVALIDACAO.md
---

# BUG-MENSAGEM-COLUNA-VAZIA-MISTA

**[probatório → execução]** Nome de coluna `""` é dado válido e representável. O controle
`{"": [1, 2]}` faz round-trip exato; porém, quando a mesma coluna mistura número e string, o
fail-loud omite qual coluna falhou.

## Comparação mínima

Artefato completo:
[`nome-vazio.observacao.json`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/outputs/nome-vazio.observacao.json).

```text
{"v": [1, "x"]}  -> "coluna 'v': tipos escalares MISTOS ..."
{"":  [1, "x"]}  -> "tipos escalares MISTOS ..."
```

As duas entradas levantam `HierarchicalError`, como devem. O problema é somente a perda da
identidade no segundo diagnóstico. A entrada homogênea e seu round-trip estão materializados em
`inputs/nome-vazio.entrada.json` e `outputs/nome-vazio.roundtrip.json`.

## Causa local

`_scalar_type(values, name)` monta o prefixo com `if name`. Isso trata `""` como ausência de nome,
embora o parâmetro use `None` para representar a ausência e o ADR-0046 torne `""` um nome válido.

## Consequência

O changelog da 0.8.3 afirma que o erro misto passou a nomear a coluna e o valor. A afirmação vale
para nomes truthy, mas não para todo o domínio de nomes aceitos pelo formato.

## Critérios de aceite

- [x] `encode({"": [1, "x"]})` continua falhando alto e a mensagem contém `coluna ''`.
- [x] Lista anônima continua sem inventar nome de coluna.
- [x] Coluna nomeada não muda a mensagem fora do prefixo já existente.
- [x] Controle homogêneo com nome vazio preserva wire e round-trip.
- [x] Gates `test_regression_v1_baseline.py` e `test_real_world_snapshots.py` verdes, conforme I5.
- [x] Lab reexecutado e reclassificado como fechado.

## Estado

**FECHADO em 2026-08-30.** A causa era a que o ticket aponta, e o critério 2 dele antecipou
uma armadilha que tornava a correção óbvia errada.

O prefixo usava `if name`, e `""` é falsy. Mas trocar por `if name is not None` sozinho não
bastava: a raiz não-dict é embrulhada em `[{"": data}]` (o envelope `#V`,
`hierarchical.py`), então uma **lista solta** chega ao `_scalar_type` com a mesma chave `""`
de um `{"": [...]}` legítimo. As duas produzem literalmente a mesma chamada, e a lista teria
passado a anunciar `coluna ''`, que é o que o critério 2 proíbe.

Quem sabe a diferença é o `_encode_root`, e agora é ele que a informa: os dois sítios do
envelope passam `anon=True`, que o `_derive_schema` traduz num **rótulo de mensagem**
separado do nome do campo. O nome continua indo para o header como sempre (`\z`, ADR-0046);
só o diagnóstico muda.

| entrada | diagnóstico |
|---|---|
| `{"": [1, "x"]}` | `coluna '': tipos escalares MISTOS, …` |
| `[1, "x"]` | `tipos escalares MISTOS, …` (sem coluna, porque não há) |
| `{"v": [1, "x"]}` | `coluna 'v': …`, inalterado |

Testes: `TestMensagemNomeiaColunaDeNomeVazio` em `tests/test_f0_boundary_fixes.py`, com o
round-trip do nome vazio homogêneo em quatro formas como contra-prova.

Suíte 1708, gates 33 verdes, sem mudança de wire.
