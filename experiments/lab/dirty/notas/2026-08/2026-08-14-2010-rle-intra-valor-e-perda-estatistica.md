# RLE intra-valor e perda orientada a erro — estudo e análise crítica

**2026-08-14** · duas direções do owner, numa sessão só:

> *"tinha o caso desses itens repetidos no meio do texto… `0.30000000000000004` poderia ser
> feito como `0.3(14x0)4`… ou ainda pra aproveitar o fluxo: `14x0` / `\0.3 <ref-01> 4`… um
> 'RLE fantasma' que descomprime só pra preencher dicionário, não coloca no conteúdo de fato.
> Veja se a ideia do RLE é simples ou arriscada."*
>
> *"quanto ao loss, talvez fazer ficar orientado à estatística de perdas e erros ajudaria. Se a
> perda significa algo como 1% numa soma ou multiplicação?… se é financeiramente ou fisicamente
> coerente arredondar dentro de alguma margem dentro da realidade, com justificativas em várias
> áreas."*

**Tipo**: [probatório] estudo + análise crítica. Nenhum weld, `src/tcf` intocado.

---

# PARTE 1 — RLE intra-valor

## 1.1 Já discutimos — e a ideia é sua, de 2026-06-16

Está registrada em três lugares que se cross-referenciam, sob três nomes:

| onde | id | status |
|---|---|---|
| `roadmap-hipoteses.md:400-414` (Pacote 11) | **H-INTRA-01/02/03** | aberta |
| `futuras-otimizacoes-formato.md:421-426` | **O-FMT-17** | alvo 0.8 |
| `2026-06/rle-familia-estudo.md:13-15,36` | **"C"** da família RLE | **ADIADO** |

O caso que motivou foi o seu, e é o mesmo tipo de coisa: `111.111.111-11` tem `111.` três
vezes e o pipeline **não fatora**. E o adiamento também foi seu:
*"depois revisamos o RLE na célula"* (`diario/2026-06-20.md:15`).

**Nunca houve lab** — `find experiments -iname "*intra*"` dá zero. O que existia era uma
caracterização de 2026-06-16 (o `111.111.111-11` **incha de 14 para 18 chars** por causa do
escape de dígito). **Nenhum ganho de intra-valor jamais foi medido. Este estudo é a primeira
medição.**

Há uma **divergência viva de triagem**: `ROADMAP.md:90` ainda diz "alvo 0.8", enquanto
`v08-plano-etapas.md:33`, `tickets/T-SPEC-DEEPDIVE-08.md:71-73` e os dois READMEs dizem
`.9`/pré-1.0. Fica registrada, não resolvida aqui.

## 1.2 O núcleo não captura run intra-valor — zero, e isso é estrutural

Medido com o encode real, e a razão está no código:

- O OBAT compara **só extremidades**: `core/online.py:58-71` (`lcp_len` ancorado no início,
  `lcs_len` no fim). **Não existe offset interno em lugar nenhum do arquivo.**
- A linha onde o run é deixado na mesa — `core/online.py:234-236`: `meio = s[bp_len: ls-bs_len]`
  vai **verbatim** para o wire. Um run é infixo por definição quando tem borda dos dois lados.
- O HCC também não vê caractere: `syntax.py:368-404` opera sobre **ids de átomo**.
- Os únicos RLE do core são de **linha** (`*N|`, `*N+delta|`).

**A curva, medida** (`"a" + "0"×n + "b"`, encode real, RT ok em todos):

| n | 1 valor | 20 idênticos | 20 distintos |
|---:|---:|---:|---:|
| 4 | 15 | 19 | 149 |
| 32 | 43 | 47 | 709 |
| 128 | 139 | 143 | 2629 |

Ajuste **exato, sem resíduo**: 1 valor → `bytes = n + 11`; 20 distintos → `bytes = 20n + 69`.
Ou seja **1,000 byte por caractere repetido, por linha. Zero amortização.** A única
amortização observada vem do RLE de *linha* (valor inteiro repetido), não do run.

E o OBAT **não dedupa o run entre valores distintos** quando ele é infixo:
`["x"+"0"*32+"y", "p"+"0"*32+"q"]` → 79 B, duas cópias literais. Só captura se o run **encostar
na borda** compartilhada.

## 1.3 Onde isso pagaria — e a contra-prova que mede o custo

Varredura do corpus (8 DBs, 186 colunas): **11 colunas** têm valor com run ≥6. E elas se
partem em **duas famílias com destinos opostos**:

| família | exemplo | o que acontece |
|---|---|---|
| **padding de ID** (99% dos casos) | `Clerk#000000004` | o run é **prefixo compartilhado** — OBAT+HCC já comem inteiro |
| **cauda de float** (1 coluna) | `wine.alcohol` = `10.0333333333333` | run no meio/fim, sem afixo comum — sobrevive verbatim |

**A contra-prova, medida**: colapsar os runs de `tpch-sf001/orders.o_clerk` antes do encode dá
**77.266 B contra 75.522 B — 1.744 B PIOR (−2,31%)**. Os zeros ali são *load-bearing*:
sustentam o prefixo compartilhado `Clerk#!00000*0*` e a progressão do seq-RLE. **Um RLE
intra-valor aplicado cegamente custa bytes nessa família**, que é 99% dos casos do corpus.

O teto onde ele pagaria, medido por mim na coluna inteira:

| escopo | hoje | teto (run vira 3-5 chars) | delta |
|---|---|---|---|
| `wine.alcohol` completa (6497) | 8676 B | 8462 B | **−2,47%** |
| só os 40 valores sujos | 483 B | 265 B | **−45,1%** |
| cauda sintética de 100 chars | 318 B | 24 B | −92,5% |

**A forma é sempre a mesma**: forte onde se aplica, e quase nada se aplica. Só **0,62%** dos
valores da única coluna candidata têm run, e só **476 de 23.917 chars** estão dentro de runs.
No corpus inteiro a sobra é **0,0031%**.

## 1.4 As duas grafias propostas — análise crítica

### Proposta 1 (inline, `0.3(14x0)4`): **local, mas com dois bloqueios concretos**

Você disse achar difícil embutir semântica. Os bloqueios são mais específicos que isso:

1. **O `*` já está tomado, e para exatamente esta posição.** `syntax.py:607-617` (comentário
   marcado *byte-load-bearing*) declara `lit → lit` = `*`, "senão os 2 literais colam"; e
   `lit(dig) → refs` = `*` também. `0.3*14*0*4` colide de frente com o parser
   (`syntax.py:810`), que trata `*` como separador de largura zero.
2. **O contador é dígito, e dígito escapa.** É o próprio H-INTRA-02, e a caracterização de
   junho já mediu o efeito: `111.111.111-11` → 18 chars. O escape come o ganho.

O desbloqueio existe e está registrado: **H-REF-03** — alfabeto de referência livre de
conflito, achado por **complemento** (pré-pass varre o dado, acha chars ausentes, usa-os). É o
mesmo princípio que a `polaridade._elege` já usa em produção. Numa coluna numérica o alfabeto
é dígitos + `.` + `-` + `e`, então sobram ~80 chars.

**Veredito**: não é "semântica difícil" — é **um caractere e um escape**. Ambos com solução já
desenhada no repo. Estruturalmente é o desenho **local**: não toca contagem, ordem, streaming
nem decoder estrutural.

### Proposta 2 (linha fantasma): **já existe na gramática, e é uma lacuna de fail-loud**

Aqui está o achado que muda a conversa. **O `*0|` já produz exatamente o que você descreveu**,
e eu verifiquei à mão, com a árvore limpa:

```
decode('#TCF.8\n*0|abc\ndef\n^1\n')  ->  ['def', 'abc']
decode('#TCF.8\n*0|abc\n')           ->  []          (1 linha no corpo, 0 elementos)
decode('#TCF.8\n*-1|abc\ndef\n')     ->  ['def']     (count negativo idem)
```

`abc` é **declarado e nunca emitido**, e depois referenciado por `^1`. O mecanismo:
`syntax.py:968` declara **incondicionalmente**, e só `syntax.py:974` escala a emissão por
`count`; **não há guarda `count >= 1`** (`syntax.py:926-935`). E popula as *duas* tabelas — nós
e fragmentos OBAT.

**O encoder canônico nunca emite isso** (verifiquei em 7 formas de entrada). É **wire
aceito-em-silêncio** — a mesma classe dos 4 bugs já corrigidos no `dominio_bn.py`.

E aqui está a inconsistência que vale mais que a feature: **no bN o projeto já decidiu, e
decidiu CONTRA.** `dominio_bn.py:288-292`:

> `if maior + 1 != len(dom): raise ValueError(… "só N são referenciados — corpo não-canônico
> (o encoder nunca emite slot sobrando)")`

Slot de dicionário não referenciado é **erro fail-loud** no bN e **silêncio** no corpo do core.
Independentemente de queremos ou não a feature, isso é um ticket.

**O que a linha fantasma NÃO quebra** (verificado):

- **A implicitude single-col (H-IMPLICIT-SINGLECOL-01) sobrevive.** "count = nº de linhas" já
  era falso antes desta ideia — o `*N|` desacoplou as duas grandezas. O que a implicitude
  exige é mais fraco: *a contagem é função total das linhas, calculável sem informação
  externa* — e `*0|` preserva isso. O que ela quebra é uma invariante **mais forte e não
  escrita**: *toda linha contribui ≥1 elemento*.
- **Body-order dos virtual refs**: ortogonal. A restrição é sobre *ordem de resolução*
  (`syntax.py:419-460`, precondição load-bearing em `:708-714`), e declaração-antes-do-uso a
  respeita trivialmente.
- **Streaming**: é a *mesma forma* do domínio-primeiro, que o lab de 2026-07-27 mediu como
  **17× melhor em prefixo** (`cnpj-uf`: 100 B contra 1764 B para emitir o 1º valor) por 1 byte
  de wire. Ponto **a favor**.
- Injetado em wire `.8H` nas duas posições, o fantasma é **transparente** — inclusive na coluna
  que define o total e sob o cross-check de exaustão. Custo medido: **4 B**; benefício: zero.

## 1.5 Simples ou arriscada? — o veredito

**Nenhuma das duas é arriscada da forma que você temia, e nenhuma paga agora.**

- A **inline** é local; o obstáculo é escolher caractere (H-REF-03) e o escape, não semântica.
- A **fantasma** não quebra os invariantes que eu esperava que quebrasse — e o motivo é
  desconfortável: ela já existe, sem guarda. Reusar de propósito exigiria **decidir contra a
  regra que o bN já aplica**, e a versão honesta é primeiro **fechar a lacuna**, depois decidir
  se abre a porta com contrato.
- **O que reprova as duas agora é o dado**, não a arquitetura: 0,0031% de sobra no corpus, e
  **−2,31% (custo) na família que domina 99% dos casos**.

E um ponto que nenhuma das duas resolve: **a grafia fracional já ataca exatamente os mesmos 40
valores**. Os sujos de `wine.alcohol` são `n/30` — divisões por 3 exportadas com `%.15g`. O run
é o **sintoma**; a fração é a **causa**. Dois mecanismos disputando o mesmo nicho, e um deles já
está medido e é semanticamente mais fundo.

---

# PARTE 2 — Perda orientada a estatística de erro

Sua pergunta *"1% numa soma ou numa multiplicação?"* tem resposta formal, e a medição em dado
real é mais dura que a teoria.

## 2.1 A mesma perda, por cinco lentes (medido em `online-retail`, 3000 linhas)

Arredondando `UnitPrice` a **1 casa**:

| lente | ingênuo | maior-resto |
|---|---|---|
| erro máximo **por valor** | **28,57%** | 28,57% |
| erro na **SOMA** | 0,083% | **0,00008%** |
| erro na **MÉDIA** | 0,083% | 0,00008% |
| erro na **RECEITA** (Σ preço×qtd) | 0,54% | 0,05% |
| erro máx na receita **por linha** | **28,57%** | 28,57% |

Duas leituras não-óbvias:

1. **O erro relativo passa intacto pelo multiplicador.** 28,57% no preço vira 28,57% na receita
   daquela linha. O produto **não dilui**.
2. **A soma dilui em três ordens de grandeza** — os erros têm sinal e se cancelam. E o
   maior-resto leva a soma a exato, mil vezes melhor que o ingênuo.

**E o achado que contraria a intuição**: a `d=0`, o maior-resto fica **pior na receita** que o
ingênuo (0,66% contra 0,036%). Preservar a soma **não** preserva o produto — o método
redistribui o resíduo sem saber o multiplicador, e pode empilhá-lo onde a quantidade é grande.
**Preservar um agregado pode degradar outro.**

## 2.2 A lente que quebra: diferença de próximos

`margem = venda − custo`, com os dois arredondados:

| d | erro máx nos **operandos** | erro máx na **margem** | margens que trocaram de **SINAL** |
|---|---|---|---|
| 2 | 0,000% | 100,0% | 1 / 500 |
| 1 | 16,7% | **506,1%** | **162 / 500** |

**Um terço das margens trocou de sinal** — lucro virou prejuízo. E a literatura explica por quê
de um jeito que importa para o formato: pelo **lema de Sterbenz**, a subtração em si é
**exata**; o erro veio inteiro dos *inputs já arredondados*. O fator de amplificação é
`|x| / |x−y|`, ilimitado.

**Consequência direta para o TCF**: decidir *"gravar a diferença ou deduzi-la do par"* deixa de
ser questão de bytes e vira **cláusula do contrato de erro**. Se a derivada é deduzida, a
tolerância tem de ser declarada **na derivada** e propagada para trás, apertando os pais. Isso
toca [[materializacao-minimal]] e o DERIVED-DROP (H-LOSS-02) diretamente.

## 2.3 As justificativas por área (literatura, com fonte)

| área | métrica canônica | o que a norma exige EXATO | tolerância típica |
|---|---|---|---|
| **propagação** | absoluto (soma) · relativo (produto) | nada — é lei de composição | GUM Eq. (12): erros relativos compõem ponderados pelo expoente |
| **financeiro** | **grade** de casas (ISO 4217 minor unit) | o **total**, não a linha | apresentar 2 casas, **calcular 4-6** (HMRC VATREC12020) |
| **metrológico** | incerteza `u`, expandida `U = k·u_c` | nada — o nº de dígitos é **derivado da incerteza** | `u` com 2 algarismos significativos; `k=2` ≈ 95% (GUM 7.2.6) |
| **científico** | `ABS`, `PW_REL`, `PSNR` | nada, exceto no modo *reversible* | SZ3 default `1e-3`; SDRBench 1e-2 a 1e-4 |
| **estatístico** | base de arredondamento + aditividade | **marginais e total geral**, por construção | erro por célula < base (zero-restricted) |

Três coisas que valem citar literalmente:

- **O princípio jurídico do viés.** O HMRC permite arredondar para baixo a *invoice traders*
  porque *"it will normally impact on both the output tax of the supplier and the input tax of
  the customer"* — **o erro cancela na contraparte** — e **nega** a retalhistas, porque sem
  contraparte que deduza o viés vira perda de receita. Generalizando: *o arredondamento é
  aceitável quando é não-viesado ou quando o viés cancela; inaceitável quando se acumula numa
  direção.* É por isso que half-even existe.
- **ISO 4217 fixa os dígitos e não especifica modo nenhum.** Modo é outra camada.
- **A GUM inverte a pergunta**: não é "quantas casas posso cortar", é "a incerteza determina
  quantos dígitos **existem**". Gravar além da resolução do instrumento é ruído, não informação.
- **Dois níveis, achados independentemente em duas áreas**: HMRC manda calcular a 5-6 casas e
  apresentar a 2; a GUM 7.2.6 manda reter dígitos extra *"to avoid round-off errors in
  subsequent calculations"*. **Apresentação ≠ armazenamento** — um contrato honesto tem dois
  slots.

## 2.4 O vocabulário mínimo — 4 eixos + 1 qualificador

Testados por redução mútua; um dos cinco propostos **colapsa**:

| eixo | o que declara | por que é irredutível |
|---|---|---|
| **`quantum`** | grade absoluta (`x̂ ∈ {k·q}`) | **estritamente mais forte que `abs`**: o financeiro exige que o valor seja *expressável* em centavos, não meramente perto de um |
| **`abs`** | `\|x̂−x\| ≤ ε` | é o invariante que **compõe sob soma** |
| **`rel`** | `\|x̂−x\|/\|x\| ≤ ε` | é o invariante que **compõe sob produto** — as duas operações que você citou pedem os dois eixos |
| **`agg-exact`** | `Σ x̂ = round(Σ x)` num eixo declarado | restrição de **conjunto**, não de ponto: nenhuma tolerância pontual a implica. É o único que obriga o encoder a resolver **alocação** |
| **`mode`** *(qualificador)* | `half-even` / `half-up` / `down` / `stochastic` | duas normas com o **mesmo `quantum`** divergem no modo, e o modo decide o **viés** — é a distinção do HMRC |

**`significativos` colapsa em `rel`** (`s` sig ≈ `ε_r ≈ 5·10^-s`). Fica como açúcar de
declaração, não como eixo.

Isso substitui o `DECIMALS + AGG-soma` que a `loss-taxonomia.md` §4 propunha como início
mínimo — que estava certo na direção e curto em dois eixos (`rel` e `mode`).

---

## O que este estudo orienta

1. **RLE intra-valor**: mecanismo caracterizado pela primeira vez, com teto medido
   (0,0031% do corpus) e **contra-prova de custo** (−2,31% onde domina). **Fica adiado, agora
   com número** — e o pré-requisito é H-REF-03, não a grafia.
2. **A lacuna do `*0|` é um ticket próprio**, independente da feature: o mesmo padrão é
   fail-loud no bN e silencioso no core.
3. **O loss ganha um eixo novo**: a perda deixa de ser "quantas casas" e passa a ser
   *o que se promete, e sob qual operação*. E a medição mostrou que **preservar um agregado
   pode degradar outro** — o que nenhum dos vocabulários da literatura cobre.

## Conexões

`H-INTRA-01/02/03` · `O-FMT-17` · `H-REF-03` · [`rle-familia-estudo.md`](../2026-06/rle-familia-estudo.md) ·
[`loss-taxonomia.md`](../2026-06/loss-taxonomia.md) · Pacote 10 (`H-LOSS-00/01/02/03`) ·
[`2026-08-14-1739`](2026-08-14-1739-loss-e-lossless-alterado-pesquisa.md) ·
lab [`2026-08-14-1745`](../../2026-08/2026-08-14/2026-08-14-1745-grafia-fracional-e-escala-com-excecoes/)

**Fontes externas**: [GUM JCGM 100:2008](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e) ·
[HMRC VATREC12020](https://www.gov.uk/hmrc-internal-manuals/vat-trader-records/vatrec12020) ·
[ECJ C-302/07 Wetherspoon](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62007CJ0302) ·
[ISO 4217](https://www.iso.org/iso-4217-currency-codes.html) · [SZ3](https://github.com/szcompressor/SZ3) ·
[zfp modes](https://zfp.readthedocs.io/en/release1.0.1/modes.html) ·
[Cox 1987, controlled rounding](https://www.tandfonline.com/doi/abs/10.1080/01621459.1987.10478456)
