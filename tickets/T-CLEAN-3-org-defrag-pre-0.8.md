---
title: T-CLEAN-3 — defrag de organização (docs/tickets/diário) pós-#TCF.8-default, pré-review 0.8
status: open
priority: P2
created: 2026-07-09
updated: 2026-07-09
blocked-by: []
related:
  - tickets/META-STRATA-GOVERNANCE.md
  - tickets/T-CLEAN-2-strata-defrag.md
  - STATUS.md
  - MAP.md
  - experiments/lab/dirty/notas/diario/README.md
---

# T-CLEAN-3 — defrag de organização (sucessor do T-CLEAN-2)

**[dispositivo→execução]** Rodada de higiene de superfície pedida pelo owner (2026-07-09) DEPOIS de
fechar o `#TCF.8`-default (M1-M5, ADR-0032). **Objetivo**: arrumar redundâncias e furos de organização
pra **facilitar o review do que falta pro 0.8** — não é um fim em si. Sucessor do
[T-CLEAN-2](T-CLEAN-2-strata-defrag.md) (round anterior, QW+DB feitos 2026-07-01), sob
[META-STRATA-GOVERNANCE](META-STRATA-GOVERNANCE.md).

## ⚠️ REGRAS DE SEGURANÇA (colisão temporal — diretriz do owner 2026-07-09)

A ordem de autoridade é o **histórico de commits, do agora pra trás**. Ao arrumar:
1. **git = juiz.** Quando um arquivo for ambíguo (obsoleto? vivo?), `git log`/`git blame` do arquivo
   decide o que ele significava na ERA dele — não o entendimento de hoje.
2. **3 categorias a distinguir** (o motivo da arrumação):
   - **(a) antigo mas desenvolvido AGORA** → VIVO (manter; no máximo re-indexar/re-datar).
   - **(b) antigo obsoleto que RECUPERAMOS e arrumamos** → VIVO (atualizado; NÃO arquivar).
   - **(c) genuinamente antigo e obsoleto** → arquivar (mover pra `old/`/tombstone), **nunca deletar**.
3. **Nunca reescrever/reordenar** conteúdo que codifica uma decisão válida na época. **Anotar (bridge),
   não sobrescrever**; **arquivar, não deletar**.
4. **Cross-ref**: cada mudança aponta o commit/ADR que a justifica (rastreabilidade recuperável).
5. Ordem: **redundância óbvia e sem-colisão primeiro** → arquivos ambíguos (comparar com o git) por último.

## Levantamento (2026-07-09, verificado contra git)

- **Índice de tickets furado**: `tickets/README.md` lista 43 rows; existem **62** arquivos → **19 fora do
  índice**. Breakdown (git, último commit): 13 `closed*` (histórico), 3 `deferred`, **2 `open`**
  (T-STUDY-HIERARCHICAL-TCF, T-FLOW-ENCODE-STRATEGIES-TELEMETRY — trabalho VIVO não-descobrível), 1
  matrix-done. Nenhum é colisão-risco (os do `.8` já estão no índice).
- **Diário furado (PROBLEMA, owner)**: ~25 dias úteis com commit mas SEM entrada de diário —
  **2026-05-22→06-11** (14 dias) e **2026-06-16→06-30** (11 dias). A info EXISTE (git + blocos SESSÃO no
  STATUS + notas datadas), mas o canal cronológico está furado. Reconstrução = era-authority (git).
- **STATUS.md — pilha de bridges fora de ordem de autoridade**: ~217 linhas de topo (25% do arquivo) são
  blocos RECONCILIAÇÃO/RETIFICAÇÃO empilhados por ordem de ESCRITA; o leitor vê o mais VELHO (2026-06-24)
  primeiro. **Decisão de design pendente do owner** (consolidar num bloco atual+histórico / reordenar /
  deixar).
- **`docs/article/`**: MORTO (0 arquivos; só `figuras/` vazia). Resíduo.
- **8 notas com marcador superada/subordinada** (`arquitetura-funil-camadas`, `dicas-limpeza-dead-code`,
  `dict-referencia-hipoteses`, `roadmap-hipoteses`, `tcf8-estrutura-plano`, `tcf8-vista-o-que-falta`,
  `v08-plano-etapas`, `welding-plan`): a maioria é VIVA-anotada (categoria b, bridged nesta sessão);
  `v08-plano-etapas` tem nome stale (ROADMAP já marca) + é referenciada por ROADMAP/STATUS → classificar.
- Não-verificado (2º nível, se pagar): `docs/archive/` (182 arq) + `docs/workbench/` (186 arq);
  `INDEX.md` auto-gerado com `Updated: ?` (rodar `scripts/index.py`?).

## Caminho-feliz (tiers — do óbvio/sem-colisão ao ambíguo/git-comparação)

### T1 — óbvio, zero-colisão ✅ FEITO 2026-07-09
- [x] **T1-a** Índice de tickets: 19 rows adicionadas em `tickets/README.md` como seção "Indexados
  retroativamente (backfill)" — geradas MECANICAMENTE do frontmatter (title+status) + data do último
  commit; tabela existente NÃO reordenada (só aditivo). Índice agora cobre 62/62.
- [x] **T1-b** `docs/article/`: confirmado MORTO — conteúdo real foi arquivado em `docs/archive/` no
  commit `8f33744` (T-DOC-1..6, reorg v0.5); links restantes só DENTRO de `_archive/` (históricos,
  intocados); a pasta era dir vazio NÃO-rastreado pelo git (resíduo local do move) → removida
  localmente, zero impacto no git.
- [x] **T1-c** `INDEX.md` regenerado via `scripts/index.py` (verificado com `--check` + diff inspecionado
  antes): remove entradas com paths QUEBRADOS (labs já movidos pra `old/welded/` — o script pula `old/`
  por design) + lista os labs novos da semana como candidatos a frontmatter. Artefato DERIVADO
  alcançando a realidade; versão antiga recuperável no git.

### T2 — julgamento leve / decisão pendente
- [ ] **T2-a** `STATUS.md` bridges: **aguarda decisão do owner** (3 opções levantadas). Sem isso, não mexer.
- [ ] **T2-b** `v08-plano-etapas.md` (nome stale + 0.7.2 absorvido no 0.8.0): anotar/renomear (git mv preserva
  history) — comparar referências (ROADMAP/STATUS/2 notas) antes; categoria (b) vs (c).

### T3 — ambíguo, exige comparação com git (CUIDADO — por último)
- [ ] **T3-a** Diário: reconstruir entradas retroativas dos gaps (05-22→06-11, 06-16→06-30) a partir de
  `git log` + blocos SESSÃO do STATUS + notas datadas da era. **Reconstruir da autoridade da época**, não
  retrofitar o entendimento de hoje. Incremental (um gap por vez). Valor: completude histórica (a info já
  existe em git — prioridade MENOR pro review 0.8, mas "barato agora, caro depois").
- [ ] **T3-b** Classificar as notas antigas restantes (`arquitetura-funil`, `welding-plan`, `dicas-limpeza`,
  etc.) nas 3 categorias via git-history: (a) viva / (b) recuperada / (c) obsoleta→arquivar. Comparar com o
  que MAP/STATUS/ROADMAP ainda referenciam. Arquivar (c) com tombstone; **nunca deletar**.

## Avaliação honesta (owner: "veja se a decisão de arrumar é boa")

- **T1 vale claramente** (barato, alto valor pro review 0.8 — legibilidade do estado ativo). Fazer.
- **T2-a** é a única que toca o princípio Strata a fundo → decisão do owner antes.
- **T3 vale, mas é prioridade MENOR pro 0.8** (a info existe no git; é completude/higiene, não bloqueio).
  Fazer incremental, com a maior cautela de colisão.
- **Não bloqueia o 0.8**: o `.8` está code-completo + docs-reconciliado; esta arrumação SERVE o review, não o gate.

## Critérios de aceite

Ticket de higiene (fecha por tier, não de uma vez):
- [ ] T1 (a/b/c) feito — passada mecânica, sem colisão.
- [ ] T2 destravado por decisão do owner (a) e executado (b) com git-comparação.
- [ ] T3 incremental, cada item cross-ref ao commit/era que o justifica; arquivar-não-deletar.
- [ ] Nada de conteúdo com decisão-de-época perdido (regra 3). Diário retroativo aponta os commits-fonte.
