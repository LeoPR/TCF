# TCF — Copilot Instructions

> **O guia canônico é [`AGENTS.md`](../AGENTS.md) na raiz. Leia ele.**
>
> Este arquivo é só um ponteiro. Ele **não** re-expressa nem destila o guia:
> a versão destilada anterior derivou da fonte (ficou dizendo `#TCF.6`
> congelado e baselines desatualizados) — o custo da duplicação. Qualquer
> regra, checklist, convenção, gate ou "NUNCA" está em `AGENTS.md`.

Rota: [`AGENTS.md`](../AGENTS.md) (regras) → [`STATUS.md`](../STATUS.md)
(estado vigente) → [`MAP.md`](../MAP.md) (onde fica o quê).

Os três pontos que mais custam caro se ignorados — o detalhe está no guia:

- **Não modificar `src/tcf/`** sem aprovação explícita (é o código canonical).
- **Não push** pra GitHub/`main` sem solicitação explícita; **sem** `Co-Authored-By:`.
- Mudança em HCC `_detect_compositions` / pré-pass / prune **deve** passar
  `tests/test_real_world_snapshots.py` (gate byte-canonical real-world).
