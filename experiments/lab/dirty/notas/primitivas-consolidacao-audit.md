# TCF — primitivas com nomes diferentes que fazem coisas parecidas (audit p/ revisar) [reference]

**Data**: 2026-07-08. **Observação do owner**: "muito conceito que, apesar de nomes diferentes, as
primitivas do TCF parecem fazer coisas parecidas." **Por que acontece**: o vocabulário cresceu **por
feature** (cada ADR/hipótese batizou seu mecanismo), não **por primitiva** — então há sinônimos espalhados
(`vocabulary.md` define `^N` e `@dict` em seções separadas sem notar que são o mesmo dict+índice). Esta
sessão bateu nisso repetidamente (bN=irmão do dict; hex=base-94; EnumSpec-no-go=bN). **Escopo do audit**:
consolidação **CONCEITUAL** (vocabulary.md / notas unificadas), **NÃO** renomear código (`src/tcf` intocado).

## Clusters (nomes diferentes → primitiva comum) — priorizados

### ⭐ Cluster 1 — DICIONÁRIO / ÍNDICE / REFERÊNCIA (o maior, mais claro)
Todos = **"guardar valores distintos uma vez + referenciar por índice"**. Diferem em **escopo · radix · lugar**.

| nome | escopo | radix do índice | lugar | fonte |
|---|---|---|---|---|
| `^N` (line-ref / whole-value) | per-coluna | decimal (inline, exige escape) | no body | HCC |
| `@dict` (V2-B) | per-coluna | base-94 | tabela separada | ADR-0025 |
| `&<G>` (cross-dict / H-GDICT) | cross-coluna | base-94 | header | 2026-06 |
| **bN** (bit-packing) | per-coluna | **bits** | body (V2-L) | H-TYPE-02 |
| ref-stream `*N|^k` | per-coluna | — (é a corrente de índices) | body | HCC |

**Já notado** (parcial): [`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) H-REF — "`^N` JÁ é
um dict-index; há DOIS sistemas paralelos de referência". **Valor de consolidar**: ALTO — é onde a sessão
mais se confundiu. Uma "referência unificada" (uma primitiva `dict(escopo, radix, lugar)` de que `^N`/`@`/
`&`/bN são instâncias) esclareceria o design e o `min()`. **Casa**: `vocabulary.md` §referência + uma nota-mãe.

> ✅ **FEITO (2026-07-08)**: entrada canônica em [`docs/vocabulary.md`](../../../../docs/vocabulary.md)
> §"Primitiva: referencia por indice" (tabela de instâncias + 4 consequências) + seção detalhada
> "A primitiva unificada" em [`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md) (4 eixos:
> granularidade/escopo/radix/lugar + 5 consequências de design + regra anti-drift: hipótese nova de
> referência se posiciona nos eixos ANTES de ganhar nome).

### Cluster 2 — RLE / RUN / REPETIÇÃO
Todos = **"N ocorrências de um padrão, contadas em vez de expandidas"**. Diferem em **o que repete**.

| nome | o que repete |
|---|---|
| `*N\|line` | linha idêntica adjacente |
| `*N+delta\|` (seq-RLE) | linha near-identical (delta nos escape-digits) |
| V2-RLE-STREAM | run dentro do stream de índices do V2-B (REFUTADO geral) |
| RLE intra-valor (H-INTRA) | run dentro de UM valor (adiado) |

**Já consolidado** (parcial): [`rle-familia-estudo.md`](rle-familia-estudo.md). **Valor**: MÉDIO — a família
já tem nota; falta amarrar no vocabulary.

### Cluster 3 — SPEC / NATURE / TIPO
Todos = **"forma conhecida que permite pré-tx/compressão/aceleração, regida por round-trip"**.
- **natures** (CPF/CNPJ/IP, TemplatedCheckedSpec) · **tipos** (int/float/bool/enum) · **EnumSpec** (no-go).
**Já consolidado** (esta sessão): [`tipos-como-specs.md`](tipos-como-specs.md) + [`specs-capacity-map.md`](specs-capacity-map.md)
(espectro único). **Valor**: MÉDIO-ALTO — o espectro está descrito, mas o vocabulário ainda fragmenta
"nature" vs "tipo" vs "spec". Amarrar os três termos como UM.

### Cluster 4 — OMITIR / DEDUZIR / DECLARAR / CONVENÇÃO / AUTORIDADE / SEMI-IMPLÍCITO
Todos = **"o que é carregado vs deduzido do que sobra vs declarado fora"**.
- **omit-contract** (T-FMT-OMIT-OR-DECLARE, 4 categorias) · **hex-default** (=convenção-default) ·
  **autoridade** (mandatório/natural/deduzido) · **versionamento semi-implícito** (ADR-0029, 3 camadas:
  órfão/header/chamada) · **inferências** do checklist (C2 deduz / C4 by-choice).
**Valor**: ALTO — o mesmo princípio aparece com 5 nomes. O omit-contract (pré-1.0) É a generalização; os
outros são instâncias. Consolidar sob ele.

### Cluster 5 — SPLIT / DECOMPOSIÇÃO / FATORAÇÃO / HIERARQUIA
Todos = **"quebrar um valor/tabela em partes que comprimem/reconstroem melhor"**.
- `%split` (V2-C, separador de campo) · `schema.py` (decompõe tabela) · cross-dict (fatora valores
  compartilhados) · TCF.8H hierárquico (árvore) · factorized DBs (prior-art).
**Valor**: MÉDIO — níveis diferentes (valor/campo/coluna/tabela/documento); vale um mapa de "em que nível
cada um decompõe".

### Cluster 6 — MARCADOR / PREFIXO / DISCRIMINADOR / FLAG
Todos = **"1 char no header que roteia um fluxo"**. **Já consolidado hoje**:
[`tcf8-header-char-registry.md`](tcf8-header-char-registry.md). **Valor**: FEITO (só falta promover a canônico).

## Recomendação (por onde revisar)

1. **Cluster 1 (dict/índice/referência)** — maior confusão, maior valor. Escrever uma **referência
   unificada**: a primitiva é *dicionário indexado*; `^N`/`@`/`&`/bN são instâncias por (escopo, radix,
   lugar). Isso desambigua o `min()` e o roadmap H-REF/H-GDICT/H-TYPE-02.
2. **Cluster 4 (omitir/deduzir/declarar)** — 5 nomes p/ um princípio; consolidar sob o omit-contract.
3. **Cluster 3 (spec/nature/tipo)** — amarrar os 3 termos no vocabulary como UM espectro.
4. Clusters 2/5/6 já têm nota-família/registry; só falta **amarrar no `vocabulary.md`** (a casa canônica).

**Método** (Strata): a consolidação é no `vocabulary.md` + notas-mãe (apontar, não renomear); **zero
`src/tcf`** (os nomes de código/formato ficam — é o VOCABULÁRIO conceitual que unifica). Cada cluster vira
uma entrada "primitiva X, instâncias {a,b,c} por eixos {…}".

## Cross-links
- Vocabulário canônico: [`docs/vocabulary.md`](../../../../docs/vocabulary.md) (casa da consolidação).
- Notas-família já existentes: [`dict-referencia-hipoteses.md`](dict-referencia-hipoteses.md),
  [`rle-familia-estudo.md`](rle-familia-estudo.md), [`specs-capacity-map.md`](specs-capacity-map.md),
  [`tipos-como-specs.md`](tipos-como-specs.md), [`tcf8-header-char-registry.md`](tcf8-header-char-registry.md).
