# B2 — design do cross-dict híbrido V2 (group-dict), opt-in #TCF.8 [design]

**Data**: 2026-06-27. **Tipo**: design (zero-código; `src/tcf` intocado — o weld é B3, sob
aprovação). Ancora no [result.md](result.md) (B1, fechado-positivo). Família:
[tcf8-estrutura-plano.md](../notas/tcf8-estrutura-plano.md) §4. Refs: V2-B
[ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md), espaço de ref
[dict-referencia-hipoteses.md](../notas/dict-referencia-hipoteses.md).

## O que o B1 fixou (premissas do design)
- **Onde paga** (único regime): **same-domain-reference columns** — 2+ colunas referenciando o
  mesmo domínio (FK repetida, origem/destino, grafo source/target). Real: SNAP grafo **−19.3%**,
  OpenFlights −4.6/−6.6% textual + lazy cross-col (dict lido 1×).
- **A dobradiça** (decide pool sim/não):
  ```
  net(grupo) = (Σ_c tab_per_col_c − tab_grupo)          [dedup: tabelas duplicadas colapsam]
             − Σ_c N_c · (w(K_grupo) − w(K_c))            [custo: índice mais largo, por linha]
  ```
  Ganha **sse** o pooling **não cruza limite de largura base-94** (94/8836/…) E há overlap real.
  Same-domain (Jaccard≈1) → K_grupo ≈ K_c → custo ≈ 0 → ganho = dedup puro.
- **Híbrido**: pool só grupos net-positivos; colunas disjuntas/parciais ficam **per-column**
  (V2-B atual) → captura o ganho sem a perda de E2/(c)/(d).
- **Brotli FORA do gate** (correção owner 2026-06-21): incompatível com lazy; sinal qualitativo só.

## Princípio: B2 estende o `@dict` do V2-B (não reinventa)
V2-B já tem tabela-de-únicos + stream base-94 **por coluna**. B2 acrescenta UM nível: a tabela
pode ser **de grupo** (compartilhada por colunas same-domain), **hoistada pro header**. Não
exige H-REF-01/02 (unificar `^N`/`@`) — esses são refactor mais fundo, futuro. B2 é o group-dict
pragmático sobre o V2-B.

## (1) Particionamento — greedy custo-modelado (o coração)
Pré-pass cross-coluna no encode multi-col (o encoder já tem todas as colunas). **A regra de pool
É a fórmula da dobradiça aplicada gulosamente** — não um threshold solto de Jaccard:

```
candidatas = colunas dict-elegíveis (as que o V2-B já escolheria: cardinalidade ≤ limite)
1. agrupar candidatas por SIMILARIDADE de domínio (Jaccard alto entre value-sets)
2. para cada grupo-candidato G:
     dedup   = Σ_c bytes(tab_c) − bytes(tab_G)            # tab_G = união dos únicos
     custo   = Σ_c N_c · (w(K_G) − w(K_c))                # largura base-94 por linha
     pool(G) sse  dedup > custo                            # net-positivo (dobradiça)
3. colunas fora de qualquer G net-positivo → per-column (V2-B atual, sem perda)
```
- **Determinístico** (greedy estável por ordem de coluna) → `encode` reproduzível (RT).
- A largura é **bound por grupo** (namespace 0-based do grupo), nunca global-flat → resolve o
  estouro de largura do E2 (V1 naive). "Índices da coluna do 0" vira "índices do GRUPO do 0".
- O **decoder NÃO recomputa** o particionamento: o header **declara** os grupos (resultado). O
  greedy é só encoder-side.

## (2) Formato #TCF.8 opt-in — group-dict no header
Multi-col `#TCF.8M`. Acrescenta uma seção de **group-dicts** (prelúdio serial: decodar 1×, depois
colunas paralelizam). Esboço (marcador exato = detalhe de B3; proponho `&`):

```
#TCF.8M<meta-inline>            meta das colunas (como hoje)
&0=<tab_grupo_0>                group-dict 0 (união dos únicos; mesma codificação de tab do V2-B)
&1=<tab_grupo_1>                group-dict 1
<corpo>:
  coluna em grupo G  → marcador @&G + stream base-94 (índices no namespace DO GRUPO G)
  coluna dict avulsa → @<tab própria> + stream  (V2-B atual, inalterado)
  coluna não-dict    → como hoje
```
- `tab_grupo` usa a MESMA serialização de tabela do V2-B (reuso, não formato novo).
- O custo de header do group-dict é **a tabela 1× + a declaração de pertença** — medido barato no
  B1 (E3: 55 B p/ 15 valores; o custo real era largura, não tabela).
- **Membership**: cada coluna grupada referencia `&G` no seu marcador → o header não precisa de
  lista separada de pertença (vai no próprio marcador da coluna).

## (3) Decode + lazy (a porta estrutural)
- **Decode**: lê os `&G=tab` do header (prelúdio serial, 1×) → cada coluna grupada indexa no
  `tab_G`. Após o prelúdio, colunas **paralelizam** (sem auto-referência inline cross-coluna).
- **Lazy** (B4, `view.py`): consulta numa coluna same-domain lê o stream dela + o `tab_G` **1×
  (compartilhado)**. Cross-col ("tudo que toca o nó X" = scan dos streams do grupo) lê o dict
  **1× em vez de C×** — o ganho estrutural medido no B1 (decodes 2→1, −19.3% no grafo).

## (4) Byte-neutralidade & gate
- **Default-off byte-idêntico**: sem grupo net-positivo (ou flag opt-in off) → saída idêntica à
  de hoje. **D1-D9=1523B / D17a=303B intactos** (single-col nunca grupa; multi-col sem same-domain
  degrada pra V2-B). Invariante #TCF.8.
- **Gate B3** (antes de weldar): textual + lazy em **≥2 reais** (SNAP −19.3% ✓; OpenFlights
  −4.6/−6.6% — passa pela porta estrutural lazy, byte sub-15% mas o owner aceitou same-domain como
  regime); `test_real_world_snapshots` verde; re-pin; **L0 Strata**; **brotli fora do gate**.

## (5) Relação com H-REF (escopo)
B2 fica sobre o V2-B (tabela+stream). **H-REF-02** (atom-IDs globais contínuos) seria a unificação
mais profunda (o `^N` do HCC e o `@` do V2-B viram um só, índices globais) — daí o GDICT sairia "de
graça", mas é refactor de core (futuro). **B2 não depende disso**: group-dict é a versão pragmática
e mensurável agora. H-REF-03 (escape-free) é ortogonal (ataca o `^N` inline, não o `@`).

## Questões abertas pra B3 (bikeshed no weld)
1. **Marcador**: `&` p/ group-dict? Conflita com algum literal? (checar escape no corpo.)
2. **Threshold de similaridade** do passo 1 (antes do filtro de custo): Jaccard ≥ ? (B1: same-domain
   é ≈1; partial-share (c) perde — o filtro de custo já barra, mas um pré-corte acelera.)
3. **Interação com min_header / fallback `~` / split `%` / dict `@`**: ordem dos marcadores no
   corpo; precedência. (B2 é cross-coluna, aplica ANTES do per-column V2-B.)
4. **Custo exato de header** do `&G=tab` na contagem (entra no modelo de custo do passo 2?).
5. **≥3 colunas same-domain**: o ganho escala com nº de colunas no grupo (B1 só testou pares) —
   validar num prototype read-only antes do weld.

## Próximo passo recomendado
**Prototype read-only** (fora de `src/tcf`, pós-transform sobre o `encode` multi-col): implementar
o particionamento custo-modelado + a forma `&G` como transform de texto, **rodar em SNAP +
OpenFlights** (Z:) e confirmar (a) RT lossless, (b) −19.3%/−5% reproduzidos, (c) ≥3-col escala.
Se confirmar → B3 (weld opt-in em `src/tcf`, ADR, sob aprovação).
