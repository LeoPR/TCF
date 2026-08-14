# RLE intra-valor — dá para fazer barato?

**2026-08-14** · direção do owner, reabrindo a própria ideia de 2026-06-16:

> *"tinha o caso desses itens repetidos no meio do texto… `0.30000000000000004` poderia ser
> feito como `0.3(14x0)4`… ou ainda pra aproveitar o fluxo: `14x0` / `\0.3 <ref-01> 4`… um
> 'RLE fantasma' que descomprime só pra preencher dicionário, não coloca no conteúdo de fato.
> Veja se a ideia do RLE é simples ou arriscada."*

**Uma pergunta**: o núcleo já aproveita repetição de caractere **dentro** de um valor? Se não,
dá para fazer **barato**?

**Tipo**: [probatório] estudo + análise crítica. Nenhum weld, `src/tcf` intocado.
**Lab (a evidência)**: [`2026-08-14-2010-rle-intra-valor-medida`](../../2026-08/2026-08-14/2026-08-14-2010-rle-intra-valor-medida/).

> Esta nota nasceu misturada com o estudo de propagação de erro. O owner pediu a separação
> (*"misturamos coisas… faça um por vez em labs diferentes com análises diferentes"*), e ela
> está certa: são perguntas distintas, com métodos e vereditos distintos. A outra metade virou
> [`2026-08-14-2010-perda-propagacao-de-erro.md`](2026-08-14-2010-perda-propagacao-de-erro.md).

---

## 1. Já discutimos — e a ideia é sua, de 2026-06-16

Registrada em três lugares que se cross-referenciam, sob três nomes:

| onde | id | status |
|---|---|---|
| `roadmap-hipoteses.md:400-414` (Pacote 11) | **H-INTRA-01/02/03** | aberta |
| `futuras-otimizacoes-formato.md:421-426` | **O-FMT-17** | alvo 0.8 |
| `2026-06/rle-familia-estudo.md:13-15,36` | **"C"** da família RLE | **ADIADO** |

O caso que motivou foi o seu: `111.111.111-11` tem `111.` três vezes e o pipeline **não
fatora**. E o adiamento também foi seu — *"depois revisamos o RLE na célula"*
(`diario/2026-06-20.md:15`).

**Nunca houve lab** (`find experiments -iname "*intra*"` dá zero). A única coisa medida era o
inchaço por escape: `111.111.111-11` de **14 para 18 chars**. Nenhum ganho jamais foi medido.

Há uma **divergência viva de triagem**, registrada e não resolvida: `ROADMAP.md:90` diz "alvo
0.8"; `v08-plano-etapas.md:33`, `tickets/T-SPEC-DEEPDIVE-08.md:71-73` e os dois READMEs dizem
`.9`/pré-1.0.

## 2. O núcleo captura zero — e é estrutural, não descuido

- O OBAT compara **só extremidades**: `core/online.py:58-71` (`lcp_len` do início, `lcs_len` do
  fim). **Não existe offset interno em lugar nenhum do arquivo.**
- A linha onde o run é deixado na mesa — `core/online.py:234-236`: `meio = s[bp_len:ls-bs_len]`
  vai **verbatim** para o wire. Um run com borda dos dois lados é infixo por definição.
- O HCC não vê caractere: `syntax.py:368-404` opera sobre **ids de átomo**.
- Os únicos RLE do core são de **linha** (`*N|`, `*N+delta|`).

**Medido no lab** — par de contra-prova com mesmo comprimento e alfabeto:

| caso | corpo | bytes |
|---|---|---|
| `0.30000000000000004` | `\0.\30000000000000004` | **29** |
| `0.31415926535894704` | `\0.\31415926535894704` | **29** |

**Diferença zero.** E a curva tem coeficiente **exato**: `d(bytes)/d(N)` = **1,0** (um valor) e
**20,0** (vinte valores distintos), sem resíduo, até N=256. **Zero amortização.**

## 3. Onde pagaria — e onde custa

Duas famílias, destinos opostos:

| família | exemplo | o que acontece |
|---|---|---|
| **padding de ID** (99% das colunas com run) | `Clerk#000000004` | o run é prefixo compartilhado — OBAT+HCC já comem |
| **cauda de float** (1 coluna no corpus) | `10.0333333333333` | run no meio, sem afixo comum — sobrevive verbatim |

Teto medido (run vira 5 chars de **1 byte**, escolhido por complemento — a ideia da `H-REF-03`;
é limite **superior**, nenhum mecanismo real é de graça):

| coluna | hoje | teto | delta |
|---|---:|---:|---:|
| `wine.alcohol` (6497) | 8676 B | 8512 B | **−1,89%** |
| `tpch.o_clerk` (15000) | 75.522 B | 74.241 B | −1,70% |
| `tpch.c_name` (1500) | **87 B** | 93 B | **+6,90% — CUSTA** |

**A contra-prova é o `c_name`**, e o mecanismo dela é o mais instrutivo do estudo: 1500 valores
(`Customer#000000001`…) formam uma **progressão aritmética** que o seq-RLE esmaga para **87
bytes**, e colapsar os runs **destrói a progressão**. O run ali não é redundância sobrando — é o
que **sustenta outro mecanismo**.

> **Número não medido pelo lab, fonte atribuída**: a sobra no corpus **inteiro** (0,0031%, 11 de
> 186 colunas com run ≥6) vem da varredura do levantamento `wf_7824248d-02d`, não do `run.py`.
> Como a contra-prova do `o_clerk` desse mesmo levantamento **não reproduziu** (ele reportou
> −2,31% de custo; o lab mediu 1,70% de ganho), trate como indicativo até ter lab próprio.

## 4. As duas grafias — análise crítica

### Inline (`0.3(14x0)4`) — **local**, com dois bloqueios concretos

Você achou que o difícil era embutir semântica. É mais específico:

1. **O `*` já está tomado, e para exatamente esta posição.** `syntax.py:607-617` (comentário
   marcado *byte-load-bearing*) declara `lit → lit` = `*` — "senão os 2 literais colam" — e
   `lit(dig) → refs` = `*` também. `0.3*14*0*4` colide de frente com o parser (`syntax.py:810`),
   que trata `*` como separador de largura zero.
2. **O contador é dígito, e dígito escapa.** É o próprio `H-INTRA-02`, com o efeito já medido em
   junho.

O desbloqueio existe e está registrado: **`H-REF-03`** — alfabeto de referência achado por
**complemento** do dado. É o mesmo princípio que a `polaridade._elege` já usa em produção; numa
coluna numérica sobram ~80 chars.

**Veredito**: não é semântica difícil — é **um caractere e um escape**, ambos com solução já
desenhada. Estruturalmente é o desenho **local**: não toca contagem, ordem, streaming nem
decoder estrutural.

### Linha fantasma — **já existe na gramática, e é uma lacuna de fail-loud**

O `*0|` já produz exatamente o que você descreveu. Verificado à mão, árvore limpa:

```
decode('#TCF.8\n*0|abc\ndef\n^1\n')  ->  ['def', 'abc']
decode('#TCF.8\n*0|abc\n')           ->  []
decode('#TCF.8\n*-1|abc\ndef\n')     ->  ['def']
```

`syntax.py:968` declara **incondicionalmente**; só `syntax.py:974` escala a emissão por `count`.
**Não há guarda `count >= 1`.** O encoder canônico nunca emite (9 formas testadas).

**A inconsistência vale mais que a feature**: `dominio_bn.py:288-292` levanta `ValueError` se um
slot de domínio não é referenciado — *"o encoder nunca emite slot sobrando"*. Fail-loud no bN,
silêncio no core. Ticket: **`T-RLE-COUNT-ZERO`**.

**O que ela NÃO quebra** (verificado):

- **A implicitude single-col sobrevive.** "count = nº de linhas" já era falso — o `*N|`
  desacoplou as duas grandezas antes desta ideia. O que a implicitude exige é mais fraco: *a
  contagem é função total das linhas*. O que quebra é uma invariante **mais forte e não
  escrita**: *toda linha contribui ≥1 elemento*.
- **Body-order dos virtual refs**: ortogonal — a restrição é sobre ordem de *resolução*
  (`syntax.py:419-460`, precondição em `:708-714`), e declaração-antes-do-uso a respeita.
- **Streaming**: é a mesma forma do domínio-primeiro, medido **17× melhor em prefixo**. Ponto
  **a favor**.
- Injetado em wire `.8H` nas duas posições, é **transparente**. Custo: 4 B; benefício: zero.

## 5. Simples ou arriscada? — o veredito

**Nenhuma das duas é arriscada como você temia. E nenhuma paga agora.**

- A **inline** é local; o obstáculo é caractere e escape, não semântica.
- A **fantasma** não quebra os invariantes que eu esperava — e o motivo é desconfortável: ela já
  existe, sem guarda. Reusá-la de propósito exigiria **decidir contra a regra que o bN já
  aplica**. A ordem honesta é fechar a lacuna primeiro, depois decidir se abre a porta com
  contrato.
- **O que reprova as duas é o dado**: ganho de 1,89% na melhor coluna, e **custo** na família que
  domina o corpus. Um mecanismo cego perde; com FLOOR não perderia, mas o ganho fica confinado
  ao nicho.

E um ponto que nenhuma resolve: **a grafia fracional já ataca os mesmos 40 valores**. Os sujos
de `wine.alcohol` são `n/30` — o run é o **sintoma**, a divisão é a **causa**.

## O que orienta

1. Continua **adiado — agora com número**. O pré-requisito é `H-REF-03`, não a grafia.
2. **`T-RLE-COUNT-ZERO` é ticket próprio**, independente da feature.

## Conexões

`H-INTRA-01/02/03` · `O-FMT-17` · `H-REF-03` · **`T-RLE-COUNT-ZERO`** ·
[`rle-familia-estudo.md`](../2026-06/rle-familia-estudo.md) ·
irmã: [`2026-08-14-2010-perda-propagacao-de-erro.md`](2026-08-14-2010-perda-propagacao-de-erro.md)
