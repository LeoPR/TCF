# B1.0 — cross-dict (H-GDICT): evidência sintética mínima [probatório]

**Data**: 2026-06-21 · lab read-only (`src/tcf` intocado). Script: [`synth_minimal.py`](synth_minimal.py).
Modela com os internos REAIS do V2-B (`_v2b_encode`, `_encode_column`, `_v2b_width`).

## O que foi medido

Duas representações do MESMO conteúdo categórico, só o corpo do dict (tabela + stream;
meta do header estimada à parte):

- **@dict per-column (HOJE, V2-B)**: cada coluna = `<len(tab)>\n` + tabela própria + stream `N·w(K_c)`.
- **cross-dict GLOBAL (H-GDICT)**: 1 tabela compartilhada (união dos únicos) + cada coluna = stream `N·w(K_global)`.

`w(K)` = largura base-94 do índice (1 char até K=94; 2 até 8836; ...).

## Resultados (textual | brotli q11)

| caso | descrição | per-col | cross-dict | net textual | net brotli |
|---|---|---|---|---|---|
| **E1** | 3 flags SIM/NÃO, alto overlap, K_global=2 (w=1) | 102 B | **82 B** | **−20 (ganha)** | 49→**40** (ganha) |
| **E2** | 3 cols 40-distintos disjuntos, N=200, K_global=120 (w 1→2) | 642 B | 1236 B | **+594 (perde)** | 74→173 (perde) |
| **E3** | misto: flags+UFs compartilham, porte disjunto, K_global=15 (w=1) | 257 B | **199 B** | **−58 (ganha)** | 118→**96** (ganha) |

Decomposição do net (só colunas que seriam dict):
- **E1**: economia_tabela **+20**, custo_índice **0** → +20.
- **E2**: economia_tabela +6, custo_índice **−600** (3 cols × 200 linhas × +1 char) → −594.
- **E3**: economia_tabela **+58**, custo_índice **0** → +58.

## Leitura — a dobradiça é o LIMITE DE LARGURA

O net do cross-dict decompõe em exatamente dois termos:

```
net = (Σ tabelas_per_col − tabela_global)   [economia: tabelas duplicadas colapsam]
    − Σ_c N_c · (w(K_global) − w(K_c))       [custo: índice global mais largo, pago em TODA linha]
```

- **Economia** = só dos valores que **de fato se repetem entre colunas** (a tabela deles deixa
  de ser guardada N vezes). Vale pouco por valor (cada entrada de tabela é curta), mas escala com
  o nº de colunas que compartilham.
- **Custo** = `w(K_global) − w(K_c)` pago em **cada linha de cada coluna**. É **zero** enquanto a
  união fica no mesmo bucket de largura base-94 da coluna; vira **+1 char/linha** (e mais) assim que
  `K_global` cruza 94 / 8836 / ...

**Conclusão central**: cross-dict ganha **sse e só se** o pooling **não cruza um limite de largura**
(E1, E3: K_global ≤ 94 → custo 0 → ganho = dedup puro). Se cruza (E2), o custo por-linha-por-coluna
domina e o cross-dict **perde feio, inclusive sob brotli** (os bytes de padding do índice são
baixa-entropia, brotli recupera parte, mas o per-column continua melhor).

## Implicação direta pro design (as 3 tensões do owner)

1. **Paralelismo ↔ sincronismo**: confirmado que compartilhar dict **inline cross-coluna** (coluna B
   referencia valor definido na coluna A) cria dependência serial. A única forma de compartilhar SEM
   acoplar é **hoistar a tabela pro header** → prelúdio serial único (decodar a tabela 1×) e depois
   as colunas paralelizam. Streaming = **uma pausa frontal** (carregar o dict), não pausas espalhadas.
2. **Custo do dict no header**: medido — a TABELA compartilhada no header é barata (E3: 55 B p/ 15
   valores). O custo real **não é a tabela**, é a **largura do índice** quando o namespace global
   incha (E2). A intuição "perderia uns bytes ao ceder a auto-referência" é verdadeira só quando o
   pooling cruza o bucket de largura.
3. **Namespace de índice cross-coluna**: é exatamente o que causa o estouro de largura. Um namespace
   **global flat** (0..K_global−1) força a largura do maior K. **Manter namespaces por GRUPO**
   (cada grupo 0-based, pequeno) bound a largura → resolve a tensão. "Índices de cada coluna do 0"
   vira "índices de cada GRUPO do 0".

## Caveats

- **Sintético mínimo** (viés declarado: construído pra isolar o mecanismo). NÃO generaliza —
  o gate exige ≥5 reais (anti-incidente 2026-05-21). Aqui só estabelece o MODELO e a dobradiça.
- Meta de header (`@<size>=<name>` per-col vs declaração do dict global + marcador por coluna)
  não incluída — é secundária vs os efeitos de corpo medidos; entra no design #TCF.8.
- Brotli em blob minúsculo tem overhead alto; os sinais batem com o textual mas o número real
  precisa de volume.
