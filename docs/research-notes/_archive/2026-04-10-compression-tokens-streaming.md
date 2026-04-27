# Pesquisa 2026-04-10: Compressao columnar, tokens e streaming

Documento consolidado de pesquisa sobre 4 temas levantados pelo usuario:

1. Compressao columnar avancada (SQL Server como guia)
2. Tokens vs caracteres em LLMs (por que importa)
3. Compressao stream / buffered (vs batch)
4. O "token" no nome TOON — onde esta na historia?

---

## 1. Compressao columnar — SQL Server e Vertipaq

### 1.1 Tecnicas usadas por columnstore (referencia)

SQL Server columnstore usa 5 tecnicas principais combinadas em cada segmento:

| Tecnica | O que faz | Aplica em |
|---------|-----------|-----------|
| **Value Encoding** | Transformacao matematica para reduzir tipo (ex: subtrair base, dividir por fator) | Numericos |
| **Dictionary Encoding** | Mapeia valores para IDs; pode ser global ou por segmento | Strings (esp >32 chars) |
| **Run-Length Encoding** | Valores consecutivos repetidos → count+value | Dados sorted/aggregated |
| **Bit Packing** | Usa exato numero de bits necessarios (1-10, 12, 21) | Inteiros apos value encoding |
| **Archival (XPRESS)** | Camada extra LZ-like | Opcional, para armazenamento frio |

Fonte: [SQL Server Data Compression](https://learn.microsoft.com/en-us/sql/relational-databases/data-compression/data-compression),
[Columnstore Overview](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview),
[Vertipaq Optimization](https://www.red-gate.com/simple-talk/databases/sql-server/bi-sql-server/vertipaq-optimization-and-its-impact-on-columnstore-compression/)

### 1.2 Como isso mapeia para TCF textual

TCF **nao pode** usar bit packing (e textual). Mas pode usar **equivalentes textuais:**

| SQL Server (binario) | TCF (textual) — proposta | Ticket |
|----------------------|---------------------------|--------|
| Bit packing (1-21 bits) | Reducao de digitos (`14744547` vs `147445.47`) | H-advanced-encodings |
| Value encoding (base + offset) | `base=X deltas=Y Z W` | H-advanced-encodings |
| Frame-of-Reference | `offset_from=X: Y Z W` | H-advanced-encodings |
| Dictionary por segmento | Ja temos via L3 | - |
| Min/max por segmento | `# STATS_local chunk=1-100: ...` | H-advanced-encodings |
| XPRESS archival | gzip/brotli externo | P-transport-compression (CLOSED) |

### 1.3 Decisao do encoder por segmento

**Observacao critica do SQL Server:** o encoder escolhe **automaticamente**
qual tecnica usar por segmento, baseado no conteudo. Nao e "L2 para tudo".

Exemplo:
- Coluna `id` sequencial → delta encoding
- Coluna `nome` repetitiva → dictionary
- Coluna `status` com valores consecutivos → RLE
- Coluna `total` com faixa estreita → Frame-of-Reference

**Isso pode virar `--level=auto`** no TCF: encoder analisa cada coluna
e escolhe a melhor tecnica.

### 1.4 Singlestore como referencia adicional

SingleStore (columnstore DB moderno) usa tecnicas similares mas abertas:
- String encoding: dictionary, run-length, bit packing
- Integer encoding: value encoding, delta, FOR
- Hybrid approach baseado em cardinality

Fonte: [SingleStore Docs on Columnstore Encoding](https://docs.singlestore.com/db/v9.0/reference/sql-reference/data-types/encoding-string-data-in-columnstore-tables/)

**Para o paper:** citar SQL Server e SingleStore como prior art em columnstore
binario. Posicionar TCF como "primeira aplicacao dessas tecnicas em formato
TEXTUAL para LLMs".

---

## 2. Tokens vs Caracteres — por que medir tokens

### 2.1 O problema fundamental

Todos os nossos findings F30-F94 usam `prompt_chars`. LLMs cobram em
**tokens**, nao caracteres. A conversao char → token nao e linear.

Approximacao classica: **~4 chars por token** (ingles). Mas isso varia de:
- **1 char/token** (caracteres especiais, numeros, simbolos raros)
- **8+ chars/token** (palavras comuns do treinamento)

### 2.2 Por que BPE agrupa de forma nao-linear

Byte Pair Encoding aprende merges durante o treinamento do tokenizer:
1. Comeca com caracteres individuais como tokens
2. Encontra o par mais frequente e cria um novo token
3. Repete ate atingir o vocabulario-alvo

**Consequencia:** tokens representam **pedacos frequentes do corpus de
treinamento**, nao unidades sintaticas.

- `Ana` → provavelmente 1 token (nome frequente)
- `Caneta` → provavelmente 2 tokens (`Can`, `eta`) — palavra pt-BR rara em corpus EN
- `3*Ana` → 3 tokens (`3`, `*`, `Ana`) — combinacao nunca treinada
- `147445.47` → 4-5 tokens (numeros grandes sao segmentados)

### 2.3 Por que TCF pode perder em tokens mesmo ganhando em chars

Exemplos concretos a verificar:

**Caso A — linha CSV:**
```
Ana,Caneta,2024-01-15,3,2.50,7.50
```
Tokens esperados (GPT-4 cl100k_base): ~15-18 tokens

**Caso B — mesmo dado em TCF L0:**
```
pessoa:
Ana
produto:
Caneta
dt:
2024-01-15
qtd:
3
preco_unit:
2.50
total:
7.50
```
Tokens esperados: ~20-25 tokens (**mais linhas = mais tokens de newline**)

TCF L0 tem **mais chars** que CSV? Nao (ambos similares). Mas pode ter
**mais tokens** por causa do padrao `nome_coluna:\nvalor\n` que gera
muitos newlines.

**Caso C — TCF L2 (RLE):**
```
pessoa:
8*Ana
12*Bruno
produto:
5*Caneta
4*Lapis
```
`8*Ana` — como tokeniza? Se `Ana` e 1 token, `8*Ana` e 3 tokens.
No L0 expandido, `Ana` × 8 seria 8+8=16 tokens (palavra + newline).
**L2 ganha:** 3 tokens < 16 tokens.

**Mas:** depende do tokenizer ter aprendido o padrao.

### 2.4 Validacao contra TOON (que mede em tokens)

TOON reporta numeros em tokens reais (tiktoken). Benchmarks:
- TOON: 54% reducao vs JSON (em tokens)
- Exemplo: JSON 2703 → TOON 1009 = -62.7%

**Se TOON mede 54% reducao em tokens**, nos precisamos medir TCF com
o **mesmo tokenizer** para comparacao justa. Senao nao e apples-to-apples.

### 2.5 Confusao no nome "TOON"

**Observacao do usuario:** "TOON fala de token, mas ele mostra uma
compressao apenas textual, onde esta o token na historia?"

**Resposta:** TOON e "**Token-Oriented**" porque o design foi **otimizado
PARA tokens** em mente, nao porque processa tokens. O formato e textual
como JSON, mas cada decisao de design foi:

- "E se removermos esse caractere? Tokeniza melhor?"
- "E se declararmos fields uma vez? Economiza tokens?"
- "E se usarmos comma ao inves de colon? Tokeniza diferente?"

**O "token-oriented" e filosofia de design, nao mecanismo tecnico.**

TOON nao e "mais token-oriented" que TCF em principio — ambos sao
textuais, ambos podem ser medidos em tokens. A diferenca e:
- TOON: **otimizado empiricamente** para tiktoken (GPT-4)
- TCF: **ainda nao medido** em tokens reais

**Nosso trabalho:** validar se TCF tambem economiza tokens ou so chars.
Se economiza tokens (em tiktoken), podemos dizer "TCF e token-efficient".
Se nao, temos que ajustar o formato (delimitadores, padroes) para
aprender quais sao token-friendly.

### 2.6 Estrategia: formato "BPE-friendly"

Para maximizar tokens-por-caractere, o formato deveria:

1. **Usar padroes frequentes do treinamento:** `value, value, value` (CSV-like)
   e melhor que `value\nvalue\nvalue` (mais newlines)
2. **Evitar caracteres raros:** `*`, `|`, `@` podem ser 1 token cada
3. **Reusar palavras comuns:** nomes de colunas em ingles tokenizam melhor
4. **Agrupar numeros:** `1 2 3 4` pode ser melhor que `1,2,3,4` — depende
5. **Minimizar newlines:** cada `\n` e um token

**Hipotese para TCF:** mudar notacao RLE de `8*Ana` para `Ana x8`
poderia tokenizar melhor porque `x8` e palavra comum em ingles.
**Nao validado** — precisa testar.

Fonte: [TOON format explained](https://blog.logrocket.com/reduce-tokens-with-toon/),
[BPE from scratch](https://sebastianraschka.com/blog/2025/bpe-from-scratch.html),
[Karpathy minbpe](https://github.com/karpathy/minbpe)

---

## 3. Streaming / Buffered compression

### 3.1 Problema atual do TCF

Nosso encoder atual faz **batch processing**:
1. Le todas as linhas do CSV para memoria
2. Processa colunas inteiras (sort, RLE, dict)
3. Gera saida completa em string

Para datasets grandes (100K+ rows), isso pode:
- Estourar memoria
- Ter latencia alta antes de enviar o primeiro byte
- Bloquear outras operacoes

### 3.2 Modelos de compressao streaming

**gzip streaming (Python stdlib):** `zlib.compressobj()` permite chunks
incrementais:
```python
compressor = zlib.compressobj(level=6, wbits=31)
output = b""
for chunk in input_chunks:
    output += compressor.compress(chunk)
output += compressor.flush()
```

- **Memoria baixa:** buffer interno fixo (~32KB janela LZ77)
- **Latencia baixa:** primeiros bytes saem antes do fim
- **Desvantagem:** ratio um pouco pior que batch (sem visao global)

**heatshrink:** compressao LZSS para embedded systems. Usa janela de
256-1024 bytes. Projetado para memoria minima (kilobytes).
Fonte: [heatshrink GitHub](https://github.com/atomicobject/heatshrink)

**HTTP Chunked Transfer Encoding:** envio em blocos independentes,
cada um com seu header. Protocolo padrao (RFC 7230).
Fonte: [Chunked transfer encoding Wikipedia](https://en.wikipedia.org/wiki/Chunked_transfer_encoding)

### 3.3 Como TCF poderia ser streaming

**Desafios fundamentais:**
- Sort precisa de TODAS as linhas (nao e streamable)
- Dict precisa conhecer vocabulario antes de emitir indices
- STATS precisa de count/sum/min/max globais

**Solucoes parciais:**

#### 3.3.1 Streaming L0 (expanded) — trivial
Sem sort, sem dict, sem RLE → emite linha por linha.
```
pessoa:
Ana
Bruno
Carla
...
total:
2.50
3.00
...
```
Problema: nao e columnar se voce emite row-by-row. Teria que fazer
2 passadas (uma por coluna) OU manter buffer de uma coluna inteira
em memoria.

**Solucao real:** chunked columnar — processa 1000 linhas por vez,
emite bloco, limpa buffer, repete.

```
# TCF v0.2 level=0 chunked=1000
## vendas n=509 chunks=1

## chunk 1 rows=1-509
pessoa:
Ana
Bruno
...

## chunk 2 rows=510-1018
pessoa:
David
Eva
...
```

Cada chunk e **independente** — decoder reconstroi juntando.
Memoria pico: 1000 linhas × 6 colunas = ~6K valores em buffer.

#### 3.3.2 Streaming L1 (RLE) — possivel
RLE trabalha em janela movel. Pode processar chunk-by-chunk:
```
chunk 1: 8*Ana 12*Bruno 5*Carla
chunk 2: 3*Carla 10*David  ← continua o padrao do chunk anterior
```
Problema: se um run atravessa fronteira de chunks, fica quebrado.
Solucao: aceitar o overhead minimo (1-2 grupos RLE extras por chunk).

#### 3.3.3 Streaming L2 (sort + RLE) — dificil
Sort global nao e streamable. **Alternativas:**
- **Sort local por chunk:** cada chunk e sorted independentemente.
  Pior compressao global mas streamable.
- **External sort:** usa disco (multi-pass). Streamable mas lento.
- **Approximate sort:** bucket sort por hash, streamable com erro.

#### 3.3.4 Streaming L3 (dict + sort + RLE) — muito dificil
Dict global precisa de 2 passadas (primeiro constrói dict, depois
aplica). **Nao e streamable nativamente.**

**Alternativa:** dict por chunk (menor mas funcional). Cada chunk
tem seu `# dict col: ...` proprio.

### 3.4 Beneficios reais de streaming TCF

Para uso em APIs HTTP chunked:
- Menor Time-To-First-Byte (TTFB)
- Memoria constante (~chunk_size)
- Compatibilidade com HTTP/2 streaming
- Util em IoT / edge (memoria limitada)

**Caveat:** perde ratio de compressao vs batch completo. Tradeoff.

### 3.5 Proposta de ticket

Sera criado: **H-streaming-encoder**
- Implementar chunked L0/L1 como modo opcional
- Medir memoria peak vs tempo vs ratio
- Comparar streaming TCF vs streaming gzip direto
- Avaliar se vale a pena (muitos sistemas usam chunked transfer)

---

## 4. Sintese das descobertas

### 4.1 Questao: "Todo esse trabalho vale a pena?"

Ate agora, as evidencias que **favorecem** TCF:

| Favorecimento | Evidencia |
|---------------|-----------|
| Compressao apos gzip | F70-F73 (TCF+gzip 29% < CSV+gzip em 5K rows) |
| Accuracy LLM tabular | F50 (TCF L0 49% > CSV 19% em Etapa 2) |
| STATS shortcut unico | F81-F94 (nenhum outro formato tem) |
| Orientacao columnar | Unico no espaco LLM (TOON e row-oriented) |

Evidencias que **desfavorecem** TCF:

| Desfavorecimento | Evidencia |
|------------------|-----------|
| Ratio char/token desconhecido | Pode perder vs TOON em tokens |
| Sort nao e streamable | Perde em memoria vs gzip streaming |
| Complexidade de decoder | Mais dificil de implementar em C/JS que CSV |
| Sem peer review | TOON tem arxiv, TCF nao (ainda) |
| Nicho especifico | So dados tabulares repetitivos |

### 4.2 Estrategia refinada

**Antes de concluir que TCF vale a pena, precisamos:**

1. **Medir em tokens reais** (E-token-count) — valida ou invalida findings
2. **Comparar com TOON no mesmo benchmark** (P-competing-formats) — ponto de referencia
3. **Testar encodings avancados** (H-advanced-encodings) — SQL Server tem razao
4. **Validar streaming** (H-streaming-encoder) — viabilidade em APIs modernas
5. **Rodar G-utility-analysis** — consolidacao final honesta

Se apos tudo isso o TCF tiver nicho claro → publicar.
Se nao tiver → publicar como "formato experimental, resultados honestos".

### 4.3 Questoes abertas

- TCF ganha de TOON em tokens? (incerto)
- Advanced encodings (delta, FOR) ajudam ou atrapalham LLMs?
- Streaming TCF e viavel sem perder muita compressao?
- Existe um "token-friendly TCF" diferente do atual?

---

## Referencias

### Columnstore compression
- [SQL Server Data Compression](https://learn.microsoft.com/en-us/sql/relational-databases/data-compression/data-compression)
- [Columnstore Indexes Overview](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview)
- [Vertipaq Optimization — Red Gate](https://www.red-gate.com/simple-talk/databases/sql-server/bi-sql-server/vertipaq-optimization-and-its-impact-on-columnstore-compression/)
- [Columnstore Architecture — Simple Talk](https://www.red-gate.com/simple-talk/databases/sql-server/t-sql-programming-sql-server/hands-on-with-columnstore-indexes-part-1-architecture/)
- [SingleStore Columnstore Encoding](https://docs.singlestore.com/db/v9.0/reference/sql-reference/data-types/encoding-string-data-in-columnstore-tables/)

### BPE e tokenizers
- [Byte-pair encoding — Wikipedia](https://en.wikipedia.org/wiki/Byte-pair_encoding)
- [Karpathy minbpe GitHub](https://github.com/karpathy/minbpe)
- [BPE from scratch — Sebastian Raschka](https://sebastianraschka.com/blog/2025/bpe-from-scratch.html)
- [Let's Build the GPT Tokenizer — fast.ai](https://www.fast.ai/posts/2025-10-16-karpathy-tokenizers.html)
- [Understanding LLM Billing — Eden AI](https://www.edenai.co/post/understanding-llm-billing-from-characters-to-tokens)

### TOON em detalhes
- [TOON GitHub](https://github.com/toon-format/toon)
- [TOON format explained — LogRocket](https://blog.logrocket.com/reduce-tokens-with-toon/)
- [TOON vs JSON — TensorLake](https://www.tensorlake.ai/blog-posts/toon-vs-json)
- [Orange Force TOON review](https://theorangeforce.com/the-orange-force-news/toon-token-efficiency-useful-cases/)

### Streaming compression
- [Python zlib compressobj](https://docs.python.org/3/library/zlib.html)
- [heatshrink — atomicobject](https://github.com/atomicobject/heatshrink)
- [Chunked transfer encoding — Wikipedia](https://en.wikipedia.org/wiki/Chunked_transfer_encoding)
- [Stream-based lossless compression — Springer](https://link.springer.com/chapter/10.1007/978-981-16-4095-7_16)
- [gzip-stream Python package](https://github.com/leenr/gzip-stream)
