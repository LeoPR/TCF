---
title: How to — Fluxo de hipotese ate' producao (TCF)
type: how-to
status: active
tags: [methodology, workflow, lifecycle, dirty, clean, canonical, ADR]
created: 2026-05-18
updated: 2026-05-18
---

# Fluxo de hipotese ate' producao no TCF

Como uma ideia caminha de **rascunho informal** ate' **codigo canonical
em `src/tcf/`**. Cada estagio tem **proposito, artefatos esperados,
gates de validacao, e onde fica registrado**.

> **Por que este doc**: evitar que bugs/decisoes/experimentos fiquem
> orfaos. Cada coisa tem ESTADO conhecido (qual estagio) e PROXIMO
> estagio claro (criterio de avanco).

## Estagios

```
1. Ideia/Observacao
       v
2. Hipotese registrada (roadmap-hipoteses.md)
       v
3. Sub-experimento dirty (lab/dirty/YYYY-MM-DD-*/NN-name/)
       v  (confirmada-empirica)
4. Consolidacao em prototype clean (lab/clean/EXP-NNN-*/)
       v  (validada conceitualmente)
5. ADR documentando decisao (docs/adr/NNNN-*.md)
       v  (aprovado)
6. Integracao em src/tcf canonical
       v  (welded, byte-canonical OK ou re-baseline justificado)
7. **PRODUCAO** (API publica from tcf import encode, decode)
```

## Estagio 1 — Ideia/Observacao

**Trigger**: insight em conversa, achado empirico inesperado,
critica de design, bug observado.

**Onde fica**: diario do dia
(`experiments/lab/dirty/notas/diario/YYYY-MM-DD.md`).

**O que registrar**: o que foi observado, em qual contexto, qual a
intuicao inicial. NAO precisa formalizar ainda.

**Gate pra avancar**: a ideia se mostra **relevante** (apareceu mais
de uma vez OU bloqueia alguma direcao).

## Estagio 2 — Hipotese registrada

**Trigger**: ideia merece teste sistematico.

**Onde fica**: `experiments/lab/dirty/notas/roadmap-hipoteses.md`,
com ID (`H-DA-NN`, `H-RW-NN`, `H-ED-NN`, `H-FIX-NN`).

**O que registrar**:
- ID + descricao 1 linha
- Status: `aberta`
- Onde sera testada (planejado)
- Ressalvas conceituais

**Gate pra avancar**: planejamento existe pra sub-exp; tempo/escopo
viavel.

## Estagio 3 — Sub-experimento dirty

**Trigger**: hipotese ativa.

**Onde fica**: `experiments/lab/dirty/YYYY-MM-DD-nome-do-lab/NN-descricao/`

**Estrutura minima**:
- `README.md` com YAML frontmatter (status, tags, type, hypothesis)
- `run.py` (executavel)
- `result.md` com decisao final
- `outputs/<datasets>/` com artefatos inspecionaveis
- (opcional) `audit.py`, `*.py` modulos

**Gates de validacao**:
- RT byte-canonical em datasets aplicaveis
- Bytes vs baseline (qualitativo)
- Observacoes que confirmam OU refutam hipotese

**Status no fim**:
- `confirmada-empirica` (datasets testados; nao implica generalizacao)
- `refutada` / `refutada-parcial`
- `absorvida` em outra hipotese

**Atualizar roadmap-hipoteses.md** com status novo + ref ao result.md.

**Gate pra avancar**: confirmada-empirica + valor mensuravel
(ganho >= threshold OU bug fixavel).

## Estagio 4 — Prototype clean

**Trigger**: sub-exps dirty mostram solucao funcional + integravel.

**Onde fica**: `experiments/lab/clean/EXP-NNN-nome/`

**Estrutura minima**:
- `README.md` com YAML frontmatter (status, predecessor, welds)
- `run.py` valida em datasets representativos
- `report.md` (gerado por run.py)
- Modulos `.py` cleaned-up (welded dos dirty)
- `outputs/` artefatos

**Gates de validacao**:
- Reproduz dirty lab numbers (sanity check)
- RT byte-canonical mantido
- Performance e escala medidos
- Limites conceituais documentados

**Caracteristicas**:
- Codigo limpo (sem prints debug, comentarios verbose)
- Single-pass mantido (vertice triplice)
- API publica clara (`encode`, `decode`)
- `src/tcf` intocado (importa, nao modifica)

**Gate pra avancar**: pelo menos 2 datasets reais OU 5+ sinteticos
diversos validados.

## Estagio 5 — ADR

**Trigger**: prototype clean estavel; integracao em canonical viavel.

**Onde fica**: `docs/adr/NNNN-imperative-phrase.md`

**Template** (MADR):
- Status (proposed → accepted)
- Date, Deciders, Tags
- Context and Problem Statement
- Considered Options (3+ alternatives)
- Decision Outcome (chosen option + rationale)
- Pros and Cons of the Options
- Validacao apos fix (se aplicavel)
- Justificativa pra tocar src/tcf canonical
- Riscos residuais
- Cross-references

**Gate pra avancar**: ADR aceito + nenhum risco residual bloqueante.

## Estagio 6 — Integracao em src/tcf canonical

**Trigger**: ADR aceito + welding-plan pronto.

**Onde fica**: `src/tcf/` (intocado sem ADR aceito).

**Processo**:
1. Backup git (commit limpo antes)
2. Aplicar mudanca minima (so' o necessario)
3. Comentar mudanca: `# Fix YYYY-MM-DD: <descricao> (ver ADR-NNNN)`
4. **Validacao multi-camada** (TODAS devem passar):
   - EXP-007 (D1-D9 byte-canonical vs M9)
   - EXP-010 (delta-aware single-col, 20 datasets)
   - EXP-011 / EXP-012 / EXP-013 (multi-col real-world)
   - Outros experimentos clean ativos
5. Se quebrar M9 baseline: **STOP**. Re-analise:
   - Quebra e' aceitavel pra ganho de robustez?
   - **Re-baseline e' OPCAO**: registrar novo baseline no ADR + EXP-007.
   - Nao re-baselinear sem decisao explicita do user.

**Gate pra avancar**: validacao multi-camada OK OU re-baseline
justificado e aprovado.

## Estagio 7 — Producao

**Trigger**: src/tcf modificado + validado + commited.

**O que faz parte**:
- API publica: `from tcf import encode, decode`
- Documentacao canonical em `docs/algorithms/`
- Welding documentado em `experiments/lab/dirty/notas/welding-plan.md`

**Manutencao continua**:
- Auditoria periodica
  (`docs/how-to/audit-memorias-e-documentacao.md`)
- ADRs novos quando design evolui
- Stale markers em entradas mutaveis

## Distincoes importantes

### Pre/post complementar vs integracao algoritmica

- **Pre/post wrapper**: aplica transformacao ANTES/DEPOIS do
  algoritmo principal. Ex: pre-process de strings, post-process
  de bytes. **NAO conta como fix do algoritmo** — e' band-aid.
- **Integracao algoritmica**: muda o algoritmo IN-PLACE pra
  resolver causa raiz. **E' o fix real**. Requer ADR + validacao
  multi-camada.

Wrappers sao OK em prototype clean (validacao). NAO sao OK em
src/tcf canonical — la' so' integracao.

### Surface fix vs root cause fix

- **Surface fix**: workaround que esconde o bug (ex: substitui
  `""` por `"?"` antes de encode). **NAO ACEITAVEL** em
  canonical.
- **Root cause fix**: corrige onde o bug nasce. ADR documenta
  por que. Aplica em canonical apos validacao.

### M9 byte-canonical: invariante vs reanalisavel

- M9 (1615 bytes em D1-D9) e' o **baseline de regressao** atual.
- **Invariante padrao**: nao mudar sem decisao explicita.
- **Reanalisavel**: pode ser re-baselineado SE:
  - Ganho de robustez/correcao justifica
  - Decisao explicita do user
  - Novo baseline registrado em ADR + EXP-007
  - Justificativa do desvio numerico explicada

## Naming conventions ao longo do fluxo

| Estagio | Naming |
|---|---|
| Hipoteses delta | `H-DA-NN` |
| Hipoteses real-world | `H-RW-NN` |
| Hipoteses escape-deduction | `H-ED-NN` |
| Hipoteses fix de bug | `H-FIX-NN` |
| Observacoes empiricas | `O-NN` |
| Otimizacoes formato | `O-FMT-NN` |
| ADRs | `NNNN-imperative-phrase.md` |
| Sub-exp dirty | `NN-description/` dentro do lab |
| EXP clean | `EXP-NNN-name/` |
| Pacote tematico | `Pacote N — Nome` |

## Como invocar este fluxo

Em conversas/sessoes:
- "Vou aplicar o fluxo de hipotese ate' producao" → consultar este doc
- "Estamos em qual estagio?" → checar `roadmap-hipoteses.md` + diario
- "Precisa de ADR?" → estagio 5 do fluxo

Em codigo (comentarios):
- `# Implementa H-DA-07 (sub-exp 04, ADR-0003)`
- `# Fix bug empty-string (ver ADR-0006)`

## Antipatterns a evitar

- **Pular estagios**: ideia → src/tcf direto, sem dirty/clean/ADR
- **Surface fix em canonical**: workaround em src/tcf
- **Sem ADR pra mudanca grande**: decisao some no diario
- **Hipotese sem id**: nao da' pra rastrear
- **Estagio sem gate**: avanca sem validar
- **Diario sem entries**: perde linha do tempo

## See also

- [AGENTS.md](../../AGENTS.md) — guia canonico
- [MAP.md](../../MAP.md) — wayfinding
- [vocabulary.md](../vocabulary.md) — termos
- [audit-memorias-e-documentacao.md](audit-memorias-e-documentacao.md) — manutencao
- [ADR-0005](../adr/0005-discoverability-claude-md-root.md) — discoverability
- [welding-plan.md](../../experiments/lab/dirty/notas/welding-plan.md) — exemplo de processo de welding
