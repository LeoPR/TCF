# 0021 — Incidente OneDrive × `.git` no TCF: recuperação (causa = hipótese)

**Status**: accepted (recuperado; causa raiz registrada como HIPOTESE, sem acao estrutural)
**Date**: 2026-06-03
**Deciders**: project owner
**Tags**: incident, git, onedrive, recovery, infra

## Context

O repositório TCF vive em `C:\Users\leona\OneDrive\Documents\Projects\Acadêmicos\TCF`
— **dentro de uma pasta sincronizada pelo OneDrive**. Em 2026-06-03, ao
retomar o trabalho, o `import tcf` carregava a API v0.2 antiga e a suíte
quebrava na coleta.

## O que aconteceu (diagnóstico)

O OneDrive sincronizou um estado conflitante do repositório, causando
corrupção em duas camadas:

1. **`.git` revertido**: `HEAD`/`main`/`reflog` apontavam para `e979cd5`
   ("Workbench ciclo 3 cabecalho v0.4", ~abril, v0.4) — **158 commits atrás**
   do trabalho real. Os commits novos (datasets, reorg Fases 0-7, H-PERF-06,
   STATUS sync `81eee60`) **existiam como objetos** no `.git` (verificado via
   `git cat-file`), mas `main` não os referenciava. Provável: OneDrive
   sincronizou um snapshot antigo do `.git` por cima, preservando objetos
   soltos em `objects/` mas revertendo refs.

2. **Arquivos de nome-colidido embaralhados**: onde v0.5 e v0.6 têm o mesmo
   nome (`src/tcf/{__init__,decoder,encoder,schema}.py`, `pyproject.toml`,
   `tests/test_shaper.py`, e vários READMEs/docs), o OneDrive pôs a versão
   ANTIGA como arquivo-base e salvou a versão CORRETA (v0.6) como
   `<nome>-DESKTOP-SG30VJF.<ext>` (21 arquivos no total). Um conflito
   (`old/tests/test_p01_p02_p03-DESKTOP-SG30VJF.py`) chegou a ser commitado
   por engano num commit antigo.

Nada foi perdido — toda a história e o código v0.6 estavam recuperáveis.

## Recuperação (executada 2026-06-03)

1. **Backup** completo antes de qualquer ação destrutiva:
   `Z:\tcf-backups\2026-06-03-onedrive-incident\` = cópia do `.git` +
   `git bundle --all` (19.9 MB) + alvo registrado.
2. **`git reset --hard 81eee60`** — `main` de volta ao commit mais recente
   real (STATUS sync, filho da Fase 7 `bb02cff`). Verificado: `81eee60` é
   descendente linear de `e979cd5` (+158 commits), e seu `src/tcf/` contém
   o v0.6 completo (22 arquivos: natures, composicional, core, _core/detect.pyx,
   side_outputs, schema build_schema, etc.).
3. **Limpeza**: deletados os 21 `-DESKTOP-SG30VJF` (lixo de conflito; versões
   corretas já restauradas pelo reset) + o stray commitado (commit 06d4dc1).
4. **Validação**: `import tcf` expõe API v0.6 (`encode/decode/SideOutputs/
   build_schema/natures`); suíte **280 passed + 1 xfailed**; working tree
   bate com o commit.

## Causa raiz — HIPÓTESE (correção 2026-06-03)

> **Correção honesta:** uma versão anterior deste ADR afirmava causa
> "multi-máquina sistêmica". A evidência NÃO sustenta isso — ver abaixo.

Hipótese mais provável: **latência local × OneDrive numa máquina só.**
Durante rajadas de commit (sprints intensas do TCF), o OneDrive tentou
sincronizar arquivos `.git` no meio da escrita e gerou cópias de conflito
(`-DESKTOP-SG30VJF`) em vez de uma versão única. Evento **raro e pontual**,
recuperável — não defeito do OneDrive nem corrupção aleatória.

**Ressalva temporal (erro de análise corrigido):** a varredura encontrou
também conflitos com OUTRO nome de máquina (`DESKTOP-6NFNFQF`), mas TODOS de
**2022–2023** — fósseis de máquina antiga fora de uso. A análise inicial
"comprimiu" anos de artefatos como se fossem um único incidente recente, e
concluiu erradamente "duas máquinas ativas". O owner trabalha em UMA máquina.

## Decision

**Nenhuma ação estrutural agora.** O TCF foi recuperado e verificado íntegro
(working tree == HEAD por hash; `.git` fsck limpo; 5847 arquivos 100%
hidratados — OneDrive sobe o estado correto). Mover o repo / excluir do sync
fica como **opção futura, não-urgente**, a avaliar só se o problema recorrer.

Estratégia leve registrada (se recorrer): ter remoto git (`git push` — o
`.git` local deixa de ser cópia única) e/ou pausar sync durante commits
intensos. Detecção rápida no início de sessão: `git log -1` + procurar
`-DESKTOP-*` em `.git` + confirmar `import tcf`.

## Consequences

- **Positivo**: repo recuperado integralmente e verificado; incidente
  documentado com diagnóstico honesto (hipótese, não certeza inflada).
- **Risco residual**: baixo. Pode recorrer em rajada de commit + sync
  simultâneo, mas é raro e a detecção/recuperação é simples.
- **Sem ação pendente obrigatória** — só vigilância leve.

## Links

- Nota cross-projeto (raiz Documents): `NOTA-onedrive-git-observacao.md`
- Backup: `Z:\tcf-backups\2026-06-03-onedrive-incident\`
- Commit de recuperação base: `81eee60` (HEAD real restaurado)
- Commit de limpeza: `06d4dc1`
