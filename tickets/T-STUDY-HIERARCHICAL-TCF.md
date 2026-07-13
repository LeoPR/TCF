---
title: T-STUDY-HIERARCHICAL-TCF — TCF para JSON aninhado (guarda-chuva: grupo de labs / peças)
status: open
priority: P2
created: 2026-07-05
updated: 2026-07-05
blocked-by: []
related:
  - experiments/lab/dirty/notas/estudo-tcf-hierarquico-mapa.md
  - experiments/lab/dirty/2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/
  - experiments/lab/dirty/2026-07-05-1543-tcf8-estrutura-aninhada-pessoa-telefones/
  - experiments/lab/dirty/2026-07-05-1608-linking-pai-filho-cabecalho/
  - experiments/lab/dirty/2026-07-05-1650-multicol-n-hierarquia/
  - experiments/lab/dirty/2026-07-05-1830-bracket-meta-hierarquia/
  - experiments/lab/dirty/2026-07-05-1840-estudo-notacoes-agrupamento/
  - experiments/lab/dirty/2026-07-05-1906-cardinalidades-inferencia/
  - experiments/lab/dirty/2026-07-05-2017-teoria-cardinalidade-forca/
  - experiments/lab/dirty/2026-07-05-2328-tcf8-schema-cardinalidade-explicito-implicito/
  - experiments/lab/dirty/2026-07-01-header-minimal/
  - experiments/lab/dirty/notas/teoria-cardinalidade.md
  - experiments/lab/dirty/2026-07-05-nested-tcf-study/result.md
  - datasets/coverage-matrix.md
  - experiments/lab/dirty/notas/dirty-lab-convencoes.md
---

# T-STUDY-HIERARCHICAL-TCF — TCF hierárquico (guarda-chuva)

**[probatório]** Estuda como representar um documento **aninhado** de API em TCF (tabular). Decorre do
pedido do owner (2026-07-05) por um "TCF aninhado similar ao JSON". **Não é 1 lab — é um GRUPO de peças
que se juntam.** Mapa do grupo + como as peças formam o todo:
[estudo-tcf-hierarquico-mapa.md](../experiments/lab/dirty/notas/estudo-tcf-hierarquico-mapa.md).

> **PROMOVIDO A WELD DO `.8` (owner 2026-07-13)**: o reescopo `.8`=feature-complete decidiu que a
> hierarquia entra no `.8`. Este guarda-chuva (feasibility, `confirmada-conceitual`) permanece a base
> **probatória**; o **weld** para `src/tcf` vive em **[T-CODE-TCF8H-WELD](T-CODE-TCF8H-WELD.md)**
> (dispositivo→exec, gate de CAPACIDADE — RT-exato em JSON aninhado real + non-regressão + aprovação
> `src/tcf`). O codec de referência é o EXP-015 (`experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/`).

## Peças (labs) — estado

- **P1** `1509-...tabelao-vs-2tabelas` — desnormalizar vs normalizar; RLE↔referência. (medido, RT OK)
- **P2** `1543-...tcf8-estrutura-aninhada` — 2 TCF.8 empilhados + envelope self-describing. (RT OK)
- **P3** `1608-...linking-pai-filho-cabecalho` — **abordagem A**: blocos empilhados + header de ligação
  pai/filho (hint `#TCF.8 N`, adjacência). Modular/buscável. (RT OK, S4+S6)
- **P4** `1650-...multicol-n-hierarquia` — **abordagem B**: 1 multi-col + flag `N` + linha `#H`. (RT OK)
- **P5** `1830-...bracket-meta-hierarquia` — **abordagem C** (mais enxuta): hierarquia em **colchetes no
  meta**; `M`/`N` + array-vs-objeto **deduzidos**; hierarquia opt-in. (RT OK, S4+S6)
- **P6** `1840-...estudo-notacoes-agrupamento` — **estudo** da notação (start/end vs contagem vs
  profundidade): bytes ~empatam, precisa de 1 portador de forma; escolha é parse/stream. (RT topologia OK)
- **P7** `1906-...cardinalidades-inferencia` — **cardinalidade** 1×1/1×N/N×1/N×N deduzida dos dados (FD)
  → mecânica TCF. **Amarra o grupo**: 1:N↔hierarquia (dual RLE), N:1↔@dict (já existe), N:N↔ponte. (4 casos OK)
- **P8** `2017-...teoria-cardinalidade-forca` + [teoria-cardinalidade.md](../experiments/lab/dirty/notas/teoria-cardinalidade.md)
  — **TEORIA**: força (forte/fraca/quase/induzida) + rápido(RLE)-vs-pleno(OBAT/HCC) + **ortogonalidade**
  (cardinalidade ⊥ compressibilidade) + **cascade** (Parquet). Hipóteses **H-CARD-01..07** no roadmap. (medido)
- **P9** `2328-...tcf8-schema-cardinalidade-explicito-implicito` — **PONTE com o header-minimal**: a
  linguagem semântica TCF.8 (cardinalidade/hierarquia) **explícita → dedução → mínima**. A forma mínima
  **converge pra P5**; irredutível = magic + arestas de hierarquia + markers + sizes; **custo transmitido
  ZERO** (o resto é deduzido). Fecha o círculo header-minimal (O-FMT-14) × hierárquico. (medido, RT OK)
- **P10-P11 (futuro, exige aprovação — toca src/formato)**: protótipo TCF.8 (arestas explícitas + resto
  deduzido) + O-FMT-14 derivável · link posicional / N:N (repetition level) p/ array-in-array e N raízes.

> **NOTA (2026-07-05)**: este grupo é um **detour de teoria/estrutura** a partir do estudo **header-minimal**
> (o "plano geral"). Feasibility mapeada (P1–P8, tudo RT OK, `confirmada-conceitual`, nada em `src/tcf`).
> **Próximo do owner**: revisar tickets → voltar ao header-minimal. Consolidação (P9) fica para quando o
> owner decidir a base A/B/C.

## Pergunta

Duas representações do mesmo documento aninhado:
- **A · tabelão (cross)**: desnormaliza (contexto repetido por linha) → 1 TCF; o RLE colapsa a repetição.
- **B · duas tabelas**: normaliza (T0 contexto 1×, T1 série + fk) + manifest → 2 TCFs ligados por cabeçalho.

Qual custa menos, e sob qual condição (payload plano vs reconstrução exata do JSON)?

## Estado (2026-07-05) — feasibility MEDIDA (lab)

Lab [2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas](../experiments/lab/dirty/2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/)
— artefatos reproduzíveis (`run.py`), decode reconstrói o JSON (OK). Achado (`artifacts/05-bytes-medida.txt`, brotli q11):
- **Reconstrução** (precisa do JSON): **B vence** M=1 (297<314) e M=3 (354<370) — robusto.
- **Plano** (só a tabela): empate dentro do ruído (<1KB, overhead-dominado).
- **Princípio**: a multiplicidade ×N é conservada; **RLE ↔ referência são duais** (mesma info, ~mesmo
  tamanho). O schema não compra compressão, compra **reconstrução** — e B herda a partição pai/filho de
  graça (colocação física), enquanto A precisa enumerá-la. Prior art: **factorized DBs** (Olteanu &
  Zavodny), **Dremel/Parquet** rep/def levels (Melnik 2010), **Heath** (integridade sse chave).

## Próximos passos (progressão dirty)

- [ ] **Realista**: >1k linhas, contexto pesado (muitas colunas de equipment longas) — onde B deve abrir.
- [ ] **Bordas**: M=1 série de 1 ponto; colunas 100% constantes vs 100% distintas; dedução vs schema.
- [ ] **Extrapolação**: M grande (muitos equipamentos), achar o **crossover** exato fora do ruído.
- [ ] **Gate real-world** (Adult/TPC-H ou telemetria real) antes de qualquer `confirmada-empirica`.
- [ ] Variantes: manifest enxuto; **fk implícita por ordenação** (dropar a coluna fk); schema deduzido
      vs explícito (custo de integridade).
- [ ] Se a ideia provar: **abrir zero** no proto formal (não copiar `hierlib.py`).

## Relação

Complementa T-DATA-TRANSMISSION-GROUPING (forma-tx `nested-response`) e o nested-tcf-study (envelope +
blocos). Aqui é o **como** de um ramo aninhado; lá é o **envelope** que embrulha os blocos.
