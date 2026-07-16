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

## Ciclo 3 (owner 2026-07-15) — PERFIL DE USO (parâmetro/heurística) + preparar-para-ambos

Decisão de método (owner): **não firmar uma escolha agora** — construir a ESTRUTURA que suporta as
duas opções, decidida por **parâmetro OU heurística**, com o **default vindo de medição em MASSA
depois** (não agora; agora = ter a funcionalidade, não otimizar prematuramente).

Não é só o header. É uma **família de escolhas** sob um mesmo guarda-chuva de **PERFIL DE USO**
(nome PROVISÓRIO — owner não quer firmar nome ainda; a IDEIA é o eixo):
- **eixo**: "otimizado p/ **API/transmissão**" (payload minúsculo, latência, terminal) × "p/
  **armazenamento/massa de dados**" (grande, re-comprimido) — OU uma **heurística** que decide sozinha.
- **escolhas que vivem sob o perfil**:
  - **forma do header** (A inline × B bloco) — por densidade de colunas-especiais (medido: crossover);
  - **null/ausência**: máscara (P1) × índice de substituição (este) — a "fix dos elementos" pode ser
    no HCC ou depois; dá pra **deduzir automático** por heurística;
  - **bN** (H-TYPE-05, "bN sob perfil de compressão" — JÁ era essa ideia);
  - **L3 multiplicidade** explícita×deduzida (H-L3-OPT-BLOCK).
- **requisito estrutural**: o código nasce **preparado pra ambos** (não hard-code de uma opção), pra
  a medição em massa poder comparar depois. Registrado como **H-PROFILE-01** no roadmap.
- **TCF tem que ganhar em transmissão realista estilo API** (norte declarado) — mas ATÉ isso pode ser
  o perfil "API"; a medição em massa dirá o default provável.

## Espaço de design a MAPEAR (o que o estudo decide)

1. **Forma do header** (2 candidatos a protótipar + medir):
   - (a) byte no META por-coluna (ex.: um marcador após o size — `nome:size` + byte de especiais);
   - (b) um bloco de header separado que declara os especiais da coluna/documento uma vez.
2. **Quais especiais no P3/JSON**: só **null** (bit 0). NaN/±Inf ficam FORA (não são JSON RFC 8259;
   entram com P2/tipos — mas o mecanismo já nasce pronto pra eles).
3. **Ausência como índice? (owner D, ciclo 3)** — hoje ausência é máscara `-` (P1, forma de TRABALHO).
   **Forma definitiva EM ABERTO** (owner: "podemos discutir ainda uma forma mais definitiva"). O
   requisito agora não é decidir, é **ter a estrutura pra MEDIR em massa depois** (máscara `-` ×
   ausência-como-índice-reservado). Se índice ganhar, presença e null unificam no MESMO framework.
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

## Revisão crítica 2026-07-15 — element-mask versus índice de substituição

**[probatório→opinião técnica; sem weld nesta seção]** Após o estudo P3b de element-mask
([lab `2026-07-15-2230-p3b-null-elemento-estudo`](../2026-07-15-2230-p3b-null-elemento-estudo/result.md),
RT 8/8 didático), as duas rotas foram comparadas contra o `src/tcf` real e contra formatos
colunares estabelecidos. A conclusão é separar a **unificação semântica** da **unificação física**:
P3a e P3b pertencem à mesma família de definition/validity levels, mas não precisam usar o mesmo
stream físico.

### Falsificadores da unificação pelo índice

1. **O L1 não é um dicionário obrigatório.** O caminho real é OBAT + HCC + seq-RLE. O protótipo de
   índices (`2026-07-15-2101`) modela um dicionário puro; reservar `0` no protótipo não prova que o
   índice possa entrar no L1 sem alterar a numeração de referências, o fallback, o framing e os
   gates byte-canônicos. A integração seria uma mudança no núcleo, não uma extensão L2 transparente.
2. **Null estrutural não tem stream de valor para receber índice.** P3a já faz RT de campo escalar,
   objeto, array e all-null. Um objeto inline não possui coluna de valores própria; um array possui
   count e colunas filhas. Para representar `objeto=null` ou `array=null` com índice seria necessário
   criar um stream de validade por instância. Esse stream seria semanticamente uma máscara, apenas
   com outro nome.
3. **Null de elemento-objeto precisa preservar a estrutura.** Em `[{}, null, {}]`, o decoder precisa
   saber que o elemento nulo não consome nenhuma coluna descendente. Um índice de valor escalar não
   codifica sozinho essa decisão estrutural; a element-mask faz isso diretamente e mantém os nomes e
   a topologia dos filhos.
4. **A P3a já está soldada com máscara.** Trocar retroativamente o mecanismo para obter uma
   unificação física criaria uma mudança de contrato no caminho que já foi validado com dado real.
   A vantagem alegada do índice para P3b só existe se também reabrirmos P3a e os gates do L1.
5. **O custo medido do índice ainda é de forma, não do L1.** O estudo admite que seus bytes são
   aproximados: a máscara comparada era crua e o índice não passou pelo OBAT/HCC real. O resultado
   robusto é a hipótese de unificação e o crossover dependente do perfil, não um ganho byte-canônico.

### Forma recomendada para P3b

Manter a semântica comum de definition stream, mas materializá-la na cardinalidade correta:

- P3a: máscara por instância do campo, com `.`=valor, `-`=ausente e `0`=null.
- P3b: máscara por elemento do array, com `.`=valor e `0`=null; não precisa de `-` porque o `count`
  já determina quais posições existem.
- Array element-nullable: ordem **count → emask → densos**.
- Invariante de alinhamento:

  $$
  |emask| = \sum_i count_i
  $$

- Invariante de consumo: `count` determina quantos símbolos da `emask` são lidos; `0` não consome
  corpo; `.` consome exatamente um valor escalar ou uma instância de objeto-filho.

Isso preserva sem ambiguidade:

| forma | representação lógica |
|---|---|
| `[]` | `count=0`, sem slots de `emask` |
| `[null]` | `count=1`, `emask=0`, sem denso |
| `[valor]` | `count=1`, `emask=.`, um denso |
| `[valor, null, valor]` | `count=3`, `emask=.0.`, dois densos |

O header demonstrado pelo estudo, `nome#?[...]`, deve ser lido como “este array tem element-mask”,
não como um novo tipo de valor. Para um array de objetos, a mesma marca protege o consumo das colunas
descendentes.

### Literatura convergente

- [Apache Arrow — Columnar Format](https://arrow.apache.org/docs/format/Columnar.html): cada array
  possui validity bitmap próprio, inclusive arrays filhos de listas e structs. Em dictionary
  encoding, os índices têm validade separada; `null` não precisa ser uma entrada do dicionário.
- [Apache Parquet — Nulls](https://parquet.apache.org/docs/file-format/nulls/): nullidade é
  codificada em definition levels e nulls não entram no stream de dados.
- [Apache Parquet — Nested Encoding](https://parquet.apache.org/docs/file-format/nestedencoding/):
  definition levels e repetition levels são streams distintos, calculados a partir da estrutura
  aninhada; dictionary indices são outra codificação.
- [Dremel (Melnik et al., 2010)](https://research.google/pubs/dremel-interactive-analysis-of-web-scale-datasets-2/):
  fundamenta a separação entre definição/presença e repetição em dados aninhados.
- [Apache ORC — Specification](https://orc.apache.org/specification/ORCv1/): `PRESENT` é separado
  de `DATA` mesmo quando a coluna usa dictionary encoding; listas usam `PRESENT + LENGTH + child`,
  e o child tem nulidade independente.

Esses formatos não tratam validade como um valor comum do dicionário. A element-mask do TCF é a
tradução textual, inspecionável e comprimível pelo próprio L1 dessa mesma separação.

### Recomendação registrada

**Weld recomendado: element-mask em L2 para P3b.** É aditivo, mantém OBAT/HCC intactos, preserva a
topologia de objetos nulos e segue a separação já validada em P3a. O índice-de-substituição permanece
como possível representação física futura, especialmente para folhas escalares e perfis de null
raro, mas não deve ser o mecanismo semântico canônico de P3 nem bloquear o weld.

H-PROFILE-01 pode comparar posteriormente, em massa e no L1 real, máscara versus índice para folhas
compatíveis. Se o índice vencer nesse subdomínio, ele entra como otimização escolhida por perfil; não
substitui os streams de definição necessários para objetos, arrays e elementos de objeto.

### Gate antes do weld

O estudo didático cobre 8/8 formas. O weld deve ainda provar: emask com tamanho curto/longo,
caractere inválido, coluna densa exaurida ou sobrando, combinação de field-mask e element-mask,
array todo-null, elemento-objeto null, aninhamento e byte-idêntico quando nenhum elemento é null.

**Confiança:** Média-Alta. A forma tem RT didático e respaldo arquitetural/literário; ainda falta o
gate realista e adversarial integrado ao core.

## Ciclo 4 (owner 2026-07-15) — o PRINCÍPIO DECISOR: O(1)/stream/separável/view

**[dispositivo — fecha a decisão de mecanismo]** O perfil do TCF é ser **o mais O(1) possível no
decode**: isso o torna **stream**, com **partes separáveis e analisáveis**, com **menos memória,
processamento e/ou latência**. O diferencial é esse foco **+ o `view()` com agregação geral
inter-compression** (operar sobre o comprimido sem materializar).

Esse princípio é o **EIXO que decide** o mecanismo de especiais (não é preferência):
- A **máscara é um stream de validade SEPARADO** → responde nulidade/presença **sem materializar os
  valores** (contar non-null, filtrar presentes, agregar por presença rodam na máscara sozinha). É
  exatamente o diferencial view/agregação-inter-compression + streamável + baixa-memória.
- O **índice enterra a validade no stream de valores** → analisar nulidade exige o stream de dados;
  contra o diferencial. E não representa null estrutural (objeto/array) sem virar máscara com outro nome.
- Convergência de estado-da-arte: **Arrow (validity bitmap) · Parquet/Dremel (definition levels) ·
  ORC (PRESENT)** separam validade de dados MESMO sob dictionary encoding — nunca tratam null como
  entrada do dicionário. A element-mask é a tradução textual/inspecionável/L1-comprimível disso.

**DECISÃO FECHADA**: a **máscara** (presença P1 · null-campo P3a · element-mask P3b) é o mecanismo
**canônico** de definição/validade — coerente com o eixo O(1)/view, e unifica P1/P3a/P3b/L3 como a
mesma escolha "separabilidade primeiro". O **índice-de-substituição** fica como **nicho** do perfil
"armazenamento/max-compressão" (folhas escalares, null raro), medido depois sob [[H-PROFILE-01]] no
L1 real — NUNCA para null estrutural, nunca bloqueia o weld. Segue o weld da **element-mask (L2)** p/ P3b.
