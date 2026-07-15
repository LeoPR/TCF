# 0033 — Weld do codec hierárquico `#TCF.8H` no core (L2/L3 aditivo sobre L1 reusado)

**Status**: welded (2026-07-14)
**Date**: 2026-07-14
**Deciders**: project owner
**Tags**: format, hierarchy, weld, codec, 3-layers, capability-gate, 0.8

> **welded 2026-07-14.** Promove o codec hierárquico de protótipo (research-track, EXP-015) para
> `src/tcf`, fechando o gate que o [ADR-0031](0031-hierarchical-discriminator-H.md) deixou aberto
> ("reserva o char + a semântica de dispatch; NÃO welda o codec"). O weld é **aditivo**: um módulo
> novo `src/tcf/hierarchical.py` (camadas L2/L3) que é **cliente** do compressor de coluna (L1)
> existente, sem alterá-lo. Executa a decisão de reescopo `.8 = feature-complete "1.0"`
> ([T-REL-08-CLOSEOUT](../../tickets/T-REL-08-CLOSEOUT.md)); ticket dono
> [T-CODE-TCF8H-WELD](../../tickets/T-CODE-TCF8H-WELD.md).

## Context and Problem Statement

O ADR-0031 reservou o char `H` no discriminador do `#TCF.8` e definiu sua semântica de dispatch,
mas **não weldou o codec** — a gramática do meta-árvore seguia research-track (EXP-015 +
T-FMT-TCF8H-HEADER) e o welding ficou **gated** (aprovação `src/tcf` + não-regressão real-world).
Com o reescopo do owner (`.8` = tudo que funciona), a hierarquia entra no `.8` como a expansão de
**capacidade** do 1.0 — o dado aninhado que a tabela plana não representa. Faltava o ato dispositivo
que promove o codec e registra sob que arquitetura e que gate.

A pergunta: como weldar o codec hierárquico **sem risco** para o núcleo plano já validado (D1-D9,
real-world), e com que fronteira de escopo?

## Decision Outcome — weld aditivo em 3 camadas (L1 intocado)

O insight do owner (2026-07-14) é que o TCF se separa em **três camadas** e o weld deve respeitá-las:

- **L1 — compressor de coluna**: recebe uma lista de strings, devolve um corpo. É o mesmo para
  single / multi / hierarquia. É o `tcf.encode`/`decode` de coluna que **já existe** e **não muda**.
- **L2 — relacionamento entre colunas**: a topologia da árvore (contenção pai→filho) vive no
  **header**; só a descrição no header já reconstrói o dataset, independente de como as colunas
  foram comprimidas. É o análogo do cross-dict — um mecanismo para as colunas "conversarem".
- **L3 — otimização pelo relacionamento**: deduções que economizam bytes (última-folha-sem-size,
  omit-closes). Opcional: tirar L3 e o dataset ainda reconstrói (só maior).

**Realização**: um módulo novo `src/tcf/hierarchical.py` implementa L2/L3 como **cliente** de L1
(`encode(coluna)` / `decode(body)`), via **shredding** — a árvore é fatiada em blocos de colunas
(raiz + um bloco por array), ligados por `#count` explícito. `decoder.py` troca o fail-loud do char
`H` por rota real (dispatch O(1)); `__init__.py` exporta `encode_hierarchical`; `decode()` auto-roteia
pelo magic. `encode` plano (single/multi) e o corpo órfão permanecem **byte-idênticos**.

### Wire (alinhado ao ADR-0031)

`#TCF.8H<meta>\n<colunas>` — **sem-espaço** (herda de `M`; refina o protótipo EXP-015 que usava
espaço). Gramática do meta: `nome:size` (escalar) · `nome{...}` (objeto 1:1) · `nome#:csize[...]`
(array de objetos, `csize` = tamanho da coluna de count) · `nome#:csize[]:asize` (array de escalares).
Sizes em bytes; nomes com separador escapados (herda T-FMT-NAME-ESCAPING). `HierarchicalError` para
entrada fora de contrato (fail-loud).

### Escopo — o que o weld COBRE e o que é fail-loud (fronteira registrada)

- **Cobre** (classe coberta): raiz = lista de objetos com **schema uniforme** por nível; escalares
  string; objetos `{}` (1:1); arrays `[]` de objetos ou escalares (1:N) com `#count`; arrays vazios;
  múltiplos arrays irmãos; arrays aninhados. Isto é a superfície dos **clássicos de transmissão**
  (cadastro, pedido aninhado, telemetria).
- **Fail-loud / próximos incrementos** (NÃO neste weld): objetos **ragged** (chave faltando → máscara
  de presença / def-level); **tipos** e `null` (tudo string; camada ortogonal — deixado pro FIM por
  decisão do owner); **N raízes**; **N:N/snowflake** (FK — super-hierarquia, H-HIER-MULTITABELA-01).

### Multiplicidade EXPLÍCITA (`#count`) como default

O weld grava a multiplicidade **explicitamente** (coluna `#count` por array), não deduzida do run do
pai. Isso dá independência de bloco (paralelismo, estrutura legível sem materializar o dado). A forma
deduzida (menos bytes em registro estreito) é uma **otimização de L3** (bloco de parâmetros:
latência/memória/velocidade/compressão), **hipótese aberta deixada pro fim** — não decidida aqui.

## Decision Drivers

- **Baixo risco por construção**: L1 intocado ⇒ o flat fica byte-idêntico; o hierárquico é um
  cliente + um dispatch. É por isso que o codec já rodava sem tocar `src/tcf`.
- **Gate de CAPACIDADE, não de compressão**: hierarquia representa dado que a tabela plana não
  representa; o critério é RT-exato + não-regressão flat, não ≥15% (ADR-0024 / T-REL-08).
- **Separação de camadas** habilita otimização e paralelismo por coluna independentes depois (L3 em `.9`).

## Considered Options

- **Weld aditivo L2/L3 sobre L1 reusado** (esta). Baixo risco, camadas separadas.
- **Integrar a hierarquia no encoder plano** (um `encode` que detecta aninhamento): rejeitada —
  acopla L2 ao L1, arrisca o byte-canonical plano, mistura camadas.
- **Manter research-track até `.9`**: rejeitada pelo reescopo do owner (`.8` = feature-complete).
- **Multiplicidade deduzida como default** (menos bytes): adiada — vira otimização L3 opt-in; o
  default explícito dá independência/paralelismo (medido: Pareto no registro largo, o comum).

## Consequences

**Positivas**:
- `#TCF.8H` decoda em produção; `decode()` auto-roteia. Capacidade de dado aninhado no `.8`.
- Flat byte-idêntico (D1-D9=1523, D17a=300, real-world=89616 pinados verdes) — weld não regride nada.
- Gate verde: `tests/test_hierarchical_rt.py` (clássicos + bordas + fuzz seedado 1200 docs;
  o lab `2026-07-14-2120` roda 8000/8000). Suíte total 646 passed.

**Negativas / custos**:
- Escopo é a **classe coberta**; ragged/tipos/null/N-raízes/N:N são fail-loud (fronteira registrada,
  incrementos futuros). Um `#TCF.8H` com chave faltando é rejeitado (não corrompe).
- L3 hoje está parcialmente misturada no L2 (deduções embutidas no encode) — desacoplar em passe
  próprio é dívida registrada pra `.9`.

## Update 2026-07-15 — P1 presença/ragged (chave opcional) welded

**[dispositivo→feito]** 1º incremento de paridade JSON (T-CODE-TCF8H-JSON-PARITY): chave OPCIONAL
(objeto ragged), o construto JSON de API mais comum que o codec rejeitava. Gramática:
`nome?:msize` — `?` cola no nome (vira char estrutural, entra no escape), `msize` = tamanho da
coluna-MÁSCARA de presença (vem ANTES das colunas do campo, como o `#count`). Alfabeto 3-estados:
`.`=presente · `-`=ausente · `0`=RESERVADO null (P3, fail-loud). Corpo denso (só instâncias
presentes). É o **definition-level do Dremel** em forma textual inspecionável (pilar explicabilidade).

**Aditivo e compatível**: dado SEM raggedness → wire **byte-idêntico** (o `?` só aparece onde há
campo opcional, deduzido do dado). Estudo: [lab 2026-07-15-0125](../../experiments/lab/dirty/2026-07-15-0125-p1-presenca-ragged-estudo/).

**Endurecimento (auditoria adversarial `wf_e548aeaa-055`)**: junto com o P1, o `_derive_schema`
passou a **validar tipo honestamente** — tipo estrutural misto (scalar/object/array), `null`,
array-de-objetos-sem-chaves = `HierarchicalError`, NUNCA `str()`-engolido. O decode ganhou guardas
de frame (size≥0, size omitido só na última coluna, máscara válida, coluna exaurida, raiz-lista).
Isso fecha **corrupções silenciosas pré-existentes** do próprio weld (array-de-objetos-vazios,
size-None-no-meio). Gate: suíte 684 passed, pins flat byte-canônicos verdes.

**Fronteira ainda fail-loud** (próximos incrementos): tipos escalares preservados (P2), `null`
distinto (P3, `0` já reservado), rep-level/N-raízes (P4), N:N (super-hierarquia). Limitação
declarada: truncamento da última folha (size omitido) é indetectável — vale p/ `.8M`/`.8H`.

## Relation to other ADRs

- **Fecha o gate** deixado por [ADR-0031](0031-hierarchical-discriminator-H.md) (que reservou `H` e
  adiou o codec). Consome a semântica de dispatch e a regra sem-espaço.
- **Estende** [ADR-0029](0029-version-format-identification-semi-implicit.md) (discriminador) e
  [ADR-0032](0032-tcf8-default-format.md) (`#TCF.8` default) — `H` é a realização multi-col hierárquica.
- Herda [T-FMT-NAME-ESCAPING](../../tickets/T-FMT-NAME-ESCAPING.md) (escape de nome) e
  [T-FMT-HEADER-BASE-HEX](../../tickets/T-FMT-HEADER-BASE-HEX.md) só onde aplicável (sizes de coluna).
- Sob a política [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md) (pré-1.0, git-as-compat): o
  weld é dispositivo; baselines flat permanecem pinados; a hierarquia é feature nova, não muda o passado.
