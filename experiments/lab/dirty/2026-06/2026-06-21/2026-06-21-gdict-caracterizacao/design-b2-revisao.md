# B2 — revisão adversarial do design (6 lentes × verify cético) [probatório]

**Data**: 2026-06-27. **Método**: workflow multi-lente (rt-correctness, byte-model,
format-integration, lazy-parallel, gate-methodology, alignment-adr) → 35 achados → verify cético
por achado. **Resultado: 24 confirmados (0 blocker, 2 major, 17 minor, 5 nit) / 11 refutados.**

> **✅ A-D APLICADAS** (2026-06-27) no [design-b2.md](design-b2.md) revisado: (A) group-dict virou
> prelúdio length-prefixed do corpo + modo de coluna `&<G>` stream-only; (B) dobradiça com
> `bytes(tab_G)` medido + custo de header + prosa da largura corrigida; (C) "paralelizam"→"decodáveis
> independentemente" + cache keyed-por-grupo; (D) gate N≥5 + overfit declarado + brotli-controle.
Revê [design-b2.md](design-b2.md). Conclusão: o **núcleo é sólido**; os defeitos concentram-se no
**wire-format framing** e na **honestidade de gate/prosa** — tudo doc-level (zero src/tcf).

## O núcleo SOBREVIVEU (ataques refutados que dão confiança)
- **Particionamento custo-modelado**: greedy chain-group "perde 3+col" → REFUTADO (não-issue).
- **Reuso do V2-B**: "slot V2-B não reusável" → REFUTADO (reuso ok).
- **Discriminador #TCF.8**: "`&` colide com o 1-char ADR-0029" → REFUTADO (group-dict NÃO é tipo
  novo; vive dentro do #TCF.8M).
- **`&` no stream base-94**: "colide com byte 0x26 do stream" → REFUTADO (prelúdio é length-framed,
  não escaneado).
- **OpenFlights sub-15% "trave movida"** → REFUTADO (porta estrutural lazy é critério legítimo).
- **H-REF-02 como futuro** → REFUTADO (posicionamento correto, sem dívida).

## (A) CORREÇÃO ESTRUTURAL — wire-format framing [2 major + cluster]
O erro real do design: o esboço da §2 põe `&G=tab` como **linhas de header** entre shebang e corpo.
**Mas #TCF.8M não tem header multi-linha** — o corpo começa logo após a 1ª `\n` (core.py:300-304;
view.py:70-72). E `tab_grupo` (saída de `_encode_column`) **contém `\n`/`=`/`,`** → framing por
delimitador é impossível.
- `gd-tcf8m-no-header-lines` (major), + `tcf8m-header-sem-slot`, `format-gdict-header-linhas`,
  `v8m-inline-meta-no-header-lines`, `gd-tab-contem-lf-virgula-igual`.
- **`gdict-col-self-contained-broken` (major)**: `_decode_v2b`/`_dict_parts` assumem a tabela DENTRO
  do body da coluna. Group-dict quebra isso → **coluna agrupada é um SLOT NOVO (stream-only)**, não
  "V2-B inalterado" (confirmado; `grouped-slot-difere-de-v2b` reforça).
- `meta-slot-size-vs-groupref-int-parse` + `gd-amp-nao-reservado`: o slot de size é `int()`; `&G`
  não cabe ali; `&` precisa ser reservado contra nomes/mode-prefix.

**→ Correção (toda derivável do próprio V2-B):**
1. Group-dicts viram um **PRELÚDIO length-prefixed no INÍCIO DO CORPO** (não header lines):
   `<n_grupos>\n` + N×(`<ntab>\n<tab_bytes>`), fronteira por byte-count (igual ao slot V2-B). O
   `cursor` avança além do prelúdio antes das colunas. É exatamente o "prelúdio serial" que o design
   já cita (só estava desenhado errado).
2. **Coluna agrupada = slot stream-only** distinto: marcador próprio (não no slot int-size), width
   derivado do K do grupo já carregado no prelúdio. Gramática do token inclui `:spec` (ordem fixa).

## (B) REFINAR A DOBRADIÇA [3 minor]
- `gdict-formula-header-blind`: a fórmula é header-cega (não conta o marcador `&G`/coluna nem o
  framing do prelúdio). **Desprezível no regime-alvo same-domain** (~32B vs 152K no SNAP); só importa
  no nicho flag/survey (que B2 não banca). **Fix**: somar o termo de header ao custo antes do greedy
  poolar grupos flag marginais.
- `gdict-namespace-width-not-bound`: a prosa "largura bound por grupo, nunca estoura" é forte demais
  — o **termo de custo** é o guard, não o Jaccard (união same-domain PODE cruzar 94/8836; o greedy
  rejeita via custo). O algoritmo já está certo; **é a prosa de L19/L44-45 que mente**. Fix: reescrever
  + caso de teste (união cruza bucket → não pool).
- `gdict-dedup-nonlinear-hcc`: dedup é não-linear sob HCC (range colapsa). **Fix**: B3 computa
  `bytes(tab_G)` encodando a união de verdade (`_encode_column`), nunca estimando por Jaccard.

## (C) HONESTIDADE LAZY/PARALELISMO [4 minor + 1 nit]
- `no-parallel-decode-substrate`: **não existe decode paralelo** — paralelismo é só no encode.
  **Fix**: rebaixar "colunas paralelizam" → "colunas permanecem decodáveis independentemente APÓS o
  prelúdio serial".
- `gdict-parse-no-header-section` + `touched-dedup-cross-col-shared-table`: o ganho lazy "dict 1×"
  exige um `self._group_dict` keyed por GRUPO (não por coluna), populado 1× num estágio de
  prelúdio-parse no view.py (trabalho de B4). Sem isso o "decodes C→1" não materializa.
- `single-col-degrade-accounting` + `gdict-single-col-downside-nonzero` (nit): single-col em grupo
  materializa a tabela do grupo (∝ (1−Jaccard)·|união|; 0B no SNAP, +64-88B no OpenFlights).

## (D) HONESTIDADE DE GATE [3 minor; 2 ataques duros REFUTADOS]
- `gate-n2-vs-n5-anti-incidente`: "≥2 reais" contradiz o checklist do projeto (**N≥5 fontes**).
  **Fix**: ou alinhar a ≥5 fontes same-domain (rotas, edge-list, de/para, FK-repetida, co-ocorrência),
  ou declarar explicitamente um gate reduzido com justificativa.
- `ext-validity-overfit-snap-nao-declarado`: o único ≥15% é **um grafo**. **Fix**: declarar que a
  feature ativa em ZERO canônicos (overlap intra-blob ~0) e que o ganho é frágil em N grande
  (OpenFlights cai pra 4-7%).
- `brotli-fora-do-gate-sinal-ruim-ignorado`: tirar brotli do gate é legítimo (lazy), mas não pode
  **silenciar** o sinal. **Fix**: registrar brotli como caveat qualitativo (medir same-domain K-grande
  sob brotli como sinal antes do weld).

## Veredito
Nenhum blocker. O **mecanismo** (particionamento, dobradiça, regime same-domain, reuso V2-B,
posicionamento H-REF) está validado adversarialmente. Os 24 confirmados são **doc-level**: corrigir o
wire-format framing (A — group-dict é prelúdio-de-corpo, coluna agrupada é slot stream-only), refinar
3 pontos da dobradiça (B), e honestizar lazy/gate (C/D). **Nenhum exige redesenho** — exigem revisão
de design-b2.md antes do protótipo. Recomendação: aplicar A-D no design, depois protótipo read-only.
