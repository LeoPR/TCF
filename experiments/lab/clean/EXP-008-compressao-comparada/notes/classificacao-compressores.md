# Classificacao de compressores por natureza de uso

## Esquema

Cada compressor recebe uma ou mais **classes** que descrevem
**onde** ele e' usado na pratica.

| Classe | Definicao | Standard |
|---|---|---|
| `web/http` | Content-Encoding aceito em HTTP/1.1+ e HTTP/3 | IANA HTTP Content Coding Registry |
| `file/archive` | Compressao de arquivo, streaming arquivado, backup | UNIX tradition + format specs |
| `parquet` | Compressor padrao em Apache Parquet (columnar) | Parquet format spec |
| `general` | Standalone, sem caso de uso especifico ancorado | n/a |

Um compressor pode estar em multiplas classes — por exemplo `gzip`
e' nativo em **todas as 4**.

## Tabela

| Compressor | Lib | Nivel | web/http | file/archive | parquet | general | RFC / spec |
|---|---|---:|:---:|:---:|:---:|:---:|---|
| `gzip` | gzip (stdlib) | 9 | ✓ | ✓ | ✓ | ✓ | RFC 1952 |
| `brotli` | brotli 1.2.0 | 11 | ✓ |  | ✓ |  | RFC 7932 |
| `zstd` | zstandard 0.25.0 | 22 | ✓ | ✓ | ✓ | ✓ | RFC 8478 |
| `lzma` (xz) | lzma (stdlib) | 9 (preset) |  | ✓ |  |  | xz format |
| `bz2` | bz2 (stdlib) | 9 |  | ✓ |  |  | BWT (Burrows-Wheeler) |

## Justificativas por compressor

### `gzip` — universal

DEFLATE (LZ77 + Huffman). Vinculado a HTTP desde HTTP/1.1
(RFC 1945, 1996). Suportado em todo browser / servidor / proxy /
Parquet engine. Implementacao mais conservativa: rapido, ratio
medio, baixo overhead. Classes: `web/http`, `file/archive`
(`.tar.gz` ubíquo), `parquet` (suportado nativo), `general`.

### `brotli` — web-first

Desenvolvido pela Google (RFC 7932, 2016) com **dicionario
estatico de 120 KB** otimizado pra HTTP text content (HTML/CSS/JS).
Quality 11 e' lento (~1500us em paginas pequenas) mas atinge
ratios menores que gzip-9. Adotado em Parquet (Apache 1.10+) por
ser eficaz em text columns. **Nao usado em arquivos
gerais** (no Linux/Unix archivers).
Classes: `web/http`, `parquet`.

### `zstd` — escalavel

Desenvolvido pelo Facebook (RFC 8478, 2018). Range de nivel **1-22**
muito amplo. Level 22 e' lento (~100us / variavel) mas atinge ratio
comparavel a xz com decompress muito rapido (~3us). Suportado em
HTTP (`Content-Encoding: zstd`), em `.tar.zst`, e em Parquet. Por
versatilidade, **e' classificado em todas as 4 classes**.

### `lzma` (`xz` format) — arquivo

LZMA2. Foco em ratio maximo, **muito CPU-intensivo** (~55ms /
operacao em paginas pequenas no level 9). Nao adotado em HTTP por
custo de descomprimir. Comum em distribucoes Linux
(`Packages.xz`), em `.tar.xz`, em PyPI sdists. **Apenas
`file/archive`**.

### `bz2` — arquivo legado

Burrows-Wheeler Transform + Huffman. Foi popular em backups Linux
nos 2000s, depois superseded por xz/zstd. **Nao usado em HTTP**
(nao tem token oficial Content-Encoding). Adotado em alguns
arquivos `.tar.bz2`. **Apenas `file/archive`**, mantido pra
referencia historica.

## Compressores ausentes (gap conhecido)

| Compressor | Por que falta | Classes esperadas |
|---|---|---|
| `snappy` | Padrao Parquet default; precisaria `python-snappy` (binding C) | `parquet`, `general` |
| `lz4` | Comum em Parquet (lz4_raw, lz4_hadoop); precisaria `lz4` | `parquet`, `file/archive` (.tar.lz4) |
| `lzo` | Legado em Hadoop/Parquet; precisaria `python-lzo` | `parquet` |
| `deflate` raw | Equivalente a gzip sem header; redundante aqui | `web/http` |

Adicionar futuros se necessario pra completar `parquet` class.

## Como reports usam as classes

- [`02-bytes-por-classe.md`](../reports/02-bytes-por-classe.md) —
  tabela por classe, com **menor por classe** marcado pra cada
  dataset.
- O ranking de **classe campea** mostra:
  - `web/http` vence ou empata em **15/15 datasets** (esperado;
    inclui brotli e zstd que sao os mais agressivos).
  - `parquet` empata com `web/http` em todos (mesma intersecao:
    gzip + brotli + zstd).
  - `general` (gzip + zstd) e' segundo lugar.
  - `file/archive` puro (lzma + bz2) e' inferior nessa escala.
