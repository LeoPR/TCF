---
title: T-FMT-NAME-ESCAPING — Escape/quoting de nomes de coluna (e chaves de hierarquia) no meta do header
status: open
priority: P1
created: 2026-07-09
updated: 2026-07-09
gate: pre-.8-default
blocked-by: []
related:
  - tickets/T-FMT-HEADER-BASE-HEX.md
  - tickets/T-FMT-TCF8H-HEADER.md
  - docs/adr/0029-version-format-identification-semi-implicit.md
  - experiments/lab/dirty/notas/tcf8-header-char-registry.md
---

# T-FMT-NAME-ESCAPING — escape/quoting de nomes no meta

**[dispositivo→código]** Direção do owner (2026-07-09): resolver as colisões de caractere em **nome de
coluna** (e futuras chaves de hierarquia) com **escaping/quoting** — as técnicas já consagradas de CSV —
em vez de **rejeitar** o nome (o que o encoder faz hoje). Estudar uma forma inteligente (quoting implícito
de aspas + escape pra `:` e similares, pra viajarem junto com o nome); **por enquanto**, resolver com
**escapes** dos caracteres que dão conflito.

## O problema (o que a revisão pré-bump 2026-07-09 achou)

O parser do meta separa por `,` (colunas) → `=` (size/nome) → `:` (nome/nature-id). O name-guard
(`multi/core.py:120-133`) **REJEITA** hoje nome com `,`/`=`, com `:` (só quando há nature) e começando com
`!@%`. Dois defeitos:
- **`:` sob #TCF.8-default (blocker do flip)**: o guard só proíbe `:` quando há nature, mas o decode v8 faz
  `rsplit(':')` **incondicional** → com #TCF.8 default, `encode({'created:at': …})` decoda como coluna
  `created` + warning "nature-id desconhecido: at" → **RT quebrado em silêncio**.
- **`#` no início do nome (bug pré-existente)**: o parse tolerante do meta v7 come um `# `/`#` inicial →
  `encode({'# foo': …})` decoda como `{'foo': …}` sem erro (`core.py:319-322`, `view.py:78-83`).

Nomes com `:` são hoje **VÁLIDOS** (pinados em `test_natures.py:255-259`) — rejeitar sempre seria breaking
de superfície de input. Escapar preserva a superfície E fecha o RT.

## Direção (interim + smart)

**Interim (desbloqueia o .8-default)** — usar a convenção `\` que o formato **já tem** no corpo
(`_escape_lit` em `syntax.py:83` escapa digit-runs + `* \ ~`). Escapar no NOME, no emit, os chars
estruturais; des-escapar no parse. Chars a escapar: `,` `=` `:` `\` + `#`/`!`/`@`/`%` no **início**
(e `{` `}` `[` `]` quando entrar hierarquia). O tokenizer do meta passa a splitar em separador
**NÃO-escapado** (`,`/`=`/`:` precedidos de nº par de `\`). Round-trip exato; substitui o name-guard
(rejeita → escapa). **Lockstep**: `multi/core.py` (emit + parse) + `view.py` (re-parse lazy).

**Smart (o alvo deste ticket)** — desenhar a forma inteligente: **quoting implícito** (envolver o nome em
aspas SSE contém separador — como CSV) vs **escape por char** (`\:`); decidir qual é mais limpo/inspecionável;
cobrir TODOS os separadores + os chars de hierarquia; provar round-trip; medir o custo em byte (escape só
paga quando o nome tem o char — caso raro). Reusar o vocabulário do [char-registry Eixo 3](../experiments/lab/dirty/notas/tcf8-header-char-registry.md).

## Escopo / relação
- **Desbloqueia** o `.8-default` (decisão owner 2026-07-09): sem isso o `:` quebra RT no default. Deve
  entrar **com ou antes** do flip.
- Ortogonal ao hex (nomes vêm depois do size; sem interação).
- Interage com a **gramática da hierarquia** (`{}[]` no meta-árvore) — o escape tem que cobri-los quando o
  codec TCF.8H for adiante.

## Critério de aceite
- [ ] Interim: escape backslash dos chars estruturais no nome; tokenizer split-em-não-escapado; RT provado
  (incl. `created:at`, `# foo`, `a,b`, `x=y`). Name-guard vira escape (não rejeita).
- [ ] Lockstep `core.py` (emit+parse) + `view.py` (re-parse) + testes.
- [ ] Smart: decisão quoting-implícito vs escape-por-char, com custo-byte medido e round-trip.
- [ ] Cobre os chars de hierarquia (`{}[]`) pro codec TCF.8H.
