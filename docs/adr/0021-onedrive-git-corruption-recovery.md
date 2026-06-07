# 0021 — Incidente: corrupção do repo por OneDrive + recuperação

**Status**: accepted (incidente documentado + recuperado)
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

## Decision — causa raiz

**O repositório NÃO deve ter o `.git` sincronizado pelo OneDrive.** Decisão
do owner (2026-06-03): **excluir o `.git` (e idealmente o repo) do sync do
OneDrive**, mantendo a pasta no local atual. Opções equivalentes registradas:
mover o repo pra fora do OneDrive (`Z:\` ou `C:\dev\`) elimina a causa de vez.

## Consequences

- **Positivo**: repo recuperado integralmente; incidente documentado pra
  rastreabilidade; causa raiz identificada.
- **Risco residual**: enquanto os arquivos de trabalho continuarem no
  OneDrive (mesmo com `.git` excluído), conflitos de arquivo-base podem
  recorrer. Mitigação real = repo fora do OneDrive.
- **Ação pendente (owner)**: configurar exclusão do sync (ver abaixo).

## Como excluir do sync do OneDrive (referência)

- **Opção A (recomendada, definitiva)**: mover `TCF/` pra fora do OneDrive
  (ex: `C:\dev\TCF\` ou `Z:\repos\TCF\`). Reabrir editores/terminais no novo
  caminho. Atualizar `config/storage.json` se necessário (Z: continua igual).
- **Opção B (excluir só do sync)**: OneDrive não tem exclusão por-subpasta
  confiável para `.git`; a via prática é "Settings → Sync and backup →
  Manage backup" ou usar um `.gitignore` do OneDrive não existe. A forma
  suportada é mover a pasta. (Por isso A é recomendada.)

## Links

- Backup: `Z:\tcf-backups\2026-06-03-onedrive-incident\`
- Commit de recuperação base: `81eee60` (HEAD real restaurado)
- Commit de limpeza: `06d4dc1`
