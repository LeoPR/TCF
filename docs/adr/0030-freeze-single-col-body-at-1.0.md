# 0030 — Congelar o formato do body single-col no 1.0 (contrato do órfão default)

**Status**: accepted (política; efeito no 1.0)
**Date**: 2026-06-25
**Deciders**: project owner
**Tags**: format, versioning, 1.0, freeze, single-col, identification

> Decide a POLÍTICA de congelar o formato do body single-col quando o projeto
> atingir 1.0. É o **linchpin** do órfão default de [ADR-0029](0029-version-format-identification-semi-implicit.md).
> Efeito no 1.0 — **pré-1.0 o formato ainda pode ser refinado** (ADR-0024).

## Context and Problem Statement

[ADR-0029](0029-version-format-identification-semi-implicit.md) (identificação semi-implícita)
estabelece o **órfão default**: single-col simples = **body puro, sem shebang** (camada 1,
0 bytes de header). Isso é o que dá byte-economia ao caso mais comum. **Mas**: um blob sem
marcador só é decodável pra sempre se o formato do body for um **contrato imutável**. Senão,
um `.tcf` órfão antigo fica ambíguo quando o formato do body evoluir. Logo, ADR-0029 nomeou
o **congelamento do body single-col no 1.0 como pré-requisito** ("linchpin"). Este ADR
formaliza essa decisão.

## Decision

**No 1.0, o formato do body single-col vira um contrato IMUTÁVEL.** Um blob órfão
(body-only, sem shebang) é decodável pra sempre como "TCF 1.x single-col, formato congelado".

### O que é congelado
O **body single-col M10 canonical**: a gramática de saída do HCC (marcadores `^ * , ~ .. \`),
o pipeline OBAT+HCC+seq-RLE, e a convenção (sem brackets, LF only, UTF-8). Evidência pinada:
`tests/test_regression_v1_baseline.py` (D1-D9=1523B, D17a=303B) + `tests/test_real_world_snapshots.py`
(89616B). Ao 1.0, esses pins viram o contrato.

### Regra de identificação (junto com ADR-0029)
- **Major version = EXTERNO**: você sabe que decodifica TCF 1.x (extensão/lib/contexto).
- Um body single-col órfão é "1.x congelado". Se um 2.0 futuro mudar o body, blobs 1.x
  órfãos dependem de a lib saber que são 1.x (regra major-externo).

### A disciplina que isso impõe (consequência desejada)
Toda otimização futura do body (EI, H-INTRA, etc.) passa a ser, obrigatoriamente, um
**desvio OPT-IN MARCADO** (família #TCF.8) — nunca uma mutação silenciosa da base. Isso É a
estratégia semi-implícita de ADR-0029: mudança = desvio explícito e versionado.

### Janela pré-1.0
A política tem efeito **no 1.0**. **Pré-1.0** (estado atual, pacote 0.7.x) o formato do body
AINDA pode ser refinado — [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md) (git-as-compat:
minors são marcadores de dev, baselines re-pináveis). Ou seja: refinar a base ANTES de
congelar é permitido; congelar é o ato do 1.0.

## Decision Drivers
- Órfão default (ADR-0029) só é seguro se o body for contrato estável.
- O body M10 é maduro (validado D1-D9 + real-world gated) — bom candidato a congelar.
- Byte-economia do órfão > custo de travar a evolução da base (que cavalga em desvios marcados).

## Consequences
**Positivas**:
- Órfão default decodável pra sempre (byte-economia do caso comum, sem ambiguidade).
- Disciplina: otimizações viram desvios opt-in marcados (#TCF.8), não mutações silenciosas.
- Estende a filosofia de freeze de [ADR-0017](0017-format-spec-v1-frozen.md) (#TCF.6) ao single-col.

**Negativas / custo**:
- Evolução da BASE do body single-col pós-1.0 exige **major bump** (2.0) OU um desvio marcado.
  É o trade-off do contrato de estabilidade (aceito).
- Órfão exige conhecimento externo de "isto é TCF 1.x" (extensão/lib) — coberto pela regra
  major-externo.

## Alternatives considered
- **Não congelar / marcador de versão em todo single-col**: quebraria a byte-economia do
  órfão (header em todo blob, D1-D9 muda). Rejeitado (ADR-0029 já decidiu o órfão default).
- **Congelar agora (pré-1.0)**: tiraria a janela de refino. Rejeitado — congelar no 1.0
  preserva a flexibilidade pré-1.0 (ADR-0024).

## Relation to other ADRs
- [ADR-0029](0029-version-format-identification-semi-implicit.md) (semi-implícito): este ADR
  É o linchpin que ADR-0029 nomeou. Sem ele, o órfão default não fecha.
- [ADR-0017](0017-format-spec-v1-frozen.md) (#TCF.6 frozen): mesma filosofia de freeze,
  aplicada ao single-col body.
- [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md): formaliza major-externo + a janela
  pré-1.0 (re-pinável até o 1.0).
- [ADR-0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md): o 1.0 é o
  marco onde o eixo FORMATO congela a base single-col.
