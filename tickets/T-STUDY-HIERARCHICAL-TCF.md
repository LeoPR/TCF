---
title: T-STUDY-HIERARCHICAL-TCF — TCF para estrutura hierárquica completa
status: open
priority: P2
created: 2026-07-05
updated: 2026-07-13
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
  - experiments/lab/dirty/2026-07-13-dataseth-json-bridge/
  - experiments/lab/dirty/2026-07-13-1835-dataseth-special-scalars/
  - experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md
  - datasets/coverage-matrix.md
  - experiments/lab/dirty/notas/dirty-lab-convencoes.md
---

# T-STUDY-HIERARCHICAL-TCF — TCF para estrutura hierárquica completa

**[probatório]** Estuda como representar uma estrutura de dados **hierárquica** em TCF. JSON é a primeira
fonte de pesquisa, não o contrato de origem. Decorre do pedido do owner (2026-07-05) por um "TCF aninhado
similar ao JSON". **Não é 1 lab — é um GRUPO de peças
que se juntam.** Mapa do grupo + como as peças formam o todo:
[estudo-tcf-hierarquico-mapa.md](../experiments/lab/dirty/notas/estudo-tcf-hierarquico-mapa.md).

O plano atual de pesquisa, incluindo a hipótese de `null`, `NaN` e infinitos, está em
[dataseth-hierarquia-completa-plano.md](../experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md).

> **PROMOVIDO A WELD DO `.8` (owner 2026-07-13)**: o reescopo `.8`=feature-complete decidiu que a
> hierarquia entra no `.8`. Este guarda-chuva (feasibility, `confirmada-conceitual`) permanece a base
> **probatória**; o **weld** para `src/tcf` vive em **[T-CODE-TCF8H-WELD](T-CODE-TCF8H-WELD.md)**
> (dispositivo→exec, gate de CAPACIDADE — RT-exato do DatasetH + adaptador JSON de prova + non-regressão
> + aprovação `src/tcf`). O codec de referência é o EXP-015 (`experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/`).

## REFOCO 2026-07-13 — pesquisa antes do acoplamento

**[dispositivo→pesquisa]** O requisito é que o TCF entenda **estrutura hierárquica**, qualquer que seja a
fonte. JSON é apenas a primeira fonte conveniente para estudar o problema. O core não deve conhecer JSON,
nem criar uma API `encode_json`: `encode` continua sendo a única entrada de codificação do core, e os
adaptadores de fonte/saída ficam fora de `src/tcf`.

### Vocabulário provisório

- **Documento de origem**: JSON, resposta de API, banco, Arrow, ou outra fonte que contenha uma árvore.
- **DatasetH**: nome provisório do dataset hierárquico intermediário. Ele deve carregar a estrutura de
  objetos/arrays, folhas, ordem, tipos, `null`, ausência/presença e repetição sem depender de JSON.
- **TCF.H**: representação textual dessa estrutura no wire format `#TCF.8H`.
- **Adaptador de saída**: transforma o DatasetH decodificado em JSON, outro banco ou outra representação.

O tipo Python concreto de DatasetH ainda não está decidido. Primeiro se congela a semântica; depois se
escolhe a representação que melhor separa topologia, folhas e metadados.

### Caminho feliz de pesquisa

```text
fonte (JSON, API, banco, ...)
  -> adaptador da fonte
  -> DatasetH
  -> encode(DatasetH)
  -> TCF.H (#TCF.8H)
  -> blob_tcf
  -> decode(blob_tcf)
  -> DatasetH
  -> adaptador de saída
  -> JSON, outro banco ou outra representação
```

O primeiro caso executável será:

```text
JSON -> DatasetH -> TCF.H -> blob_tcf -> DatasetH -> JSON
```

O teste central do core será `decode(encode(dataset_h)) == dataset_h`. O teste JSON fica na camada do
adaptador: `json -> DatasetH` e `DatasetH -> json`. Assim, uma aprovação do caminho JSON não transforma
JSON em dependência semântica do TCF.

### Pesquisa das bibliotecas

| biblioteca | o que entrega | papel possível | limite para o DatasetH |
|---|---|---|---|
| [`json`](https://docs.python.org/3/library/json.html) | `dict`/`list`/escalares Python; `object_hook` e `object_pairs_hook` | primeiro parser e adaptador de fonte | não define dataset, schema ou topologia colunar |
| [`pandas.json_normalize`](https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html) | DataFrame flat por `record_path`/`meta` | steelman de flatten e comparação | achata a árvore e exige decisões de normalização |
| [`pyarrow.json`](https://arrow.apache.org/docs/python/json.html) + tipos Arrow | `struct`/`list`/`map`, tipos e nulls em arrays colunares | referência externa para uma árvore colunar | dependência opcional; leitor JSON aceita JSON Lines, não é contrato do core |
| [`ijson`](https://github.com/ICRAR/ijson) | itens por prefixo ou eventos `start_map`/`map_key`/`start_array` | parser streaming para fontes grandes | produz eventos/objetos; o adaptador ainda precisa construir DatasetH |

Conclusão da primeira passada: a biblioteca `json` resolve a **leitura da árvore**, `pandas` resolve um
**flatten tabular**, Arrow oferece a comparação mais próxima de um **dataset colunar hierárquico**, e
`ijson` resolve a **leitura incremental**. Nenhuma substitui a especificação do DatasetH. O core continua
sem dependências externas; as comparações vivem em experimento ou gadget.

### Etapas de pesquisa

- [x] **R0a — plano de escopo**: registrar o estudo de DatasetH/hierarquia completa e a hipótese
  H-HIER-SCALAR-01 em [dataseth-hierarquia-completa-plano.md](../experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md).
- [ ] **R0b — vocabulário e contrato**: definir DatasetH, topologia, tipos, presença, repetição, ordem,
  raízes escalares e limites; separar equivalência semântica de preservação lexical do JSON. Inclui a
  matriz de `null`, `NaN`, `+Infinity`, `-Infinity`, strings colidentes e ausência; `bN` é candidato de
  representação, não a definição desses valores.
- [ ] **R1 — adaptador JSON**: `json.loads`/`object_pairs_hook` para a primeira implementação; testar
  `null`, objetos ragged, arrays mistos/nested, vazios, Unicode, LF e números sem stringificação.
- [ ] **R2 — comparação de representações**: comparar árvore Python, `json_normalize`, Arrow nested e
  eventos `ijson`; medir o que cada forma preserva e o que precisa de side-channel.
- [ ] **R3 — DatasetH independente da fonte**: construir um fixture equivalente sem passar por JSON e
  provar que o mesmo DatasetH pode ser alimentado por outra origem.
- [ ] **R4 — codec externo TCF.H**: testar `DatasetH -> TCF.H -> DatasetH` sem tocar `src/tcf`.
- [ ] **R5 — decisão de acoplamento**: somente após R0-R4 definir a superfície de `encode`/`decode` e
  abrir o weld do core; nenhum import de JSON deve entrar em `src/tcf`.

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

## Pergunta histórica

Duas representações do mesmo documento aninhado:
- **A · tabelão (cross)**: desnormaliza (contexto repetido por linha) → 1 TCF; o RLE colapsa a repetição.
- **B · duas tabelas**: normaliza (T0 contexto 1×, T1 série + fk) + manifest → 2 TCFs ligados por cabeçalho.

Qual custa menos, e sob qual condição (payload plano vs reconstrução exata da estrutura de origem)?

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
