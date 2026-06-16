# TCF · Tabular Compact Format

[![CI](https://github.com/LeoPR/TCF/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoPR/TCF/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.7.1%20(pré--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.7%20default-blue)

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

**TCF** *(244 B, formato 0.7, saída real do `encode`)*: o que se repete vira referência; o que é único fica cru.

```
#TCF.7 M
!44=nome,42=email,28=cidade,20=plano,!cpf
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

- Linha 1, shebang: `#TCF.7 M` é o formato 0.7, multi-coluna.
- Linha 2, meta das colunas (`tamanho=nome`).
  O `!` marca uma coluna guardada **crua** (quando o raw fica menor que o TCF).
  A última (`cpf`) não leva tamanho: vai até o fim (e o `!` mostra que também é crua).
- Os corpos vêm concatenados, **delimitados por tamanho, não por quebra de linha**.
  Por isso a coluna crua `nome` (`…Diego Rocha`) emenda direto no e-mail (`an*a*…`).
- No corpo: `*3|Sao Paulo` é *"Sao Paulo, 3×"* (repetição).
  `^1` é *"igual à linha 1"* (substituição).
- Na coluna de **e-mail** o TCF vai mais fundo (prefixo único + domínio comum referenciado).
  É onde mais economiza, e onde o texto fica mais denso.
- Já a coluna **`cpf`** é o oposto: valores quase todos únicos, **nada a fatorar**.
  O TCF guarda **cru** (`!cpf`) — não comprime, mas também **não infla** (é o fallback).
  *(São placeholders inválidos — dígitos repetidos. Para CPF/CNPJ real há uma* nature *opt-in,
  ADR-0015, que tira `.`/`-` e regenera o dígito verificador — aí sim comprime.)*

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

- **encode** tira a pontuação, guarda os 9 dígitos como um número curto (base-94, ~5 chars)
  e **descarta o verificador**;
- **decode** **recalcula** o verificador (mod-11) e reinsere a pontuação — reconstrução **exata**.

Os mesmos 4 CPFs do exemplo, isolados numa coluna: sem filtro **76 B** (cru, com escapes);
com `nature=SPEC_CPF`, **27 B** (−64%). Concretamente, como sai dos nossos labs
([`2026-05-24-cpf-templated-checked/`](experiments/lab/dirty/2026-05-24-cpf-templated-checked/)):
`111.111.111-11` → `%g$.u` (14 → 5 chars); o decode regenera os 2 dígitos verificadores e a
pontuação. (No cadastro inteiro: cru **244 → 208 B**, −15%.)

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

cpfs = ["111.111.111-11", "222.222.222-22"]    # placeholders inválidos
blob = encode(cpfs, nature=SPEC_CPF)
assert decode(blob, nature=SPEC_CPF) == cpfs    # decode precisa da mesma nature
```

Dois detalhes honestos:

- São **opt-in e, por ora, out-of-band**: o `.tcf` ainda **não carrega um marcador** dizendo
  "esta coluna é CPF", então o `decode` precisa receber a mesma `nature`. Um marcador
  auto-descritivo (decode reconhece sozinho) está registrado como evolução (alvo 0.8).
- Valor que não bate (verificador inválido, formato mascarado) cai em **literal** (`_`) sem
  nunca quebrar o round-trip — o filtro **nunca corrompe** o dado.

> ⚠️ **Em evolução.** Os filtros já funcionam e estão validados nos labs, mas ainda são
> **opt-in manuais**: o auto-detect e o **marcador auto-descritivo** (o `decode` reconhecer a
> nature sozinho) estão sendo trabalhados (alvo 0.8). Trate esta seção como *work-in-progress*.

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

# Naturezas (opt-in): CPF/CNPJ/IP comprimidos sem digito verificador/padding
from tcf import SPEC_CPF
text = encode(["111.111.111-11", "222.222.222-22"], nature=SPEC_CPF)  # placeholders inválidos
```

`encode` dispatcha por tipo (list → single-column, dict → multi-column).
`decode` roteia pelo shebang.

Tutorial passo-a-passo: [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md).
Guias praticos: [`docs/how-to/`](docs/how-to/).

## Formato 0.7 (default): onde os bytes vão

O `encode` multi-coluna sai em **0.7 / `#TCF.7`** por default ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
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
  O flag `M` no shebang já declara que vêm colunas, então o meta dispensa o prefixo `# `.
  E a última coluna não leva tamanho, vai até o fim ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)).

```python
text = encode(table)        # 0.7 / #TCF.7, é o default, sem flags

# knobs opt-out (default True) — pra modificar o comportamento / inspecionar:
text = encode(table, fallback=False, min_header=False)  # força o legado #TCF.6
text = encode(table, min_header=False)                  # #TCF.7 com header verboso
text = encode(table, min_len=5)                         # override do min_len do OBAT (default: auto)
text = encode(table, sort_by="cidade")                  # ordena linhas pela coluna (order-free, +compressão)
```

> `sort_by` reordena as linhas pela coluna (agrupa similares → menos bytes,
> 5-15% com chave low-card). É **order-free**: o `decode` devolve a ordem
> ordenada, não a original. Use só quando a ordem das linhas não importa.

No cadastro de 5 colunas do topo, comparado ao formato legado `#TCF.6`:

| formato | meta line | bytes |
|---|---|---:|
| **0.7 / `#TCF.7`** (default) | `!44=nome,42=email,28=cidade,20=plano,!cpf` | **244** |
| `#TCF.6` (legado) | `# 45=nome,42=email,28=cidade,20=plano,76=cpf` | 265 |

A diferença (−21 B) vem de duas coisas que o 0.7 faz e o `#TCF.6` não: a coluna `cpf` cai
pra **raw** (`!cpf`) em vez de inflar, e o **header mínimo** (sem `# `, última coluna sem
tamanho). O ganho é proporcionalmente maior em **payloads pequenos**.

Pré-1.0, o encoder só escreve o formato mais novo.
O `#TCF.6` legado ainda é **lido** pelo decoder, e `git checkout` reproduz a era 0.6 ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
O dicionário low-card (V2-B) e o split estrutural já estão no default; a compressão lossy fica no [roadmap](docs/adr/0018-v2-format-roadmap.md).

## Estado (pré-1.0)

- **Pré-1.0** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)).
  Os minors do formato (`#TCF.4/.5/.6/.7`) são iterações de desenvolvimento rumo a um **1.0 sólido**, sem compat rígida entre eles (git reproduz versões antigas).
  v2.0 fica pra depois.
- Implementação canônica em [`src/tcf/`](src/tcf/).
  Round-trip sempre lossless (`decode(encode(x)) == x`).
- Default **0.7 / `#TCF.7`**: fallback ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)) + header mínimo ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)), ver seção acima.
  O `#TCF.6` legado é lido pelo decoder.
- Suíte: **398 passed, 1 xfailed**.
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

Núcleo pinado em testes: D1-D9 = **1523 B** (51.1% do raw, single-col); D17a multi-col = **303 B** (0.7 com V2-B; legado `#TCF.6` = 322 B).
Real-world multi-coluna (9 tabelas Adult + TPC-H, 136k linhas): **−33.02% weighted** vs CSV raw.

**E contra gzip / brotli / zstd?**
Outra categoria: são compressores binários *opacos* (precisa descomprimir pra ler qualquer coisa).
No **cadastro acima**, sob compressão HTTP (`Content-Encoding`):

| formato | cru | gzip | br | zstd |
|---|---:|---:|---:|---:|
| JSON | 596 | 218 | 212 | 211 |
| CSV  | 277 | 177 | **162** | 165 |
| TCF  | **244** | 209 | 185 | 194 |

TCF é o menor **cru** (e legível); sob compressão binária o **CSV+brotli** ganha (162 vs 185) —
porque o TCF já removeu a redundância que o gzip/brotli reaproveitam (o TCF comprime só 244→185;
o CSV 277→162). O TCF **troca um pouco de ratio por legibilidade** e **se compõe** com eles
(244 → 185 com brotli). O `gzip` ainda carrega ~18 B fixos de moldura por mensagem; `br`/`zstd`,
quase nada — em payload minúsculo isso conta. (Os números usam os compressores no **nível máximo**
— melhor caso pra eles; numa API simples a compressão às vezes nem está ligada, e quando está usa
nível baixo por default: nginx gzip `1`, brotli `6`. Ver [notas dos compressores](experiments/lab/clean/EXP-008-compressao-comparada/notes/classificacao-compressores.md).)

No agregado de 15 datasets sintéticos **single-column** (EXP-008, onde os welds multi-col do 0.7
não se aplicam) a mesma história: `csv+brotli` = 1742 B contra `tcf+brotli` = 2116 B. Tabelas
completas: [reports do EXP-008](experiments/lab/clean/EXP-008-compressao-comparada/reports/).

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

### Proposta: `view()` — agregar com descompressão seletiva

Uma API *lazy* sobre o blob: conecta **sem descomprimir**, e só materializa a coluna
(e as linhas) que o agregador precisa. Filtrar por algo descomprime **só** o que tem relação.
*(Proposta, validada em PoC — [`2026-06-16-lazy-query/`](experiments/lab/dirty/2026-06-16-lazy-query/); ainda não em `src/tcf`.)*

```python
v = view(blob)                                # conecta, não descomprime nada
v.count()                                     # 6        toca: valor
v.sum("valor")                                # 750      toca: valor
v.avg("valor")                                # 125
v.max("valor"), v.min("valor")                # 200, 80
v.where("cidade", "Sao Paulo").count()        # 4        toca: cidade
v.where("cidade", "Sao Paulo").sum("valor")   # 470      toca: cidade, valor
```

O `toca:` é o ponto (saída real do PoC): a soma filtrada materializou **só** `cidade` +
`valor` — `cliente` e `plano` nunca foram descomprimidos. Um `decode()` (ou um gzip/brotli
por cima) materializaria as 4 colunas **inteiras** antes de qualquer conta. Agregadores:
`count`, `sum`, `min`, `max`, `avg`, mais `where` pra filtrar. Passo seguinte: usar os
marcadores `*N|` / `*N+delta|` pra contar/somar **runs** sem nem expandir a coluna.

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
- **Mais specs** (templated/checksummed/numéricos) + **marcador auto-descritivo** de nature e
  **repetição intra-valor** (fatorar `111.` dentro de um CPF) — alvo 0.8.

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

Pré-1.0 (ADR-0024): o pacote está em `0.7.x` — o *minor* acompanha o formato
(`#TCF.7`) e o *patch* é contador de release, desacoplado do comportamento.

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
├── src/tcf/                 ← CANONICAL v0.7 API (OBAT+HCC, encode/decode, #TCF.7 + #TCF.6 legado)
├── old/tcf/                 ← motor v0.5 (niveis L0–L3), congelado-historico (ver LEVELS-REVIEW.md)
├── scripts/                 ← Shaper (stratified sampling), CSV→SQLite, setup_* datasets
├── experiments/lab/         ← labs v0.7 (dirty + clean): compressao composicional
├── llm-benchmark/           ← benchmark LLM v0.5 (harness: runners + llm_eval), acessorio
├── tests/                   ← pytest suite (v0.7)
├── datasets/                ← canonical metadata + samples (dados reais em Z:)
├── tickets/                 ← planejamento markdown (YAML frontmatter)
├── docs/
│   ├── algorithms/          ← specs canonicos v0.7 (OBAT, HCC, TCF-format) [reference]
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

## Tools shipped (v0.7)

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

- **I want to use TCF in my pipeline** → API v0.7: `from tcf import encode, decode` ([src/tcf/](src/tcf/)); manual v0.7 pendente. v0.5: [docs/archive/manual_v05/](docs/archive/manual_v05/)
- **I want to read the findings** → [docs/findings/](docs/findings/) (v0.5 LLM, historico)
- **I want to run the LLM benchmark** → [llm-benchmark/](llm-benchmark/) (acessorio v0.5)
- **I want to understand the architecture** → [docs/theory/](docs/theory/)
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
