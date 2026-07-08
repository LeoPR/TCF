---
title: T-FMT-OMIT-OR-DECLARE — Contrato de omissão (deduzível / convenção-default / declaração-obrigatória) — AVALIAR pré-1.0
status: open
priority: P2
created: 2026-07-07
updated: 2026-07-07
gate: pre-1.0
blocked-by: []
related:
  - tickets/T-OPT-INFERENCE.md
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - experiments/lab/dirty/2026-07-01-header-minimal/result.md
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
---

# T-FMT-OMIT-OR-DECLARE — o que pode ser omitido, e o que vira declaração obrigatória

**[probatório→decisão pré-1.0]** Princípio do owner (2026-07-07, ilustrado por hex + magic): toda informação
que o formato normalmente carrega pode ser **omitida pra economizar bytes** — mas se o que sobra **não a
deduz**, ela vira **declaração obrigatória** (param no encode E no decode). A classe (codec) tem de
**perceber e obrigar um ou outro**. **Apenas anotado** — avaliar antes de fechar o 1.0.

## A distinção que torna isto decidível (revisão crítica)

O owner agrupou dois mecanismos que **diferem em segurança** — separá-los é o miolo:

- **Convenção-default** (ex.: hex-base, tipo=string): o marcador é omitido, o decoder aplica uma **convenção
  fixa** → **continua auto-descritivo**, **sem param**. Só o **desvio** da convenção (ex.: decimal) precisa
  de marcador/param. **Seguro** — pode ser default pelo ganho (o "hex default" do owner).
- **Supressão-sem-convenção** (ex.: magic `#TCF.N`): **não há default seguro** — sem magic o decoder não
  distingue "não-é-TCF" de "TCF-com-magic-suprimido". Suprimir **exige** declaração externa (encode+decode),
  **não-auto-descritivo** por construção.

> `hex sem declarar` do owner: hex-**default** (convenção) NÃO precisa declarar; declarar é pra o **desvio**
> (decimal) ou pra supressão-sem-convenção. Não confundir os dois.

## As 4 categorias (o mapa a fechar pré-1.0)

| categoria | exemplo | auto-descritivo | precisa declarar |
|---|---|---|---|
| **sempre presente** | bodies, arestas de contenção | — | — |
| **deduzível** | M, cardinalidade, rows, kind (checklist C2) | sim | não |
| **convenção-default** | hex-base, tipo=string, última-sem-size | **sim** (convenção) | só o **desvio** |
| **supressível-c/-declaração** | magic/versão, header-derivável (O-FMT-14) | **não** | **sim** (encode+decode) |

## Invariantes de segurança (o "obrigar um ou outro")

1. **Fail-loud, nunca adivinhar**: pra a categoria 4, marcador ausente + sem declaração → o codec **ergue
   erro**, não chuta. Marcador suprimido + declaração errada/ausente = **mis-decode SILENCIOSO** (`"10"`→
   decimal quando era hex; RT quebra sem avisar). Invariante pré-1.0: **nenhum mis-decode silencioso sob
   supressão**. Testável: decode sem o marcador e sem o param DEVE falhar explícito.
2. **Proveniência da declaração**: param externo (ex.: versão sob magic suprimido) tem de ser **gravado**
   em algum lugar — senão o "git reproduz versões antigas" (ADR-0024) quebra (não se reproduz um decode cujo
   param out-of-band se perdeu). A declaração precisa de um **home de proveniência**.
3. **Hierarquia de risco**: suprimir o **magic** (perde "é TCF? qual versão?" + a âncora do versionamento)
   é **categoricamente mais arriscado** que um marcador intra-formato (hex). Provável decisão: adotar
   **convenção-defaults** livremente (hex, tipo-str); tratar **supressão-de-magic** como opt-in de alto
   risco (flag `--no-magic`/`--minimal`), sempre com declaração + fail-loud + proveniência.

## Exemplo do owner (magic suprimido) — didático mas real

`#TCF.8` gasta ~6 bytes; num payload minúsculo é fração grande (diretriz byte-level,
[project_byte_level_compression_focus]). Suprimir: `encode(..., magic=False)` exige `decode(..., version=8)`
declarado. Se o decode recebe bytes sem `#TCF<versão>` → ambíguo (não-TCF OU versão-a-declarar) → **erro
pedindo a versão**. É o caso extremo da categoria 4; é o O-FMT-14 ("header derivável por contrato") levado ao
limite (suprimir até o magic).

## Onde isto já aparece (unifica registros existentes)

- **hex-default** ([T-OPT-INFERENCE](T-OPT-INFERENCE.md) item 1) = convenção-default (categoria 3).
- **O-FMT-14 / header-derivável** (checklist C4, [header-minimal](../experiments/lab/dirty/2026-07-01-header-minimal/result.md))
  = supressível-c/-declaração (categoria 4).
- **eixo autoridade** (mandatório/spec-natural/deduzido, `tipos-como-specs.md`) = a mesma distinção vista
  pelo lado da entrada.
- **versionamento** (ADR-0024, git-as-compat) = a proveniência que a categoria 4 exige.

## Critério de aceite (a fechar pré-1.0)

- [ ] Classificar cada campo omitível do formato nas 4 categorias (deduzível / convenção-default / supressível).
- [ ] Decidir **quais marcadores** são supressíveis e sob qual flag (provável: convenção-defaults sim;
      supressão-de-magic opt-in alto-risco).
- [ ] Especificar o **fail-loud** (decode sem marcador+sem param → erro), com teste.
- [ ] Definir o **home de proveniência** das declarações out-of-band (pra não quebrar git-as-compat).
- [ ] Confirmar que nenhuma convenção-default cria mis-decode silencioso (ex.: hex-default + rede de dedução
      dec/hex do T-OPT-INFERENCE fecha sem ambiguidade).
