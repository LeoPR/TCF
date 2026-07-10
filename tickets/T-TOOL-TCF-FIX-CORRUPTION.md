---
title: T-TOOL-TCF-FIX-CORRUPTION — reparador de .tcf com algum grau de corrupção (ideia, pensar depois)
status: open
priority: P3
created: 2026-07-10
updated: 2026-07-10
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - src/tcf/multi/core.py
---

# T-TOOL-TCF-FIX-CORRUPTION — reparador de blobs corrompidos

**[dispositivo→registro]** Ideia do owner (2026-07-10, durante o F0 do T-QA-8): fazer um tipo de
"fix" de TCF — ferramenta que tenta RECUPERAR um `.tcf` com algum grau de corrupção. Fica registrado
pra pensar depois; **não é escopo do 0.8**.

## Ancoragem: o decode agora MARCA as situações

O lote F0 (BUG-01/02) fez o decode fail-loud com mensagens `meta corrompido: ...` — esses pontos são
os GANCHOS de detecção que um reparador consumiria (detectar já está feito; reparar é o passo novo):

- **nome DECLARADO vazio** (`<size>=`): encoder nunca emite ('' vira anônima) — `_parse_meta`.
- **backslash dangling** (cauda ímpar no fim do nome): encoder nunca emite — `_unesc_name_strict`.
- **size hex inválido** — `_hex_size`.
- (registrados, ainda SEM marcação — BUG-04/05 do T-QA-8 §3): versão futura `#TCF.9M` caindo no
  decode órfão; **body truncado** (sizes do header não batem com os bytes disponíveis; sem
  cross-check de n_rows entre colunas). Quando fixados, viram mais ganchos.

## Esboço (pra discussão futura)

- Vive FORA de `src/tcf` (gadget, filosofia CLAUDE.md: detecta/alerta/repara em ferramenta, o core
  nunca "arruma" calado). `scripts/tcf_fix/` ou spin-off.
- Grau de corrupção tratável (hipóteses): meta truncado → re-derivar sizes contando bodies?; body
  truncado → recuperar colunas ANTERIORES ao corte (sizes hex dão offsets); token fundido por escape
  → propor splits candidatos; sempre output = RELATÓRIO + blob-candidato, nunca sobrescrever.
- Princípio: reparo é sugestão auditável (diff), decisão é do usuário.

## Critério pra abrir o trabalho

Owner prioriza depois do material comprobatório (T-QA-8) e da publicação 0.8.
