---
title: T-API-BOUNDARY-CONTRACTS — revisão profunda das fronteiras/semânticas da API antes do 1.0
status: open
priority: P2
created: 2026-07-10
updated: 2026-07-10
gate: pre-1.0
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - src/tcf/encoder.py
  - src/tcf/multi/core.py
---

# T-API-BOUNDARY-CONTRACTS — fronteiras da API: isolamento agora, semântica definitiva pré-1.0

**[dispositivo→registro]** Direção do owner (2026-07-10, ao aprovar o lote 3 do T-QA-8 F0):

> "o núcleo trabalha com strings mas tem algumas coisas relacionadas com anterior e próximo,
> diferença etc... tem também as questões dos specs. mas vamos tratar essas fronteiras primeiro,
> já pra ter os isolamentos. O código tendo tratamento pode identificar eles e a gente pode mudar
> comportamento. [...] faça um ticket pra inspecionar melhor no futuro, antes de terminar o 1.0."

Ou seja: os fail-louds/conversões do lote 3 são **ISOLAMENTO** — cada caso agora é identificado
num ponto único do código, então mudar o comportamento depois é trocar UMA decisão, não caçar
corrupção espalhada. Este ticket guarda a lista do que re-inspecionar **antes de fechar o 1.0**.

## O que ficou isolado no lote 3 (estado atual = fail-loud/converte; re-decidir aqui)

| caso | hoje (lote 3) | questão aberta pro 1.0 |
|---|---|---|
| BUG-08: meta vazio + body vazio | ValueError (não-emitível) | semântica de VAZIO no formato (junto com 0-rows/O-FMT-20: registro-'0' schema-declare pra append/parquet/tcfx) |
| BUG-09: str/bytes como valor de coluna | TypeError que ensina | aceitar iteráveis não-list (tuple? generator? numpy?) — contrato de container |
| BUG-10a: não-str em list | converte via `_to_str` (= dict, None→'') | conversão é a semântica certa pro núcleo-de-strings? tipos com relação anterior/próximo (deltas, cadência) e specs numéricos podem querer o VALOR TIPADO, não a str — cruzar com META-TYPE-ENCODERS/H-TYPE |
| BUG-10b/c/d: layers/parallel/decode tipos | TypeError/ValueError na porta | — (estável) |
| BUG-10c: parallel=1 | serial deduzido (sem pool) | ok; rever se paralelismo intra-coluna (V2-J) mudar o contrato |
| BUG-10e: name= sem nature | ValueError | name deveria existir sem nature (rotular single-col órfão)? exigiria header — decisão de formato |
| BUG-10f: stamp+dict | ignorado (M já é magic) — documentado | — |
| BUG-10g: nature=+dict / nature_per_col=+list | ValueError cruzado | unificar num kwarg só (`nature=` aceitando spec OU dict)? decode tem a MESMA assimetria calada (decode(single, nature_per_col=) ignora) — alinhar |
| tuple como valor de coluna | aceito (len+iter funcionam) | formalizar ou rejeitar |
| parallel= com list | ignorado calado | warning? single-col paralelo não existe |
| spec customizado fora do `SPEC_REGISTRY` | header `:id` exige `decode(..., nature=spec)` ou `nature_per_col` com `spec.name == id`; registry core vence | decidir antes do 1.0 se haverá registry carregável; nunca inferir spec por forma |

## Por que não decidir agora

Pre-1.0 o custo de mudar é zero (git-as-compat, ADR-0024) e o material comprobatório (T-QA-8)
ainda vai revelar o que os usos reais pedem. As questões de TIPO (anterior/próximo, diferença,
specs) dependem do rumo do META-TYPE-ENCODERS — decidir contrato de container antes disso seria
chute.

## Critério de aceite

- [ ] Passada única pré-1.0 revisando a tabela acima, caso a caso, com decisão registrada
  (manter/mudar) e testes de contrato atualizados.
- [ ] Simetria encode/decode conferida (kwargs ignorados calados no decode também).
- [ ] Cruzado com T-FMT-OMIT-OR-DECLARE (vazios) e META-TYPE-ENCODERS (tipos/specs).
