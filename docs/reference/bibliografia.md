# Bibliografia — fundamentos de literatura do TCF (compressão colunar / lazy / DSL)

**Tipo**: reference (Diataxis). **Construída**: 2026-06-27 via survey multi-workstream +
**verify anti-alucinação** (cada citação checada na web; 24 recomendadas, **24 verificadas reais,
0 rejeitadas**). Organiza a literatura pelos [5 workstreams](../../experiments/lab/dirty/notas/resegmentacao-workstreams-2026-06-27.md).

> **Estado**: NÃO há PDFs baixados pra esses temas (os PDFs em `Z:/caches/corpus/pdf2md/` são
> corpus do pdf2md — Transformer/BERT, sem relação). **Este doc É a biblioteca** (lista curada +
> alvo de download). Antes desta varredura o repo só citava 2 destes (Roaring, FOR) — a literatura
> de column-store/compressão estava sub-referenciada.

## Fundacionais (cross-cutting W1+W2+W3 — baixar primeiro)
- **Abadi, Madden, Ferreira (2006)** — *Integrating Compression and Execution in Column-Oriented
  Database Systems.* SIGMOD 2006, 671-682. DOI 10.1145/1142473.1142548.
  → **A referência-mãe**: cataloga RLE/dict/bit-vector/FOR e funda "operar sobre o comprimido sem
  materializar" = o pilar lazy/O(1) do TCF + V2-B (ADR-0025) + o bit-vector = a nature bool→bits (W2).
- **Abadi, Boncz, Harizopoulos, Idreos, Madden (2013)** — *The Design and Implementation of Modern
  Column-Oriented Database Systems.* Foundations and Trends in Databases 5(3), 197-280. DOI 10.1561/1900000024.
  → **Survey/livro-texto de facto**: late materialization + vectorized exec + operate-on-compressed
  num só lugar. Dá nome acadêmico ao decode-DAG do hquery01 (W3).
- **Stonebraker et al. (2005)** — *C-Store: A Column-oriented DBMS.* VLDB 2005, 553-564.
  → Fundador do column-store moderno; projeções ordenadas = o knob `sort_by`→RLE do TCF (W1/W3).
- **Melnik et al. (2010)** — *Dremel: Interactive Analysis of Web-Scale Datasets.* PVLDB 3(1),
  330-339. DOI 10.14778/1920841.1920886.
  → Linhagem Dremel→Parquet; column-pruning/predicate-pushdown (V2-K); NULLs via definition levels
  (modelo pro tratamento de vazio/ausência no W2, alternativo ao null-bitmap denso).

## W1 — Cross-dict same-domain (dicionário compartilhado)
- **Apache Parquet — "Encodings" spec** (RLE_DICTIONARY, enum 8). https://parquet.apache.org/docs/file-format/data-pages/encodings/
  → O desenho que o V2-B reproduz no textual (dict por column-chunk + índices RLE/bit-packed +
  fallback). O escopo **per-coluna** do Parquet é exatamente o que o W1/H-GDICT quer **generalizar**
  pra cross-column.
- **Zukowski, Heman, Nes, Boncz (2006)** — *Super-Scalar RAM-CPU Cache Compression.* ICDE 2006.
  DOI 10.1109/ICDE.2006.150.
  → PDICT/PFOR/PFOR-DELTA: a trinca dict+FOR+delta com fallback/patches. Informa V2-B (PDICT) +
  seq-RLE multi-delta (ADR-0016 ~ PFOR-DELTA).
- **Raman, Swart (2006)** — *How to Wring a Table Dry: Entropy Compression of Relations and Querying
  of Compressed Relations.* VLDB 2006, 858-869.
  → **Diretamente relevante ao caveat "some sob brotli"**: dá o **piso de entropia** que um dict-index
  textual persegue + o argumento de query-sobre-comprimido. Baliza o que vale otimizar antes de o
  brotli recuperar.

## W2 — Binarização por nature (bool/categórica → bits)
- **Wu, Otoo, Shoshani (2006)** — *Optimizing bitmap indices with efficient compression.* ACM TODS
  31(1), 1-38. DOI 10.1145/1132863.1132864.
  → WAH (Word-Aligned Hybrid), o esquema seminal de bitmap comprimido word-aligned. Vocabulário
  (literal vs fill words) pra decidir se a nature bool deve ser bitmap alinhado.
- **Lemire, Kaser, Aouiche (2010)** — *Sorting improves word-aligned bitmap indexes.* DKE 69(1), 3-28.
  → EWAH + prova que **ordenar reduz o índice ~9×**. Conecta `sort_by` à binarização bool (sort
  multiplica a compressão do bit-vector, não só do RLE textual) → base pra um gate "binarizar+sort".
- **Goldstein, Ramakrishnan, Shaft (1998)** — *Compressing relations and indexes.* ICDE 1998, 370-379.
  **[já citado no repo]** → Frame-of-Reference (min + offsets em bits mínimos); o análogo binário do
  delta/min_len textual do TCF; liga V2-L a colunas numéricas curtas.
- **Chambi, Lemire, Kaser, Godin (2016)** — *Better bitmap performance with Roaring bitmaps.* SP&E
  46(5), 709-719. DOI 10.1002/spe.2325. **[já citado no repo]** → Roaring: encoding por container
  (denso/esparso/runs) — o padrão "escolher encoding por chunk" aplicável a chunks de N rows.

## W3 — Decode paralelo + lazy multi-coluna
- **Abadi, Myers, DeWitt, Madden (2007)** — *Materialization Strategies in a Column-Oriented DBMS.*
  ICDE 2007, 466-475.
  → **Fonte do termo "late materialization"** que nomeia o W3; funda o "adiar materialização" do
  hquery01 (agg-filtrada ~7.9% do blob).
- **Boncz, Zukowski, Nes (2005)** — *MonetDB/X100: Hyper-Pipelining Query Execution.* CIDR 2005,
  225-237.
  → Execução vetorizada (vector-at-a-time): o modelo acadêmico pro scan vetorizado do dict-stream +
  paralelismo-por-coluna (hquery01 §9.2, H-QUERY-04c).
- *(+ Chambi Roaring 2016, acima)* → multi-predicate AND = interseção de bitmaps (o `.tcfx` / sidecar
  quando há múltiplos predicados).

## W4 — TCFL (linguagem de spec compilável, no-eval)
- **Ford (2004)** — *Parsing Expression Grammars: A Recognition-Based Syntactic Foundation.* POPL
  2004, 111-122. DOI 10.1145/964001.964011.
  → PEG (escolha priorizada `/`, sem ambiguidade): fundamento do parser da DSL + a "linguagem de
  expressão restrita" do F5.
- **Hutton, Meijer (1998)** — *Monadic Parsing in Haskell.* JFP 8(4), 437-444. (+ tech report
  *Monadic Parser Combinators*, NOTTCS-TR-96-4, 1996.)
  → **Parser/transform combinators**: compor parsers de primitivas pequenas = o modelo exato do
  "compõe, não escreve código" do F5. *(verify: a citação original confundia os dois títulos —
  corrigido aqui.)*
- **Mettler, Wagner, Close (2010)** — *Joe-E: A Security-Oriented Subset of Java.* NDSS 2010.
  → **Resolve a tensão expressividade × no-eval** do F5 com precedente: segurança por **subset
  auditável** (remover construções perigosas), não por filtrar entrada arbitrária. Nomeia o
  invariante "vocabulário fechado / least-privilege" do natures_compiler.
- **ISO/IEC 7064:2003** — *Check character systems.* (supersedes ISO 7064:1983.)
  → Spec normativa dos check-digits (mod-M puros e híbridos): ancora a biblioteca fechada de
  check-fns (mod11-cpf/cnpj/luhn) + o vocabulário aritmético que o F5 cogita expressar.
- **Pezoa, Reutter, Suárez, Ugarte, Vrgoč (2016)** — *Foundations of JSON Schema.* WWW 2016, 263-273.
  DOI 10.1145/2872427.2883029.
  → Primeira formalização de DSL declarativa de validação; precedente pro `.dsl` flat + round-trip
  como semântica + schema-on-read (spec no header #TCF.8).
- *(+ Thompson (1968), CACM 11(6), 419-422 — regex→NFA linear: base do template→regex do
  natures_compiler; matching seguro/linear.)*

## Lacunas / prioridade de download (se virar paper-library)
1. **Abadi 2006 + survey 2013** — cobrem W1/W2/W3 num par; maior retorno.
2. **Raman & Swart 2006** — o argumento de entropia/query-sobre-comprimido (responde o caveat brotli).
3. **Joe-E 2010 + ISO 7064 + Ford PEG 2004** — a tríade que sustenta o W4 (no-eval + check-digit + gramática).
Os demais são reforço. Roaring e FOR já estavam citados (não precisa re-introduzir).

## Cross-links
[re-segmentação 5 workstreams](../../experiments/lab/dirty/notas/resegmentacao-workstreams-2026-06-27.md),
[dict-referencia-hipoteses](../../experiments/lab/dirty/notas/dict-referencia-hipoteses.md) (W1),
[filtros-dsl-plano](../../experiments/lab/dirty/notas/filtros-dsl-plano.md) (W4/F5),
ADR-0016 (seq-RLE), ADR-0018 (V2-L/V2-J/V2-K), ADR-0025 (V2-B).
