# Teoria da compressao de strings em TCF — fundamentacao

**Data**: 2026-05-12
**Origem**: pedido do user para fundamentar o trabalho de compressao por
afixo/trie antes de continuar empiricamente.

## Objetivo deste documento

Antes de continuar testando variantes empiricamente, estabelecer:
1. O que ja existe na literatura (estado da arte)
2. Modelo matematico das 3+1 abordagens propostas pelo user
3. Analise de complexidade (espaco × tempo × razao de compressao)
4. Limites teoricos (smallest grammar problem)
5. Protocolo de teste empirico **realista** que nao decida em poucos bytes

---

## 1. Estado da arte (literatura)

### 1.1 Front Coding (PFC)

Tecnica classica para dicionarios de strings **ordenados**. Cada string
representada por:
- `LCP(s_i, s_{i-1})` — comprimento do prefix comum com a anterior
- `s_i[LCP:]` — sufixo unico

Equivale ao que TCF v0.5 esta fazendo com flag `P` (Etapa 1) e o que
o user propos com **prefix-V3 inline**.

[Plain Front Coding paper (VLDB)](https://link.springer.com/article/10.1007/s00778-020-00620-x).

### 1.2 Dictionary Encoding em columnar (Parquet/Arrow)

Mapeia valores unicos por coluna para inteiros. Padrao em OLAP. TCF
ja implementa via flag D (Etapa 1) com refs `<idx>` e `:<idx>`.

[Columnar Database Dictionary Encoding](https://medium.com/towards-data-engineering/columnar-database-compression-dictionary-encoding-0d81925b908c).

### 1.3 Suffix Sharing (TAIL)

Estrutura que compartilha sufixos comuns entre strings. Equivale ao
**suffix trie** que o user propos. Bem-estudada em B+trees.

### 1.4 Grammar-based compression

Familia de algoritmos que constroem **gramatica livre de contexto**
(CFG) para representar a string. Cada nao-terminal eh um padrao
recorrente. Decompressao = derivar a gramatica.

**Re-Pair** (Larsson & Moffat, 1999): algoritmo greedy que substitui
o **par de simbolos mais frequente** por um nao-terminal e repete.
Complexidade O(n) tempo mas **5x memoria** do input.

**Sequitur** (Nevill-Manning & Witten, 1997): online, le 1 char por
vez e mantem 2 propriedades: digram uniqueness + rule utility.

[Re-Pair na HandWiki](https://handwiki.org/wiki/Re-Pair).

A trie multi-prefix do user **e equivalente** a uma forma restrita
de gramatica baseada em prefixos compartilhados. **Nao eh smallest
grammar** mas eh aproximacao razoavel quando dados tem estrutura
hierarquica.

### 1.5 Smallest Grammar Problem (SGP)

**Resultado fundamental**: encontrar a menor CFG que gera uma string
eh **NP-hard** (mesmo em alfabetos finitos, provado em 2016).

**Limite de aproximacao**: O(log(n/g*)) onde g* eh tamanho da menor
gramatica. **Nao admite PTAS a menos que P=NP**.

**Implicacao para TCF**: nunca vamos achar a compressao "perfeita"
em tempo polinomial. Algoritmos heuristicos (Re-Pair, Sequitur,
nossa trie) sao **aproximacoes**. Avaliar empiricamente eh
necessario, mas nao podemos esperar nem prometer otimalidade.

[Smallest grammar problem (Wikipedia)](https://en.wikipedia.org/wiki/Smallest_grammar_problem).

---

## 2. Modelo matematico das 4 abordagens propostas

User propos 4 estrategias:

### A. Batch all-at-once com ordenacao

```
1. Ler N strings na memoria
2. Ordenar (em memoria, nao persistente)
3. Construir trie com count por no
4. Selecionar prefixos uteis
5. Emitir
```

**Complexidade**:
- Tempo: O(N·L·log N) (sort) + O(N·L) (trie) = O(N·L·log N)
- Memoria: O(N·L) (trie completa)
- Razao de compressao: **proxima do otimo de greedy**

### B. Bidirecional (prefix + suffix)

```
1. Repetir A para forward
2. Repetir A com strings reversas (suffix trie)
3. Comparar bytes; escolher melhor
4. Emitir com flag de direcao
```

**Complexidade**:
- Tempo: 2x A
- Memoria: 2x A (mas pode-se descartar uma apos comparacao)
- Razao: melhor de prefix vs suffix por dataset

### C. Streaming (RLE-style, sem ordenacao)

```
1. Ler 1 string por vez
2. Atualizar trie incremental
3. Emitir conforme padrao detectado
```

**Complexidade**:
- Tempo: O(N·L)
- Memoria: O(g) onde g = tamanho da gramatica
- Razao: **pior** em casos onde padrao grande aparece cedo

**Exemplo**:
- Ana, Anabel, Anabela, Anabelinha
- Linha 1 emite "Ana" como prefix
- Linha 2 reusa "Ana" mas precisa de "bel" adicional
- Sem batch, perde otimo "Anabel" como prefix maior

### D. Buffer pequeno (LZ77-style)

```
1. Manter janela deslizante de B strings
2. Otimizar dentro da janela
3. Emitir + descartar primeira
```

**Complexidade**:
- Tempo: O(N·L·B) (otimizacao por janela)
- Memoria: O(B·L)
- Razao: **trade-off** ajustavel via B

**Insight do user (importante)**:
> "padrões menores antes ficam mais fáceis de aplicar em padroes que crescem"
> "padrões maiores ficam mais dificeis de diminuir"

Confirma assimetria do streaming. Buffer resolve quando padrao
**emerge gradualmente**.

---

## 3. Analise comparativa

| Approach | Tempo | Memoria | Razao | Complexidade decoder |
|----------|-------|---------|-------|----------------------|
| A. Batch | O(N·L·log N) | O(N·L) | otima-greedy | O(N·L) — single-pass |
| B. Bidirecional | 2× A | 2× A (peak) | melhor de A,A_rev | igual A |
| C. Streaming | O(N·L) | O(g) | sub-otima | O(N·L) |
| D. Buffer-W | O(N·L·B) | O(B·L) | entre A e C | O(N·L) |

**Insight**:
- **Decoder eh sempre O(N·L) single-pass** (gramatica simples).
- Diferenca esta no **encoder**.
- TCF v0.5 prioriza **decoder simples** (LLM-friendly), entao qualquer
  uma das 4 funciona se o decoder converge.

---

## 4. Limites teoricos relevantes

### 4.1 NP-hardness

SGP eh NP-hard. Implicacoes:
- **Nao podemos provar otimalidade** sem brute-force exponencial
- Toda comparacao empirica entre algoritmos eh **relativa**
- Heuristicas tem garantias logaritmicas (Re-Pair, LCA)

### 4.2 Razao de compressao depende dos dados

Resultado importante: **nao existe algoritmo otimo para todos os casos**.
- Em datasets com hierarquia clara (codigos `INV-/PED-/REQ-`), trie
  vence
- Em datasets planos com 1 prefix dominante, front coding simples vence
- Em texto aleatorio sem estrutura, **nada comprime** (entropia limita)

### 4.3 Limite de Shannon

Para distribuicao uniforme de tokens, compressao maxima eh
H(X) bits/symbol. **Nenhum algoritmo bate Shannon** sem perda.
Em datasets reais, H(X) eh muito menor que log(|alfabeto|), por isso
compressao funciona.

---

## 5. Onde TCF se posiciona

TCF v0.5 NAO compete com:
- bzip2/zstd em razao maxima
- Re-Pair em razao otima (NP-hard de qualquer modo)
- Snappy/lz4 em velocidade

TCF v0.5 compete por:
- **Legibilidade** (texto puro, decodavel a olho/LLM)
- **Estrutura preservada** (colunar, schema)
- **Razao razoavel** (quando dados tem padrao)
- **Composability** (flags ortogonais)

**Implicacao**: empiricamente, esperamos perder de gzip+CSV em razao
mas ganhar em propriedades estruturais.

### 5.1 Criterio de escopo — estrutural vs estatistico

**Adicionado 2026-05-19 apos reflexao sobre LZ77**:

> Uma tecnica entra no TCF se explora ESTRUTURA SEMANTICA visivel
> ao LLM/humano. Se so explora ESTATISTICA byte-level, deixar para
> o gzip.

| Tecnica | Estrutural ou estatistica? | TCF? |
|---------|---------------------------|------|
| RLE-linha (`=N`) | estrutural | sim |
| DICT por valor | estrutural | sim |
| Prefix/Suffix DICT | estrutural (afixo tem semantica) | sim |
| PATRICIA bidir | estrutural (hierarquia explicita) | sim |
| Multi-decl `**` | estrutural (cascata de afixos) | sim |
| Dedução de marcadores | estrutural (omite redundancia visivel) | sim |
| Substring com separadores semanticos | estrutural (`@`, `.`, `:`, `-`) | sim |
| **LZ77 substring janela** | **estatistica** | **NAO — gzip faz** |
| Huffman / arithmetic | estatistica pura | NAO — gzip faz |
| BWT | estatistica binaria | NAO — bzip2 faz |

**TCF e gzip sao COMPLEMENTARES, nao concorrentes**. TCF captura
estrutura semantica; gzip captura redundancia estatistica residual.

### 5.2 Substring estrutural vs LZ77 — distinção importante

Substring matching **estrutural** explora pontos de quebra semanticos:
- Email: parte antes/depois do `@`
- URL: blocos separados por `/`, `?`, `#`
- CPF: 4 grupos separados por `.` e `-`
- IP: 4 octetos separados por `.`

Isso **eh estrutural** (separadores tem significado) e cabe no TCF.

Substring matching **estatistico** (LZ77) ignora semantica:
- Janela deslizante de bytes
- Match em qualquer posicao arbitraria
- Captura "ababab" igual a "userN@gmail" se eles aparecerem com mesma freq

**LZ77 nao cabe no TCF** porque sobrepoe gzip e perde legibilidade.

### 5.3 Criterio empirico de validação

Para confirmar que uma tecnica TCF **agrega valor sobre gzip**, rodar:

```
TCF + gzip < gzip(CSV)   → TCF agrega valor
TCF + gzip ≈ gzip(CSV)   → TCF nao agrega (gzip sozinho ja resolve)
TCF + gzip > gzip(CSV)   → TCF atrapalha (markers atrapalham gzip)
```

Em labs ate 2026-05-19, a maioria dos cenarios cai na categoria 3
(TCF+gzip > gzip(CSV) por 5-22%) — **sinal de que markers estruturais
custam mais que economizam apos gzip**.

**Mas isso eh OK** se o objetivo eh legibilidade pra LLM (nao bytes
maximos). TCF + gzip + LLM-readable >>> gzip(CSV) + LLM-illegible.

A medicao certa eh:
1. **Bytes pre-gzip** (TCF eh melhor — porque elimina redundancia visivel)
2. **Legibilidade a olho** (so TCF tem)
3. **Decoder simples** (so TCF tem)
4. **Bytes pos-gzip** (gzip(CSV) tende a ganhar marginalmente)

Para casos LLM, item 2 domina. Para storage puro, item 4 domina —
nesses casos use Parquet.

---

## 6. Protocolo experimental realista

### 6.1 Erros a evitar (relembrando o pedido do user)

1. **Decidir com poucos bytes**: 50 rows sintetico nao decide nada
2. **1 dataset enviesado**: pode ser caso atipico dos 5%
3. **Ignorar variabilidade**: 1 seed nao representa
4. **Confundir empirico com teorico**: bytes medidos nao provam algoritmo
5. **Comparacao injusta**: compressores diferentes em escopos diferentes

### 6.2 Protocolo correto

**Para validar uma tecnica de compressao em TCF**:

```
Etapa 1 — Algebra (esta nota): justificativa teorica
  - Modelo matematico claro
  - Complexidade analisada
  - Razao de compressao com cota teorica

Etapa 2 — Lab dirty (mesa de testes): intuicao matematica
  - Datasets sinteticos com estrutura conhecida
  - Verificar que algoritmo se comporta como predisse
  - Identificar zonas de quebra (worst case)

Etapa 3 — Lab clean (validacao empirica): bases reais
  - 5+ datasets de classes diferentes (relacional, time-series, text, etc.)
  - 3+ seeds por experimento (para variabilidade)
  - Comparacao com baselines (CSV, JSON, gzip, dictionary encoding)
  - Estatisticas: media + desvio + min + max
  - Tabela de classes onde GANHA / EMPATA / PERDE

Etapa 4 — Stress / escala: limite
  - Datasets >= 100k rows
  - Verificar curvas de tempo + memoria
  - Confirmar que complexidade prevista eh real

Etapa 5 — Publicar / promover ao core
  - So depois de 4 etapas
  - Documentar caveats e limites
  - Auto-bypass implementado nas zonas onde perde
```

**Apenas Etapas 1+2 nao decidem nada permanentemente.** Sao
**exploratorias**.

### 6.3 Datasets canonicos sugeridos para Etapa 3

Cobrir 5 classes de "shape" de string:

| Classe | Exemplo | Esperar |
|--------|---------|---------|
| Identificadores estruturados | `Supplier#NNNNNN`, `INV-2026-NNNN` | prefix dominante |
| Emails / URLs | `user@domain.com` | suffix dominante |
| Texto livre | nomes proprios, descricoes | sem padrao |
| Datas / timestamps | ISO, `YYYY-MM-DD` | prefix curto |
| Codigos hash / UUID | hex 32, base64 | sem padrao |

Para cada classe, 3 tamanhos (small=100, medium=10k, large=1M) e 3
seeds. Total: 5×3×3 = 45 experimentos por algoritmo.

---

## 7. Decisao para o trabalho atual

A trie multi-prefix com 6 variantes (prefix/suffix × V1/V2/V3) **ja
foi validada na Etapa 2** (lab dirty). Resultados:

| Cenario | Melhor variante | Ganho vs SRDMP |
|---------|----------------|---------------:|
| E1 user example | suffix-V3 | -26.4% |
| E2 emails 2 dominios | suffix-V3 | -12.1% |
| E3 emails 3 dominios | suffix-V3 | -6.6% |
| E4 codigos 3 prefixes | prefix-V3 | -42.5% |

**Roundtrip 24/24 OK**. Algebricamente eh consistente com Front
Coding + grammar-based encoding restrito.

**Proxima fase (Etapa 3)** antes de promover ao core:
1. Coletar datasets reais nas 5 classes
2. Implementar **auto-detect** de direcao (prefix vs suffix vs nenhum)
3. Rodar matriz formal com 3 seeds
4. Validar que trie ganha em pelo menos 60% dos cenarios
5. Caso ganhe: promover. Caso nao: **manter no dirty** com nota.

**Importante**: NAO descartar a trie por bytes em 1 dataset. A pergunta
empirica eh "em quantos % dos casos reais ganha".

---

## 8. Observacoes sobre o "atemporal" do user

User mencionou **avaliacao atemporal**: pensar a coluna como um todo
em vez de streaming. Isso eh o **batch approach** (A) da literatura.

Na pratica, **batch eh quase sempre melhor** que streaming **se a
memoria permitir**. Streaming so vence quando:
- Dataset eh maior que RAM
- Resposta precisa ser entregue em pedacos (streaming real)

Para **arquivos finitos** (caso TCF), batch eh apropriado.

**Excecao importante**: chunks/batches conforme M-chunks-v04. Se um
chunk for tratado como unidade autocontida, batch dentro do chunk +
streaming entre chunks combina os dois mundos.

---

## 9. Sintese

### Validado teoricamente

- TCF v0.5 com flag P (Etapa 1) eh Front Coding por coluna
- TCF v0.5 com trie multi-prefix (Etapa 2) eh grammar-based restrita
- Auto-detect prefix/suffix eh decisao por dataset, nao universal
- Decoder permanece simples O(N·L) em todas as variantes

### Conhecido sobre limites

- SGP eh NP-hard; nenhum algoritmo polinomial otima
- Razao depende da entropia / estrutura do dataset
- Heuristicas tem garantias logaritmicas
- TCF NAO mira otimalidade — mira legibilidade + razao razoavel

### Como prosseguir

1. **Etapas 1 + 2 ja feitas** para trie multi-prefix
2. **Etapa 3 (validacao em escala)** eh proximo passo
3. **NAO promover ao core** sem Etapa 3
4. **Documentar** este protocolo para nao repetir o erro de "decidir com
   1 dataset"

## 10. Adaptacao dos algoritmos da literatura para TEXTO (nao binario)

A literatura de compressao trabalha majoritariamente com **bits e bytes
binarios**. TCF eh **texto puro** (ASCII/UTF-8 legivel). Como adaptar?

### 10.1 Principio: representar conceitos binarios em caracteres ASCII

| Conceito binario | Representacao texto TCF |
|-----------------|------------------------|
| Indice em log2(N) bits | Inteiro decimal em chars (`1`, `42`, `127`) |
| Bit-flag | Char unico (`*`, `+`, `:`) |
| Pointer/offset | Inteiro chars |
| Run length encoding | `N*<token>` literal |
| Dictionary index | `<idx>` ou `:<idx>` (TCF flag M) |

**Custo**: chars sao 8 bits cada, mesmo para representar idx pequeno.
Indice 1 ocupa 1 char (8 bits), nao 1 bit. **Overhead vs binario eh
~3-5x** em medio.

**Beneficio**: texto eh:
- Inspecionavel a olho
- Diff-avel via git
- Streaming-friendly (nao quebra em meio a byte)
- LLM le diretamente

### 10.2 Quanto dos algoritmos da literatura sao replicaveis em texto?

| Algoritmo | Replicavel em TCF | Comentario |
|-----------|-------------------|------------|
| Front Coding (PFC) | **SIM, ja feito** | Flag P Etapa 1 = PFC sem ordenacao global |
| Re-Pair greedy | **PARCIAL** | Trie multi-prefix do lab 2026-05-12 eh restricao |
| Sequitur online | **PARCIAL** | Streaming variant; troca otimo por velocidade |
| Suffix sharing (TAIL) | **SIM, lab pendente** | Flag S' (suffix-V3 do lab 2026-05-12) |
| LZ77/LZ78 sliding window | **PARCIAL** | Buffer-based; ainda nao testado em TCF |
| Burrows-Wheeler Transform | **NAO** | Binario por natureza; perderia legibilidade |
| Huffman coding | **NAO** | Bit-level por natureza |
| Arithmetic coding | **NAO** | Idem |

**Nota**: BWT/Huffman/Arithmetic comprimem ao **nivel de bits**, abaixo
de 1 byte por simbolo. TCF nao consegue replicar isso preservando
legibilidade. **OK para gzip downstream cuidar disso**.

### 10.3 Binarizacao parcial futura (aceitavel)

Algumas partes do TCF poderiam **virar binarias contidas em chars**:

- **Indices longos** com base-94 (chars imprimiveis) → mais denso
- **Marcadores** com chars Unicode reservados (mantem ASCII compativel)
- **Bit-packed flags** dentro de 1 char base-64

Isso eh **otimizacao futura** — nao agora. Manter ASCII puro
simples por enquanto.

---

## 11. Latencia adaptativa — escolher algoritmo por orcamento de tempo

Insight do user (importante): **dado um orcamento de latencia (ms),
escolher a abordagem mais eficiente possivel naquele tempo**.

### 11.1 Espectro de complexidade

```
RAPIDO ←-----------------------------------→ OTIMO
streaming  buffer pequeno  buffer grande  batch
O(N)       O(N·B)          O(N·B²)         O(N·log N)
+memoria minima             +memoria maxima
+razao sub-otima            +razao otima
```

### 11.2 Decisao por contexto

| Contexto | Tempo disponivel | Memoria | Algoritmo recomendado |
|----------|------------------|---------|----------------------|
| Stream live, baixa latencia | < 10ms/MB | KB | streaming (RLE/Sequitur-light) |
| API request normal | 50-200ms | MB | buffer pequeno (W=64-256) |
| Batch ETL noturno | segundos+ | GB | full batch + ordenacao |
| Arquivo offline | sem limite | qualquer | full batch + bidirecional |
| Stream com burst | misto | adaptativo | hibrido (tier-based) |

**TCF v0.5 eh agnostico** — encoder pode receber `mode`:
- `mode=fast` → streaming
- `mode=balanced` → buffer
- `mode=optimal` → batch
- `mode=auto` → escolhe por tamanho do dataset / disponibilidade

### 11.3 Streaming nao eh objetivo unico

User levantou: **streaming eh CASO, nao OBJETIVO PRINCIPAL**. TCF
suporta streaming porque algumas aplicacoes precisam (live, low-latency).
Mas a **maioria dos casos** eh batch finito (arquivo, API com payload
completo).

Portanto:
- **Default = batch** (memoria permite, otimiza)
- **Streaming = opt-in** quando aplicacao requer
- **Buffer = compromisso** quando ambos importam

### 11.4 Insight de latencia + memoria abundantes

User: "se tivermos muita memoria e processador, ate existe a possibilidade
de comprimir avaliando tudo e ainda fazer no tempo pedido"

**Verdade matematica**: para N pequeno (< 100k strings, comum em web),
batch full em RAM moderna leva milissegundos. Nao ha tradeoff real —
batch sempre vence.

Tradeoff aparece em:
- Datasets > RAM (terabytes)
- Requisitos hard real-time (jogos, audio)
- Devices embarcados (microcontroladores)

Para TCF tipico (arquivos ate alguns GB), **batch otimal eh viavel**.

---

## 12. Sources / referencias da literatura

- [Faster string dictionary compression (VLDB 2020)](https://link.springer.com/article/10.1007/s00778-020-00620-x)
- [OnPair: short strings compression](https://www.arxiv.org/pdf/2508.02280)
- [Order-Preserving Key Compression (SIGMOD 2020)](https://www.pdl.cmu.edu/PDL-FTP/Storage/zhang-sigmod20.pdf)
- [Practical String Dictionary Compression](https://kampersanda.github.io/pdf/InnovateData2017.pdf)
- [Adaptive String Dictionary Compression (EDBT 2014)](https://openproceedings.org/2014/conf/edbt/0002RF14.pdf)
- [Grammar-based code (Wikipedia)](https://en.wikipedia.org/wiki/Grammar-based_code)
- [Re-Pair (HandWiki)](https://handwiki.org/wiki/Re-Pair)
- [Smallest grammar problem (Wikipedia)](https://en.wikipedia.org/wiki/Smallest_grammar_problem)
- [Online algorithm for grammar-based compression (MDPI Algorithms)](https://www.mdpi.com/1999-4893/5/2/214)
- [Grammar-based compression in streaming model (arXiv)](https://ar5iv.labs.arxiv.org/html/0912.0850)
- [Approximation of grammar-based compression via recompression](https://www.sciencedirect.com/science/article/pii/S0304397515004685)
- [Columnar Database Dictionary Encoding](https://medium.com/towards-data-engineering/columnar-database-compression-dictionary-encoding-0d81925b908c)
