---
title: T-API-BOUNDARY-CONTRACTS — congelar as fronteiras/semânticas da API no .8 (= 1.0)
status: open
priority: P1
created: 2026-07-10
updated: 2026-07-13
gate: .8
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

## FREEZE 2026-07-13 (owner: `.8` = 1.0 — decidir AGORA, supersede "não decidir agora")

O reescopo `.8`=feature-complete (2026-07-13) **inverte** a seção "Por que não decidir agora" abaixo:
se o `.8` é o 1.0, os contratos de borda **congelam agora**. Além da tabela do lote 3, o congelamento
resolve as lacunas do **modelo JSON** levantadas na avaliação 2026-07-13 (o `.8` cobre o subconjunto
plano/homogêneo/string; estas são as bordas onde ele diverge do JSON):

| borda JSON | comportamento MEDIDO hoje | decisão a congelar no `.8` |
|---|---|---|
| `null` (≠ `""` ≠ ausente) | `None` não preserva (RT False; coage) | **decidir**: fail-loud em `None` (núcleo é strings, não há null) OU sentinela reversível. Default recomendado: **fail-loud claro** ("None não é representável; use '' ou um sentinela seu") — não inventar null no formato |
| tipos escalares (number/bool) | preservados como STRING byte-exato (`1.0`/`007`/`1e3`) | **congelar**: `.8` é lossless de STRING; tipo não é distinguido. `123`(num JSON) e `"123"` viram a mesma string. Documentar como contrato (quem quer tipo usa schema-gadget / `:tipo` da hierarquia em W4 do TCF.8H) |
| registros ragged (keys diferentes por objeto) | `ValueError` (colunas de tamanhos diferentes) | **congelar fail-loud**: tabela exige colunas alinhadas. JSON ragged → responsabilidade do produtor alinhar (ou vai por hierarquia) |
| `\n` dentro de valor | `ValueError` (LF delimita linhas) | **DECISÃO PENDENTE do owner**: (a) manter fail-loud declarado, ou (b) **escape de LF no corpo** (format-change, precisa RT+gate) — cruza T-FMT-QUOTING-STUDY. É a maior lacuna funcional vs JSON |
| `""` vazio vs coluna vazia | RT OK (`''` preservado); coluna toda-vazia → registro-'0'/schema (BUG-03/O-FMT-20) | **congelar**: `''` é valor legítimo; semântica de coluna/registro vazio já isolada (T-FMT-OMIT-OR-DECLARE) |

**Tabela do lote 3** (BUG-08..10g abaixo): cada linha ganha uma decisão **manter/mudar** registrada,
com teste de contrato. A maioria = **manter o fail-loud/conversão atual** (já é o comportamento certo
pro núcleo-de-strings); as exceções a decidir são `\n`-em-valor (acima) e a unificação `nature=`/
`nature_per_col=` (BUG-10g — alinhar encode/decode).

> A hierarquia (T-CODE-TCF8H-WELD) **herda** este contrato: se o `.8` congela "tudo string", `#TCF.8H`
> preserva escalares como string; se entrar `:tipo`, é decisão conjunta (W4 daquele ticket).

## Por que não decidir agora (SUPERSEDED 2026-07-13 — mantido por histórico)

Pre-1.0 o custo de mudar é zero (git-as-compat, ADR-0024) e o material comprobatório (T-QA-8)
ainda vai revelar o que os usos reais pedem. As questões de TIPO (anterior/próximo, diferença,
specs) dependem do rumo do META-TYPE-ENCODERS — decidir contrato de container antes disso seria
chute.

## Critério de aceite

- [ ] Passada única pré-1.0 revisando a tabela acima, caso a caso, com decisão registrada
  (manter/mudar) e testes de contrato atualizados.
- [ ] Simetria encode/decode conferida (kwargs ignorados calados no decode também).
- [ ] Cruzado com T-FMT-OMIT-OR-DECLARE (vazios) e META-TYPE-ENCODERS (tipos/specs).
