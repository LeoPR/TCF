---
title: Plano — ÍNDICES DE SUBSTITUIÇÃO (elementos especiais via dicionário pré-semeado no header)
type: plan
status: aberta
created: 2026-07-15
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/BUG-SEQRLE-RANGE-EMPTY-B.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md (H-SUBST-INDEX-01, H-HIER-SCALAR-01)
  - experiments/lab/dirty/2026-07-13-1921-dataseth-typed-header-domain/
  - src/tcf/composicional/syntax.py (numeração de referências — L1)
---

# Plano — índices de substituição para elementos especiais (null primeiro)

**[dispositivo→plano; estudo-primeiro, NÃO weldar antes de medir + aprovar]** Ideia do owner
(2026-07-15): tratar null (e a família de especiais) **na camada de referência/dicionário do L1**,
não como estado de máscara. O núcleo já numera as referências descobertas (0,1,2,…); um marcador no
header **pré-semeia** o dicionário com os especiais nos índices baixos.

## Conceito

- O dicionário/tabela de referências de uma coluna **nasce PRÉ-SEMEADO** com os elementos especiais
  reservados (índices 0..k−1), como se fossem "descobertos de fábrica". As referências descobertas
  pelo TCF continuam depois (k, k+1, …).
- **NÃO é "if null desloca"** (lógica condicional nova). É "a tabela já começa preenchida": o start
  da lista de elementos vem populado com os reservados. Menos lógica, não mais.
- Um **byte combinatório** no header declara QUAIS especiais estão reservados → até **8 especiais**
  (null, ausência, NaN, +Inf, −Inf, + reservados) nos índices 0..7, em ordem canônica.
- No corpo, um especial é **referência ao seu índice reservado** — tratado como qualquer outra
  referência. Ex.: bit de null setado → índice 0 = null; toda referência a 0 é null.
- **Por-coluna** (encaixa no L1 independente/paralelo). Global = evolução (cross-dict/V2-L).

## Mecanismo (o ponto que torna lossless — corrige a refutação anterior)

O lab `2026-07-13-1921` **refutou** "null=índice" porque **stringificava** null → token `"null"`,
que **colidia** com a string real `"null"`. Aqui a reserva é na **camada de referência com
SENTINELAS NÃO-STRING** (marcadores que nunca são iguais a nenhuma string real):
- encode: o L2 passa ao L1 a coluna com posições especiais MARCADAS (sentinela ≠ qualquer string);
  o L1 pré-semeia a tabela e referencia o slot reservado nessas posições. Strings reais (inclusive
  `"null"`, `""`) são descobertas normalmente e ganham índices ≥ k. **Sem colisão** (a reserva é
  posicional na tabela, não por valor string).
- decode: referência a um índice reservado → materializa o especial (índice 0 → `None`).

## Ciclo 2 (owner 2026-07-15) — natureza única + pipeline de refinamento + dono-versão

**null/true/false são a MESMA natureza** — valores identificados cujo índice reservado mapeia pra um
**valor Python tipado** (0→`None`, 1→`True`, 2→`False`), não pra uma string. **A string SAI do
arquivo** e passa a viver no **dicionário da VERSÃO** (não no `.tcf`): arquivo + versão recupera. Não
tratar null como super-especial — é só um tipo identificado cuja string inicial some, sobrando o marcador.

- **Dono-versão do dicionário de especiais**: o mapa (índice→valor especial) é parte do FORMATO; freeze
  no 1.0, evolutivo pré-1.0 (ADR-0024). Documentar (ADR quando weldar). É o que torna "a string some" lossless.
- **Pipeline de refinamento** (composável, cada estágio opcional):
  1. **descobrir** (pré-pass/OBAT ou pré-filtro reconhece null/bool como candidatos) →
  2. **reservar índice** (ESTE plano — string sai do arquivo, vira referência) →
  3. **bN** (`.9`/H-TYPE-02 — empacota o stream de refs em bits p/ baixa-cardinalidade).
  null usa só o (2); bool ganha no (3).
- **Insight**: o índice reservado resolve `true`-string vs `True`-bool **mais limpo que a tag C-híbrida**
  do H-TYPE-01 — é QUAL índice se referencia (índice 1 = bool `True`; string `"true"` = índice
  descoberto). **bool migra pro framework de índices; número (cardinalidade infinita) fica na dedução.**
- **Escopo (owner)**: protótipo **null-only** agora; design generaliza pra family+bN mas NÃO implementa.
  Hook do `.9`: manter o stream de refs **empacotável por bN** (não acoplar índice-substituição ao
  encoding físico) + tabela de reservados **extensível** (true/false depois, sem rework). Fazer funcionar,
  deixar preparado, não encher de lixo pra limpar depois.

## Espaço de design a MAPEAR (o que o estudo decide)

1. **Forma do header** (2 candidatos a protótipar + medir):
   - (a) byte no META por-coluna (ex.: um marcador após o size — `nome:size` + byte de especiais);
   - (b) um bloco de header separado que declara os especiais da coluna/documento uma vez.
2. **Quais especiais no P3/JSON**: só **null** (bit 0). NaN/±Inf ficam FORA (não são JSON RFC 8259;
   entram com P2/tipos — mas o mecanismo já nasce pronto pra eles).
3. **Ausência como índice? (owner D)** — hoje ausência é máscara `-` (P1). Medir se ausência-como-
   índice-reservado ganha da máscara de presença. Se sim, presença e null unificam no MESMO framework.
4. **Ordem canônica dos reservados** (qual bit → qual índice) — fixar p/ determinismo.

## Medições (os "fundamentos" — owner: as medições dão base)

- **Custo do deslocamento é DECIMAL, não byte** (owner C): o índice é textual; +1 empurra refs em
  fronteiras de dígito (9→10, 99→100, 999→1000). Medir o Δbytes real em colunas com null a vários
  regimes de cardinalidade (poucas refs = quase-grátis; perto de 9/99/999 = discutível). Quantificar,
  não assumir.
- **null-as-index vs máscara-`0`**: bytes + complexidade + a **unificação P3a/P3b** (null-em-campo E
  null-em-elemento no MESMO mecanismo — o maior ganho vs máscara, que precisaria de element-mask nova).
- **ausência-as-index vs máscara-`-`** (item 3): bytes; decide se a ausência migra pro framework.
- **Byte-compat**: coluna SEM especiais → byte combinatório zero/ausente → **byte-idêntico** (compat
  do P1 preservada). Só colunas com especiais pagam.
- **4 vias**: `ausente` ≠ `null` ≠ `"null"` (string) ≠ `""` (string) — a distinção que só a reserva
  estrutural dá (a assinatura do P3).

## Gate / validação (mesma esteira do P1)

RT-exato; adversarial (posições inicial/meio/fim; coluna all-null; null em escalar/objeto/array;
null em elemento; nested; máscara/frame/byte-header corrompidos → fail-loud, nunca corrupção
silenciosa); non-regressão flat byte-idêntica (D1-D9/D17a/real-world); probe real-world.

## Risco

- **Toca o L1 core** (numeração de referências em `src/tcf/composicional/syntax.py`) — sai de
  "aditivo em L2" (a máscara) pra "mexer no núcleo". Precisa aprovação arquivo-a-arquivo + gate
  byte-canônico (ADR-0024). É o **mesmo arquivo** do `BUG-SEQRLE-RANGE-EMPTY-B` → pensar os dois juntos.
- Por isso: **estudo-primeiro num lab**, com sentinelas não-string e reserva por-coluna, medindo
  tudo acima, ANTES de qualquer weld. Se a medição confirmar (unificação + custo baixo), este
  framework SUBSTITUI a máscara-`0` como o mecanismo de P3 (a máscara fica só pra presença — ou também
  migra, item 3).

## Ordem

1. Owner ratifica a forma do header a protótipar (a ou b) — ou o estudo mede as duas.
2. Lab `YYYY-MM-DD-HHMM-substituicao-indices-null-estudo/` (código zerado do contrato, não copia proto).
3. Mede null-as-index (campo + elemento) vs máscara; custo do deslocamento decimal; 4 vias; compat.
4. Decide: weld do framework (com aprovação) OU volta pra máscara se não pagar. Depois: ausência (D),
   e o mecanismo fica pronto pra NaN/Inf (P2).

## Relação com trabalho anterior

- **Refina/supera H-HIER-SCALAR-01** (que tratava null/NaN/Inf como domínio tipado no header) — este
  é o "domínio declarado no header" na forma de índices reservados pré-semeados, sem stringificar.
- **Supersede a máscara-`0` do P1** como candidato de P3 (a decisão é do estudo). A máscara de
  **presença** (`.`/`-`) do P1 permanece; o slot `0` reservado fica livre.
- Registrado como **H-SUBST-INDEX-01** no roadmap.
