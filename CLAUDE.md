# TCF — Claude Code

> **O guia canônico é [`AGENTS.md`](AGENTS.md)** (brand-free, fonte única).
> **Leia ele primeiro** — regras de acesso, checklists, gates de evidência,
> convenções e a lista NUNCA vivem lá, não aqui. Este arquivo existe só porque
> o Claude Code carrega `CLAUDE.md` automaticamente, e guarda o que é
> específico desta ferramenta. Divergência entre os dois: **`AGENTS.md` vence.**

## Rota de entrada

1. [`AGENTS.md`](AGENTS.md) — guia canônico (regras)
2. [`STATUS.md`](STATUS.md) — estado vigente
3. [`MAP.md`](MAP.md) — onde fica o quê
4. [`README.md`](README.md) — overview pra humano

## Específico do Claude Code — hierarquia de memória

`AGENTS.md` §6 descreve as camadas de conhecimento de forma agnóstica. O
mapeamento concreto nesta ferramenta:

- **Escopo-usuário** — `~/.claude/projects/<slug>/memory/` (`MEMORY.md` + um
  arquivo por fato). Preferências pessoais e feedback de processo, **cross-projeto**,
  fora do repo. Não versionado aqui.
- **Escopo-projeto** — [`AGENTS.md`](AGENTS.md) + `docs/adr/`, versionados em git.
  É o que é COMUM ao time.

Regra de tier: se vale pra qualquer projeto → escopo-usuário. Se é conhecimento
do TCF partilhado via git → `AGENTS.md`/ADR. Não duplicar entre os dois.

Memórias de incidente citadas em `AGENTS.md` (caminhos locais desta máquina):
[`feedback_discoverability_falha_EXP_012`](../../../.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/feedback_discoverability_falha_EXP_012.md) ·
[`project_reorg_separation_of_concerns`](../../../.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/project_reorg_separation_of_concerns.md)
