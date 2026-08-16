# O `.8M` em estágios — o mapa de maleabilidade, e onde estão as soldas

> **Owner (2026-08-16)**: *"ver se não tem soldas duras demais no código, para que ele fique
> mais maleável para possíveis otimizações algorítmicas (cache/buffer, paralelismo,
> semiparalelismo, transmissão com pouca memória, decodificação rápida em stream)... os
> códigos que permitem isso podem ficar um pouco mais separados só pra dar visibilidade...
> o TCF precisa ser uma linguagem — o algoritmo está em Python mas poderia ser Rust ou C;
> o importante é que os algoritmos sejam identificados."*
>
> A régua dele: **1)** `A→F` fundido → **2)** `A→B→C→D→E→F` segmentado pra visibilidade →
> **3)** `A→F` re-fundido *com prova*. **O `.8` olha o 1) espiando o 2); o `.9` faz o 3).**
> Bate com a direção já registrada: `.9` = legibilidade de blocos pra port; 1.0 fecha em Rust.

Tudo abaixo é leitura de código com `arquivo:linha` + o que os labs `1400` e `1450` mediram.
**Nada aqui é implementação** — é o mapa que precede.

---

## 1. Saúde primeiro (a pergunta direta do owner)

**A suíte completa passa: 1260 passed, 3 skipped, 79s** (2026-08-16, pós-welds de single-col).
Gates byte-canonical verdes. O header do `.8M` está íntegro: o invariante de fronteira (as
fatias `[ini:fim)` cobrem o corpo sem furo nem sobra) foi verificado por assert nos labs
`1400` e `1450`, em todas as permutações. **Encode/decode saudáveis; a exceção conhecida é o
`T-POLARIDADE-COME-NOME`** (coluna única com nome terminando em pontuação — defeito real,
reproduzido, aguardando decisão de conserto).

---

## 2. O encode do `.8M` em estágios — o que já é "2)" e o que ainda é "1)"

| estágio | o que faz | onde | fronteira |
|---|---|---|---|
| **E1** valida + stringify | guards (str-iterável, lengths, 0-linhas, `\n` no nome, `''` anônima) + `_stringify_checked` | `multi/core.py:279-339` | **limpa** — fonte única compartilhada com o ramo list do encoder |
| **E2** corpo core por coluna | `_encode_column` (o MESMO do single-col) | `multi/parallel.py:30` (serial) · `:101` (workers) | **limpa e JÁ PARALELA** — byte-idêntico ao serial; módulo declara "concern de HOSPEDEIRO, não do core portável" |
| **E3** candidatos por coluna | `min(tcf, raw, dict, split)` | `_best_of`, `multi/core.py:420-434` | função limpa, **mas idioma divergente** (§4.1) |
| **E4** FLOOR da nature | compara blob serializado inteiro, com × sem spec | `multi/core.py:439-481` | **SOLDA** (§4.2) |
| **E5** emissão do meta+corpo | monta linha 1 + concatena corpos | `_serialize`, `multi/core.py:398-418` | **closure** dentro de `_encode_multi` (§4.3) |

Custo estrutural já conhecido e ticketado: E2 **sempre** materializa o corpo `tcf` mesmo
quando raw/dict/split vence — `T-GATES-ANTES` (`.9`) é exatamente isso.

## 3. O decode do `.8M` em estágios

| estágio | o que faz | onde | fronteira |
|---|---|---|---|
| **D0** polaridade de borda | despolariza ANTES de qualquer dispatch | `decoder.py:154-161` | **A SOLDA MAIS DURA** — não conhece a gramática M/H e come o fim do meta (`T-POLARIDADE-COME-NOME`) |
| **D1** dispatch 1 char | disc no índice 6; desconhecido = fail-loud | `decoder.py:164-190` | limpa |
| **D2** parse do meta | `[(size, nome, modo, nat)]` | `_parse_meta`, `multi/core.py:177-232` | **O MODELO** — fonte única, decode E view consomem (paridade por construção) |
| **D3** fatiamento por sizes | offsets = prefix-sum dos sizes | `multi/core.py:595-619` | limpa; **todos os offsets saem do header sozinho** |
| **D4** decode por modo | raw / dict / split / tcf | `multi/core.py:607-616` | pura por coluna |
| **D5** aplicação de natures | resolve `:id` + `decode_value` | `decoder.py:205-217`, FORA do core | separação certa — o core fica nature-agnóstico (`multi/core.py:539-545`) |
| **D6** integridade deduzida | truncado / excedente / n_rows | `multi/core.py:602-633` | limpa, custo ~zero — **com 1 gap novo** (§4.4) |

**A prova viva de que os estágios são reais**: o `view` já compõe D2+D3+D4 por fora do
decode (fatiar sem decodificar). Um segundo consumidor usando as mesmas peças de outro jeito
é o teste de que a segmentação existe de fato, não só no desenho.

---

## 4. As soldas encontradas — cada uma com o desapontamento nomeado

### 4.1 Dois idiomas para a MESMA ideia (E3 × single-col)

O single-col monta uma **lista de candidatos + `min()`** (`encoder.py:549-600`,
`candidatos.append(...)` → `min(...)`). O `.8M` faz a mesma coisa como **cadeia de ifs**
(`_best_of`). Mesma álgebra, duas grafias — e é por isso que a união dos candidatos
(`T-UM-CAMINHO-SO`) custa mais do que deveria: cada mecanismo novo precisa ser escrito nos
dois idiomas. **Unificar o idioma (lista+`min()`) é o "resumir o multi-column" mais barato
que existe** — não muda byte, muda o custo de tudo que vem depois.

### 4.2 O FLOOR serializa o blob inteiro (E4)

`multi/core.py:473-475`: para cada coluna com spec, o FLOOR chama `_serialize` **duas vezes
sobre a tabela inteira** (com e sem o candidato). Correto — never-worse global, o custo do
`:id` e do size entram na conta — mas funde a decisão com a emissão: O(specs×colunas)
serializações do blob todo. O equivalente local (delta do corpo + delta do meta da coluna) é
byte-idêntico *por construção a provar* e corta isso para O(1) por candidato. Candidato `.9`,
com contra-prova byte-canonical obrigatória.

### 4.3 `_serialize` é closure (E5)

O emissor da gramática do meta vive **dentro** de `_encode_multi`, capturando
`drop_names`/`min_header`. O leitor (`_parse_meta`) é função de módulo endereçável; o emissor
não. Para o objetivo-linguagem (port Rust/C), o par emissor/leitor da gramática deveria ser
**um PAR nomeado e endereçável** — hoje só metade é.

### 4.4 D6 não confere contagem de colunas (gap NOVO, medido no lab `1450`)

O decode não confere `len(result) == len(pares do header)`. Wire à mão com coluna ANÔNIMA na
posição 0 + coluna NOMEADA `"0"` → as duas viram a chave `"0"` e o dict **sobrescreve
calado**: header declara 3 colunas, decode devolve 2, valores da anônima somem. O encode não
emite essa forma (chaves de dict são únicas; `''` tem guard próprio em `core.py:316-326`) —
é decode-de-wire-estrangeiro, mas a régua do BUG-05 ("integridade deduzida de graça") cobre:
**é 1 linha de fail-loud**. Precisa de aprovação (mexe em src).

### 4.5 D0: a polaridade antes do fork

Já registrada (`T-POLARIDADE-COME-NOME`). No vocabulário desta nota: uma camada de borda
soldada **antes** do ponto onde precisava enxergar o fork. A decisão pendente é de fronteira
— escapar o nome contra o alfabeto da polaridade no emissor, ou dar escopo de disc à borda.

---

## 5. Prontidão para os vetores do owner (cache/buffer/paralelo/stream/memória)

| vetor | estado | o que falta |
|---|---|---|
| paralelismo de **encode** | **existe** (E2), byte-idêntico, work-stealing | cap global (`T-CODE-PARALLEL-BUDGET`, `.9`) |
| paralelismo de **decode** | não existe — mas D3 mostra que é **só orquestração**: offsets todos deduzíveis do header, cada coluna é tarefa independente | zero mudança de formato; candidato `.9` limpo |
| **stream de decode** (decodificar coluna a coluna conforme chega) | **possível HOJE** para todas menos a última (precisa de EOF); com `min_header=False` nem essa | nada no formato; é API/consumo |
| **stream de encode** / TTFB | bloqueado: sizes antes do body (V2-J, ADR-0018; O-FMT-15 é o degrau zero) | decisão já tomada: defer 2.0 |
| **memória** | encode materializa tudo (corpo tcf de cada coluna mesmo perdedor + `b"".join`, `core.py:503`); decode pode ser O(1 coluna) fatiando — o view prova | `T-GATES-ANTES` ataca metade; o resto é `.9` |

O resumo que importa: **o header é o único coldstart** — exatamente como o owner formulou.
Depois da linha 1, cada coluna é independente nos dois sentidos, e os três vetores de
paralelismo/stream de LEITURA não pedem nenhuma mudança de formato. O único bloqueio de
formato é do lado da EMISSÃO (sizes-antes-do-body), e já está decidido como defer.

---

## 6. Os algoritmos nomeados — o índice para port (o objetivo-linguagem)

| algoritmo | papel | onde |
|---|---|---|
| **OBAT** (Online Bidirectional Affix Tokenizer) | tokenização/afixos do corpo core | `alg16`; `encoder.py::_encode_column` |
| **HCC** (Hierarchical Compositional Coding) | composição hierárquica de refs | `M8.A`; `composicional/` |
| **RLE adjacente** `*N\|` + **seq-RLE** `*N+d\|` + **periódico** `*N~...\|` | runs, progressões e ciclos | ADR-0040; `composicional/hcc_seqrle.py` |
| **polaridade** | delimitador de borda single-col | ADR-0035; `composicional/polaridade.py` |
| **bN de domínio** (`B`/`C`) + **denso b1/b2** | baixa cardinalidade em bits | ADR-0036/0037; `composicional/dominio_bn.py`, `bitpack.py` |
| **dict-V2B** | dicionário categórico + stream base-94 | ADR-0025; `multi/dict_v2b.py` |
| **split estrutural** `%` | template 1× + campos de dígito como sub-tabela (recursa em `_encode_multi`) | ADR-0026; `multi/split.py` |
| **natures per-valor** | pre-tx opt-in com fallback literal `_`; id em 2 planos (`name`/`wire_id`) | ADR-0015/0027/0041; `natures/` |
| **FLOOR / `min()` de candidatos** | competição never-worse | single: `encoder.py:549-600` · multi: `core.py:420-481` |
| **gramática do meta `.8M`** | `par ::= pre corpo nat`; pre ∈ `{'',!,@,%}`; sizes HEX; última sem size; anônima = posicional | emissor `core.py:398-418` · leitor `core.py:177-232` (EBNF completa no mapeamento de M/H, journal `wf_4e4e1119`) |

Quem tiver esta tabela + os ADRs citados consegue reimplementar o `.8M` sem ler o Python —
esse é o critério. O que ainda **não** atende o critério: o emissor-closure (§4.3) e os dois
idiomas de FLOOR (§4.1).

---

## 7. Vínculo

Labs: [`1400-cadastro-popular-header-do-M`](../../2026-08/2026-08-16/2026-08-16-1400-cadastro-popular-header-do-M/) ·
[`1450-ordem-de-colunas-no-M`](../../2026-08/2026-08-16/2026-08-16-1450-ordem-de-colunas-no-M/) —
Tickets: `T-UM-CAMINHO-SO` · `T-GATES-ANTES` · `T-CODE-PARALLEL-BUDGET` · `T-POLARIDADE-COME-NOME` ·
`T-8H-UM-CANDIDATO-SO` — ADRs: 0018 (V2-J) · 0022/0025/0026 (modos) · 0023 (min_header) ·
0029 (disc) · 0032 (`.8M` default) · 0041 (dois planos) — Direções:
`project_rust_1_0_e_dot9_legibilidade` (o `.9`/1.0 que esta nota alimenta) ·
`contrato-externalizado-e-aceleradores.md` (o inventário das 12 ideias).
