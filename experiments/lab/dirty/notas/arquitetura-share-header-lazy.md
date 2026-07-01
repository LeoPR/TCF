# Reorganização — arquitetura share × header × lazy (o balanço compressão↔lazy) [teoria]

**Data**: 2026-07-01. **Tipo**: reorganização de teoria (owner). Consolida a re-exploração do
cross-dict ([diário 07-01](diario/2026-07-01.md), [sketch](../2026-07-01-crossdict-emprestimo-indices/))
num mapa de design. Ancorado na [bibliografia](../../../docs/reference/bibliografia.md) (Abadi/Parquet/
Dremel) e no que já existe no repo. Objetivo do owner: **balanço, não descarte** — comandos pra
escolher, casos que ajudam compressão e prejudicam lazy podem valer se a troca for reanalisável.

## Princípio governante: compressão ↔ lazy é um TRADE (Abadi 2006)
Compartilhar (cross-dict, cross-column refs) **melhora compressão** mas **piora a seletividade lazy**
(pra decodar 1 coluna você precisa ler o que ela compartilha). Independência (per-coluna) é o inverso.
**Isto é o tema central de Abadi 2006** (*Integrating Compression and Execution*). A decisão do owner:
tratar como **eixo de comando** (opt-in por caso de uso), não um vencedor único.

## Eixo 1 — ONDE mora o compartilhamento cross-coluna
| opção | o que é | estado / veredito |
|---|---|---|
| **(a) OBAT node-share** | árvore/sufixos compartilhada entre colunas | ⚠️ owner: mais difícil, tira o controle de complexidade do OBAT (vários OBATs buscando numa árvore comum). **Encostar** — acoplamento alto, risco. |
| **(b) HCC ref-share** | HCC compartilha **virtual refs** similares entre colunas | ⭐ **mais plausível**. O HCC **JÁ TEM** virtual refs com **body-order constraint** (`syntax.py:347,578`: "alias resolvida antes"). A ideia do owner "a ref principal aparece antes" **é essa regra** — estender cross-coluna é generalização natural. |
| **(c) Header/prelúdio dict** | tabela compartilhada hoistada (B2 / H-REF-02) | fixa largura global → **falhou o gate** (união grande cruza bucket). OK só p/ small-union (SNAP-like). |
| **(d) Per-coluna, sem share** | dict per-col (DICT-HIGHCARD) | ✅ baseline robusto (−16..−36% vs OBAT/HCC). O **alicerce** — tudo acima constrói sobre ele. |

**HCC ref-share (b), dois sub-modos** (owner):
- **(b1) cascata ordenada**: col2 espera o dict de col1, col3 espera 1+2… — pipeline; decode parcial-
  paralelo; lazy razoável (dependência só "pra trás").
- **(b2) cross independente de ordem**: col1 pode referenciar col2/3, desde que a ref principal
  apareça antes — DAG total; mais assíncrono; **pior pro lazy** (dependência em qualquer direção).

## Eixo 2 — o modelo de decode assíncrono (o espectro do trade)
```
stream O(1)  →  cascata (col N espera <N)  →  DAG (b2)  →  independente (d)
menos share ─────────────────────────────────────────────► mais share
mais lazy/seletivo ◄───────────────────────────────────── menos lazy
```
Já existe o frame: [hquery01-decode-dag](hquery01-decode-dag-indices-design.md) (decode-DAG,
colunas como nós; H-QUERY-04c paralelismo por coluna). O owner nota: mesmo **stream sem paralelismo**
o TCF é ~O(1) em vários cenários; só o (b2) order-independent é questionável.

## Eixo 3 — o PAPEL do header (o grande reframe do owner)
**Insight do owner**: um header que é só **dado movido** é quase **desperdício** — é "uma coluna que
não descomprime dado por si". Só paga se for pra decode multi-coluna **totalmente paralelo**. E "em
último caso a própria 1ª coluna se comporta como header" → **header e 1ª-coluna colapsam**.

**Reframe (= Parquet/Dremel, da bibliografia)**: o header deixa de ser *container de dado
compartilhado* e vira **índice/estatística pra lazy**:
- **stats/zone-maps** (min/max/count por coluna) — pushdown de predicado (Dremel; `.tcfx` do hquery01).
- **offsets/pontos de acesso** — pra materializar só a coluna/faixa necessária (Parquet footer).
- **dicas de spec** (descrição CPF, natures #TCF.8 `:spec`) e stats — via **SideOutputs** (já capta
  isso zero-custo).
- **hints in-data** (no meio das colunas): pontos de acesso/índice/estatística sem função
  descompressiva — como os **page headers** do Parquet.

Ou seja: **o header vira um tipo de índice, não de dado.** O dict/ref compartilhado, se existir, é "quase
um índice" — e aí a pergunta certa é *como reusá-lo pro lazy*, não *como guardar dado nele*.

**Refinamento (owner 2026-07-01) — utilidades do header ALÉM do lazy** (a experimentar, não só lazy):
o header pode dar **dicas melhores no DECODE** em si — (i) dicas de **paralelismo** (onde as colunas
se destravam), (ii) **offset** de algo (pular pra uma faixa), (iii) **contagem/estatística** de dica.
Candidato bom a "algo útil de índice", mas **hints in-data** (no meio das colunas, sem função
descompressiva — dica posicional/numérica) ou **sidecar `.tcfx`** podem ser melhores → **precisa
experimento**. Intuição do owner: os **hints in-data** servem como **"índice streaming"** pra usar
lazy **durante transmissão** ponto-a-ponto (quando não há `.tcfx`). Experimentar também **o que se
adequa a Parquet / HDFS / outros formatos de armazenamento** (interop). Decisão adiada — registrar
pra retomar depois do DICT-HIGHCARD.

## Eixo 4 — DICT-HIGHCARD é o alicerce (mas CONDICIONAL — caracterizado 2026-07-01)
O dict per-col é a **base independente**, MAS a [caracterização](../2026-07-01-dict-highcard/result.md)
mostrou que ele é **condicional** (não o robusto −16..−36% que o B2 sugeria): dict só vence high-card
**sem estrutura** (espalhado); OBAT/HCC vence com estrutura (sequência/grupo/ordenado). O encoder já
faz `min(tcf,raw,v2b,split)` por coluna → a base é **descapar o V2-B** (dict vira candidato do min,
byte-safe). **Consequência p/ o share**: o cross-dict/HCC-ref-share tem de bater um per-col que já é
**min-ótimo** — barra mais alta. "1ª coluna como dict" só ajuda quando ela É dict-vencedora (espalhada).

## Mapa: ideia do owner → eixo → o que já se aproxima
| ideia | eixo | já existe (aproxima) |
|---|---|---|
| 1ª coluna como dict / "header ou 1ª coluna é o mesmo" | E1(b)/E3 | header colapsa com 1ª-coluna; H-REF-02 |
| índices móveis / empréstimo / OBAT-vira-dict | E1(c)/(b) | H-REF-02 (atom-IDs contínuos) |
| OBAT node-share | E1(a) | — (novo, encostado: risco) |
| HCC ref-share cascata (b1) | E1(b1)/E2 | **HCC virtual refs body-order** (existe!) + hquery01 |
| HCC cross order-independent (b2) | E1(b2)/E2 | hquery01 decode-DAG (H-QUERY-04c) |
| header = índice/stats, hints in-data | E3 | SideOutputs, `.tcfx`, #TCF.8 `:spec`; **Parquet/Dremel** (bib) |
| balanço compressão×lazy por comando | princípio | **Abadi 2006** (bib) |

## O balanço (comandos, não descarte) — o pedido do owner
Nenhuma opção é "jogada fora". Vira **eixo de comando** (flag/config por caso de uso):
- `share=off` (default): per-coluna, lazy máximo (DICT-HIGHCARD).
- `share=hcc-cascade`: (b1) compressão↑, lazy razoável (dependência pra trás).
- `share=hcc-dag`: (b2) compressão↑↑, lazy↓ (só quando o caso justifica).
- `header=index`: emite stats/offsets pra lazy (E3), custo pequeno, ganho de query.
Um caso pode ajudar compressão e piorar lazy — **mantém-se como comando reanalisável**, não descarte.

## Open questions / próximo
1. **DICT-HIGHCARD primeiro** (o alicerce): caracterizar o dict per-col sem cap por N/K, 5 fontes + canônicos.
2. HCC ref-share (b1 cascata) é o candidato de compartilhamento mais plausível (reusa body-order) —
   prototipar depois do alicerce, medindo o **trade lazy** explicitamente (não só bytes).
3. Header-índice (E3): desenhar o que entra (stats/offsets/spec) — liga com `.tcfx`/hquery01 (0.9).
4. Conflitos do [diário 07-01](diario/2026-07-01.md) (C1-C5) seguem válidos p/ o compartilhamento.

## Cross-links
[diário 07-01](diario/2026-07-01.md), [sketch empréstimo](../2026-07-01-crossdict-emprestimo-indices/),
[dict-referencia-hipoteses](dict-referencia-hipoteses.md) (H-REF), [hquery01](hquery01-decode-dag-indices-design.md),
[bibliografia](../../../docs/reference/bibliografia.md) (Abadi/Parquet/Dremel), [gate B2](../2026-06-27-gdict-b2-prototype/gate-result.md).
