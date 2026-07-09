# 0031 — Discriminador `H`: multi-col hierárquico (especialização de `M`)

**Status**: accepted (2026-07-09)
**Date**: 2026-07-09
**Deciders**: project owner
**Tags**: format, header, discriminator, hierarchy, self-describing, dispatch, 0.8

> **accepted 2026-07-09.** Estende o discriminador de 1 char do [ADR-0029](0029-version-format-identification-semi-implicit.md)
> com `H` = **multi-col COM hierarquia**, uma especialização de `M`. Formaliza o char que o
> protótipo `#TCF.8H` (EXP-015, research-track) já usava ad-hoc, fechando a colisão latente
> registrada no [char-registry](../../experiments/lab/dirty/notas/tcf8-header-char-registry.md).
> **Reserva o char + a semântica de dispatch; NÃO welda o codec hierárquico** (isso é gated,
> ticket próprio). Consome as decisões de [T-FMT-TCF8H-HEADER](../../tickets/T-FMT-TCF8H-HEADER.md).

## Context and Problem Statement

O ADR-0029 definiu o discriminador de 1 char logo após `#TCF.8` (`M`=multi, ` `=single+spec,
`\n`=version-stamp), com slots livres "reserváveis". O estudo hierárquico (EXP-015, peças P1-P9)
produziu um codec CSV↔JSON aninhado que emite `#TCF.8H …` — mas o `H` foi pego **ad-hoc**, sem
entrar no discriminador do 0029. O char-registry (2026-07-08) marcou isso como **colisão latente**:
sem reserva formal, um fluxo futuro poderia pegar `H` pra outra coisa.

A pergunta: `H` deve virar char de discriminador **formal** do `.8`, e com que semântica?

## Decision Outcome — `H` = multi-col hierárquico, especialização de `M`

O caractere no índice 6 (logo após `#TCF.8`) passa a ter **cinco** valores, numa progressão de
estrutura (do mais simples ao mais rico):

| após `#TCF.8` | tipo | header | fonte |
|---|---|---|---|
| *(nada, body direto)* | single-col órfão (DEFAULT, 0 B) | — | ADR-0029 camada 1 |
| ` ` (espaço) | single-col + spec | `#TCF.8 [nome]:spec` | ADR-0029 |
| `\n` | single-col version-stamp | `#TCF.8\n<body>` | ADR-0029 |
| `M` | **multi-col plano** | `#TCF.8M<meta>` | ADR-0029 |
| `H` | **multi-col hierárquico** (M + árvore) | `#TCF.8H<meta-árvore>` | **este ADR** |

**A lógica (owner)**: espaço = single · `M` = multi · **`H` = `M` com hierarquia**. `H` é uma
**especialização de `M`**: ambos são multi-col self-describing; `H` adiciona a topologia de
árvore (contenção pai→filho em `{}`/`[]`) ao meta. A leitura do próprio meta já denunciaria a
hierarquia (colchetes), mas o char no índice 6 **formaliza** e — o motivo prático — dá ao decode
um **dispatch O(1)**: reconhece "hierárquico" e roteia pro codec-árvore ANTES de inspecionar o
meta, sem sniff.

### `H` NÃO leva espaço (herda a regra de `M`)

Como `M`, o `H` **cola o meta** direto: `#TCF.8H<meta>`, sem espaço. O espaço é o discriminador
do **single+spec** (ADR-0029) — usá-lo no `H` colidiria com a própria lógica "espaço = single" e
gastaria 1 byte. **Refinamento vs o protótipo**: o EXP-015 emitiu `#TCF.8H <meta>` (com espaço,
escolha de legibilidade do protótipo research-track); ao weldar, o codec DEVE alinhar pra
sem-espaço (M-family). Byte-economia + consistência.

### Escopo desta decisão (o que ela É e o que NÃO é)

- **É**: reserva do char `H` no discriminador + a semântica "multi-col hierárquico, especialização
  de M" + a regra sem-espaço. Ato dispositivo de FORMATO.
- **NÃO é**: welding do codec hierárquico em `src/tcf`. A gramática do meta-árvore (colchetes,
  omit-closes, última-sem-size, `:tipo`) segue **research-track** (EXP-015 + T-FMT-TCF8H-HEADER);
  seu welding é **gated** (gate real-world `test_real_world_snapshots.py` + aprovação `src/tcf` +
  re-pin de baselines, ADR-0024) e vive num ticket próprio. `src/tcf` **não muda** com este ADR.
- Até weldar, o decoder de produção NÃO reconhece `H` (é um char reservado, não implementado); um
  blob `#TCF.8H…` só é decodável pelo protótipo EXP-015.

## Decision Drivers

- **Fechar a colisão latente** (char-registry): reservar `H` impede que outro fluxo o tome.
- **Dispatch O(1)** no decode: roteamento por char, sem inspecionar o meta (o próprio motivo do
  discriminador de 1 char do 0029).
- **Consistência do modelo**: `H` cabe na progressão single→multi→multi-hierárquico sem inventar
  eixo novo; é a especialização natural de `M`.
- **Byte-economia**: sem-espaço (herda de `M`) — 1 B a menos que o protótipo.

## Considered Options

- **`H` = especialização de `M`, sem-espaço** (esta). Fecha a colisão, dispatch O(1), consistente.
- **Deixar `H` como codec research-track não-reservado**: o protótipo continua usando `H` mas o
  formato não o reserva. Rejeitada — mantém a colisão latente aberta (algum fluxo futuro pega `H`).
- **Hierarquia como flag DENTRO do meta de `M`** (ex.: `#TCF.8M` + marca de árvore no meta): não
  precisa de char novo, mas perde o dispatch O(1) (decode teria de parsear o meta pra saber que é
  árvore) e mistura dois níveis. Rejeitada.
- **`H` COM espaço** (como o protótipo EXP-015): rejeitada — colide com a lógica "espaço = single"
  e gasta 1 byte.

## Consequences

**Positivas**:
- Discriminador do `.8` fechado e sem colisão; `H` reservado com semântica clara.
- Decode roteia hierarquia em O(1) (char no índice 6), sem sniff do meta.
- Modelo de header coeso: órfão / espaço / `\n` / `M` / `H` — uma progressão só.

**Negativas / custos**:
- O protótipo EXP-015 (com espaço) fica **desalinhado** com a forma canônica (sem-espaço) —
  item de alinhamento no welding (não afeta a decisão, é higiene de código research).
- `H` reservado mas **não implementado** em `src/tcf` até o weld gated — um blob `#TCF.8H` só
  decoda no protótipo por ora (documentado; não é regressão, é feature futura).

## Relation to other ADRs

- **Estende** [ADR-0029](0029-version-format-identification-semi-implicit.md) (discriminador de 1
  char) — adiciona o 5º valor `H` à tabela de realização.
- Depende de [ADR-0030](0030-freeze-single-col-body-at-1.0.md) só indiretamente (multi/`H` não são
  o órfão default congelado).
- Consome as decisões de estrutura do header em [T-FMT-TCF8H-HEADER](../../tickets/T-FMT-TCF8H-HEADER.md)
  (omit-closes, última-sem-size, colchete) — que permanecem research-track até o weld.
