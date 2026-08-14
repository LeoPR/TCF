# Perda orientada a erro — o que a tolerância significa, por operação e por área

**2026-08-14** · direção do owner:

> *"quanto ao loss, ainda precisa de estudo, talvez fazer ficar orientado à estatística de
> perdas e erros ajudaria. Por exemplo, se a perda significa algo como 1% numa soma ou
> multiplicação? não só pelo valor em si, mas se eu passar algo que seja financeiramente, ou
> fisicamente coerente arredondar dentro de alguma margem dentro da realidade, com
> justificativas em várias áreas."*

**Uma pergunta**: a mesma perda, medida por lentes diferentes, dá o mesmo número?

**Tipo**: [probatório] medição + literatura. Nenhum weld, `src/tcf` intocado.
**Lab (a evidência)**: [`2026-08-14-2010-perda-propagacao-de-erro`](../../2026-08/2026-08-14/2026-08-14-2010-perda-propagacao-de-erro/).

> Esta nota nasceu misturada com o estudo de RLE intra-valor. O owner pediu a separação
> (*"misturamos coisas… faça um por vez em labs diferentes com análises diferentes"*). A outra
> metade é [`2026-08-14-2010-rle-intra-valor.md`](2026-08-14-2010-rle-intra-valor.md).

---

## 1. A resposta curta: não, e a diferença é de ordens de grandeza

Arredondando `UnitPrice` a **1 casa**, 3000 linhas reais de `online-retail`:

| lente | ingênuo | maior resto |
|---|---:|---:|
| erro máximo **por valor** | **66,67%** | 66,67% |
| erro na **soma** | 0,18536% | **0,00029%** |
| erro na **média** | 0,18536% | 0,00029% |
| erro na **receita** (Σ preço×qtd) | 0,25024% | 0,16606% |
| erro máx na receita **por linha** | **66,67%** | 66,67% |
| **bytes** | 4090 | **4156** |

**A pergunta "posso arredondar 1%?" é malformada** — falta dizer *1% de quê*.

Quatro leituras, três delas não-óbvias:

1. **A soma dilui em três ordens de grandeza.** Os erros têm sinal e se cancelam; e o maior
   resto leva a soma a exato, ~640× melhor que o ingênuo.
2. **O produto NÃO dilui.** O erro relativo passa **intacto** pelo multiplicador: 66,67% no
   preço é 66,67% na receita daquela linha.
3. **Preservar a soma custa bytes** (4156 contra 4090): o maior resto cria valores distintos que
   o ingênuo colapsaria. A soma exata não é de graça.
4. **Preservar um agregado pode degradar outro.** O maior resto é ~640× melhor na soma e só
   ~1,5× melhor na receita — ele redistribui o resíduo **sem saber o multiplicador**. **Nenhum
   vocabulário da literatura cobre esse conflito.**

## 2. A lente que quebra: diferença de próximos

`margem = venda − custo`, ambos arredondados:

| d | erro máx nos **operandos** | erro máx na **margem** | trocaram de **sinal** |
|---:|---:|---:|---:|
| 3 | 0,000% | 7,4% | 0 / 500 |
| 2 | 0,000% | 85,2% | 0 / 500 |
| 1 | 11,111% | **825,9%** | **203 / 500** |

**Quarenta por cento das margens trocaram de sinal** — lucro virou prejuízo. E note `d=2`: erro
**zero** nos operandos e ainda **85%** na margem.

Pelo **lema de Sterbenz** a subtração em si é **exata**; o erro veio inteiro dos *inputs já
arredondados*. A amplificação é `|x| / |x−y|`, ilimitada.

**Consequência direta para o formato**: decidir *"gravar a diferença ou deduzi-la do par"* deixa
de ser questão de bytes e vira **cláusula do contrato de erro**. Se a derivada é deduzida, a
tolerância tem de ser declarada **nela** e propagada para trás, apertando os pais. Toca
[[materializacao-minimal]] e o DERIVED-DROP (`H-LOSS-02`).

## 3. As justificativas por área

| área | métrica canônica | o que a norma exige **exato** | tolerância típica |
|---|---|---|---|
| **propagação** | absoluto (soma) · relativo (produto) | nada — é lei de composição | GUM Eq. (12) |
| **financeiro** | **grade** de casas (ISO 4217 minor unit) | o **total**, não a linha | apresentar 2 casas, **calcular 4–6** |
| **metrológico** | incerteza `u`, expandida `U = k·u_c` | nada — os dígitos são **derivados da incerteza** | `u` com 2 sig; `k=2` ≈ 95% |
| **científico** | `ABS`, `PW_REL`, `PSNR` | nada, exceto o modo *reversible* | SZ3 default `1e-3` |
| **estatístico** | base + aditividade | **marginais e total**, por construção | erro/célula < base |

Quatro pontos que valem literalmente:

- **O princípio jurídico do viés.** O HMRC permite arredondar para baixo a *invoice traders*
  porque *"it will normally impact on both the output tax of the supplier and the input tax of
  the customer"* — **o erro cancela na contraparte** — e **nega** a retalhistas, porque sem
  contraparte o viés vira perda de receita. Generalizando: *arredondamento é aceitável quando é
  não-viesado ou quando o viés cancela; inaceitável quando se acumula numa direção.*
- **ISO 4217 fixa os dígitos e não especifica modo nenhum.** Modo é outra camada.
- **A GUM inverte a pergunta**: não é "quantas casas posso cortar", é "a incerteza determina
  quantos dígitos **existem**". Gravar além da resolução é ruído, não informação.
- **Apresentação ≠ armazenamento**, achado independentemente em duas áreas: o HMRC manda
  calcular a 5–6 casas e apresentar a 2; a GUM 7.2.6 manda reter dígitos extra *"to avoid
  round-off errors in subsequent calculations"*.

## 4. O vocabulário mínimo — 4 eixos + 1 qualificador

Testados por redução mútua; um dos cinco propostos **colapsa**:

| eixo | declara | por que é irredutível |
|---|---|---|
| **`quantum`** | grade absoluta (`x̂ ∈ {k·q}`) | **estritamente mais forte que `abs`**: a norma monetária exige o valor *expressável* em centavos, não meramente perto de um |
| **`abs`** | `\|x̂−x\| ≤ ε` | o invariante que **compõe sob soma** |
| **`rel`** | `\|x̂−x\|/\|x\| ≤ ε` | o invariante que **compõe sob produto** — as duas operações citadas pedem os **dois** eixos |
| **`agg-exact`** | `Σ x̂ = round(Σ x)` num eixo declarado | restrição de **conjunto**: nenhuma tolerância pontual a implica; obriga **alocação**, não arredondamento local |
| **`mode`** *(qualificador)* | `half-even` · `half-up` · `down` · `stochastic` | duas normas com o **mesmo `quantum`** divergem no modo, e o modo decide o **viés** — é a distinção do HMRC |

**`significativos` colapsa em `rel`** (`s` sig ≈ `ε_r ≈ 5·10⁻ˢ`). Fica como açúcar de declaração.

Isso **substitui** o "começar minimal: DECIMALS + AGG-soma" da `loss-taxonomia.md` §4 — certo na
direção, curto em dois eixos (`rel` e `mode`).

## O que orienta

1. A perda deixa de ser "quantas casas" e passa a ser **o que se promete, e sob qual operação**.
2. O vocabulário acima é o conteúdo do `H-LOSS-00` (meta-camada de contrato), que é
   pré-requisito de qualquer weld lossy.
3. **Conflito entre agregados** é achado novo, sem cobertura na literatura: preservar a soma
   pode piorar o produto.

**GATE inalterado**: o formato é lossless-puro por decisão do owner (2026-06-15). Nada aqui é
proposta de weld.

## Conexões

`H-LOSS-00` (vocabulário) · `H-LOSS-01` (maior resto) · `H-LOSS-02` (DERIVED-DROP) ·
`H-LOSS-03` (o PoC de junho) · [`loss-taxonomia.md`](../2026-06/loss-taxonomia.md) ·
[`2026-08-14-1739`](2026-08-14-1739-loss-e-lossless-alterado-pesquisa.md) ·
irmã: [`2026-08-14-2010-rle-intra-valor.md`](2026-08-14-2010-rle-intra-valor.md)

**Fontes**: [GUM JCGM 100:2008](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e) ·
[HMRC VATREC12020](https://www.gov.uk/hmrc-internal-manuals/vat-trader-records/vatrec12020) ·
[ECJ C-302/07 Wetherspoon](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62007CJ0302) ·
[ISO 4217](https://www.iso.org/iso-4217-currency-codes.html) · [SZ3](https://github.com/szcompressor/SZ3) ·
[zfp modes](https://zfp.readthedocs.io/en/release1.0.1/modes.html) ·
[Cox 1987](https://www.tandfonline.com/doi/abs/10.1080/01621459.1987.10478456)
