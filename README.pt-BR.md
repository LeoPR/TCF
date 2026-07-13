<!-- l10n: doc_id=readme · lang=pt-BR · source_lang=en · translation_of=README.md · synced=2026-07-01 -->
[English](README.md) · **Português**

> Tradução de [`README.md`](README.md). Se houver divergência, o original em inglês prevalece.
> A régua de atualização é o histórico do git: se o `README.md` mudar depois desta tradução, esta versão fica desatualizada.

# TCF · Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.8.0%20(pré--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.8%20default-blue)

> **E se desse pra transmitir a mesma tabela com bem menos bytes,
> sem virar um arquivo binário que ninguém mais consegue abrir e ler?**

Um cadastro pequeno, nos três formatos (bytes reais, saída de verdade):

**JSON** *(596 B)*: repete o nome de cada campo em toda linha.

```json
[ { "nome": "Ana Souza",  "email": "ana@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium",
    "cpf": "111.111.111-11" },
  { "nome": "Bruno Lima", "email": "bruno@acme.com.br",
    "cidade": "Sao Paulo", "plano": "Premium",
    "cpf": "222.222.222-22" }, … ]
```

**CSV** *(277 B)*: tira os nomes repetidos, uma linha por registro.

```csv
nome,email,cidade,plano,cpf
Ana Souza,ana@acme.com.br,Sao Paulo,Premium,111.111.111-11
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium,222.222.222-22
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic,333.333.333-33
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium,444.444.444-44
```

**TCF** *(242 B, formato 0.8, saída real do `encode`)*: o que se repete vira referência; o que é único fica cru.

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
222.222.222-22
333.333.333-33
444.444.444-44
```

**Como ler:**

- Linha 1, a assinatura e o meta inline: `#TCF.8M` é o formato 0.8, multi-coluna;
  os tamanhos estão em hexadecimal.
- O meta (`tamanho=nome`) usa `!` para raw, `@` para dicionário e `%` para split estrutural
  quando esses candidatos vencem. O `!` marca uma coluna guardada **crua** (quando o raw fica menor que o TCF).
  A última (`cpf`) não leva tamanho: vai até o fim (e o `!` mostra que também é crua).
- Os corpos vêm concatenados, **delimitados por tamanho, não por quebra de linha**.
  Por isso a coluna crua `nome` (`…Diego Rocha`) emenda direto no e-mail (`an*a*…`).
- No corpo: `*3|Sao Paulo` é *"Sao Paulo, 3×"* (repetição).
  `^1` é *"igual à linha 1"* (substituição).
- Na coluna de **e-mail** o TCF vai mais fundo (prefixo único + domínio comum referenciado).
  É onde mais economiza, e onde o texto fica mais denso.
- Já a coluna **`cpf`** é o oposto: valores quase todos únicos, **nada a fatorar** pelo pipeline
  default. O TCF guarda **cru** (`!cpf`) — não comprime, mas também **não infla** (é o fallback).
  *(São placeholders de dígitos repetidos: mod-11-válidos, mas a Receita nunca os emite — fakes
  seguros. A* `nature` *opt-in (ADR-0015) tira `.`/`-` e dropa o dígito verificador derivável; com
  `nature_per_col={"cpf": SPEC_CPF}` esta MESMA coluna comprime — ver "Nature filters" abaixo.)*

JSON repete a estrutura inteira.
CSV repete os valores.
O **TCF fatora o que se repete**, referencia o resto e **mantém cru o que é único** (sem inflar), continuando **texto ASCII que você abre e lê**.

Mas quanto mais fundo ele fatora (veja o e-mail), mais denso o texto fica.
*Legível não quer dizer óbvio à primeira vista.*

Em tabelas grandes a diferença cresce: ver [Resultados](#resultados).

## O que é o TCF

Um formato **textual** e **sem perdas** (`decode(encode(x)) == x`) para tabelas de strings.

Comprime parecido com um zip/gzip, mas com uma diferença: o resultado **continua texto ASCII que você abre e inspeciona**, sem descomprimir.
Não fica tão óbvio quanto o original (quanto mais o TCF fatora, mais denso o texto), mas nunca vira um blob opaco.
Cada coluna passa por um pipeline próprio.

É essa a faixa que o TCF ocupa: **compacto como um compressor, inspecionável como texto**.
(Precisa de ratio máximo? Dá pra rodar gzip/brotli por cima: eles se compõem.)

## Como ele faz isso: OBAT + HCC

Duas camadas, explicadas pelo propósito (specs: [`docs/algorithms/`](docs/algorithms/)).

**OBAT** (Online Bidirectional Affix Tokenizer) *acha o que as strings têm em comum.*
Para cada valor, procura o maior prefixo **e** sufixo compartilhado com os anteriores (domínios de e-mail, raízes de URL, códigos da mesma família).
Escreve o trecho uma vez e referencia o resto.

É um **front-coding bidirecional**: generaliza o front-coding clássico de dicionários de strings (Witten et al.; HTFC/RPDac, Brisaboa et al.).
O "bidirecional" é o que captura o **sufixo** comum (`@acme.com.br`), não só o prefixo.

A busca por afixos é da família das **árvores de prefixo/sufixo**: tries, **Patricia/radix tree** (Morrison 1968), suffix trees.
Na prática o OBAT acelera essa busca com um **índice de trigramas**, que derruba o custo de O(N²) ingênuo para ~O(N^1.42) (sub-quadrático, quase-linear).
*(Trocar o índice por uma Patricia trie é candidato futuro: [exploração](docs/theory/patricia-trie-exploration.md).)*

**HCC** (Hierarchical Compositional Coding) *decide o que vale a pena nomear e agrupa repetições.*
Pega os tokens do OBAT, fatora composições recorrentes em **referências nomeadas reutilizáveis** (operador `~`) e colapsa repetidos (RLE, inclusive sequências quase-iguais, tipo IDs que só mudam no fim).

Como referência aponta para referência, o resultado é um **grafo acíclico (DAG) de fragmentos**: na prática uma *gramática* / straight-line program do conteúdo.
É o espírito do **Re-Pair** (Larsson & Moffat 1999) e do **Sequitur** (Nevill-Manning & Witten 1997), mas operando sobre os **tokens** do OBAT (não sobre bytes) e com operadores próprios (`~` cria nó nomeado, `,` só concatena).

É o que mantém a saída pequena **e** inspecionável: os grupos `*N|...` ficam à vista.

**Velocidade.**
O lado caro é o **encode** (a busca de afixos do OBAT), trazido a quase-linear pelo índice de trigramas (mais o acelerador Cython opcional).
O **decode** é uma **passada linear única**: só expande as referências (lookups O(1)) e os grupos RLE, sem nenhuma busca.
Rápido e previsível.

## Filtros por natureza (opt-in)

Alguns valores têm **estrutura conhecida** que o compressor genérico não explora.
Um CPF `123.456.789-09` são só **9 dígitos úteis**: a pontuação é fixa e os 2 dígitos
finais (verificador) são **deriváveis** dos outros 9. Um *filtro de natureza* (opt-in) usa isso:

- **encode** tira a pontuação, guarda os 9 dígitos como um número curto (base segura, ~5 chars;
  o alfabeto atual tem 80 caracteres utilizáveis)
  e **descarta o verificador**;
- **decode** **recalcula** o verificador (mod-11) e reinsere a pontuação — reconstrução **exata**.

Nature não é pré-transformação forçada. O **FLOOR** compara o blob serializado completo, incluindo
o custo do header `:id`; se a nature perde, o pipeline original permanece e nenhum marcador é emitido.
Isso protege dados ordenados em que split/dicionário vencem uma codificação base absoluta. O caveat
medido do CNPJ é importante: uma nature pode ajudar no sintético e ainda aumentar uma tabela real.

Filtros já implementados ([ADR-0015](docs/adr/0015-natures-templated-checked-weld.md)):

| filtro | formato | o que o decode reconstrói |
|---|---|---|
| `SPEC_CPF`  | `NNN.NNN.NNN-DD`     | pontuação + 2 díg. verificadores (mod-11) |
| `SPEC_CNPJ` | `NN.NNN.NNN/NNNN-DD` | pontuação + 2 díg. verificadores (mod-11) |
| `SPEC_IP`   | IPv4 `N.N.N.N`      | pontos + octetos canônicos (padroniza p/ ativar RLE em subnets) |

O mesmo mecanismo de spec vale pra **números**: o `SPEC_IP` acima já é numérico (octetos);
sequências e IDs numéricos com cadência o pipeline *delta-aware* captura sozinho
(`*N+delta|`, seq-RLE); e specs de **decimal / monetário / precisão** estão no roadmap
(cruzam a linha lossy → 2.0).

```python
from tcf import encode, decode
from tcf import SPEC_CPF

# Placeholders de dígitos repetidos: PASSAM no mod-11 (então a nature os comprime),
# mas a Receita nunca os emite — não mapeiam pessoa real (fakes seguros p/ exemplo).
cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]

blob = encode(cpfs, nature=SPEC_CPF)   # a nature VENCE aqui (4 CPFs distintos)
print(blob)
# #TCF.8 :cpf     <- header single-col auto-descritivo: o spec ESTÁ aplicado
# %g$.u           <- "111.111.111-11" (14 B) -> 5 chars: corpo de 9 díg em base-80,
# )K%\7l             a máscara e os 2 díg verificadores caem (o decode recalcula)
# .\1&Cc
# \0r(LU
assert decode(blob) == cpfs            # decode lê `:cpf` do header, sem passar spec

# Os mesmos 4 CPFs: 76 B raw single-col -> 39 B com a nature (-49%). Em tabela,
# passe por coluna: encode(tabela, nature_per_col={"cpf": SPEC_CPF}); a meta inline
# da coluna cpf então carrega `:cpf` (ex.: `#TCF.8M!15=nome,!cpf:cpf`).
```

Dois detalhes honestos:

- São **opt-in e auto-descritivas quando vencem**: single-column leva `#TCF.8 nome:id`; multi-column
  leva `:id` no meta inline. O `decode(blob)` resolve `cpf`, `cnpj` e `ip` pelo registry core.
- Spec customizado pode ser usado, mas o decoder precisa receber um spec cujo `name` coincide
  exatamente com o ID do header.
- Valor que não bate (verificador inválido, formato mascarado) cai em **literal** (`_`) sem
  nunca quebrar o round-trip — o filtro **nunca corrompe** o dado.

> **Escopo cadastral em exploração.** CEP, RG, identificação de motorista, telefone e códigos
> genéricos foram medidos fora do core. Nenhum é spec canônico do `.8` ainda; veja a matriz em
> [`T-SPEC-STATUS-08`](tickets/T-SPEC-STATUS-08.md).

## Getting started (1 minuto)

```python
from tcf import encode, decode

# Single-column: lista de strings
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
assert decode(text) == ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]

# Multi-column: dict de colunas
table = {
    "id":    ["1", "2", "3"],
    "email": ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"],
}
text = encode(table)
assert decode(text) == table  # round-trip lossless

# Naturezas (opt-in): CPF/CNPJ/IP comprimidos sem dígito verificador/padding.
# A nature se auto-descreve no header (#TCF.8 :cpf) quando vence a comparação de
# tamanho, então o decode não precisa do spec.
from tcf import SPEC_CPF
cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33"]  # dígitos repetidos: mod-11-válidos, nunca emitidos (fakes seguros)
text = encode(cpfs, nature=SPEC_CPF)
assert decode(text) == cpfs
```

`encode` dispatcha por tipo (list → single-column, dict → multi-column).
`decode` roteia pela assinatura de formato.

Tutorial passo-a-passo: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Guias praticos: [`docs/how-to/`](docs/how-to/).

## Formato 0.8 (default): onde os bytes vão

O `encode` multi-coluna sai em **0.8 / `#TCF.8M`** por default ([ADR-0032](docs/adr/0032-tcf8-default-format.md)).
Quatro coisas, todas automáticas (sem flag), cada coluna escolhendo a menor representação:

- **Fallback por coluna.**
  Guarda a coluna em raw quando o raw fica menor que o TCF ("nunca pior que raw").
  Marcada com `!` no meta ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)).
- **Dicionário low-card.**
  Coluna com poucos valores distintos vira tabela de únicos + índices compactos,
  em vez de um ref por linha.
  Marcada com `@` no meta ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md)).
- **Split estrutural.**
  Valor estruturado (decimal, data, datetime, CPF) com template uniforme vira
  campos separados (o template guardado uma vez), e cada campo low-card cai no dicionário.
  Marcada com `%` no meta ([ADR-0026](docs/adr/0026-structural-split-weld.md)).
- **Header mínimo.**
  O flag `M` na assinatura já declara que vêm colunas, então o meta é inline, os tamanhos ficam em
  hexadecimal, separadores de nomes são escapados e a última coluna não leva tamanho
  ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)).
- **Competição de naturezas.**
  CPF/CNPJ/IP são candidatos opt-in. O blob completo vence ou empata com o baseline; se a nature
  perde, a coluna original permanece e nenhum `:id` é emitido.

```python
text = encode(table)        # 0.8 / #TCF.8M, é o default, sem flags

# knobs opt-out (default True) — pra modificar o comportamento / inspecionar:
text = encode(table, fallback=False, min_header=False)  # só candidatos TCF, meta verboso
text = encode(table, min_header=False)                  # #TCF.8M com todos os tamanhos
text = encode(table, min_len=5)                         # override do min_len do OBAT (default: auto)
text = encode(table, sort_by="cidade")                  # ordena linhas pela coluna (order-free, +compressão)
```

> `sort_by` reordena as linhas pela coluna (agrupa similares → menos bytes,
> 5-15% com chave low-card). É **order-free**: o `decode` devolve a ordem
> ordenada, não a original. Use só quando a ordem das linhas não importa.

No cadastro de 5 colunas do topo, comparado ao formato legado `#TCF.6`:

| formato | meta line | bytes |
|---|---|---:|
| **0.8 / `#TCF.8M`** (default) | `!2c=nome,2a=email,1c=cidade,14=plano,!cpf` | **242** |
| `#TCF.6` (histórico) | header/body legado | não emitido pelo código atual |

O resultado de 242 B vem dos candidatos de fallback e do header inline mínimo. A coluna `cpf` cai
para **raw** (`!cpf`) em vez de inflar; os tamanhos são hexadecimais e a última coluna não leva
tamanho. O ganho é proporcionalmente maior em **payloads pequenos**.

Pré-1.0, o encoder só escreve o formato mais novo.
Os legados `#TCF.6`/`#TCF.7` não são lidos pelo código atual; `git checkout` reproduz as eras
históricas ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
O dicionário low-card (V2-B) e o split estrutural já estão no default; a compressão lossy fica no [roadmap](docs/adr/0018-v2-format-roadmap.md).

## Estado (pré-1.0)

- **Pré-1.0** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
  Os minors do formato (`#TCF.6/.7/.8`) são iterações de desenvolvimento rumo a um **1.0 sólido**, sem compat rígida entre eles (git reproduz versões antigas).
  v2.0 fica pra depois.
- Implementação canônica em [`src/tcf/`](src/tcf/).
  Round-trip sempre lossless (`decode(encode(x)) == x`).
- Default **0.8 / `#TCF.8M`**: fallback, dicionário, split estrutural, meta hexadecimal inline,
  escaping e IDs de nature autorizados pelo header; veja a seção acima. Os legados `.6/.7` são recuperados via git.
- Suíte: **634 passed, 2 skipped** na execução local completa atual; rode `pytest` para o número do seu ambiente.
  Baselines de byte = guardas de regressão, re-pináveis em mudança intencional ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
- Mudanças: [`CHANGELOG.md`](CHANGELOG.md).
  História M0-M14: [`experiments/lab/dirty/notas/historia-dirty-lab.md`](experiments/lab/dirty/notas/historia-dirty-lab.md).

> O ciclo **v0.5** (formato columnar para LLM benchmark) é acessório e vive separado.
> Ver a seção "Benchmark LLM v0.5" mais abaixo.

## Resultados

**Sem nenhum compressor, o TCF é o formato de _texto_ mais compacto do conjunto.**
Nos 15 datasets sintéticos do [EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/):

| formato (texto puro, sem compressor) | bytes |
|---|---:|
| **TCF** | **3131** |
| CSV | 4872 |
| JSON | 5409 |
| JSONL | 7001 |

~36% menor que CSV e ~42% menor que JSON, continuando legível.

Núcleo pinado em testes: D1-D9 = **1523 B** (51.1% do raw, single-col); D17a multi-col = **300 B** (`#TCF.8M`, meta hexadecimal inline).
Real-world multi-coluna (9 tabelas Adult + TPC-H, 136k linhas): **−33.02% weighted** vs CSV raw.

**E contra gzip / brotli / zstd?**
Outra categoria: são compressores binários *opacos* (precisa descomprimir pra ler qualquer coisa).
No **cadastro acima**, sob compressão HTTP (`Content-Encoding`):

| formato | cru | gzip | br | zstd |
|---|---:|---:|---:|---:|
| JSON | 596 | 218 | 212 | 211 |
| CSV  | 277 | 177 | **162** | 165 |
| TCF  | **242** | 206 | não medido | não medido |

TCF é o menor **cru** (e legível). O `#TCF.8M` atual mede 242B cru e 206B com gzip da stdlib;
brotli/zstd precisam de uma nova rodada com os codecs instalados antes de entrarem como números do
release. O TCF **troca um pouco de ratio por legibilidade** e **se compõe** com compressores externos.
O `gzip` ainda carrega bytes fixos de moldura por mensagem; `br`/`zstd`, quase nada — em payload
minúsculo isso conta. (Os números usam os compressores no **nível máximo**
— melhor caso pra eles; numa API simples a compressão às vezes nem está ligada, e quando está usa
nível baixo por default: nginx gzip `1`, brotli `6`. Ver [notas dos compressores](experiments/lab/clean/EXP-008-compressao-comparada/notes/classificacao-compressores.md).)

No agregado de 15 datasets sintéticos **single-column** (EXP-008, onde os welds multi-col do 0.7
não se aplicam) a mesma história: `csv+brotli` = 1742 B contra `tcf+brotli` = 2116 B. Tabelas
completas: [reports do EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/reports/).

**Atenção de escala — o cadastro acima é minúsculo (4 linhas).** Em **multi-coluna real**
(milhares de linhas) o quadro **inverte**: o **TCF cheio + brotli vence o CSV + brotli** —
ex.: Adult com 3 000 linhas, `tcf-0.8+brotli` = **21,8 KB** vs `csv+brotli` = 30,4 KB (−28%).
E quanto **mais** TCF, **menor** o resultado pós-brotli (medido em 4 datasets reais:
[`2026-06-16-staged-and-ordering-brotli/`](experiments/lab/dirty/old/refuted/2026-06-16-staged-and-ordering-brotli/)).
Em payload minúsculo a moldura domina e não há o que fatorar; **a vantagem do TCF aparece com volume**.

## Pra onde vai a 1.0 — consultar quase sem descomprimir

O que o TCF já faz hoje aponta pra meta da **1.0**: usar a **própria estrutura da compressão
como índice**, pra responder perguntas **quase sem descomprimir** e com **pouca memória**.

A saída textual já carrega dicas que valem como metadados:
- `*N|Sao Paulo` diz que há **N linhas iguais** ali — uma **contagem/agrupamento** pronta,
  sem expandir os N itens.
- `^1` diz "igual à linha 1" — multiplicidade/dedup visível.
- `*N+delta|template` (seq-RLE) descreve uma **progressão** (ex.: IDs sequenciais) sem listar
  cada valor.

Ou seja, dá pra **contar elementos, agrupar e até somar** lendo os marcadores — materializando
só o pedaço necessário. Um compressor binário (gzip/brotli) por cima faria o oposto: você teria
que **alocar memória e descomprimir tudo** pra só então varrer os dados. É essa a faixa que a
1.0 quer firmar: **compacto e ao mesmo tempo consultável**, não um blob opaco. Os filtros por
natureza (CPF/CNPJ/IP e, no roadmap, numéricos) entram aqui — dão estrutura semântica explícita
sem perder a legibilidade (ainda em evolução, ver acima).

### `view()` — caminhos de consulta SQL-like com descompressão seletiva *(API read-only do core)*

Uma API *lazy* sobre o blob: conecta **sem descomprimir**, e só materializa a coluna
(e as linhas) que o agregador precisa. Filtrar por algo descomprime **só** o que tem relação.
Ela é SQL-like em capacidade, não um parser SQL: oferece projeção, filtros, encadeamento AND,
agregadores e agrupamentos como métodos Python. Não implementa joins, NULL SQL, ORDER/LIMIT ou
um planejador geral.

```python
v = view(blob)                                # conecta, não descomprime nada
v.count()                                     # 6        toca: valor
v.sum("valor")                                # 750      toca: valor
v.avg("valor")                                # 125
v.max("valor"), v.min("valor")                # 200, 80
v.where("cidade", "Sao Paulo").count()        # 4        toca: cidade
v.where("cidade", "Sao Paulo").sum("valor")   # 470      toca: cidade, valor
```

O `toca:` é o ponto (saída real): a soma filtrada materializou **só** `cidade` +
`valor` — `cliente` e `plano` nunca foram descomprimidos. Um `decode()` (ou um gzip/brotli
por cima) materializaria as 4 colunas **inteiras** antes de qualquer conta. Agregadores:
`count`, `sum`, `min`, `max`, `avg` + `where`; **L3–L5 já implementados** — contar/agrupar
**sem expandir** (via dicionário/raw; o `*N|` do modo-tcf é entrelaçado, **não separável**),
filtro pelo índice do dicionário, e group-by por **layout ordenado** (`sort_by`).

Em dados reais (online-retail, 5 000 × 8), responder *"quantos itens o usuário X comprou"*
(`where(CustomerID=X).sum("Quantity")`) **materializa 7,9% do blob** — `count()` toca 0,2% —
contra 100% de um `decode()`. Memória e latência baixas caem direto da estrutura. É uma
API read-only do core e lê o `#TCF.8M` atual.

Superfície atual: `count`, `sum`, `min`, `max`, `avg`, `where`, `select`, `group_count` e,
experimentalmente, `group_ranges`/`agg_by` em layouts ordenados. Colunas `@dict`/raw podem ser
consultadas estruturalmente; uma coluna `tcf` entrelaçada pode exigir materialização completa.
O contrato detalhado está em [`docs/reference/lazy-view.md`](docs/reference/lazy-view.md).

## Roadmap 2.0

Depois de uma 1.0 sólida (registrado, **não** implementado — ver
[ADR-0018](docs/adr/0018-v2-format-roadmap.md)):

- **Agregados sem perda mesmo sendo lossy por linha** — somas/médias exatas no agregado ao
  arredondar com resíduo (ex.: parcelamento, `valor = soma(parcelas)`) e *drop* de coluna
  derivável (`total = base + imposto`). Cruza a linha lossless → decisão explícita + GATE
  (Pacote 10, [`loss-taxonomia.md`](experiments/lab/dirty/notas/loss-taxonomia.md)).
- **Streaming / baixa latência (V2-J)** e **disco zero-copy / column-pruning (V2-K)** —
  transmitir e ler por pedaço, sem buffer-over-buffer.
- **Camada binária interna (V2-L)** — empacotar o corpo em bytes mantendo header textual e
  grupos visíveis (estilo Parquet, mas ainda explicável). Não compete com gzip/brotli: é
  representação binária do **mesmo** conteúdo lógico.
- **Mais specs** (templated/checksummed/numéricos), Ceiling delta-aware, índices locais e
  **repetição intra-valor** — pesquisa `.9`/pré-1.0, com gate real-world.

## Install

```bash
pip install tcf-format        # ou: uv pip install tcf-format
```

A **distribuição** chama-se `tcf-format`; o **pacote importável** é `tcf` (sem
dependências de runtime):

```python
from tcf import encode, decode

tabela = {
    "nome": ["ana", "bruno", "carla"],
    # CPFs de exemplo com digitos repetidos: invalidos por convencao (rejeitados
    # por qualquer validador; a Receita nunca os emite). Nao correspondem a pessoas reais.
    "cpf":  ["111.111.111-11", "222.222.222-22", "333.333.333-33"],
}
blob = encode(tabela)
assert decode(blob) == tabela        # round-trip lossless
```

Para CPF/CNPJ/IP há *natures* opt-in (ADR-0015, `encode(coluna, nature=SPEC_CPF)`)
que regeneram o dígito verificador no decode.

Pré-1.0 (ADR-0024): o pacote está em `0.8.0` — o *minor* acompanha o formato
(`#TCF.8`) e o *patch* é contador de release, desacoplado do comportamento.

## First-time setup (dev)

```bash
# Clone + install dev deps
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"

# (recomendado) instalar pre-commit hooks
pre-commit install

# Rodar hooks em todos arquivos (opcional, baseline)
pre-commit run --all-files
```

Hooks configurados (ver [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):
- `ruff` lint + format
- `detect-secrets` (scan)
- basicos: trailing-whitespace, end-of-file-fixer, check-merge-conflict, check-added-large-files
- custom: bloqueia cache dirs (`__pycache__/`, `.pytest_cache/`, etc.) acidentalmente staged

## How to cite

Ver [`CITATION.cff`](CITATION.cff). GitHub renderiza badge "Cite this
repository" na pagina do repo automaticamente.

---

## Benchmark LLM v0.5 (acessorio, projeto paralelo)

> Esta secao resume o ciclo **v0.5** (formato columnar para consumo por LLMs).
> NAO e' o algoritmo TCF v0.7 acima. Todo o material vive separado.

O ciclo v0.5 mediu compreensao de tabelas por LLMs (CSV/JSON/TOON/TCF,
Linha A "LLM le e computa" + Linha B "LLM gera SQL"): 7 modelos comerciais
+ 13 locais, 2 datasets, 2256 registros, 38 findings.
Usava o **motor de niveis** (`EncodeConfig(level=N)`) em [`old/tcf/`](old/tcf/).
Ver [`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md) para a semantica L0–L3.

- **Harness** (runners, llm_eval, scripts): [`llm-benchmark/`](llm-benchmark/)
- **Catalogo de achados** F-Q01..Q38: [`docs/findings/`](docs/findings/)
  + [`docs/FINDINGS_SUMMARY.md`](docs/FINDINGS_SUMMARY.md)
- **Manual / paper v0.5**: [`docs/archive/manual_v05/`](docs/archive/manual_v05/)
  + [`docs/archive/article_v05/`](docs/archive/article_v05/)

Candidato a spin-off (`tcf-llm-tools`) no futuro. Pode re-validar contra v0.7
se Phase 2 for revivida.

---

## Repository layout

```
TCF/
├── src/tcf/                 ← API CANÔNICA v0.8 (OBAT+HCC, encode/decode/view, #TCF.8)
├── old/tcf/                 ← motor v0.5 (niveis L0–L3), congelado-historico (ver LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← labs v0.8 (dirty + clean): compressao composicional
├── llm-benchmark/           ← benchmark LLM v0.5 (harness: runners + llm_eval), acessorio
├── tests/                   ← pytest suite (v0.8)
├── datasets/                ← canonical metadata + samples (dados reais em Z:)
├── tickets/                 ← planejamento markdown (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← specs canonicos v0.8 (OBAT, HCC, TCF-format) [reference]
│   ├── adr/                 ← decisoes numeradas, imutaveis
│   ├── theory/              ← fundamentos teoricos [explanation]
│   ├── how-to/, tutorials/  ← Diataxis
│   ├── findings/            ← catalogo cientifico v0.5 LLM (F-Q01..Q38) [historico]
│   ├── workbench/           ← dev timeline, research notes (partes em _archive/)
│   └── archive/             ← material v0.5/v0.1 congelado (manual_v05, article_v05, etc.)
├── config/                  ← storage.json (aponta Z:), api_keys (gitignored)
├── README.md                ← you are here
└── CHANGELOG.md             ← release history
```

> Para o mapa detalhado, ver [MAP.md](MAP.md). Os diretorios `docs/manual/`
> e `docs/article/` NAO existem; o material v0.5 correspondente esta em
> `docs/archive/manual_v05/` e `docs/archive/article_v05/`.

---

## Ferramentas entregues (v0.8)

O encoder e' a ferramenta principal; auxiliares de suporte (NAO TCF-core):

- **Shaper** (`scripts/shaper/`): stratified, FK-preserving sampling framework.
  Standalone-able as a separate library; see
  [shaper-as-standalone-tool note](docs/workbench/research-notes/_archive/2026-04-25-shaper-as-standalone-tool.md)
- **DatasetReader** (`scripts/dataset_reader.py`): uniform interface
  over SQLite hubs (rows, columns, query, column_stats)
- **setup_\*.py** (`scripts/`): download/geracao dos datasets canonicos
  (Adult, TPC-H, IBGE, CNPJ, etc.); ver [datasets/README.md](datasets/README.md)

> Pré-1.0: **library-only** (sem CLI; ver `pyproject.toml`).
> O benchmark LLM v0.5 (CommercialClient, M-series runners) vive em
> [`llm-benchmark/`](llm-benchmark/), com instrucoes de reproducao no README de la'.

---

## Where to go next

- **Quero usar TCF no pipeline** → API v0.8: `from tcf import encode, decode` ([src/tcf/](src/tcf/)); veja o [tutorial](docs/tutorials/getting-started.pt-BR.md) e os [guias](docs/how-to/).
- **I want to read the findings** → [docs/findings/](docs/findings/) (v0.5 LLM, historico)
- **I want to run the LLM benchmark** → [llm-benchmark/](llm-benchmark/) (acessorio v0.5)
- **I want to understand the architecture** → [docs/theory/](docs/theory/)
- **I want to see the roadmap** → [ROADMAP.md](ROADMAP.md) (tiers: pré-1.0 / 2.0 / pesquisa); detalhe granular em [roadmap-hipoteses.md](experiments/lab/dirty/notas/roadmap-hipoteses.md)
- **Quero caminhos de consulta SQL-like sem materializar tudo** → [`tcf.view`](docs/reference/lazy-view.md) (`count`/`sum`/`where`/group-by, quando o modo da coluna permite)
- **I want to share / pitch TCF** → [docs/divulgacao-tcf.md](docs/divulgacao-tcf.md) (material de divulgação, estilo post)
- **I want to read the paper** → drafts v0.5: [docs/archive/article_v05/](docs/archive/article_v05/) (paper v0.7 pendente)
- **I want to see how it evolved** → [CHANGELOG.md](CHANGELOG.md) +
  [docs/workbench/](docs/workbench/)

---

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Project conceived as part of an academic dissertation (TCC). Datasets:
[UCI Adult Census](https://archive.ics.uci.edu/ml/datasets/adult) and
[TPC-H](https://www.tpc.org/tpch/) (via DuckDB tpch extension).
(Ciclo v0.5) Commercial LLM testing supported by personal credits;
total spend $9.46 USD for 1968 records (75% cache savings).
