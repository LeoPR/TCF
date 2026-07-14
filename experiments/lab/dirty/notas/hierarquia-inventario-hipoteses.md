---
title: Hierarquia — inventário de hipóteses (exaustão da questão) [probatório]
type: experiment
status: aberta
created: 2026-07-14
ticket: tickets/T-STUDY-HIERARCHICAL-TCF.md
related:
  - experiments/lab/dirty/notas/estudo-tcf-hierarquico-mapa.md
  - experiments/lab/dirty/notas/teoria-cardinalidade.md
  - experiments/lab/dirty/2026-07-05-1543-tcf8-estrutura-aninhada-pessoa-telefones
  - experiments/lab/dirty/2026-07-05-1608-linking-pai-filho-cabecalho
  - experiments/lab/dirty/2026-07-06-2246-tcf8h-fronteira-link-posicional
  - experiments/lab/dirty/2026-07-13-2325-hierarquia-cardinalidade
  - experiments/lab/dirty/2026-07-13-2356-rle-dual-multiplicidade-deduzida
---

# Hierarquia — inventário de hipóteses (para ESGOTAR, não firmar)

**[probatório→síntese]** Levantamento a pedido do owner (2026-07-14): *recuperar o estudo* (não
re-deduzir), *pegar TODAS as opções e experimentar*, e *esgotar* a questão de hierarquia. Produto de
workflow (recuperação de 5 fontes + 30 hipóteses de 5 lentes + crítico de completude). **Não escolhe
vencedor, não firma.**

## Reframe do owner (dispositivo)

- Representações de hierarquia **NÃO são opções mutuamente exclusivas**. O MESMO DatasetH é
  potencialmente VÁRIAS materializações ao mesmo tempo, escolhidas pelo **consumo** (tabelão pra
  alimentar CSV; árvore pra emitir JSON; normalizado pra banco). É **projeção, não escolha**.
- **1:N ≡ N:1** — a mesma aresta de pontos de vista diferentes (o mesmo dado em posições de coluna
  diferentes); "sempre 1:N" pelo lado do contêiner, ou difere só por arquitetura.
- Objetivo: inventário que ESGOTA, grounded no estudo prévio.

## Resposta direta à sua hipótese ("nada muda; TCFs concatenados")

**CONFIRMADA — e JÁ IMPLEMENTADA + RT-provada** — para a **classe coberta**. Você tinha razão.

- **Peça 2 (lab 1543)** + **peça 3 (lab 1608)** já fazem: um payload hierárquico vira N blocos TCF
  independentes concatenados, ligados por **uma aresta child-side por bloco não-raiz** (`@K <pai>.<campo>[*]`).
  Blocos são **heterogêneos por natureza**: no S6 os 4 blocos são formatos DIFERENTES (TCF.8 single-col,
  TCF.7 multi-col ×2, TCF.8 array) com **pais diferentes** (geo é filho de endereco, não da raiz). RT-provado
  (P2 S4; P3 S4+S6; nested-study 24/24).
- **O link é CONTENÇÃO, não FK** (quem-contém-quem basta; sem chave de join). **Dispositivo.**
- Child-side é **append-only/stackable**: acrescentar outra sub-hierarquia = concatenar uma aresta + um
  bloco, sem tocar em nada. É literalmente "buscadas como dois TCFs empilhados".
- Ou seja: **"pais/filhos/netos com estruturas diferentes na mesma chamada, sob uma raiz" = exatamente
  o que a adjacência child-side sobre blocos empilhados expressa, com ZERO mudança de gramática.**

## ⚠️ A assimetria de SEGURANÇA (achado load-bearing do crítico)

"Nada muda" vale pra CORREÇÃO na classe coberta, mas a **segurança depende de QUAL dual você usa**:

- **Envelope-de-blocos (P2/P3)**: falha **LOUD** (`NotImplementedError`) nos casos fora da classe.
- **Tabelão integrado / Modelo A** (protótipos 2325): pode **CORROMPER CALADO** em array-dentro-de-array
  (B3 serializa o array aninhado como string → RT-mismatch). **MITIGADO no lab 2325**: o `encode_h` tem
  auto-verificação (`decode_h(blob)==records` → `AmbiguityError`), que transforma essa corrupção em
  fail-loud. Valida a decisão daquele guard. **Sem o guard, o dual integrado tem armadilha de corrupção
  silenciosa nos mesmos inputs onde o envelope falha loud.**

## A fronteira (onde "nada muda" PARA) — a taxonomia SETTLED

| grau | mecânica | classe | estado |
|---|---|---|---|
| **contenção** | quem-contém-quem (aresta child-side) | raiz única; objeto⊃objeto (1:1) qualquer profundidade; array-folha de objetos escalares sob objeto single-instance | **RT-provado, dispositivo** |
| **presença** (def-level) | máscara 3-estados `.`/`0`/`-` por coluna | chaves ausentes / null-em-coluna (heterogeneidade INTRA-nível) | **RT-provado** (B1/B2, 1 char/linha) |
| **repetição** (rep-level) | um NÚMERO posicional (onde o array reinicia) | array-em-array, objeto/array dentro de elemento de array, N raízes | **caracterizado, NÃO implementado** (peça 11/B3) |
| **normalização** (N:N) | tabela-ponte / FK / join key | N:N, cubo multidimensional, snowflake com dimensão COMPARTILHADA | **fail-loud hoje** (NNError, produto cartesiano) |

**O que é genuinamente DIFÍCIL colapsa em UM primitivo faltante**: o **link posicional / rep-level**
(um número), distinto da FORMA (delimitador/contagem/profundidade). Snowflake com filho compartilhado
**excede a contenção** (precisa de FK) — é outra coisa.

## Já RESPONDIDO (dispositivo — NÃO re-estudar)

1. Concatenação de blocos heterogêneos sob raiz única faz RT (P2/P3).
2. O link da classe é CONTENÇÃO, não FK.
3. Heterogeneidade intra-nível (chave ausente, null-em-coluna) fechada pela máscara def-level 3-estados.
4. Taxonomia presença(B1/B2) / repetição(B3) / normalização(B4) — DECIDIDA.
5. Dualidade 1:N≡N:1 (parent-side/child-side são duais; child-side escolhido por append-only).
6. Escolher viewpoint numa aresta 1:N custa ZERO bytes pro link (multiplicidade deduzível: RLE run = nº
   de filhos; comprimento da coluna = tamanho do array) — labs 2356 + peça 9.
7. Dimensão single-column (star "dimension") já fatorada pelo @dict/RLE por-coluna (distinto<n → `*N|`).
8. Framing de PROJEÇÃO grounded e medido (Modelo A tabelão vs Modelo B nível-aware como candidatos de min(),
   lab 2356; crossover por largura).
9. N:N / múltiplos arrays irmãos = fail-loud hoje (NNError) — o cubo multidimensional é rejeitado, não corrompido.
10. Teorema do portador-de-forma (P6): exatamente UM de {delimitador-casado, contagem, profundidade}
    reconstrói a árvore; separador de irmão sozinho dá só lista plana.
11. Fidelidade de tipo é camada ortogonal (C1a/b): C-híbrida default (deduz número/bool grátis, tag só na
    colisão-string). **Ortogonal à hierarquia — camada depois, como você disse.**

## Genuinamente ABERTO (a fronteira)

- **A CORRIDA DE 3 VIAS nunca foi rodada**: envelope-de-blocos vs bracket-header-integrado/tabelão-A vs
  union-rectangle-com-máscara, no MESMO payload heterogêneo. (← o experimento mais barato, abaixo)
- Rep-level (B3): wire form / bytes / RT pra array-em-array / N-raízes — só caracterizado, não implementado.
- N:N ponte vs array denormalizado plano — nunca medido; quando normalizar, sem resolver.
- Union-schema vs concat: crossover por **SCHEMA OVERLAP (Jaccard dos field-sets)** / sparsity — nunca rodado.
- **Bytes real-world pra QUALQUER caminho de hierarquia** — nenhuma fonte N≥5 real; tudo sintético minúsculo;
  gate anti-incidente (2026-05-21) NÃO passado pra a questão inteira.
- Custo de **re-projeção no decode** (compute/memória por consumidor) — nunca precificado.
- Custo de **ordem** ao de-interleave uma coleção polimórfica em blocos-por-forma.
- **Wash-out gzip/brotli** da escolha de representação — não perguntado pra hierarquia.
- Dict compartilhado cross-block (cross-dict) pra blocos heterogêneos — deferido a V2-L, não conectado aqui.
- @dict de LINHA (determinante composto {A,B}→resto) pra dimensão snowflake — precisa TANE/HyFD ou chave do schema.
- SINTAXE do envelope (draft, redesign do owner) + tabela de OFFSET (seek) sem perder o append-only.
- Custo de TOKEN por projeção pra consumo LLM — não medido (apesar de ser o eixo não-byte declarado do projeto).

## Lacunas que o crítico achou (o inventário não cobriu)

- Custo de re-projeção no decode (compute/mem). · **Array POLIMÓRFICO + ordem** (a leitura MAIS AFIADA de
  "estruturas diferentes na mesma chamada" = um array cujos ELEMENTOS são sub-árvores diferentes → objeto-em-
  elemento-de-array, PROIBIDO). · Redundância cross-block perdida (cada bloco tem dict LOCAL). · Wash-out de
  compressão a jusante. · Union amplifica a fronteira de tipo-misto. · Ingestão de schema externo (formato/custo).
  · Modalidades de consumo além de leitura (seek, update/patch). · Custo de token LLM. · Gate real-world.
  · Netos-através-de-um-array (a profundidade em si é coberta; neto DENTRO de array não).

## As 30 hipóteses (por lente; id · veredito · enunciado curto)

**Concatenação/heterogêneo (blocos):**
- H-HET-CONCAT-01 · *já-respondida* · heterogêneo na classe = N blocos + 1 aresta child-side append-only (RT-provado).
- H-HET-CONCAT-02 · *já-respondida* · "nada muda" vale EXATO na classe coberta e nem uma forma além.
- H-HET-CONCAT-03 · *cheap-defer* · contar blocos por SHAPE-SIGNATURE (dobrar objetos de forma idêntica num bloco colunar) — **mas perde ordem se ordem importa**.
- H-HET-CONCAT-04 · *cheap-do-now* · medir o imposto do envelope (~1 linha/bloco; amortiza só em N grande).
- H-HET-CONCAT-05 · *cheap-defer* · heterogeneidade = 2 camadas ortogonais (inter-bloco por concat+contenção; intra-bloco por máscara).
- H-HET-CONCAT-06 · *research-only* · edge-list centralizado (tuple pai,campo,card,filho) PODERIA expressar snowflake — mas precisa FK.
- H-HET-CONCAT-ROOT-01 · *já-respondida* · o caso raro sob UMA raiz = zero mudança de codec (já é a classe).
- H-HET-MASK-INTRALEVEL-02 · *cheap-do-now* · ragged/null = canal de PRESENÇA por coluna (def-level), não mudança de bracket.
- H-HET-REPLEVEL-SINGLE-PRIMITIVE-03 · *risky* · tudo difícil colapsa em UM primitivo: o link posicional (um número).
- H-HET-NROOTS-SYNTHROOT-04 · *cheap-defer* · N raízes = raiz sintética SE ordem cross-root é livre; senão precisa posicional.
- H-HET-CODEC-DUAL-NEVER-RACED-05 · *cheap-defer* · envelope-de-blocos vs bracket-integrado nunca competiram.
- H-HET-SNOWFLAKE-FK-06 · *research-only* · snowflake excede "contenção não FK" (precisa join key).

**Union/sparse rectangle:**
- H-UNION-RECTANGLE-01 · *research-only* · union-schema (colunas = união; máscara de presença) como 1 retângulo.
- H-UNION-SPARSITY-CROSSOVER-02 · *research-only* · union×concat = crossover por Jaccard de field-sets.
- H-UNION-MASK-RLE-03 · *research-only* · agrupar por shape colapsa a máscara sob RLE (ordem-livre grátis; H-CARD-06).
- H-UNION-STRUCT-ABSENCE-04 · *já-respondida* · ausência ESTRUTURAL ≠ null (a máscara força a distinção).
- H-UNION-TAGGED-VARIANT-05 · *risky* · poucos shapes/muitos registros = tag por registro + registry de shapes.
- H-UNION-AS-PROJECTION-06 · *já-respondida* · o retângulo union é uma 3ª projeção reversível ("tabelão mais largo").

**Projeção/dualidade:**
- H-PROJ-ALGEBRA-01 · *research-only* · um DatasetH admite conjunto fechado de projeções RT-equivalentes; o .tcf fixa UMA canônica.
- H-PROJ-MINFLOOR-02 · *cheap-defer* · encode = min() sobre projeções POR DOCUMENTO (como o FLOOR das natures).
- H-PROJ-LOGEDGE-HDR-03 · *research-only* · header declara a aresta LÓGICA viewpoint-free; direção 1:N/N:1 = escolha no decode.
- H-PROJ-DUAL-ZEROCOST-04 · *já-respondida* · escolher viewpoint custa ZERO bytes pro link (multiplicidade deduzível).
- H-PROJ-HETERO-PERBRANCH-05 · *já-respondida* · o caso raro do owner = projeção por-ramo (cada sub-hierarquia um bloco).
- H-PROJ-NORMALIZED-SNOWFLAKE-06 · *risky* · snowflake = a projeção escolhida pra consumo de BANCO (edge-list).

**Snowflake/multidim:**
- H-SNOW-DICT-01 · *já-respondida* · dimensão single-column já fatorada por @dict/RLE (zero máquina nova).
- H-SNOW-ROWDICT-02 · *research-only* · dimensão MULTI-column como UNIDADE precisa @dict de LINHA (determinante composto).
- H-SNOW-FK-CONTAINMENT-03 · *cheap-defer* · snowflake real = DAG de FK N:1, não árvore de contenção; denormaliza+dict alcança.
- H-SNOW-SCHEMA-GADGET-04 · *cheap-defer* · "schema dá dicas" = gadget EXTERNO (alert-only, g3/FD), não o core.
- H-SNOW-PROJECTION-05 · *cheap-do-now* · star = UM DatasetH projetado (tabelão largo OU fato+dim normalizado) por consumo.
- H-SNOW-CUBE-NN-06 · *research-only* · cubo multidim (fato por MÚLTIPLAS dims independentes) = o N:N fail-loud de hoje.

## O experimento mais barato que ESGOTA vários abertos de uma vez

**A corrida de 3 vias, real-world, nunca rodada.** Pegar UM payload de API cliente-servidor **real** e
**heterogêneo** que fique na classe coberta (uma resposta de API sua, não outro S4/S6 à mão), e passar
pelos TRÊS codecs que JÁ existem nos labs:
- **(a) envelope-de-blocos** (P2/P3),
- **(b) bracket-header integrado / tabelão Modelo A** (2325),
- **(c) union-rectangle + máscara de presença**.

Por via, reportar: RT pass/fail; bytes vs JSON cru; **bytes DEPOIS de gzip/brotli** (pegar o wash-out);
classificar cada sub-estrutura como in-class vs fronteira-fail-loud; e logar as covariáveis de
heterogeneidade (Jaccard de overlap, sparsity por coluna, nº de shapes distintos, se algum array é
polimórfico) + declarar o viés (gate anti-incidente). **Barato porque os 3 codecs + RT já existem** —
só falta um harness fino + 1 fixture real; tira a questão dos sintéticos minúsculos pela 1ª vez; e uma
rodada só toca H-HET-CODEC-DUAL-05, H-UNION-01/02, o wash-out, e a assimetria de corrupção-silenciosa
(o dual integrado corrompe onde o envelope falha loud?).

**Bloqueio**: precisa de UM payload real. Se você tiver uma resposta de API representativa (mesmo
anonimizada), é o insumo que destrava tudo.
