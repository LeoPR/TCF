# 0032 — #TCF.8 vira o formato DEFAULT (multi-col); legado .6/.7 cortado; hex e escaping na família .8

**Status**: accepted (2026-07-09)
**Date**: 2026-07-09
**Deciders**: project owner
**Tags**: format, default, versioning, 0.8, legacy-cut, hex, escaping, hierarchy, self-describing

> **accepted 2026-07-09.** Torna `#TCF.8` o formato **default** de emissão (multi-col), **supersede** a regra
> "opt-in estrito SSE nature" do [ADR-0027](0027-nature-mark-header-self-describing.md), e **corta** o legado
> `#TCF.6`/`#TCF.7` de `src/tcf`. Consolida as decisões do owner de 2026-07-09 (após a revisão crítica
> pré-bump). Depende do [ADR-0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md) (aceito
> junto) pra rotular o pacote `0.8.0`.

## Context and Problem Statement

O `#TCF.8` foi introduzido opt-in (natures ADR-0027, discriminador ADR-0029), emitido **só** quando há
nature/drop_names — o argumento era **byte-neutralidade do default** (D1-D9/D17a intactos). O owner decidiu
**progredir**: `#TCF.8` vira o formato vivo; o `#TCF.7`/`#TCF.6` não têm mais função de produção — servem
só de **ponto de progresso/comparação** (pré-1.0, [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md)
git-as-compat). Manter três formatos vivos no código é redundância de versão que suja o `.8`.

## Decision Outcome

### 1. `#TCF.8` é o default de emissão (MULTI-COL)
Multi-col passa a emitir **`#TCF.8M`** (antes `#TCF.7 M`/`#TCF.6 M`). **Single-col NÃO muda**: o órfão
(0 bytes de header) continua o default single-col — congelado no 1.0 ([ADR-0030](0030-freeze-single-col-body-at-1.0.md)),
âncora de D1-D9=1523B e do gate real-world=89616B. O `.8-default` é sobre o **default multi-col + a família**,
não sobre pôr header no single-col (o [ADR-0029](0029-version-format-identification-semi-implicit.md) camada 1
segue intacto; a pergunta 0029:96-97 "stamp default ao salvar em arquivo" fica FORA deste ADR).

### 2. Escopo da família `.8`: single-col + multi-col + hierarquia (slot)
O discriminador ([ADR-0031](0031-hierarchical-discriminator-H.md)) reserva `H` = multi-col hierárquico. O
`.8` **reconhece** `#TCF.8H` como modo **conhecido-mas-não-implementado** (fail-loud, §6) — o **codec**
hierárquico vai pro **lab** (research-track, EXP-015) pra experimentar como implementar com segurança e
weldar depois (candidato `.9`). Opção **A** (slot reservado + fail-loud), não B (codec já weldado).

### 3. Hex = exclusivo da família `.8`; `#TCF.7` fica decimal (não misturar)
O weld [T-FMT-HEADER-BASE-HEX](../../tickets/T-FMT-HEADER-BASE-HEX.md) tinha aplicado hex in-place no `#TCF.7`
— **revertido**: hex é feature da família `.8`. Como `.8` vira o default (e `.7` é cortado do emit), o
default emite hex de qualquer forma; blobs `#TCF.7` publicados (0.7.1, decimais) deixam de existir no código
vivo (§4). Resolve o "dois wire-formats sob o mesmo magic".

### 4. Legado `#TCF.6`/`#TCF.7`: CORTADO de `src/tcf`
Emissão E decode de `.6`/`.7` **saem** do código vivo (`encoder`/`decoder`/`multi.core`/`view`). O código
fica **.8-only** — mais limpo, sem resolver redundância de versão. Comparação histórica com o `.8`:
`git checkout` da era, OU **cópias do legado numa pasta gitignored** (`legacy-snapshots/`, fora do git) só
pra rodar comparativos. **Sem compromisso de sobrevivência**; a versão é ponto de progresso, não produção
(ADR-0024). Consequência: blobs `.6`/`.7` no mundo não decodam mais no código novo — **aceitável pré-1.0**.

### 5. Nomes com separador (`:`/`,`/`=`/`#`-inicial/`{}[]`): ESCAPING, não rejeição
O name-guard que **rejeita** dá lugar a **escaping** (técnicas CSV consagradas) —
[T-FMT-NAME-ESCAPING](../../tickets/T-FMT-NAME-ESCAPING.md). Interim: backslash (a convenção `\` que o corpo
já usa); smart (quoting implícito) no ticket. Desbloqueia o `:` sob `.8`-default.

### 6. Fail-loud no discriminador desconhecido/reservado
Hoje um char desconhecido após `#TCF.8` (incl. `#TCF.8H`) **degrada pra decode órfão silencioso** com dados
corrompidos. Passa a **erguer erro** citando o char (ex.: "`H` reservado, não implementado" — ADR-0031).
Temporário pro `H` até o codec do lab landar.

### 7. Versionamento: pacote `0.8.0`; lazy ABSORVIDO; ADR-0028 aceito
Por [ADR-0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md) regra 1 (mudança de formato
→ minor), o pacote vai a **`0.8.0`**. O ciclo `0.7.2` (lazy+poda) é **absorvido** no `0.8.0` — **sem release
intermediário** (PyPI segura em 0.7.1; publica só quando **completo+estável**). O ADR-0028 é **aceito** junto
(reconciliando "#TCF.8 shipou opt-in sob 0.7.1": era scaffold byte-neutro; agora vira default sob 0.8.0).

## Consequences

**Positivas**: código `.8-only` limpo; um formato vivo; hex+self-describing por default; fim do "dois formatos
sob #TCF.7"; fail-loud fecha a corrupção silenciosa.

**Negativas / custos** (aceitos pré-1.0): blobs `.6`/`.7` no mundo não decodam (git/cópias pra comparar);
D17a re-medido+re-pinado (4ª vez — split embutido flipa junto, MEDIR não calcular); onda de docs/spec/pontes;
`.8` como default invalida retroativamente o argumento "byte-neutro default-off" do scaffold (por isso este ADR).

## Escopo NEGATIVO (o que este ADR NÃO faz)
- Single-col órfão e freeze 1.0 (ADR-0030) **intocados**; D1-D9 e real-world **não movem**.
- Codec hierárquico **não weldado** (vai pro lab; só o slot+fail-loud entram).
- Não decide "stamp default ao salvar em arquivo" (0029:96-97 segue aberto).
- Não publica no PyPI (release = go do owner, quando completo+estável).

## Relation to other ADRs
- **Supersede** ADR-0027 (regra "opt-in estrito SSE nature" → `.8` é default; o Cons anti-magic-permanente do
  0027 é revertido por esta decisão de progresso).
- **Refina** ADR-0029 (o default multi-col agora é a família `.8`; camada 1 single-col órfão intacta) e é
  **habilitado por** ADR-0031 (`H` reservado).
- **Depende de** ADR-0028 (aceito junto; rótulo 0.8.0). Preserva ADR-0030 (freeze single-col) e ADR-0024
  (git-as-compat, base do corte de legado).
- Implementado com [T-FMT-NAME-ESCAPING](../../tickets/T-FMT-NAME-ESCAPING.md) (§5) e o ajuste hex-.8-only de
  [T-FMT-HEADER-BASE-HEX](../../tickets/T-FMT-HEADER-BASE-HEX.md) (§3).
