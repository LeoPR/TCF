# O que falta pro `.8M` — o inventário, o gargalo, e a ordem

> **Owner (2026-08-16)**: *"veja o que mais falta pro M, vamos ir fechando."*

Inventário levantado do `STATUS.md` (15 tickets citam multi-col), das notas e do código, com
duas verificações novas medidas aqui. **Nada abaixo é implementação** — é o mapa que precede.

---

## 0. A diretriz do owner, registrada antes (não é achado meu)

> *"São várias camadas de distinção que flutuam entre serialização e paralelismo: identificar
> tipos, ver se passa pelo núcleo, ver se pode processar paralelamente **mesmo que a saída seja
> serial**, processar paralelamente **E também transmitir** paralelamente. Não é ou um ou
> outro — são muitos uns-outros **e os dois**. Por isso o planejamento de quebra em peças ajuda
> a ver o que pode ser feito ao mesmo tempo, seja entrada, meio e saída, além de ver qual
> atende mais compressão, mais velocidade, mais paralelismo, menos latência, menos memória. E
> também a parte do decode, que também tem tudo isso — entre já poder entregar uma coluna ou
> fazer filtros paralelos com entrega **enquanto o encode talvez nem tenha terminado**. A
> complexidade disso exige um estudo totalmente dedicado em muitas etapas."* (2026-08-16)

**Consequência de escopo**: o estudo dedicado **não é este trabalho** e não é `.8`. O que o
`.8` faz é **não fechar portas** — e é por isso que as 6 invariantes do lab `1530` foram
medidas: elas são o que garante que o estudo, quando vier, encontra o formato pronto.

O eixo que a formulação acrescenta e o projeto ainda **não tem registrado em lugar nenhum**:
*decode entregando enquanto o encode não terminou* — produtor e consumidor concorrentes sobre
o mesmo blob. Fica nomeado aqui para o estudo dedicado; nenhum ticket atual o cobre.

---

## 1. O gargalo: `T-META-NAO-DECLARA-MODO` trava o `T-UM-CAMINHO-SO`

Esta é a descoberta que reorganiza a fila. O `T-UM-CAMINHO-SO` (unir os candidatos) é o item
de maior retorno do M — mas **ele não pode ser feito hoje**, e o motivo está a um ticket de
distância:

- o meta do `.8M` declara **`!`raw / `@`dict / `%`split** + `<size>=<nome>:<spec>`, e o `size`
  é em **bytes**;
- os modos que faltam **carregam metadado que não cabe**: denso `#TCF.8b1258` = largura de bit
  **+ contagem de valores**; bN `#TCF.8B2258` = largura do índice **+ contagem**; polaridade
  `#TCF.8!!` = **o char eleito**;
- logo unir os candidatos exige **estender a gramática do meta** — mudança de FORMATO, não de
  código.

**A ordem correta é: estender o meta → então unir os candidatos.** Fazer o contrário é
descobrir no meio que o wire não sabe dizer o que o corpo é.

### 1b. A armadilha do marcador — e a regra do ticket está INCOMPLETA (medido aqui)

O `T-BN-MULTICOL` registra: *"marcador de modo novo no meta = **pontuação, nunca letra**
(`B178=col` é HEX-PARSEADO CALADO pelo `_parse_meta`)"*. Confirmado — e a regra **não é
suficiente**. Varri `string.punctuation + letras + espaço/tab` contra o `_parse_meta` de hoje:

| classe | chars | o que acontece |
|---|---|---|
| **seguros** (67) | `"#$&'()*,./:;<=>?[\]^_\`{|}~` + `g-z` `G-Z` | **fail-loud** — o parser nota que não conhece |
| **perigosos** (16) | `a-f` `A-F` (hex) | hex-parseado calado: `B178` vira size **45432** (`0xb178`) |
| **perigosos** | **`+`** | `int('+178',16)` = **376** — aceito como SINAL, cai em `tcf` calado |
| **perigosos** | **`-`** | size **−376** (negativo!), calado |
| **perigosos** | espaço, tab | aceitos por `int()`, caem em `tcf` calado |

**`+` e `-` são pontuação e são perigosos** — a regra do ticket os autorizaria. A regra
correta é comportamental, não tipográfica:

> **um char só serve como marcador de modo se `int(<char>+digitos, 16)` LEVANTAR.**

Isso importa por compatibilidade: um decoder antigo lendo um wire novo tem de **falhar alto**,
nunca ler um size errado. Com `+` ele leria size 376 e fatiaria a coluna errada.

---

## 2. O inventário completo — 4 grupos

### Grupo A — a solda dupla (uma causa, quatro sintomas). **Bloqueado pelo grupo B1.**

| ticket | medido | nota |
|---|---|---|
| **`T-UM-CAMINHO-SO`** | a causa | sequenciado "depois dos tipos" = agora |
| `T-BAIXA-CARD-EM-TABELA` | **5× a 12,8×** | o próprio ticket diz: *"NÃO é item de M/H: é sintoma da solda dupla e some junto com o T-UM-CAMINHO-SO"* |
| `T-BN-MULTICOL` | 13,8% | **englobado** pelo anterior |
| `T-8H-UM-CANDIDATO-SO` | 99,986% do overhead do `.8H` | o mesmo problema pela outra porta (`stamp=False`) |

Confirmado por medição própria: os candidatos de single e multi são **quase disjuntos** — no
cadastro o flat vence 4/7 e o `.8M` vence 3/7 (lab `1400`); no adult-census o flat vence 13/15
(soma de 15 wires flat = 32.972 B contra 41.925 do `.8M`). **A resposta é a união, não a
troca** — e o próprio `T-BAIXA-CARD-EM-TABELA` avisa que levar o denso pro multi **sem** unir
os caminhos *"AUMENTARIA a solda dupla"*.

### Grupo B — o que destrava (formato)

| item | estado |
|---|---|
| **B1. `T-META-NAO-DECLARA-MODO`** | **o gargalo**. Proposta registrada é barata: a cada tipo fechado, uma linha dizendo *o que este modo precisa declarar e se cabe*. Já são **4 casos** acumulados (denso, bN, polaridade, e o int com PAD/OFFPAD/B94) |
| B2. `T-SPEC-SEM-CARIMBO` | desenhado (ADR-0041 §4), falta weld; −4 B no cadastro |
| B3. O-FMT-14 (header derivável) | o único lever grande do header; feature de **contrato**, não byte |

### Grupo C — defeitos de correção (independentes, prontos, baratos)

| item | severidade |
|---|---|
| **`T-POLARIDADE-COME-NOME`** | **RT quebrado calado** — 48/64 no `.8M`, 38/64 no `.8H`, 0 warnings. A pior classe |
| `T-META-COLISAO-NOME-POSICIONAL` | perde coluna calada em wire estrangeiro; **1 linha** de fail-loud |
| `T-NATURE-IGNORADA-CALADA` (1) e (2) | `nature_per_col` descartado calado na rota tipada e com coluna inexistente |

**Nenhum depende de nada.** São os três que dá pra fechar sem decidir mais nada.

### Grupo A2 — agrupar/compartilhar entre colunas (MEDIDO 2026-08-16, escopo `.9`)

Proposta do owner: *"grupos de tipos comuns, como true/false, podem compartilhar
solidariamente o header de spec"*. Lab `1610-agrupar-tipos-comuns-no-M`, 4 predições, todas
confirmadas:

| | teto |
|---|---:|
| compartilhar a **declaração** de 5 flags | 20 B = **0,13%** |
| compartilhar o **domínio**, bool (k=2) | **0,5%** |
| compartilhar o **domínio**, k=500 | **21,2%** |
| domínios **disjuntos** | **0** |
| **ter o candidato certo** (Grupo A) nas mesmas flags | **5,7×** |

**O tipo não é a variável — o tamanho do domínio sobreposto é**; `true`/`false` é o pior caso
da proposta. As duas metades somadas valem **1/206** do Grupo A. Reproduz o `cross-dict` /
`H-GDICT` (−19,2% em same-domain-refs), **já escopado pelo owner para `0.9`** em 2026-06-24 —
a medição confirma o escopo. Correção de gatilho para quando vier: agrupar por **domínio
sobreposto**, não por tipo (detectável no pré-passe, que já calcula cardinalidade). Custo em
paralelismo: **barreira, não perda** (1 tarefa + N independentes; o `view` já faz isso dentro
de uma coluna).

### Grupo D — não é do M (fica registrado pra não voltar à fila)

`T-SPLIT-SINGLE-COL` (é do single-col; e a ressalva de ordem já derrubou parte do 7,13×) ·
`T-NUMERO-SPEC`, `T-DATETIME-TIPO` (tipos) · `T-PULSO-SINGLE-COL`, `T-LAZY-BYPASS-ARITMETICO`
(pulsos/lazy — por decisão do owner, o lazy é o último) · `T-BN-GZIP`, `T-MISTO-RLE-B64-SINGLE`.

---

## 3. O que JÁ está fechado no M (para não re-abrir)

| | evidência |
|---|---|
| o header está **no piso** | O-FMT-11 fechado; re-verificado pós-welds (lab `1530`): mesma fórmula, 12 B em 2 colunas anônimas |
| tirar os sizes **não é opção** | O-FMT-19 **refutado** — mata decode paralelo e o O(1) do lazy |
| sizes em hex é a decisão | O-FMT-18 medido; base-94 colidiria com os separadores (exigiria base-87); fica como modo byte-máximo sob contrato |
| **a fronteira de coluna está provada** | 6 invariantes testadas (lab `1530`), incluindo **decode paralelo real idêntico ao serial**, com `src/tcf` intocado |
| a ordem das colunas é livre | lab `1450`: corpos byte-idênticos em qualquer permutação; variação total 3 B |
| o perfil stream-ready custa 4 B | `min_header=False` zera as colunas que dependem de EOF |
| paralelismo de **encode** existe | `multi/parallel.py`, byte-idêntico ao serial |

---

## 4. A ordem proposta para fechar o M

1. **Grupo C inteiro** — três defeitos de correção, independentes, e um deles corrompe dado
   calado. Não espera decisão nenhuma.
2. **B1 (`T-META-NAO-DECLARA-MODO`)** — a extensão do meta, com o alfabeto seguro medido no §1b
   como restrição de desenho. É o que destrava o Grupo A inteiro.
3. **Grupo A** — a união dos candidatos, agora que o meta sabe declarar.
4. **B2** (`T-SPEC-SEM-CARIMBO`) e **B3** (O-FMT-14) — os dois são contrato-nas-pontas e podem
   vir juntos, depois.

O estudo dedicado de serialização×paralelismo (§0) vem **depois** e encontra o formato pronto —
as invariantes do `1530` são exatamente a garantia disso.

**Tudo do Grupo C e o B1 mexem em `src/tcf` e exigem aprovação explícita.**

---

## 5. Vínculo

Labs: [`1400`](../../2026-08/2026-08-16/2026-08-16-1400-cadastro-popular-header-do-M/) ·
[`1450`](../../2026-08/2026-08-16/2026-08-16-1450-ordem-de-colunas-no-M/) ·
[`1530`](../../2026-08/2026-08-16/2026-08-16-1530-piso-do-header-e-fronteira-paralela/) ·
[`1330`](../../2026-08/2026-08-16/2026-08-16-1330-polaridade-come-nome-de-coluna/) —
Nota irmã: [`estagios-e-soldas-do-M`](2026-08-16-1510-estagios-e-soldas-do-M.md) —
O-FMT-11/13/14/18/19 · ADR-0004/0023/0026/0029/0032/0035/0036/0037/0041
