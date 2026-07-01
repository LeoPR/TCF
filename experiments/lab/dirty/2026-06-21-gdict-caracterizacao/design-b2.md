# B2 — design do cross-dict híbrido V2 (group-dict), opt-in #TCF.8 [design]

**Data**: 2026-06-27 (**revisado pós-revisão adversarial** — changelog:
[design-b2-revisao.md](design-b2-revisao.md), 24 achados, 0 blocker). **Tipo**: design (zero-código;
`src/tcf` intocado — o weld é B3, sob aprovação). Ancora no [result.md](result.md) (B1,
fechado-positivo). Família: [tcf8-estrutura-plano.md](../notas/tcf8-estrutura-plano.md) §4.

**Escopo (re-segmentação 2026-06-27)**: B2 é o **W1 puro — same-domain-refs**. O caso s/n /
flag-survey **saiu** do cross-dict (medido fraco, ≤4.6% txt, brotli-neg) → virou **W2 (binarização)**.
Ver [resegmentacao-workstreams](../notas/resegmentacao-workstreams-2026-06-27.md).

**Respaldo de literatura** ([bibliografia](../../../docs/reference/bibliografia.md)): o V2-B = o
`RLE_DICTIONARY` do **Parquet** (dict por column-chunk); B2 generaliza pra cross-column. O lazy =
**late materialization** (Abadi 2007). O caveat brotli tem piso teórico em **Raman & Swart 2006**
(entropia + query-sobre-comprimido).

## O que o B1 fixou (premissas)
- **Onde paga** (único regime): **same-domain-reference columns** — 2+ colunas do mesmo domínio (FK
  repetida, origem/destino, grafo source/target, email1/2, telefone1/2). Real: SNAP grafo **−19.3%**,
  OpenFlights −4.6/−6.6% textual + lazy cross-col (dict lido 1×).
- **A dobradiça** (decide pool sim/não):
  ```
  net(grupo) = (Σ_c tab_per_col_c − tab_grupo)          [dedup: tabelas duplicadas colapsam]
             − Σ_c N_c · (w(K_grupo) − w(K_c))            [custo: índice mais largo, por linha]
             − custo_de_header (marca &G + framing do prelúdio)   [ver (1)]
  ```
  O guard É o **termo de custo** (não o Jaccard): mesmo same-domain, se a UNIÃO cruza um limite de
  largura base-94 (94/8836/…) o custo dispara e o greedy **rejeita** o pool. Same-domain típico
  (Jaccard≈1, união no mesmo bucket) → custo de largura ≈ 0 → ganho = dedup.
- **Híbrido**: pool só grupos net-positivos; disjuntas/parciais ficam **per-column** (V2-B) → captura
  o ganho sem a perda de E2/(c)/(d).

## Princípio: B2 estende o `@dict` do V2-B (não reinventa)
V2-B tem tabela-de-únicos + stream base-94 **por coluna** (= Parquet RLE_DICTIONARY). B2 acrescenta
UM nível: a tabela pode ser **de grupo** (compartilhada por colunas same-domain), **hoistada pro
prelúdio do corpo**. Não exige H-REF-01/02 (refactor mais fundo, futuro).
**Correção (revisão A2)**: a coluna grupada **NÃO é "V2-B inalterado"** — vira um **slot novo,
stream-only** (a tabela não está no body dela; está no prelúdio compartilhado). É um modo de coluna
distinto (ver §2).

## (1) Particionamento — greedy custo-modelado (o coração)
Pré-pass cross-coluna no encode multi-col (o encoder já tem todas as colunas). **A regra de pool É a
dobradiça aplicada gulosamente** — não um threshold solto de Jaccard:

```
candidatas = colunas dict-elegíveis (as que o V2-B já escolheria: cardinalidade ≤ limite)
1. agrupar candidatas por SIMILARIDADE de domínio (Jaccard alto) — pré-corte só p/ acelerar
2. para cada grupo-candidato G:
     tab_G   = _encode_column(união dos únicos)          # ENCODA a união de verdade (ver nota)
     dedup   = Σ_c bytes(tab_c) − bytes(tab_G)
     w_cost  = Σ_c N_c · (w(K_G) − w(K_c))                # largura base-94 por linha
     h_cost  = Σ_{c∈G} |marca &G no meta|  +  |framing do prelúdio de G|   # custo de header
     pool(G) sse  dedup > w_cost + h_cost                 # net-positivo (dobradiça COMPLETA)
3. colunas fora de qualquer G net-positivo → per-column (V2-B atual, sem perda)
```
- **`bytes(tab_G)` é MEDIDO encodando a união** via `_encode_column`, **nunca estimado por Jaccard/
  contagem** (revisão B-dedup): o dedup é não-linear sob HCC (range/composição colapsam a união).
- **Custo de header no modelo** (revisão B-header): a marca `&G` por coluna + o framing do prelúdio
  entram no custo. Desprezível no regime same-domain (SNAP: ~32B vs 152K), mas evita poolar grupos
  marginais (relevante fora do alvo).
- **Largura NÃO é garantida pelo namespace** (revisão B-width): o namespace-por-grupo (0-based) evita
  o estouro **GLOBAL-flat** do E2 (todas as colunas num namespace inchado), mas **não** garante custo
  0 — um grupo cuja união cruza o bucket é barrado pelo **termo de custo**, não pelo namespacing.
  → **Teste B3**: grupo same-domain cuja união cruza 94 → confirmar que **não** pool (degrada sem perda).
- **Ordem da união = invariante** (revisão A-union-order): first-appearance varrendo as colunas do
  grupo na ordem do meta. Determina tab-bytes E índices → **pinar** num teste byte-idêntico antes do weld.
- O **decoder NÃO recomputa** o particionamento: o prelúdio **declara** os grupos. Greedy é encoder-side.

## (2) Formato #TCF.8 opt-in — group-dict no PRELÚDIO DO CORPO (revisão A1)
**Correção estrutural**: `#TCF.8M` **não tem header multi-linha** (o corpo começa logo após a 1ª
`\n`), e `tab_grupo` contém `\n`/`=`/`,`. Logo os group-dicts **NÃO** são "linhas de header" — são um
**prelúdio length-prefixed no início do CORPO**, com fronteira por byte-count (igual ao slot V2-B):

```
#TCF.8M<meta-inline>\n                     meta das colunas; coluna grupada usa MODO &<G> (ver abaixo)
<n_grupos>\n                               ┐ PRELÚDIO (só existe se há coluna grupada no meta)
<ntab_0>\n<tab_bytes_0>                     │  cada grupo = length-prefixed (ntab + tab)
<ntab_1>\n<tab_bytes_1>                     ┘  cursor avança além do prelúdio
<body col 0><body col 1>...                colunas (fatiadas por `size` do meta, como hoje)
```
- **Modo de coluna `&<G>`** (novo prefixo, junto de `@ ~ %`): declara "coluna grupada, grupo G,
  **body = stream-only**" (índices base-94 no namespace do grupo G; width derivada do K_G carregado no
  prelúdio). O prefixo `&<G>` é parseado **antes** do `int(size)` → **não colide** com o slot de size
  (revisão meta-slot-int). `&` entra no conjunto reservado de marcadores (revisão A-amp).
- **Gramática do token grupado** (com nature): ordem fixa `&<G>[:spec]<size>=<name>` — o interleave
  exato de `:spec` fica pra bikeshed no B3 (revisão gd-spec-coocorrencia).
- Coluna dict avulsa (`@`) e não-dict seguem **inalteradas** (V2-B).
- Presença de qualquer coluna `&<G>` no meta ⟹ decoder lê o prelúdio antes das colunas.

## (3) Decode + lazy (a porta estrutural) — honestizado (revisão C)
- **Decode**: lê o prelúdio de group-dicts **1× (serial)** → cada coluna `&<G>` indexa no `tab_G`.
  Após o prelúdio, as colunas são **decodáveis independentemente** (sem auto-referência inline
  cross-coluna). **Não é "paralelizam"** — não há substrato de decode paralelo hoje; é *independência*
  que HABILITA paralelismo futuro (W3, hquery01, plano 0.9).
- **Lazy** (B4, `view.py`): exige um `self._group_dict` keyed por **grupo** (não por coluna),
  populado 1× num **estágio de prelúdio-parse** novo em `view.py` (revisão C-parse/C-touched). Só
  assim o "decodes C→1" do B1 se materializa. Consulta same-domain lê o stream + o `tab_G` 1×;
  cross-col ("tudo que toca X") lê o dict **1× em vez de C×** (−19.3% no grafo, late materialization).
- **Single-col numa coluna grupada** (revisão C-single-col): materializa a tabela do **grupo** (a
  união), não a da própria coluna → downside ∝ (1−Jaccard)·|união| (**0B** no SNAP Jaccard=1; **+64-88B**
  no OpenFlights). Contar `bytes(tab_G)` 1× no accounting de laziness (amortizado sobre o grupo).

## (4) Byte-neutralidade & gate — (revisão D)
- **Default-off byte-idêntico**: `force_v8`/`used_v2` ganha `or bool(group_dicts)` **só quando há
  grupo net-positivo**; sem grupo, o codepath é **byte-idêntico** ao de hoje (mesmo gate condicional
  de `nature_ids`/`drop_names`). **D1-D9=1523B / D17a=303B intactos** (single-col nunca grupa;
  multi-col sem same-domain degrada pra V2-B). Pinar que D17a sai do caminho sem-grupo.
- **Gate B3 — N≥5** (owner confirmou; alinha ao checklist anti-incidente): ≥5 fontes reais com forma
  same-domain-ref (rotas de voo, edge-lists de grafo, transações de/para, FK repetida, email1/2,
  telefone1/2). SNAP −19.3% + OpenFlights ×2 = 3; **faltam ≥2** (liga a T-DATA-1).
- **Overfit declarado** (revisão D-overfit): a feature ativa em **ZERO** dataset canônico do projeto
  (overlap intra-blob ~0); o único ≥15% é **um grafo**; o ganho é frágil em N grande (OpenFlights
  cai pra 4-7% — dict como fração menor do blob).
- **Brotli = CONTROLE padronizado** (owner): sempre reportar como **referência**, **nunca** gate
  pass/fail (incompatível com lazy). **Mas** medir same-domain K-grande sob brotli como **sinal**
  antes do weld (revisão D-brotli; não silenciar). `test_real_world_snapshots` verde; re-pin; **L0 Strata**.

## (5) Relação com H-REF (escopo)
B2 fica sobre o V2-B (tabela+stream). **H-REF-02** (atom-IDs globais contínuos) seria a unificação
mais profunda (o `^N` do HCC e o `@` do V2-B viram um só) — daí o GDICT sairia "de graça", mas é
refactor de core (futuro). **B2 não cria dívida que H-REF-02 teria que desfazer** (verificado na
revisão): group-dict é a versão pragmática e mensurável agora.

## Questões abertas pra B3 (bikeshed no weld)
1. Interleave exato de `:spec` no token `&<G>` grupado (§2).
2. Pré-corte de similaridade do passo 1 (Jaccard ≥ ?) — só acelera; o filtro de custo é o guard real.
3. Ordem/precedência dos modos no corpo (`& @ ~ %` + min_header) — B2 aplica ANTES do per-column V2-B.
4. Escala **≥3 colunas** same-domain (B1 só testou pares) — validar no prototype.

## Próximo passo recomendado
**Prototype read-only** (fora de `src/tcf`, pós-transform sobre o `encode` multi-col): implementar o
particionamento custo-modelado (com `bytes(tab_G)` medido + custo de header) + a forma `&<G>`
(prelúdio length-prefixed + modo stream-only) como transform de texto. **Rodar em SNAP + OpenFlights
+ ≥2 novos same-domain** (rumo a N≥5) e confirmar (a) RT lossless (ordem-de-união pinada), (b) ganho
reproduzido, (c) ≥3-col escala, (d) o caso "união cruza bucket → não pool". Se confirmar → B3 (weld
opt-in em `src/tcf`, ADR, sob aprovação).
