# Famílias RLE e DICT no TCF — estudo consolidado [estudo]

**Data**: 2026-06-19 · estudo (consolida medições + perguntas abertas; **não decide nada**).
Origem: owner — RLE intra-valor, RLE-STREAM e, na revisão, o **dicionário global** (a ideia que se
perdeu no caminho). **Entrar por aqui** quando o assunto for "comprimir repetição / reaproveitar
valores". Tudo cross-linkado (diretiva [[feedback-sempre-cross-reference]]).

## 1. Escopo — DOIS eixos que se confundem (RLE × DICT)

O ponto que gerou confusão: há **dois eixos** intertwined, não um. Separá-los é o objetivo.

**Eixo RLE** ("comprimir REPETIÇÃO adjacente"):
- **(A) RLE de linha** — `*N|` / `*N+delta|`. **Welded** (tcf mode).
- **(B) V2-RLE-STREAM** — RLE no stream de índices do V2-B. **Caracterizado → CLOSED-geral** (2026-06-19).
- **(C) RLE intra-valor** (H-INTRA / O-FMT-17) — repetição DENTRO de um valor. **Adiado**.

**Eixo DICT** ("referenciar VALORES repetidos por índice") — onde a ideia do owner realmente vive:
- **(D1) dict IMPLÍCITO** `^N` — a 1ª ocorrência define o atom, repetições viram índice `^N`. **Já
  existe** em tcf mode (single E multi). *(Verificado: numa coluna só, `^1`=ATIVA, `^2`=BAIXADA... =
  um dicionário. Correção 2026-06-19: single-col TEM dict, ao contrário do que a v1 deste doc dizia.)*
- **(D2) dict EXPLÍCITO per-column** `@` (V2-B) — tabela de únicos + stream packed. **Welded**, multi-col.
- **(D3) dict GLOBAL/cross-column no header** — 1 tabela compartilhada entre colunas. **= a ideia do
  owner** ([H-GDICT-01](roadmap-hipoteses.md), = O-FMT-06/07). **NÃO testado.**

> **A confusão desfeita**: V2-RLE-STREAM (B, eixo RLE) ≠ dict global (D3, eixo DICT). O que foi testado
> e fechado foi B (RLE no stream). A ideia do owner é D3 (compartilhar o dict). São coisas diferentes.

Detalhe do eixo DICT na **seção 10**.

## 2. A família em 3 níveis

| # | mecanismo | dimensão (o que repete) | status | onde vive / doc |
|---|---|---|---|---|
| **A** | RLE de linha `*N|` + seq-RLE `*N+delta|` (e `^N` = valor inteiro repetido) | **interlinha**: linha/valor inteiro adjacente | **WELDED** (dispositivo) | `src/tcf` (OBAT `core/online.py` + HCC `composicional/`); [ADR-0016](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md), [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md) |
| **B** | V2-RLE-STREAM — RLE no stream de índices do V2-B (`@dict`) | **intra-stream**: índice inteiro adjacente | **caracterizado** → CLOSED-geral / nicho aberto (probatório) | lab [result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md); registry [Pacote 11-bis](roadmap-hipoteses.md); depende de [ADR-0025 V2-B](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) |
| **C** | RLE intra-valor (H-INTRA-01/02/03 / O-FMT-17) | **intra-valor**: substring dentro de uma célula | **ADIADO** (aberta, alvo 0.8) | registry [Pacote 11](roadmap-hipoteses.md#pacote-11); [O-FMT-17](futuras-otimizacoes-formato.md) |

> **Coluna única vs multi-coluna** (a distinção que confunde): **A** (`*N|`) atua em **qualquer**
> coluna, inclusive single-col (`encode(list)`) — ordenar uma coluna só já dá RLE de graça via `*N|`.
> **B** (stream) **só existe em multi-coluna** e **só** quando a coluna cai em `@dict` (o `min()` a
> escolheu). Single-col **nunca** tem stream. Por isso A e B **nunca coexistem** na mesma coluna: o
> fallback escolhe um modo. Exemplo trabalhado dos dois caminhos: [seção "Exemplo visual" do lab](../2026-06-19-v2rle-stream-caracterizacao/result.md).

## 3. Fatos medidos — V2-RLE-STREAM (B), uso geral

> **Para a intuição visual** (se os dados fossem assim → o que B tentava → por que não deu), ver a
> **seção "Exemplo visual"** em [result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md)
> (`*N|` × stream nos 16 itens, coluna-única × multi-coluna).

Fonte: [lab result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md) (7 datasets reais, o teste
mede — não copiar números soltos). Resumo:
- **+1,19% weighted**, **0/7 datasets ≥15%** (melhor caso real: adult 7,34%). Upper bound `sort_by`
  ~13% (relationship).
- **−1,39% sob brotli** (agregado): a economia textual **some e inverte** — o brotli já captura os
  runs; os marcadores RLE viram overhead.
- → **CLOSED-INSUFFICIENT-GAIN** pro uso geral (tabelas largas / com compressor a jusante).

## 4. Fatos medidos — V2-RLE-STREAM (B), nicho "texto curto / formulário"

Fonte: [result_forms.txt](../2026-06-19-v2rle-stream-caracterizacao/result_forms.txt) (coluna isolada =
payload narrow). Em **ordem natural**, payload dominado por uma coluna low-card de texto:
- situacao (K=5, **skewed**) **+54,9%**; workclass (K=9) **+21,6%**; mesorregiao +5,5%; marital +5,3%;
  education (uniforme) +1,4%. **Todos morrem sob brotli** (−2,7% a −11,0%).
- **Nicho real**: payload minúsculo + low-card texto curto + **skewed** + ordem natural + **textual-puro**
  (sem compressor a jusante). 2 reais ≥15% *nesse nicho*. Alinha com a diretriz "transmissão minúscula".

## 5. Achado-chave — o overlap A↔B (por que B é quase um resíduo de A)

No lab, os casos **clusterizados / `sort_by`** **FLIPARAM a coluna pro modo `tcf`**: o `*N|` (A)
captura os runs longos e **vence o fallback** `min(tcf, raw, @dict, %split)` → o dict (e portanto o
stream) **nem é escolhido**. Consequência:
- **A e B competem pelo mesmo fenômeno** (repetição adjacente de valor inteiro). A já ganha onde os
  runs são **longos**.
- **B só tem espaço no regime de runs CURTOS** (ordem natural) **+ coluna skewed** — onde o dict vence
  o fallback e deixa o stream cru. Aí B captura algo que A não pega (porque A perdeu o fallback).
- Por isso B, na prática, é um **resíduo** de A: vale só na faixa estreita (curto+skewed+textual-puro).

## 6. Overlap B↔C (intra-valor) e a regra de layout

C (intra-valor) é **ortogonal em dimensão** (dentro do valor, não entre linhas/índices), mas
tematicamente "ataca repetição". O fio que liga os três:

> **A repetição capturada depende do LAYOUT**: runs longos → **A** (`*N|`); runs curtos+skewed →
> **B** (dict-stream); substring dentro do valor → **C** (intra-valor).

[H-INTRA-03](roadmap-hipoteses.md#pacote-11) já exige medir o **INCREMENTO** de C sobre
nature + split + dedup `^N` (anti-incidente 2026-05-21). O lab de B reforça: **B e C podem se
subsumir** — convém **caracterizar C antes de reabrir B** (evita retrabalho).

## 7. Custo de weld (comum a B e C)

Qualquer um dos dois, se avançar, é **format change** (grupo `#TCF.8`, ciclo 0.8 por
[ADR-0024](../../../../docs/adr/0024-pre-1.0-versioning-git-as-compat.md)) + **GATE real-world**
obrigatório + **re-pin** de baselines + complexidade permanente no decoder/lazy. Anti-incidente
2026-05-21 aplicável: ganho em sintético / coluna isolada **não generaliza** pra tabela/real-world.

## 8. Perguntas abertas (pro owner estudar)

1. O nicho **"transmissão minúscula textual-pura"** (low-card skewed, ordem natural, sem compressor a
   jusante) é prioritário o bastante pra justificar `#TCF.8` por B? (situacao +55% é real, mas estreito.)
2. **Caracterizar C (intra-valor) primeiro?** O overlap sugere que C pode subsumir B (ou vice-versa).
3. Ambos **morrem sob brotli** — o caso de uso textual-puro-sem-compressor existe de fato no roadmap,
   ou o alvo real é sempre TCF+compressor (onde A já basta)?
4. Se algum avançar: qual **engine** (OBAT vs HCC) e como medir o **INCREMENTO net** sobre A + nature +
   split + dedup `^N`?

## 9. Eixo DICT — onde a ideia do owner (dict global) realmente vive

Os índices que comprimem repetição de VALOR já existem de graça. O eixo DICT tem 3 níveis:

| nível | o que é | onde / status |
|---|---|---|
| **D1 implícito** `^N` | 1ª ocorrência define o atom; repetição vira índice `^N` | tcf mode (single+multi) — **já existe** |
| **D2 explícito** `@` (V2-B) | tabela de únicos no topo + stream packed; **por coluna** | multi-col — **welded** (ADR-0025) |
| **D3 GLOBAL** no header | **1 tabela compartilhada** entre colunas (dedupe cross-column) | **H-GDICT-01** — **não testado** |

**Por que D3 (a ideia do owner)**: hoje cada coluna `@dict` guarda **sua própria** tabela (verificado:
2 colunas SIM/NÃO guardam `[SIM,NÃO]` duas vezes — [exemplo real](../2026-06-19-v2rle-stream-caracterizacao/result.md)).
D3 põe **uma** tabela no header e todas as colunas referenciam por índice global → paga a tabela 1×.
É o **"cross-column dict"** (O-FMT-06/07) e casa com o **lazy** (dict no header = leitura única).

**Perguntas abertas de D3** (pro owner): (a) quanto de compartilhamento de valores entre colunas
compensa? (colunas disjuntas pagam índice global mais largo sem dedupe → medir o **net** vs V2-B
per-column). (b) sinergia com o gadget lazy (header dict = manifest). (c) format change #TCF.8 + GATE.
Distinto de [H-CODEBOOK-01](roadmap-hipoteses.md) (dict **externo**/versionado; D3 é **interno** ao blob).

**Relação RLE × DICT**: o `^N` (D1) é o ponto onde os eixos se tocam — é um índice de dict (eixo DICT)
e um back-ref de repetição (eixo RLE). Mas as IDEIAS a estudar são separadas: B (RLE no stream, fechado),
C (RLE intra-valor, adiado), **D3 (dict global, a ideia viva do owner)**.

**Pré-requisito do D3 — a representação da referência**: D3 (dict global) depende de resolver COMO a
referência/índice é representada (global vs per-column; alfabeto livre-de-conflito; marcador
amortizado). Apanhado de hipóteses (H-REF-01..05) em
[`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) — o owner: "se resolvermos a
referência, o cross-dict sai melhor". Ordem sugerida lá: H-REF-03 (escape-free) → H-REF-02+H-GDICT → resto.

## 10. Referências

- Lab B: [result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md) +
  [result_forms.txt](../2026-06-19-v2rle-stream-caracterizacao/result_forms.txt) +
  scripts `analyze.py` / `analyze_forms.py`.
- Registry: [roadmap-hipoteses.md](roadmap-hipoteses.md) — Pacote 11-bis (B = H-V2RLE-01/02),
  [Pacote 11](roadmap-hipoteses.md#pacote-11) (C = H-INTRA-01/02/03).
- Formato futuro: [futuras-otimizacoes-formato.md](futuras-otimizacoes-formato.md) (O-FMT-17).
- ADRs: [0016 seq-RLE](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md) (A),
  [0025 V2-B](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) (base de B),
  [0026 split](../../../../docs/adr/0026-structural-split-weld.md) (vizinho).
- Specs: [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md),
  [TCF-format](../../../../docs/algorithms/TCF-format.md). Tier: [ROADMAP](../../../../ROADMAP.md).
