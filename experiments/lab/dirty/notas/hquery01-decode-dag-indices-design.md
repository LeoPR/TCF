# H-QUERY-01 — decode como DAG, decode parametrizado, encode-para-lazy, índices escondidos [design]

**Data**: 2026-06-17 · design (NÃO implementa, **zero `src/tcf`**). Origem: owner — expandir o
lazy: "que caminho diferente no grafo de decode dá o mínimo pra uma agregação? dá pra orientar o
encode pra lazy? índices escondidos pra acelerar grouping?". Fonte: workflow `_wf_hquery01_*`
(5 lentes ancoradas no código + estado-da-arte; task we9rg45qz).

## 1. Decode como DAG (o grafo real)

O decode multi-col é um **DAG de 5 nós seriais com 4 ramos paralelos mutuamente exclusivos por
coluna**:

```
NO1 parse header (multi.py _decode_multi)      O(header)  — nome/modo/size por coluna
 └→ NO2 fatiar corpo por POSIÇÃO de byte        O(header)  — body bruto por coluna, SEM decodar
     └→ NO3 dispatch pelo marcador de modo  (! @ % tcf)
         └→ NO4 decode do corpo (função do modo)
             └→ NO5 materializar linhas (row-aligned por posição)
```

**As colunas são independentes** (nenhuma referencia outra; alinhamento é só posicional) → é isso
que dá **column-pruning de graça**. Dentro de uma coluna, o ramo decide se há **corte**:

| modo | sub-artefatos | corte pra agregação |
|---|---|---|
| `@` dict (V2-B) | tabela de K únicos + stream base-94 de N índices | **CORTE LIMPO**: count = `len(stream)//width`; group-tally = Counter sobre o stream (O(N·w), **sem expandir**); where = avalia predicado sobre os K únicos, marca posições no stream. **NO5 nunca é exigido.** |
| `!` raw | nenhum | só `nrows` estrutural (conta `\n`); qualquer agg/where força decode total |
| tcf (OBAT+HCC) | — | **SEM CORTE** — refs cruzam linhas, runs `*N|` não são contáveis sem expandir (verificado) |
| `%` split | sub-`#TCF.7` aninhado | separabilidade = a do **pior** sub-campo (se algum é tcf → fallback total) |

**Onde o `decode()` super-computa**: numa agregação sobre coluna `@dict`, ela **não precisa do NO5**
(materializar valores) — `count`/`group_count` vivem no NO3→stream. O NO5 só é exigido por
tcf/split/raw-agg. O grafo hoje é **implícito** na sequência `lazy.where(...).sum(...)`; torná-lo
**explícito** (um QueryPlan: nó por etapa, aresta por dependência) é puro tooling do gadget, **zero
formato**.

### Cortes mínimos por query (medido em online-retail/adult)
- **COUNT**: dict `O(K)` (só a tabela) / raw conta `\n` → **~0.2% do blob**.
- **GROUP-TALLY**: dict = tally do stream + decode da tabela, nunca expande os N → **~5%**.
- **AGG-FILTRADA** `sum(Quantity) where CustomerID=X`: filtro avalia K únicos + varre stream
  (retorna índices sem expandir) + `_floats` decoda **só** a coluna agregada nos índices →
  **~7.9%** (`CustomerID@dict` + `Quantity`). Filtro em coluna tcf/split = fallback (decode da
  coluna de filtro inteira).
- **CÉLULA isolada**: sem acesso random (row-aligned por posição, não offset) — caso raro; o uso
  real é `select(cols)` sobre índices.

## 2. Decode unificado (sem dois caminhos)

**Já existe UM conjunto de decoders**: `lazy._col` é mode-aware e **reusa** `_decode_column /
_decode_v2b / _decode_struct_split` do core — **não há descompressor duplicado**. O que falta é o
**pushdown** (projeção + predicado empurrados pra dentro).

- Por ramo: dict/raw/split-low-card aceitam pushdown limpo; **tcf NÃO** aceita sem graph-rewrite do
  HCC (refs inter-linha quebram saída parcial / single-pass — proibido por ADR-0002). Logo um decode
  parametrizado "puro" que nunca expande tcf é **impossível**; o atingível é *pushdown onde o modo
  permite, fallback total onde não*.
- **Forma recomendada (zero core)**: NÃO mudar a assinatura de `decode()` (mudança pública → GATE +
  ADR). Expor no gadget um super-método `LazyTCF.execute(projection=[...], where={col:(op,val)},
  agg=(op,col,by?))` que monta o QueryPlan, roteia cada coluna pro corte do seu modo e devolve saída
  parcial. Dá a **sensação de decode único parametrizado** (uma chamada, vários modos de extração),
  reusa 100% dos decoders core, zero-breaking. Unificar DENTRO do core fica adiado pra um eventual V3
  (redesign OBAT/HCC — o owner pode não querer).

## 3. Encode-para-lazy (com custo de compressão e classe)

| escolha | custo compressão | ganho lazy | classe |
|---|---|---|---|
| `fallback=True` (min por coluna) | **zero** (escolhe o menor; dict só entra quando vence) | põe low-card em `@dict` → habilita L3/L4 automático. **É o motor do lazy hoje.** | knob (já default-on) |
| `sort_by=key` | trade-off medido (adult `education` **−10%**; retail `CustomerID` **+2.3%**) | ativa L5: grupos viram runs contíguos → `agg_by` por slice | knob opt-in (não muda formato) |
| **`prefer_dict_cols=[...]`** (NOVO) | marginal (só quando tcf venceria por poucos bytes) | garante L4/L3 numa coluna de filtro conhecida em vez de cair em fallback | knob opt-in (novo kwarg; `@` já existe — só relaxa o gating de seleção) |
| blocagem/chunking | framing por bloco + perda de RLE/refs que cruzam limites (não medido) | pulo de blocos; ganho incremental incerto p/ datasets <100MB | **mudança de formato** (#TCF.8) — adiar |

Conceito-chave: **"design de lazy primeiro"** (escolher `@dict` numa coluna de filtro) vs "menor byte
isolado". É legítimo no vértice tríplice **se for opt-in** e o default lossless-puro não mudar.

## 4. Índices escondidos pra grouping — **derivável > sidecar > formato**

| técnica | onde vive | custo bytes | ganho query | explicável? |
|---|---|---|---|---|
| **min/max por coluna dict** (zone-map estilo Parquet/DuckDB) | **derivável on-the-fly** | **0 B** (reduce O(K) sobre a tabela já decodada, cacheável) | skip O(1) de coluna em predicado de range (`col>x` rejeita sem varrer) | sim (deriva dos únicos textuais) |
| **manifest/schema** (modos, card, nrows) | derivável (header parse já dá quase tudo) | ~0 B | planner escolhe corte sem tocar corpo | sim (JSON legível) |
| **offset-map de grupos** (só com `sort_by`; estilo ORC row-index) | derivável de `side_outputs.seq_rle_runs` (já capturado no encode) ou sidecar | 0 B derivado / ~100 B persistido | `agg_by(key)` sem decodar a coluna-chave inteira | sim (`{valor:(ini,count)}` reflete os runs `*N|`) |
| **offsets por valor único no stream** (dict page index) | sidecar `.tcfx` ou cache | ~K·2-5 chars / 0 B on-query | group-by vira lookup O(K) vs tally O(N·w) | sim (texto) |
| **bitmap/Roaring por valor dict** (estilo ORC/bloom) | sidecar / derivável | ~N/8 por valor; 1-2% p/ poucos valores quentes | `where(col=X)` salta varredura; AND = interseção de bitmaps | **menos** (denso) — preferir lista textual; bitmap só se N grande, sempre fora do blob |

**Sidecar `.tcfx`** = fronteira cinza: é gadget-tier (não toca o blob nem o magic), mas introduz um
artefato persistido. Opt-in, lido se existir, ignorado se ausente. Precisa **fingerprint do blob**
(consistência: detectar stale → fallback a derivar). Custo de bytes vive **fora** do `.tcf`.

## 5. Classificação (regra do owner: o que não toca o núcleo vem primeiro)

- **SÓ GADGET** (zero core/formato/bytes): QueryPlan/DAG explícito + `execute()` com pushdown;
  cortes mínimos (já L1/L3/L4/L5); índices **deriváveis on-the-fly** (min/max dict, manifest,
  offset-map via `seq_rle_runs`); cache em memória.
- **KNOB DE ENCODE OPT-IN** (sem mudar formato): `sort_by` (existe), `fallback` (existe),
  **`prefer_dict_cols`** (novo kwarg, custo marginal).
- **SIDECAR `.tcfx`** (fronteira cinza, gadget-tier mas persistido): offsets/bitmaps de colunas
  quentes; custo 2-5% em arquivo paralelo, **zero no `.tcf`**; gated por medição real-world.
- **EXIGE FORMATO NOVO** (#TCF.8, ADR + GATE + re-pin — **adiar**): blocagem/chunking; qualquer
  índice/footer in-blob (trailer Parquet-style); redesign OBAT/HCC pra tornar tcf separável.

## 6. Próximos experimentos (baratos, no gadget, em ordem)

- **E1** — QueryPlan explícito: dado `(projection, where, agg)`, lista os nós tocados e o corte por
  coluna **antes** de decodar; imprime o plano (auditoria). Formaliza o que já existe. Zero core.
- **E2** — `LazyTCF.execute(projection=, where=, agg=)`: orquestra E1, devolve saída parcial. A "cara"
  do decode unificado parametrizado, reusando `_col/_dict_parts/_dict_target_ids/_floats`.
  **RT obrigatório**: comparar com `decode()` completo + filtro manual.
- **E3** — índices deriváveis on-the-fly em memória: min/max por coluna dict + manifest. Medir
  overhead (O(K)) + skip de range-predicates. Zero bytes.
- **E4** — offset-map de grupos a partir de `side_outputs.seq_rle_runs`: provar `agg_by(key)` sem
  decodar a coluna-chave inteira. Comparar com L5 atual.
- **E5** — protótipo de **sidecar `.tcfx`** textual (JSON) com offsets-por-valor + bitmaps só p/
  colunas/valores quentes; medir overhead (alvo 2-5%) vs speedup em **adult + online-retail**
  (real-world). Decidir com números: persistir vs derivar.
- **E6** — bench `prefer_dict_cols=[col_filtro]` vs default: quantificar custo de compressão
  (marginal) e confirmar que habilita L4 onde tcf venceria por margem.

## 7. Riscos / honestidade dura

- **Viés sintético**: os % (0.2/5/7.9) vêm de colunas low-card naturais (dict). Coluna de filtro em
  tcf/high-card **não** tem corte limpo. Validar em **N≥5 real-world** antes de qualquer
  `confirmada-empirica`.
- **Limite fundamental do tcf**: OBAT+HCC entrelaçam linhas; **nenhum** gadget/índice resolve sem
  decode total ou redesign. Promessa de lazy em coluna tcf é falsa — o ganho vive em **dict/raw**.
- **Sidecar = estado a manter** (stale). Fingerprint + fallback a derivar.
- **`sort_by` é order-free** (ordem original perdida) — knob de query, não de transmissão que
  precise preservar ordem. Documentar.
- **`execute()` pode mascarar fallback total silencioso** (filtro em coluna tcf → decode inteiro). A
  API deve reportar custo/colunas tocadas (`self.touched` já existe) pra não iludir sobre "lazy".
- Mudar `decode()` core dispara GATE + ADR + re-pin → **evitar**; pushdown vive no gadget.

## 8. Recomendação

**Primeiro** (barato, zero core, alto retorno): **E1 + E2** (QueryPlan + `execute()`) entregam a
sensação de decode único parametrizado reusando as primitivas que `lazy.py` já tem — respondem
direto às ideias 1 e 2. Junto, **E3 + E4** (índices deriváveis on-the-fly): 0 bytes, só tooling —
cobrem a maior parte do "índices escondidos pra grouping" **sem nada persistido nem formato novo**.

**Depois** (se números real-world justificarem): **E5** sidecar `.tcfx` opt-in (gated por medição,
fingerprint p/ consistência) e **E6** `prefer_dict_cols`.

**Adiar** (não vale o custo agora): índice in-blob / chunking / footer Parquet-style (#TCF.8, ADR
pesada, GATE, re-pin) e redesign OBAT/HCC (viola single-pass ADR-0002).

**A "venda" do lazy aqui é o column-pruning + dict-stream-scan que já existem**, não um índice
mágico. Registrar em ADR (quando consolidar) que índices são **gadget-territory** (derivável >
sidecar > formato), **nunca in-blob por default**.
