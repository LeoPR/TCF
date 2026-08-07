# Descompressão O(1): quem faz, quem diluiu, quem morreu — e onde o bN cai

**2026-08-07 · levantamento (não é lab; nada foi medido pelos terceiros citados)**

Pergunta do owner: *"pesquise compressores atuais que trabalhem com dados e façam
descompressão O(1) — ou eles são 'diluídos' nos compressores atuais, ou não são mais
usados?"*

Método: 6 varreduras independentes com busca web + 3 lentes adversariais + crítico de
completude (83 achados brutos, 33 refutações). O que a verificação derrubou **manda** sobre
o que a varredura trouxe. Duas coisas foram conferidas **nesta máquina** e estão marcadas
como tal; todo o resto é reportado por terceiros e, pela regra §RT, **não vira afirmação do
TCF sem replicação**.

---

## A resposta curta

**Nenhum compressor de propósito geral faz acesso O(1) por elemento — e nenhum jamais
fez.** Não foi trocado: nunca entrou no design. O que se vende como "random access" em
gzip/zstd/xz/lz4 é **seek de bloco**: O(1) até o bloco, O(bloco) dentro.

A técnica de largura fixa não morreu nem foi diluída nos compressores. Ela **saiu deles** e
foi morar na camada que não comprime (Arrow in-memory) e nos formatos colunares. Está em
retorno desde ~2020 (FSST, FastLanes, ALP, Lance, Vortex).

## A divisão que explica tudo

Duas propriedades **independentes** matam o endereço calculável:

1. **Código de tamanho variável** — Huffman, FSE/ANS, range coder. Se o símbolo `i` não
   ocupa um número fixo de bits, "o bit `i*w`" não existe.
2. **Dependência entre valores** — janela LZ77, back-reference, delta.

A prova de que são independentes: **Snappy é 100% byte-alinhado, sem codificador de
entropia nenhum, e ainda assim é O(n) por elemento** — porque um `copy` referencia a saída
já produzida. **Byte-alinhamento não compra endereço; posição fixa por elemento compra.**

O vocabulário útil vem do paper do Lance (arXiv:2504.15247): encoding **transparente** não
introduz dependência entre valores (bit-packing, dicionário); **opaco** introduz (delta,
back-reference). *Transparência é metade do caminho — a outra metade é localização.*

## Os quatro regimes

| regime | quem está aí | o que paga |
|---|---|---|
| **O(1) real** — endereço calculável | Arrow fixed-size (`addr = base + i*width`), Arrow dictionary, validity bitmap; `int_vector<w>` do sdsl; **Lucene `DirectReader`/`DirectWriter`** | razão ≈ 0 (Arrow não comprime) |
| **O(1) com auxiliar succinct** | rank/select de bitvector (LOUDS no Google Mozc), RRR, Elias-Fano | espaço extra — e **na prática Θ(n), não o(n)**: 0,78%–25% de `n` é fração constante |
| **O(1) até o bloco + O(bloco) dentro** | zstd seekable, BGZF, dictzip, xz Index, Parquet Page Index, ORC RowIndex, ClickHouse LowCardinality | razão; e várias dessas tabelas guardam **tamanhos, não offsets** → prefix-sum |
| **O(log n)** | Arrow Run-End Encoded (a spec declara), gramática/SLP (Bille et al.), Roaring | — |

Pior que os quatro: **Parquet `RLE_DICTIONARY` é O(página) linear por elemento.**

## O achado que interessa ao TCF

**O bN não é o `RLE_DICTIONARY` do Parquet — e a diferença é o ponto inteiro.**

O Parquet tem as duas peças (dicionário + largura fixa) e então **embrulha os índices em
runs de comprimento variável** (headers ULEB128 alternando run bit-packed e run RLE, sem
índice de runs) — o que destrói o endereço que ele acabara de ter. O `BIT_PACKED` puro, o
único que teria endereço, está **deprecado** na spec.

O bN, por manter só a parte bit-packed **sem enquadramento de run**, preserva um endereço
que o Parquet deu de presente.

> ⚠️ **Não verificado.** O crítico registrou que não se achou declaração normativa do
> Parquet dizendo "não há acesso posicional dentro da página" — é inferência a partir da
> compressão de página + estrutura alternada de runs. **Um lab fecharia isso**, e enquanto
> não fechar, "diferencial real e verificável" é hipótese, não achado.

### O base64 preserva o endereço? Sim — mas ele não é a causa

RFC 4648 é mapeamento posicional puro, sem estado: 6 bits por char, grupos de 24 bits →
4 chars. Logo o bit `b` mora no char `⌊b/6⌋`. Padding `=` só no fim. Ressalva: a fórmula
depende de **não quebrar linha** (o RFC proíbe LF salvo quando a spec de cima mandar).

O controle negativo é decisivo: **Source Maps (ECMA-426) usa o mesmo alfabeto base64 e é
100% sequencial** — VLQ (largura variável) + valores em delta. Um formato textual
universalmente deployado, com base64, sem nenhum acesso aleatório. **A largura fixa é que
compra o endereço; o base64 apenas teve a decência de não destruí-la.**

### O domínio quebra o O(1)?

Não quebra — converte em duas fases. Índice → **posição** é O(1) puro. Índice → **valor**
exige localizar a k-ésima entrada de um corpo TCF de comprimento variável: sem tabela, é
O(k). O regime honesto do bN é **O(k) uma vez + O(1) por célula depois** — o que todo
dicionário faz, e não é "ler a célula `i` sem tocar no resto".

## Medido aqui (não é terceiro)

Sonda sobre o wire que o encoder já produz, chegando na célula `i` sem descomprimir a
coluna, contando bytes tocados:

| caso | wire | domínio | payload tocado / célula |
|---|---:|---:|---|
| k=2, n=2000 | 351 B | 3 B (plano) | **4 B** |
| k=4, n=2000 | 688 B | 7 B (plano) | **4 B** |
| k=16 prefixo comum | 1358 B | 10 B (comprimido) | **4 B** |
| k=16 sem prefixo | 1418 B | 70 B (comprimido) | **4 B** |
| k=100 ids | 2361 B | 13 B (comprimido) | **4 B** |

Conferido contra o `decode` completo em todas as posições testadas. 4 bytes por célula,
**independente de n=2000**. O domínio é decodificado uma vez (3–70 B).

> A sonda é de terminal, não é lab gravado. Vale como indício de que a propriedade existe
> no formato; **não** vale como número publicável. O lab é trabalho separado.

## Diluído, vivo ou morto

Só conta como **diluído** o que tem linhagem rastreável — descendente citando ancestral.

| técnica | estado | onde hoje | por quê |
|---|---|---|---|
| bit-packing largura fixa | vivo-mainstream | Arrow, sdsl, **Lucene**, DuckDB | é o piso; toda succinct constrói em cima |
| dicionário + índices largura fixa | vivo-mainstream | Arrow, ClickHouse LowCardinality, Parquet | convergência independente, não linhagem |
| Elias-Fano | vivo, nome intacto | folly, Erigon, PISA | ficou 40 anos parado; voltou com popcount/broadword |
| LOUDS / succinct trie | vivo, em produto | Google Mozc, marisa-trie | dicionário que precisa caber em RAM de dispositivo |
| FM-index | vivo, em expansão | BWA/Bowtie2, infini-gram mini | vive onde o índice é **menor** que o texto. É busca, não acesso |
| BBC (Antoshenkov) | **diluído** — linhagem citada | WAH, EWAH, Concise; EWAH é o formato dos `.bitmap` do Git | o paper do Roaring cita a descendência |
| BPE (Gage 1994) | reaproveitado, linhagem citada | tokenizer de GPT/Llama | sobreviveu algoritmo e nome; morreu o propósito |
| FSST/ALP/FastLanes → Vortex | **diluído** — o descendente credita | Vortex (core extension do DuckDB, 2026-01) | único caso documentado pelo próprio descendente |
| ETDC / (s,c)-Dense Code | morto | nada | varint (MIDI 1983, DWARF, Protobuf) é mais velho e **independente** |
| Ferragina-Venturini | morto por refutação medida | nada | ponteiros densos comeram toda a compressão |
| Succinct (NSDI'15) | morto | repo dormente | vendeu "query sobre comprimido" como produto genérico |
| Zuckerli, DivANS | mortos | repos arquivados | densidade sem velocidade não tem mercado |

**A lição do cemitério:** quem troca velocidade de acesso por razão **em estrutura
navegável** perde (Zuckerli). Quem troca razão por acesso, e o acesso importa, ganha
(Roaring venceu WAH exatamente nesse eixo, e disse por quê).

---

## O que o crítico derrubou

Registrado porque é a parte que costuma sumir.

1. **PFOR/PFOR-DELTA ficou de fora** da varredura inteira — e **já estava na nossa própria
   bibliografia** (`docs/reference/bibliografia.md:33-36`, Zukowski et al. 2006).
   *Conferido aqui: está lá.* A pesquisa perdeu uma linhagem que o repo já tinha.

2. **`DirectReader`/`DirectWriter` do Lucene é exatamente o acessor `get(payload, w, i)`**
   que a síntese propunha como direção nova. Está em produção há uma década.
   **Conferido aqui, no fonte:**
   ```java
   static final int[] SUPPORTED_BITS_PER_VALUE =
         new int[] {1, 2, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64};
   ```
   "*Class for writing packed integers to be directly read from Directory. Integers can be
   read on-the-fly via DirectReader.*"
   Isso derruba duas coisas da síntese: (a) o acessor não é território inexplorado; (b) o
   bN **não** "desce abaixo do piso do mainstream" — Lucene tem 1, 2 e 4 bits. Isso valia
   pro Arrow (piso int8), não pro mainstream em geral.

   **Inversão interessante:** o conjunto do Lucene é *restrito* ({1,2,4,8,12,16,…}). O TCF
   usa **todo inteiro de 1 a 8** (`w = ceil(log2(k))`). Onde `k=5`, o TCF gasta 3 bits e o
   Lucene arredondaria pra 4. Nesse eixo o TCF é mais fino que o Lucene — não menos.

3. **Negativas universais sem fonte**: "nenhum jamais fez", "ninguém implementou Bille et
   al. de forma geral", "ETDC morto / FV morto" (ausência de evidência tratada como
   evidência de ausência). Ficam como leitura, não como fato.

4. **Três saltos não marcados** numa mesma frase: DuckDB desempacota grupo de 32
   (`BITPACKING_ALGORITHM_GROUP_SIZE = 32`) → "o O(1) por célula perde no hardware" →
   "confirma a conclusão do repo de que o eixo do bN é latência". A causa provável é o
   modelo vetorizado (vector 2048), **não** custo por célula. **É hipótese**, e ia ser
   citada internamente como medição.

5. **A pergunta do owner ficou sem resposta no eixo que importa.** A tabela responde no
   eixo binário/colunar e nunca no **textual**, que é onde o TCF vive. O veredito direto:
   registro de largura fixa em texto (COBOL, NACHA, `.fai`) **não foi diluído — foi
   deslocado** por delimitador + campo variável. E **ninguém tentou-e-abandonou larguras
   sub-byte em fio textual**. Não há cemitério nesse eixo porque não houve tentativa.

6. Também ficaram de fora: **DACs** (Brisaboa/Ladra/Navarro — *a* técnica de largura
   variável com acesso direto, o comparando natural do bN), **wavelet tree**, os **marks
   do ClickHouse** (`.mrk` = par de offsets absolutos) e **FlatBuffers/Cap'n Proto**
   (tabela de offsets no cabeçalho: existe, só não é textual).

## Direções (não são tickets)

1. **Acessor `get(payload_b64, w, i)`** — aritmética `⌊i*w/6⌋` + shift/mask, sem decodar a
   coluna. Transforma propriedade de formato em propriedade de código. **Precedente:
   `DirectReader` do Lucene.** Não é novidade; é dever de casa.
2. **Se o header virar índice, gravar offsets ABSOLUTOS, não tamanhos.** Tamanhos habilitam
   *split*, não *endereço* — cuidado direto sobre `tcf8h-header-checklist.md:45`. zstd
   seekable e xz Index guardam tamanho e pagam prefix-sum; o dictzip fez isso em 1997 e
   ganhou um teto de ~1,8 GB de brinde. Se offsets doerem em bytes, o **stride** é o
   meio-termo com precedente: o PostgreSQL mediu no JSONB que offsets puros davam
   compressibilidade ruim e lengths puros davam O(N), e escolheu stride de 32.
3. **Trocar o vocabulário público**: parar de dizer "o bN dá O(1)"; dizer **"transparente,
   portanto elegível a acesso por valor assim que houver índice de localização"**. Custo
   zero, e evita o modo de falha mais comum do campo.
4. **Posicionar o bN contra Arrow/Vortex, não contra gzip.** Existe campo comparativo real
   desde 2024. (Os "100-200×" do Vortex são claim de fornecedor.)
5. **Medir no regime do TCF.** Toda a literatura succinct mede com n ≥ 10⁶, onde cache miss
   domina. O bN opera em dezenas a milhares de células, onde tudo cabe em L1 e o custo de
   *parse* domina a assintótica. **Não se achou ninguém que tenha medido esse regime** — é
   o lab que separaria o TCF da literatura, e ele não existe.

## Correção de rota registrada

A síntese apontou uma suposta divergência com
`docs/theory/vetores-de-comparacao-alem-de-bytes.md:23` ("todos atuais são sequenciais").
**Não é divergência** — conferido aqui: a linha está numa tabela cujo título é *"Vetores
não-byte para comparar **sintaxes**"*, seguida de *"Diferenças algébricas conhecidas (M2.A
vs M4.C1' vs M4.C1 v1)"*. O escopo é interno ao TCF, não compressores externos.

**Mas a linha ficou obsoleta por outro motivo, e esse é real:** ela era verdade em
2026-05-14; o bN (2026-07) quebrou a uniformidade — o payload de bits **não** é sequencial.
Registrado no próprio arquivo como atualização datada, sem reescrever a nota histórica.

## Fontes primárias

[Arrow Columnar Format](https://arrow.apache.org/docs/format/Columnar.html) ·
[Parquet Encodings.md](https://github.com/apache/parquet-format/blob/master/Encodings.md) ·
[zstd seekable README](https://github.com/facebook/zstd/blob/dev/contrib/seekable_format/README.md) ·
[RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.txt) ·
[Lucene DirectWriter (fonte)](https://raw.githubusercontent.com/apache/lucene/main/lucene/core/src/java/org/apache/lucene/util/packed/DirectWriter.java) ·
[Lucene DirectReader (javadoc)](https://lucene.apache.org/core/10_0_0/core/org/apache/lucene/util/packed/DirectReader.html) ·
[Lance, arXiv:2504.15247](https://arxiv.org/html/2504.15247v1) ·
[FSST, VLDB 2020](https://www.vldb.org/pvldb/vol13/p2649-boncz.pdf) ·
[DuckDB × Vortex](https://duckdb.org/2026/01/23/duckdb-vortex-extension) ·
[Zukowski et al. 2006 — já em `docs/reference/bibliografia.md:33`](../../../../../docs/reference/bibliografia.md)

Contexto no repo: [manual da família bN](../../../../../docs/reference/familia-bn-bits.md) ·
[EXP-016](../../../clean/EXP-016-bn-familia-bits/)
