# 0003 — Tripartite Pre/OBAT/HCC com pesos relativo vs absoluto

**Status**: accepted
**Date**: 2026-05-17
**Deciders**: project owner
**Tags**: architecture, separation-of-concerns, OBAT, HCC

## Context and Problem Statement

Quando OBAT detecta similaridade via LCP/LCS entre strings, quanto OBAT
pode/deve "propor" sobre delta semantico? Quanto HCC pode/deve
"complementar" (RLE, virtual refs, body)?

Tentativa inicial: OBAT emite `TokRefDelta(string_id, +N, unit)` — i.e.,
OBAT NOMEIA o delta com semantica (`+N` em unidade especifica).

## Considered Options

1. **OBAT type-aware** — OBAT detecta tipo, emite tokens semanticos
   (`+1d`, `+1m`)
2. **Tripartite** — Pre detecta tipo + emite **dica generica**; OBAT
   permanece **type-agnostic**, emite **marcadores abstratos**; HCC
   materializa em bytes (pesos absolutos)
3. **HCC sozinho** — OBAT intocado; HCC sozinho deve agrupar

## Decision Outcome

**Opcao 2 — Tripartite Pre/OBAT/HCC.**

| Camada | Responsabilidade | Tipo de peso | Conhece tipo? |
|---|---|---|---|
| **Pre** | Detectar tipo + gerar dica **generica** | Analise (sem bytes) | Sim |
| **OBAT** | Comparacoes relativas + decidir se quebra | **Pesos relativos** (cabe/nao-cabe) | Nao (so' modos calibrados pela dica) |
| **HCC** | Materializar + juntar inteligentemente | **Pesos absolutos** (bytes no body) | Nao |

### O ponto-chave: marcadores abstratos vs. peso absoluto

OBAT ja' opera assim:
- `TokRefPref(string_id, length)` e' **abstrato** — nao sabe quantos
  bytes vai custar no body
- Decisao de "qual ref escolher" e' por **comprimento relativo** —
  maior LCP/LCS vence, independente de bytes finais
- HCC depois decide a representacao concreta (`~`, `^N`, `*N|`)

Extender pra delta segue mesmo padrao:
- OBAT emite metadata abstrata ("este literal varia +1 relativo
  ao predecessor")
- HCC decide se isso vira: descarte, serializacao inline, RLE
  compacta, virtual ref dedicada

**OBAT nao nomeia** o delta como "+1 dia". Isso seria peso absoluto.

### Dica generica vs viciada

A dica do pre-stage **nao pode dizer "voce e' uma data"**.

Aceitavel:
- `byte_window=(X,Y)` — onde provavelmente esta a variacao
- `enable_relative=True` — habilitar comparacao relativa
- `monotonic_expected=True` — esperar sequencia ordenada
- `prefer_shape_consistency=True` — preferir same shape que anterior

Rejeitado:
- `type="date"`, `parse_as_datetime=True`, `calendar_unit="day"`

## Pros and Cons of the Options

| Opcao | Pros | Cons |
|---|---|---|
| OBAT type-aware | Mais simples conceitualmente | OBAT vira complexo; type-coupling viola separacao |
| **Tripartite** | Separacao limpa; OBAT type-agnostic; extensivel | Mais layers pra coordenar |
| HCC sozinho | Maxima conservacao; OBAT intocado | Pode atingir limite em alguns casos (validado: D11d post-transition) |

## Validacao empirica

Pacote 1 (lab `2026-05-17-OBAT-delta-aware`):
- H-DA-01 (HCC sozinho): -22% em D11a-h
- H-DA-07 (OBAT shape-preserve hint): -32% em D11a-h
- H-DA-09b (auto-detect cadence): -18% em 20 datasets sinteticos

Os tres validam aspectos da tripartite.

## More Information

- Conceitual: `experiments/lab/dirty/2026-05-17-OBAT-delta-aware/notas/modelo-conceitual.md`
- Validacao: `experiments/lab/dirty/2026-05-17-OBAT-delta-aware/sub-exps 02, 04, 09`
- Memoria projeto: `project_pacote1_delta_aware_summary.md`

## Cross-references

- [ADR-0002](0002-vertice-triplice-restricao.md) — restricao que motiva
  esta separacao
- Pacote 1 diario: `experiments/lab/dirty/notas/diario/2026-05-17.md`
  decisoes D3, D4, D5
