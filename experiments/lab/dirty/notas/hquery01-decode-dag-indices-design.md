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

---

# 9. Revisão do owner (2026-06-17) — pra pensar depois (NÃO implementar)

Três correções de rumo do owner, que mudam a **forma** do plano (não o código). Tudo abaixo é
planejamento; nenhuma atividade é pra executar agora.

## 9.1. Unificação "não-dura" — caminhos mínimos inteligentes, união bottom-up

Crítica do owner ao "decode unificado" da seção 2: **juntar tudo numa função não é unificar** —
é só *lumping*. Unificar como ALGORITMO é compartilhar sub-computação real; pôr `count`, `where`,
`group` no mesmo método sem fatorar o que é comum dá uma falsa unificação (um `if mode/op` gigante).

**Sequência de desenvolvimento correta** (a espinha do plano, substitui a leitura "top-down" da
seção 2):

1. **Fazer cada operação por si** — `count`, `group-tally`, `where`, `agg-filtrada`, `select` —
   cada uma no seu **caminho mínimo por modo** (o que a seção 1 já mapeou). Independentes, simples,
   testáveis isoladas. É o que `lazy.py` já faz em boa parte.
2. **Otimizar cada caminho** isoladamente (sem acoplar aos outros).
3. **Fatorar o COMUM** — só depois, extrair as primitivas que reaparecem. O comum real, ancorado
   no código atual, é um pequeno conjunto de **acessadores por coluna/modo**:
   - `tabela(col)` → decodifica os K únicos (dict) — usado por `group_count`, `where`, min/max.
   - `ids_por_posição(col)` → itera o stream base-94 sem expandir (dict) — usado por `where`,
     `group_count`, group-by.
   - `valor_em(col, i)` / `valores(col, idx)` → materializa só o necessário.
   - `count_estrutural(col)` → `nrows` sem decodar.
   A "unificação" verdadeira = essas primitivas compartilhadas; `execute()` (E2) vira um
   **orquestrador fino** que compõe primitivas, **não** um decodificador monolítico. Se a fatoração
   não aparecer naturalmente, é sinal de que as operações **não** são unificáveis ali — e tudo bem
   manter caminhos separados (honestidade > elegância forçada).

**Hipótese H-QUERY-04b (registrada)**: *não perseguir um `decode()` unificado; perseguir caminhos
mínimos por operação e deixar as primitivas comuns emergirem da fatoração.* Mede-se o sucesso pela
**reúso real** (quantas ops compartilham a mesma primitiva), não por "tudo numa função".

## 9.2. Paralelismo por coluna (consequência da independência do DAG)

Como as colunas são nós **independentes** (seção 1), uma query que toca colunas distintas é
**naturalmente paralela**. Exemplo do owner — *filtrar por uma coluna, agrupar por outra*:

```
sum(C) where A=x group by B   (A, B, C = colunas distintas)
 ├─ P_A: scan do stream de A  → posições onde A=x        (idx_A)        ╮ processos
 ├─ P_B: ids-por-posição de B → grupo de cada linha                    ╞ paralelos
 └─ P_C: decodifica C nas posições necessárias                         ╯ (colunas distintas)
 join POSICIONAL: pra cada i em idx_A → grupo=B[i], acumula C[i]  (row-alignment, seção 1)
```

P_A, P_B, P_C tocam **corpos de coluna distintos** → leitura/scan independentes (paralelizáveis,
até em threads/processos); o *join* é por **posição** (a i-ésima linha de cada coluna é a mesma —
invariante já usada no `where().sum()`). O **índice auxiliar é opcional e por-processo**: acelera
P_A (quais linhas casam x) ou P_B (offsets de grupo) **se existir**; sem ele, cai no scan do
stream. Isso encaixa direto no QueryPlan (E1): cada nó-coluna é um sub-plano que pode rodar solto.

**Hipótese H-QUERY-04c (registrada)**: *o QueryPlan modela cada coluna como sub-plano independente;
a execução pode ser paralela (colunas distintas não competem) e o índice auxiliar entra como
aceleração local opcional de um sub-plano, nunca como dependência.*

## 9.3. Índice e a tensão com compressão de transmissão — decidir por PERFIL DE USO

O owner notou: **índice é estranho pra versão online/transmissão** — ele infla o payload e mata a
venda de compressão. Logo a decisão de índice **não é global**, é por perfil:

| perfil | índice? | onde | porquê |
|---|---|---|---|
| **Transmissão online / one-shot / byte-minimal** | **NÃO** | — | cada byte conta; índice mataria a compressão. Derivável on-the-fly **no receptor** (0 byte transmitido). |
| **At-rest, consultado repetidamente** (`.tcf` "banco-de-dados-ish") | **talvez** | sidecar ou in-file | o índice **amortiza** sobre muitas queries; o custo de bytes é aceitável porque não é transmitido a cada consulta. |
| **Híbrido (index-on-arrival)** | **derivar local** | sidecar/in-file **gerado no receptor** | transmite enxuto (sem índice); o receptor que vai consultar muito **materializa o índice localmente** depois de receber. Combina os dois. |

**Index-on-arrival** é a síntese: o índice é um problema **at-rest/local**, derivado **depois** da
transmissão, **nunca transmitido**. Preserva a venda de compressão E dá query rápida pra quem
consulta repetido. (Registrar como a posição-default recomendada.)

**Prós/contras de TER índice** (a pesar caso-a-caso, como o owner pediu):
- **Prós**: query mais rápida (skip de scan), group-by O(K) vs O(N·w), range-predicate por zone-map.
- **Contras**: bytes a mais (mata transmissão); **estado a manter** (stale vs o blob → fingerprint);
  complexidade do leitor; ganho **modo-dependente** (zero em coluna `tcf`, que é entrelaçada).
- **Regra**: índice só quando (a) at-rest, (b) query repetida, (c) coluna `@dict`/raw (onde há
  corte), (d) medido ≥ ganho que justifique — senão o dict-stream-scan já basta.

## 9.4. Índice in-file (meio-termo) — marcadores inertes ao codec

Ideia do owner: marcadores **no mesmo `.tcf`** que são "inúteis" pro recompressor (não mudam como
nada comprime) mas servem de **dica** pra filtro/agregação. É um meio-termo entre derivável (0 byte,
mas efêmero) e sidecar (arquivo separado, sincronização).

**Como poderia funcionar** (esboço pra pensar, não spec):
- Hoje a última coluna vai "até EOF" → não dá pra anexar nada sem corromper o corpo dela. Um índice
  in-file precisa de **fronteira**: dar **size explícito também à última coluna** (perde o
  `min_header` "última sem size") + um **flag no magic** ("este arquivo tem trailer de índice").
  Depois das N colunas (somados os sizes), o resto é a região de índice.
- **Em que sentido é "inerte"**: o **codec de cada coluna** (OBAT/HCC/V2-B) fica **intocado** — os
  bytes do índice não pertencem a corpo de coluna nenhum, então **zero impacto em como comprime**.
  O `decode()` ignora o trailer (decodifica só as N colunas) → **round-trip lossless preservado**.
  O leitor lazy lê o trailer como dica.
- **Em que sentido NÃO é grátis**: o **parser de container** precisa aprender a parar na fronteira
  e a reconhecer o flag → isso **toca o spec do formato** (mais que sidecar, **menos** que
  chunking, que muda o framing/compressão dos corpos). Honestamente: é uma **extensão de container
  opt-in**, não um "marcador grátis".

**Índice in-file vs sidecar** (o trade que o owner quer pesar):

| eixo | in-file (trailer inerte) | sidecar `.tcfx` |
|---|---|---|
| arquivos | 1 (viaja junto) | 2 (gerenciar par) |
| consistência | sempre casado (gerado no mesmo encode) | pode ficar stale → precisa fingerprint |
| dropável | **não** (re-encode pra tirar) | **sim** (só apagar) |
| toca o spec? | **sim** (flag no magic + size na última col) | **não** (zero formato) |
| transmissão | infla o `.tcf` (ruim p/ online) | `.tcf` fica enxuto; índice só se quiser mandar |

**Posição (pra pensar depois)**: in-file resolve a dor de sincronização do sidecar, ao custo de
inflar o blob transmitido e de um toque no spec (flag + size). Para **at-rest single-file** é
atraente; para **transmissão** perde pro sidecar/derivável. Combina bem com **index-on-arrival**
(§9.3): o receptor reescreve o `.tcf` com trailer local se for consultar muito — sem nunca
transmitir o índice.

**Hipótese H-QUERY-04d (registrada)**: *índice in-file = extensão de container opt-in, transparente
ao codec (não muda compressão de coluna) mas detectável pelo parser (flag no magic + size explícito
na última coluna); meio-termo entre derivável e sidecar. Decidir por perfil de uso (§9.3); default
recomendado = não-transmitir (derivável/index-on-arrival).*

## 9.5. Espectro de índice atualizado (substitui o "derivável > sidecar > formato")

```
derivável on-the-fly   →   { in-file (trailer inerte)  ≈  sidecar .tcfx }   →   in-blob / chunking
   0 byte, efêmero            persistido; single-file vs dropável               muda o codec/framing
   transmissão-safe           at-rest; tensão de bytes                          format change pesado
```

- **derivável**: default pra transmissão (0 byte).
- **in-file / sidecar**: tier "índice persistido", at-rest; diferem em single-file vs dropável e em
  tocar-spec vs zero-formato (tabela §9.4).
- **in-blob/chunking**: muda como os corpos comprimem → `#TCF.8`, ADR + GATE + re-pin → adiar.

## 9.6. Plano revisado (sequência, pra pensar depois)

**Fase A — caminhos mínimos por operação** (§9.1 passo 1; quase tudo já existe): consolidar `count`,
`group-tally`, `where`, `agg-filtrada`, `select` como caminhos independentes por modo + **E1**
QueryPlan explícito (lista nós/cortes/colunas-tocadas antes de decodar).

**Fase B — otimizar + paralelismo** (§9.1 passo 2, §9.2): cada caminho otimizado; QueryPlan modela
colunas como sub-planos independentes (paralelizáveis); índice auxiliar como aceleração local
**opcional** de um sub-plano.

**Fase C — fatorar o comum** (§9.1 passo 3): extrair as primitivas (`tabela`, `ids_por_posição`,
`valor_em`, `count_estrutural`); **E2** `execute()` vira orquestrador fino sobre elas (não monólito).
RT obrigatório vs `decode()`.

**Transversal — índices, por perfil** (§9.3–9.5): **E3** deriváveis on-the-fly (0 byte, default
transmissão) + **E4** offset-map via `seq_rle_runs`. Só depois, e **gated por medição real-world**:
**E5** índice persistido — comparar **in-file (trailer)** vs **sidecar `.tcfx`** (tabela §9.4) sob o
modelo **index-on-arrival** (gerar local, não transmitir). **E6** knob `prefer_dict_cols`.

**Adiar igual à seção 8**: in-blob/chunking/footer (= `#TCF.8`) e redesign OBAT/HCC.

> Tudo nesta seção é **design pra depois**. Não implementar; não tocar `src/tcf`; índice persistido
> (in-file ou sidecar) só com números real-world que justifiquem o custo de bytes.
