---
title: "BUG-BB-CR-CRU: a união bool+str emite CR cru em wire LF-only"
type: bug
status: closed-fixed
priority: P2
severity: "E4 (canonicidade: o encoder emite byte proibido; round-trip ainda é exato)"
created: 2026-08-29
updated: 2026-08-30
gate: "correção em src/tcf só com aprovação explícita do owner (I5)"
blocked-by: []
related:
  - src/tcf/encoder.py
  - docs/algorithms/output-convention.md
  - docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md
  - experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/
  - tickets/T-QA-083-REVALIDACAO.md
---

# BUG-BB-CR-CRU

**[probatório → execução]** O wire vigente é LF-only, mas a rota single-column
`#TCF.8bB` aceita uma string extra com CR e grava o byte `0d` literalmente.

## Repro materializado

Entrada: [`cr-bb.entrada.json`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/inputs/cr-bb.entrada.json).
Wire: [`cr-bb.tcf`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/outputs/cr-bb.tcf).
Observação: [`cr-bb.observacao.json`](../experiments/lab/dirty/2026-08/2026-08-29/2026-08-29-2320-revalidacao-083-evidencia/outputs/cr-bb.observacao.json).

```python
from tcf import decode, encode

dado = [True, "a\rb"]
wire = encode(dado)

assert b"\r" in wire.encode("utf-8")
assert decode(wire) == dado
```

Hex gravado pelo runner:

```text
23 54 43 46 2e 38 62 42 32 32 0a 61 0d 62 0a 3d 73 41
                                    ^ 0d no offset 12
```

O round-trip em memória e o diff entrada/round-trip passam. Isso prova que o defeito não é perda
de dado; é o encoder produzindo um wire fora da convenção canônica.

## Controles

O mesmo runner prova quatro vizinhos:

- `encode([True, "a\nb"])` recusa: o `bB` já bloqueia LF;
- `encode(["a\rb"])` recusa CR;
- `encode({"v": ["a\rb"]})` recusa CR;
- `encode([{"v": "a\rb"}])` escapa o CR, não grava `0d` e faz round-trip.

Portanto, a aceitação não é uma política geral de CR: é um buraco específico na rota `bB`.

## Causa local

`_encode_lazy_bool` em `src/tcf/encoder.py` recusa um extra quando contém `"\n"`, mas não testa
`"\r"`. Como essa rota antecede o guard flat comum, o CR não chega à validação que protege as
outras formas.

## Contrato contradito

- `AGENTS.md`, seção de wire: **LF only, UTF-8**;
- `docs/algorithms/output-convention.md`: não usar CRLF, apenas LF;
- comportamento dos controles flat: a mensagem pública diz que `\r` não é representável.

## Critérios de aceite

- [x] `encode([True, "a\rb"])` não emite nenhum byte CR cru.
- [x] O caso segue fail-loud, como o controle `bB` com LF; nenhuma coerção ou remoção de caractere.
- [x] `decode(encode(x)) == x` permanece exato para extras sem quebra.
- [x] Controles single string, multi e hierárquico preservam o comportamento atual.
- [x] Teste dedicado grava o caso de CR, não apenas LF.
- [x] Gates `test_regression_v1_baseline.py` e `test_real_world_snapshots.py` verdes, conforme I5.
- [x] Lab reexecutado e reclassificado como fechado, com wire/round-trip novos em disco.

## Estado

**FECHADO em 2026-08-30.** A correção é uma condição em `_encode_lazy_bool`
(`src/tcf/encoder.py`): o guard de quebra de linha testava `"
" in e` e passou a testar
`""` também. O extra com CR volta a cair no `.8H`, que faz o fail-loud da união, exatamente
como já acontecia com o LF.

Os quatro controles do ticket seguem intactos, conferidos por execução: o single-col e o
multi-col recusam CR com a mensagem de quebra de linha; o `.8H` escapa e faz round-trip; e o
extra sem quebra continua emitindo o mesmo wire, byte a byte.

Testes: `TestBBSemCRCru` em `tests/test_f0_boundary_fixes.py`, com uma varredura que confere
que **nenhum** wire `bB` carrega CR cru, para doze grafias de extra, e que os LF do wire são
só os de framing.

Suíte 1708, gates 33 verdes, sem re-pin (o wire de entrada válida não muda; o que muda é uma
entrada que passou a ser recusada).
