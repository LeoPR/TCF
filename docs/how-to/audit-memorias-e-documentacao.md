---
title: How to — Auditar memorias e documentacao
type: how-to
status: active
tags: [maintenance, documentation, audit]
created: 2026-05-18
updated: 2026-05-18
---

# Auditar memorias e documentacao

Recipe pra revisao periodica (sugerido: a cada 60-90 dias OU quando
notar drift). Objetivo: evitar reincidir o
[incidente 2026-05-18](../../experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)
(perder visibilidade do que ja' existe).

## Passo 1 — Re-gerar INDEX.md e revisar

```bash
python scripts/index.py
```

Olhar:
- READMEs sem frontmatter — vale adicionar?
- READMEs com `status: active` mas inativos ha' tempo — atualizar?
- READMEs com `status: closed` mas ainda em desenvolvimento — fix
- Tags desencontradas — usar vocabulario controlado (`docs/vocabulary.md`)

## Passo 2 — Stale markers em memorias

Procurar todos `[VERIFICAR: YYYY-MM-DD]`:

```bash
grep -rn "VERIFICAR:" \
  experiments/lab/dirty/notas/ \
  ~/.claude/projects/*/memory/ 2>/dev/null
```

Pra cada marker vencido:
- Verificar se claim ainda e' verdade
- Atualizar conteudo OU postar nova data
- Se nao se aplica mais: deletar marker (e talvez o memo)

## Passo 3 — ADRs

`docs/adr/`:
- Revisar `Status` de cada
- ADR `accepted` que foi superseded mas nao marcado: corrigir
- ADRs em uso devem ser referenciados em ao menos 1 doc/README
- Verificar links externos (paper, ferramentas) — atualizar URLs quebrados

## Passo 4 — Cross-links nas READMEs principais

Re-rodar `scripts/index.py` ja' lista todas READMEs. Pra cada uma
ativa:
- Tem secao "See also"?
- Links ainda funcionam?
- Aponta pra ADRs/roadmaps relevantes?

Sugestao: spot-check 5 aleatorias.

## Passo 5 — Vocabulario controlado

Abrir `docs/vocabulary.md`:
- Algum termo novo apareceu em conversas recentes? Adicionar.
- Termo deprecated ainda aparecendo? Marcar "NAO usar" e fazer
  grep pra trocar nos docs ativos.

## Passo 6 — Roadmap de hipoteses

Abrir `experiments/lab/dirty/notas/roadmap-hipoteses.md`:
- Hipoteses `em-exp` ha' muito tempo: tem sub-exp ativo?
- Hipoteses `aberta` sem progresso: ainda relevante? mover pra
  `adiada`?
- Decorrentes registradas: vale promover algumas a hipoteses
  formais ou ADRs?

## Passo 7 — Checkpoints

`experiments/lab/dirty/notas/checkpoints/`:
- Checkpoints "atuais" mas com decisao tomada: marcar `resolved`
- Checkpoints muito antigos: arquivar ou consolidar narrativa em
  diario

## Passo 8 — Memorias user vs project

Abrir `~/.claude/projects/*/memory/MEMORY.md`:
- Entries user-scope que sao na verdade project-scope: migrar
  pra `CLAUDE.md` ou ADR
- Entries project-scope no user-scope-only: migrar
- Duplicacao entre memoria e ADR: consolidar em UM lugar (ADR ganha)

## Passo 9 — Diretorios obsoletos

Verificar:
- `docs/archive/` — v0.5; marcacao "NAO USAR" presente?
- `experiments/lab/dirty/old/` — historicos; marcacao presente?
- `old/tcf/` (se existir) — motor v0.5 obsoleto; marcacao?

## Passo 10 — Sintese da auditoria

Escrever entrada no diario do dia:
```
## YYYY-MM-DD — Auditoria de docs/memoria

- N stale markers vencidos atualizados
- N ADRs revisados (status mantido / mudado)
- N termos vocabulario adicionados
- N hipoteses promovidas/movidas
- Itens criticos pendentes: ...
```

## Sinais de drift (detectar antes de auditoria formal)

- Conversa em que voce tenta criar/baixar algo e descobrir que ja' existe
- Documento referencia algo "que era pra existir" mas nao acha
- Dois docs descrevendo a mesma coisa de forma divergente
- Decisao re-debatida porque ninguem achou o ADR original
- Memoria do Claude erra sistematicamente sobre algo do projeto

Quando notar sinal → audit imediato dessa area.

## Antipatterns a evitar

- **README sprawl**: nem todo dir precisa de README; so' onde
  agrega navegacao
- **Index hand-maintained**: usar `scripts/index.py`, nao manter
  INDEX.md a mao
- **ADR retroativo**: nao escrever ADR pra decisao trivial; usar
  diario
- **Memoria duplicada**: se o conteudo vive em ADR ou doc, memoria
  user so' aponta pra la'
- **Stale forever**: marker sem revisao = pior que nao ter

## See also

- [CLAUDE.md](../../CLAUDE.md) — guia raiz de discoverability
- [MAP.md](../../MAP.md) — wayfinding
- [vocabulary.md](../vocabulary.md) — termos controlados
- [ADR-0005](../adr/0005-discoverability-claude-md-root.md) — decisao
  do sistema
