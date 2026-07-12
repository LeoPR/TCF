---
title: T-DIST-RELEASE-0.8.0 — Release do pacote 0.8.0 (#TCF.8 default, ADR-0032)
status: open
priority: P2
created: 2026-06-21
updated: 2026-07-12
blocked-by: [T-REL-08-CLOSEOUT]
related:
  - docs/adr/0032-tcf8-default-format.md
  - docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-QA-8-material-comprobatorio.md
  - .github/workflows/release.yml
---

# T-DIST-RELEASE-0.8.0 (release do pacote 0.8.0)

> **ESTADO VIGENTE 2026-07-12 (supersede "só resta o go" de 07-09)**: C1/C2 e o smoke local
> continuam válidos como **pré-verificação**, mas C3 está operacionalmente bloqueado pelo
> [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md). Ordem por ROI: BUG-14 do domínio válido → F3 → F4 →
> F5 somente se gated → F6 docs/artefatos → este C3. Hardening de blob corrompido não fura essa
> fila. Publicação continua exigindo go explícito do owner.

> **RE-ESCOPO (ADR-0032, 2026-07-09) — este ticket VOLTA a ser o `0.8.0` (agora de verdade)**: o
> [ADR-0032](../docs/adr/0032-tcf8-default-format.md) tornou `#TCF.8` o formato **DEFAULT** → por ADR-0028
> (regra 1: mudança de formato move o minor) o pacote vai a **`0.8.0`**. O ciclo `0.7.2` (lazy+poda) foi
> **ABSORVIDO** no 0.8.0 (sem release intermediário). **ADR-0028 foi ACEITO** junto (não mais `proposed`),
> desbloqueando o rótulo. Este ticket **desbloqueado** (`blocked-by` vazio). Ação = bump 0.7.1→0.8.0 +
> CHANGELOG + tag, no **go explícito do owner** (PyPI segura em 0.7.1 até completo+estável). Os blocos
> datados abaixo (RETIFICAÇÃO 06-24 "= 0.7.2" / PONTE 07-08 / Updates) são HISTÓRICOS — leia nesta chave.

> **RETIFICAÇÃO (ADR-0028, 2026-06-24) [histórica — superada pelo RE-ESCOPO acima]**: este ticket é o
> **release `0.7.2`** (lazy + poda, formato `#TCF.7` inalterado), NÃO 0.8.0. O minor só move com mudança
> de formato → `0.8.0` fica reservado pro `#TCF.8` (cross-dict).

> **PONTE (2026-07-08)**: a carga do `0.8.0` mudou — o gate geral do **cross-dict FALHOU** (2026-06-27;
> pivô H-DICT-HIGHCARD). `0.8.0` = **release da família self-describing `#TCF.8` JÁ welded** (ato
> administrativo; fonte: reconciliação no STATUS.md + `tcf8-estrutura-plano.md`). **Pendência dispositivo
> ligada a este ticket**: **ADR-0028 segue `proposed`** — reconciliar a regra `0.N↔#TCF.N` com o fato de
> o magic `#TCF.8` já ter shipado sob 0.7.1 (scaffold opt-in) ANTES de aceitar; decisão do owner.

## Contexto / motivação

Fechar o ciclo do lazy: shipar o pacote com a view lazy promovida (A4) + a reference (A5) + a poda de
legado pré-0.7. Formato `#TCF.7` inalterado → **release `0.7.2`** (eixo C, ADR-0028). `#TCF.8` (e o
pacote `0.8.0`) ficam pro cross-dict, fora deste ticket.

## Plano (M5 — atualizado ADR-0032)

- **C1**: bump `pyproject.toml` + `src/tcf/__init__.__version__` **0.7.1 → 0.8.0**; atualizar o pino
  `test_version_pre_1_0` (`tests/test_regression_v1_baseline.py`, hoje `assert __version__ == "0.7.1"`).
- **C2**: `CHANGELOG.md` (entrada 0.8.0: #TCF.8 default, hex, escaping, legado .6/.7 cortado, lazy
  absorvido) + STATUS + ROADMAP + MAP + spec (a onda de docs do M4 já cobriu a maioria; cross-ref).
- **C3**: tag `v0.8.0` → `release.yml` publica via Trusted Publishing — **só no go do owner** (completo+estável).

## Critério de aceite

- [x] Versão **0.8.0** consistente (pyproject `0.8.0` + `__init__.__version__` + pino `test_version_pre_1_0`) — M5 2026-07-09.
- [x] CHANGELOG 0.8.0 (formato #TCF.8 default, hex, escaping, legado cortado, lazy absorvido) — M5.
- [x] Suíte local completa verde em 2026-07-12 (inclui hubs `requires_data`): **600 passed,
  2 skipped**; gate real-world = 89616B. Reexecutar no candidato final após BUG-14/F6.
- [~] `from tcf import view` no wheel publicado (smoke test pós-build) — **pré-verificado 2026-07-09 no wheel
  LOCAL** (`dist/tcf_format-0.8.0-cp313-win_amd64.whl`, buildado com `uv build` + Cython): clean-room em venv
  isolado (cwd fora do repo) passou import (`tcf`/`encode`/`decode`/`view`), `__version__==0.8.0`, RT single-col
  (orphan), RT multi-col (`#TCF.8M` inline hex), RT escaping (`a\:b\,c\=d`), lazy `LazyTCF`. **Re-confirmar no
  wheel PUBLICADO** na hora do go (Trusted Publishing sobe o mesmo arquivo).
- [ ] Gate R0 do domínio válido fechado (T-QA-8 BUG-14) + F3/F4 concluídos ou formalmente
  reduzidos por decisão registrada no T-REL-08.
- [ ] F6 concluído: README EN/PT, referência, metadata PyPI, wheel e smoke descrevem o mesmo 0.8.
- [ ] Estratégia Cython de release reconciliada com o workflow: produzir/testar a matriz de wheels
  decidida em `estrategia-distribuicao-cython.md` ou registrar explicitamente qualquer redução de
  plataforma antes da tag.
- [ ] Workflow confere `v<project.version>` = `tcf.__version__` e executa os gates do candidato.
- [ ] tag `v0.8.0` → `release.yml` (Trusted Publishing) — **go explícito do owner** (PyPI segura em 0.7.1 até lá).

## Riscos / notas

- **Bloqueado por**: fila R0-R2 do T-REL-08. A4/A5 e a decisão de B já foram fechadas; são
  contexto histórico, não o bloqueio atual.
- É o **último** da sequência (A → B → C); não destrava nada agora.

## Updates

- **2026-06-21**: aberto, blocked. A4 já fechou; faltam A5 + decisão de B antes de C.
- **2026-06-24 (decisão de escopo, owner)**: **0.8 = lazy (A1-A5, feito) + release**. Cross-dict
  (B2/B3) e filtros/spec-dict **deferidos pro 0.9** (#TCF.8 chega lá via B2). A5 feito → **só falta C
  (este ticket)**. Formato 0.8 = `#TCF.7` (sem #TCF.8). Desbloqueado p/ prep; tag/publish exige go
  explícito do owner.
- **2026-06-24-b (ADR-0028, retificação)**: este release = **`0.7.2`** (não 0.8.0); cross-dict #TCF.8
  = `0.8.0` (não 0.9). Plano acima corrigido pra 0.7.2. Sem bump agora (PyPI segura no 0.7.1).
- **2026-07-09 (pré-verificação de release, pós T-CLEAN-3)**: C1+C2+suíte **feitos** (M5). Rodada de
  de-risking ANTES do go: `uv build` gerou sdist + wheel `0.8.0` (Cython compilou); clean-room install num
  venv isolado passou o smoke completo (import + RT single/multi/escaping + lazy view; `__version__`
  correto). **Estado**: só resta o go do owner (C3, tag `v0.8.0` → Trusted Publishing). **Nota de higiene**:
  `dist/` ainda tem wheels stale `0.7.1` — a publicação deve subir só os arquivos `0.8.0` (ou limpar `dist/`
  antes do build de release; `dist/` é gitignored, resíduo local, sem impacto no git).
- **2026-07-12 (revisão por ROI)**: a frase "só resta o go" fica histórica. F1/F2 produziram
  evidência nova e a revisão encontrou BUG-14 no domínio aceito; F3/F4/F6 e os gates de artefato
  continuam antes de C3. Fonte única da ordem: T-REL-08-CLOSEOUT.
