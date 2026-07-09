# Referência / índice / dict no TCF — apanhado de hipóteses [estudo/plano]

**Data**: 2026-06-19 · plano (hipóteses a estudar; **não decide, não implementa**). Origem: owner —
"se já temos referências numéricas, por que criar novas? índices resetam entre colunas, dá pra fazer
contínuos? índice é só uma referência incremental — depois de definido pode ser qualquer coisa que
não conflite com os dados". **Pré-requisito conceitual do [H-GDICT-01](roadmap-hipoteses.md)** (dict
global): resolver a representação de referência → o cross-dict sai naturalmente. Cross-links no fim.

## Contexto — o que o TCF já faz (verificado no encoder, 2026-06-19)

- **A referência por índice já existe**: `^N` = índice 1-based do N-ésimo valor distinto (first-seen).
  Verificado: `["A","B","A","C","A","B"]` → `A / B / ^1 / C / ^1 / ^2` (`^1`=A, `^2`=B). **É um dict.**
- **Há DOIS sistemas paralelos de referência** (a redundância que o owner notou):
  - **tcf-mode `^N`**: inline, **dígitos decimais**, **per-column**, exige **escape de dígito do dado**.
    Verificado: `["111","222",...]` → `\111` (escapado); `"ab12"` → `ab\12`. O escape é o custo da colisão.
  - **V2-B `@dict`**: tabela de únicos separada + stream **base-94** (sem escape, porque é região
    separada), **per-column**.
- **Os índices RESETAM por coluna** (cada coluna é encodada independente; 2 colunas com os mesmos
  valores guardam a tabela duas vezes — verificado no exemplo SIM/NÃO).

## As 4 sub-decisões de QUALQUER referência (o espaço de design)

| # | decisão | hoje (tcf / V2-B) | a explorar |
|---|---|---|---|
| 1 | **marcador** (o que diz "isto é ref") | `^` (tcf) / posição no stream (V2-B) | amortizar / eliminar |
| 2 | **valor** (o índice) | decimal (tcf) / base-94 (V2-B) | largura mínima, global |
| 3 | **escopo** | per-column (ambos) | **global/contínuo** |
| 4 | **conflito com o dado** | dígito escapa `\` (tcf) / separação (V2-B) | **alfabeto livre-de-conflito** |

## Catálogo de hipóteses (H-REF)

**H-REF-01 — Unificar as duas referências (reusar, não recriar).**
`^N` (tcf) e o stream V2-B fazem a MESMA coisa (índice→valor). Investigar **um só** mecanismo: o
V2-B reusar os atom-IDs do HCC em vez de construir tabela+stream próprios (ou o inverso). Base p/ tudo
abaixo. *Ganho:* menos formato a manter; *risco:* mexer no core dos dois caminhos.

**H-REF-02 — Índices globais/contínuos (escopo do blob, não da coluna).**
Atom-IDs **contínuos** no blob inteiro → mesmo valor em colunas diferentes = **mesmo ID** → habilita
o dedup cross-column ([H-GDICT-01](roadmap-hipoteses.md)). *Trade:* espaço de ID maior (índice mais
largo) vs dedup da tabela. *Medir:* o net por **grau de compartilhamento** entre colunas.

**H-REF-03 — Alfabeto de referência livre-de-conflito, automático (escape-free).**
A dor verificada: dígito no dado escapa (`111`→`\111`). **Pré-pass** varre o dado → acha bytes/chars
**ausentes** → usa-os como tokens de referência → **zero escape**. É literalmente o "o índice pode ser
qualquer coisa que não conflita". *Custo:* declarar o alfabeto/mapa no header (§3-bis "chave de
decifração" — tem que viajar junto). *Ganho:* elimina escapes em dado numérico/digit-heavy. (O V2-B já
evita colisão por **separação**; isto traz o benefício pro **inline** do tcf.) **Conexão forte com
H-INTRA** (lá o escape "come" o ganho da repetição intra-valor).

**H-REF-04 — Modulação de modo (string ↔ índice), marcador amortizado.**
Em vez de marcar **cada** ref, um marcador de **MODO**: entra em "modo-referência" (os tokens
seguintes são índices, sem marcador por token) e volta a "modo-literal" quando preciso — estilo
shift-in/shift-out. Amortiza o custo do marcador em **runs densos de refs**. *Medir:* a densidade de
refs compensa o custo das trocas de modo? *Prior art:* ISO-2022 / UTF-7 (shift codes).

**H-REF-05 — Índice de largura mínima / curto pros frequentes.**
O índice escala com a cardinalidade (V2-B já faz base-94 width). Levar adiante: width mínima +
(opcional) **códigos curtos pros atoms mais frequentes**. **CUIDADO**: isso encosta em entropy-coding
e tende a **sumir sob brotli** — só com gate explícito; provavelmente o de menor prioridade.

> **Update 2026-07-07** (owner pediu pesquisa de prior-art antes de consolidar "tipos como specs"): o
> caveat acima (qualitativo, sem números na formulação original) foi **testado empiricamente** na família
> `bN` (largura de bits pura, não base-94) — ver [`tipos-como-specs.md`](tipos-como-specs.md) e
> [H-TYPE-02](roadmap-hipoteses.md). Resultado: o caveat **se confirma** — ganho pré-brotli de 2×-8× cai
> pra 1.01×-1.33× sob brotli q11 (4 colunas reais, 2 fontes). Status: `confirmada-empirica COM RESSALVA`
> (evidência = só 4 colunas/2 fontes, não o corpus completo — mesma ressalva de N<5 do H-TYPE-02).
> `confianca: Baixa` (evidência ainda estreita; alinhada ao mesmo patamar de H-TYPE-02, que compartilha os
> dados-fonte). Continua "de menor prioridade" — o gate reprovou, não há motivo pra subir prioridade.

## A primitiva unificada — referência por índice (consolidação 2026-07-08, Cluster 1 do audit)

> Origem: [audit de primitivas](primitivas-consolidacao-audit.md) — o owner notou que mecanismos com nomes
> diferentes fazem coisas parecidas. Este é o cluster maior. **Todos os itens abaixo são a MESMA primitiva:
> "guardar cada valor distinto UMA vez + referenciar por índice."** O que muda são 4 eixos ortogonais.
> Entrada canônica curta: [`docs/vocabulary.md`](../../../../docs/vocabulary.md) §Primitiva.

| instância | granularidade | escopo | radix | lugar | estado |
|---|---|---|---|---|---|
| refs OBAT + ref atômico/virtual HCC | token/afixo (`fe1`=`fe`+ref) | intra-coluna | decimal inline | body | welded (núcleo) |
| `^N` line-ref | valor/linha inteiro | per-coluna (reseta) | decimal inline + escape `\<digits>` | body | welded |
| ref-stream `*N\|^k` | corrente de `^N` em RLE | per-coluna | decimal em RLE | body | welded |
| `@dict` (V2-B) | coluna categórica | per-coluna | base-94 (sem escape, região separada) | tabela no body | welded (ADR-0025) |
| `&<G>` cross-dict (H-GDICT B2) | grupo de colunas | **cross-coluna** | base-94, namespace/grupo | header | protótipo (gate geral reprovado) |
| bN `b/b2/b4/b8` (H-TYPE-02) | coluna low-card | per-coluna | **w bits** packed | body binário (V2-L) | research (terminal-only) |

**Os 4 eixos**: granularidade (token → linha → coluna → grupo) · escopo (intra-coluna, reseta ↔
cross-coluna) · radix (decimal-inline-com-escape · base-94-sem-escape · w-bits-packed) · lugar (inline no
body · tabela separada · header · body binário V2-L).

**Consequências de design (medidas na sessão 2026-07-06/08)**:
1. **bN é irmão bit-packed do `@dict`** — mesma informação (domínio+índices), radix mais denso. Por isso o
   brotli iguala os dois (gate D3: 8.8% terminal → 1.7% pós-brotli): o entropy-coder geral acha a
   redundância que sobra em qualquer radix textual.
2. **Os modos por-coluna competem no MESMO `min()`** (`tcf/raw/dict/split[/bN]`, `multi/core.py:177-197`)
   — são instâncias da primitiva disputando a mesma coluna, não features independentes.
3. **O ref-stream `*N|^k` já É a corrente de índices** — o Formato A do bN só re-empacota o que o HCC já
   produz (não re-deriva).
4. **O EnumSpec no-go** ([specs-capacity-map](specs-capacity-map.md)) é o mesmo fato por outro ângulo: o
   M10 (dedup + `^N` + seq-RLE) **já é um encoder enumerated implícito** — daí encoder enum explícito
   perder no geral (−6.52%) e bN só ganhar terminal.
5. **Regra anti-drift**: hipótese nova de "referência/dicionário" se posiciona nesses 4 eixos ANTES de
   ganhar nome novo (evita o padrão bN-redescobre-dict).

## O payoff — por que isto faz o GDICT sair melhor

O owner: "se resolvermos isso, o cross dict pode sair melhor." Correto:
**H-REF-02 (global) + H-REF-03/04 (referência limpa) ⇒ H-GDICT deixa de ser um mecanismo novo** e vira
consequência: índices globais + refs sem escape/sem marcador-por-token = **dicionário global no header
de graça**. A ordem natural é: resolver a referência primeiro, o cross-dict é o corolário.

## Caveats duros (guardião — não repetir os fechamentos anteriores)

- **Overlap com o existente**: `^N` JÁ é um dict-index; seq-RLE JÁ pega sequências aritméticas. Toda
  H-REF tem que medir o **INCREMENTO sobre o mecanismo atual** (anti-incidente 2026-05-21), não o
  ganho absoluto. Várias podem ser subsumidas pelo que o OBAT/HCC já faz.
- **Brotli**: esquemas textuais espertos de referência tendem a **sumir sob compressor a jusante**
  (lição V2-RLE / number-nature / staged-brotli). Testar **textual-puro E sob brotli**. **Porém** — o
  payoff do GDICT/global tem componente **ESTRUTURAL** (dedup cross-column + dict no header → leitura
  única pro **lazy**), que **não é só bytes**: pode valer pela **latência/query** mesmo se os bytes
  empatarem sob brotli. Esse é o argumento mais forte da família (vs V2-RLE, que era só bytes).
- **Format change**: tudo aqui é `#TCF.8` + GATE real-world + re-pin. Caracterizar em **lab read-only**
  antes de qualquer weld. `src/tcf` só com aprovação.
- **Prior art** (não reinventar): alfabeto livre-de-conflito = *escape elision*; modulação = *shift
  codes*; dict global = *cross-column dictionary* (Parquet/colunar). Adaptar ao espaço textual do TCF.

## Ordem de estudo sugerida (barato → caro)

1. **H-REF-03** isolado (lab read-only): medir o ganho de **eliminar escapes** em colunas digit-heavy
   reais — barato e mede uma dor concreta. Liga a H-INTRA.
2. **H-REF-02 + H-GDICT** juntos: medir o **dedup cross-column** em tabelas com colunas que
   compartilham valores (enums, UF, códigos, SIM/NÃO) — textual-puro **e** sob brotli **e** o ganho de
   latência no lazy.
3. **H-REF-04** (modulação): só se 1/2 mostrarem que o marcador/escape é o **custo dominante**.
4. **H-REF-01 / H-REF-05**: consequências de desenho, depois de 1-3.

> Tudo é **plano pra estudar**. Nada caracterizado, nada weldado, `src/tcf` intocado.

## Referências

- **Payoff**: [H-GDICT-01 (dict global/cross-column)](roadmap-hipoteses.md) (Pacote 11-ter).
- **Famílias vizinhas**: [estudo RLE × DICT](rle-familia-estudo.md); H-INTRA (intra-valor,
  [Pacote 11](roadmap-hipoteses.md#pacote-11)); V2-RLE-STREAM
  ([lab](../old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md)).
- **Mecanismo atual**: [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md),
  [ADR-0016 seq-RLE](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md),
  [ADR-0025 V2-B](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md).
- **Formato futuro**: [futuras-otimizacoes-formato.md](futuras-otimizacoes-formato.md) (O-FMT-06/07
  cross-column dict). Tier: [ROADMAP](../../../../ROADMAP.md).
