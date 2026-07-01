---
title: T-DOC-3 — Terminologia: "shebang" → assinatura de formato / magic number
status: closed-canonical-set
priority: P3
created: 2026-07-01
updated: 2026-07-01
related:
  - docs/vocabulary.md
  - docs/adr/0001-tcf-format-shebang.md
  - docs/algorithms/TCF-format.md
---

# T-DOC-3 — "shebang" é impreciso

## Contexto (owner 2026-07-01)

Chamamos `#TCF.N` de **"shebang"**, mas shebang é `#!` (diretiva de interpretador Unix). O nosso
**não é shebang** — é uma **assinatura de formato / magic number** (textual), análoga a **`%PDF-1.7`**
(também `<?xml`, ou binárias `GZ`=`1F 8B`, `MZ`, `PK`). É o que `file`/libmagic usam pra inferir o
**mimetype** (`application/x-tcf`). ADR-0029 já dizia "magic-number"; só a prosa antiga ficou com "shebang".

## Escopo

"shebang" aparece **130× em 42 arquivos** (inclui o título do arquivo do ADR-0001). Fix **cirúrgico
nos docs canônicos/autoritativos**; os históricos (diários, checkpoints, labs fechados, closed
tickets) **ficam como registro** (§3 traço preservado — não reescrever o que foi dito então).

## Feito (2026-07-01) — termo canônico SETADO

- **docs/vocabulary.md**: entrada canônica "assinatura de formato / magic number" + o distintivo
  vs shebang + análogo `%PDF-`.
- **docs/adr/0001-tcf-format-shebang.md**: nota terminológica no topo (arquivo NÃO renomeado —
  preserva links); tag `magic-number`.
- **docs/algorithms/TCF-format.md**: eixo (A) usa "assinatura de formato / magic number".

## Backlog opcional (incremental, não urgente)

Varrer as menções em prosa **viva** restante (README/STATUS/CLAUDE/ROADMAP + ADRs 0004/0027/0029/0030
+ strategies-map) trocando "shebang" → "assinatura/magic" quando for prosa corrente. **NÃO** tocar
históricos. Sem pressa — o termo canônico já está estabelecido no vocabulário.

## Critério de aceite

- ✅ termo canônico definido em vocabulary.md + apontado do ADR-0001 e da spec. **FEITO.**
- backlog: prosa viva restante varrida incrementalmente (opcional).
