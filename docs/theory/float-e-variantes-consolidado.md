# Float e suas variantes: consolidado

> **Escopo**: o tipo `float` no `#TCF.8`, o que já fecha, e as variantes que mexem na **grafia**
> (lossless) ou no **valor** (loss). Consolida o ciclo de 2026-08-14.
>
> **Estado do formato**: lossless-puro. Nada aqui é proposta de weld; a decisão de escopo do
> owner (2026-06-15) mantém a perda fora do `.8`, e qualquer weld lossy exige gate real-world
> N≥5 mais decisão explícita.

---

## 1. O float está fechado, e o que isso significa

Sob o critério do owner (*"um tipo não fecha porque compensa; fecha porque foi verificado"*):
12 bordas + 5 colunas reais, 5 eixos, 0 falhas.

**Conforme em tudo**: mesmo dispatch (uma linha, tag `n`), mesmo `min()` de candidatos (RLE,
seq-RLE, polaridade, e o **mesmo `bN` de domínio** que serve bool/int/string), mesma API
(`nature=`, `min_len=`), mesma gramática de wire, mesmo RT.

**Seis peculiaridades declaradas**, duas delas load-bearing para tudo que vem depois:

1. **É metade de uma tag-união.** `n` é `int|float`, o `number` do JSON, e o tipo concreto vem
   da **grafia**, por elemento. Nenhum outro tipo compartilha tag. *Consequência*: qualquer
   transformação que altere a grafia numérica pode apagar a distinção int/float.
2. **`-0.0` é distinto de `0.0` e `==` não detecta.** Só `math.copysign` prova. Qualquer teste
   de round-trip de float que use `==` é cego para isso.
3. NaN e ±Inf são **recusados fail-loud** (fora do JSON, RFC 8259).
4. A precisão suja quebra a **escala**, não o RT.
5. O `IntPadSpec` **não é reaproveitável** (verificado `False` em 5 colunas reais).
6. A grafia canônica é a do Python (`1e-05`, `1e+20`).

---

## 2. Os dois planos de variante, e por que o gate difere

| plano | contrato | o que muda | gate |
|---|---|---|---|
| **grafia** | exato | como o valor é **escrito** no corpo | **nenhum**: é candidato de `min()` como outro qualquer |
| **valor** | exato-no-agregado / dentro-de-tolerância | o **dado** | **gateado** (Pacote 10) |

Confundir os dois é o erro que trava a conversa. `0.333333333333 → 1/3~12` e `0.25 → 25 (k=2)`
**não perdem nada**; `0.30000000000000004 → 0.3` perde.

---

## 3. O que foi medido: plano da GRAFIA

| mecanismo | funciona? | ganho | onde mora |
|---|---|---|---|
| **escala pura** (`float → int × 10^k`) | sim | −8,4% na melhor coluna real | é o candidato de hoje |
| **escala com exceções** (desenho ALP) | sim | −3,8% onde a pura **recusa** | resolve os 2 modos de falha |
| **grafia fracional** (`1/3~12`) | sim, 126/126 | −41% em dízimas distintas | **n=1 no corpus** |
| **RLE intra-valor** | **não existe** no núcleo | teto −1,89%, e **custa** onde o run sustenta outro mecanismo | adiado, com número |

**A escala pura falha de duas maneiras, não de uma**, e a segunda é a insidiosa:

- **recusa**: nenhum `k` serve → a coluna perde o candidato (`wine.alcohol`);
- **pior que nada**: um `k` serve, mas é enorme. Um valor sujo em 20 força `k=12` e a coluna vai
  de **124 para 188 B**. O mecanismo "funciona", devolve candidato válido, e só não é usado
  porque perde.

**A escala com exceções resolve as duas**, e não precisa de mecanismo novo: o núcleo já tem
exceção por-valor soldada, `MARKER_LITERAL = '_'` nas quatro natures, e
[`int_pad.py:73-74`](../../src/tcf/natures/int_pad.py#L73-L74) (`length_wrong`) **é literalmente
o patching do ALP**. Falta a grafia econômica da exceção, não o mecanismo.

**Três disciplinas que a medição impôs** (todas nasceram de defeito meu, pego pelo próprio lab):

1. **Verificar por re-emissão, nunca por tolerância.** `abs(esc − round(esc)) < 1e-9` aceita
   `0.30000000000000004` em `k=1` e devolve `0.3`, um lossless que perde, calado. A disciplina
   correta já estava escrita em `int_pad.py:75-78` (`'007' != '7'`).
2. **Recusar coluna de tipo misto.** Escalar apaga o int/float da tag-união.
3. **Guarda de maioria.** Sem ela, `k=0` "vence" marcando 1716/2000 como exceção, mas em `k=0`
   não há escala; quem decide os bytes ali é outro candidato.

---

## 4. O que foi medido: plano do VALOR

### 4.1 A mesma perda vale coisas diferentes

`retail.UnitPrice`, arredondando a 1 casa:

| lente | ingênuo | maior resto |
|---|---:|---:|
| por valor | **66,67%** | 66,67% |
| **soma** | 0,18536% | **0,00029%** |
| **receita** (Σ preço×qtd) | 0,25024% | 0,16606% |
| bytes | 4090 | **4156** |

E a lente que quebra, `margem = venda − custo`, `d=1`: erro de **11,1%** nos operandos vira
**825,9%** na margem, com **203 de 500** trocando de **sinal**.

**Quatro leituras**, três não-óbvias:

- a **soma dilui** em três ordens de grandeza (os erros têm sinal e se cancelam);
- o **produto não dilui**: o erro relativo passa intacto pelo multiplicador;
- **preservar a soma custa bytes** (4156 > 4090): o maior resto cria valores que o ingênuo
  colapsaria;
- **preservar um agregado pode degradar outro**: o maior resto é ~640× melhor na soma e só
  ~1,5× melhor na receita, porque redistribui sem saber o multiplicador. **Sem cobertura na
  literatura.**

Pelo **lema de Sterbenz**, a subtração em si é *exata*: o erro veio inteiro dos inputs já
arredondados, com amplificação `|x|/|x−y|` ilimitada. **Consequência de formato**: decidir
"gravar a diferença ou deduzi-la do par" deixa de ser byte e vira **cláusula do contrato de
erro**.

### 4.2 O vocabulário: 4 eixos + 1 qualificador

Derivado por redução mútua contra 5 áreas normativas:

| eixo | promete | compõe sob | por que é irredutível |
|---|---|---|---|
| **`quantum`** | `x̂ ∈ {k·q}` | n/a | **mais forte que `abs`**: a norma monetária exige o valor *expressável* em centavos |
| **`abs`** | `\|x̂−x\| ≤ ε` | **soma** | é o invariante aditivo |
| **`rel`** | `\|x̂−x\|/\|x\| ≤ ε` | **produto** | GUM Eq. (12) |
| **`agg`** | `Σ x̂ = Σ x` no eixo declarado | n/a | restrição de **conjunto**; obriga **alocação** |
| **`mode`** | direção do desempate | n/a | duas normas com o mesmo `quantum` divergem no modo |

`significativos` **colapsa** em `rel`. E há dois achados fora dos eixos: **apresentação ≠
armazenamento** (HMRC manda calcular a 5–6 casas e apresentar a 2; GUM 7.2.6 manda reter guard
digits) e **derivada por subtração não é coberta por vocabulário pontual nenhum**.

### 4.3 O parâmetro, prototipado

```python
Tolerancia(quantum=0.01, mode="half-even")   # a forma FINANCEIRA
Tolerancia(rel=0.01)                          # o max_error_pct do H-smart-rounding
Tolerancia(quantum=0.1, agg="soma")           # compõem por AND
```

Três estágios, **derivar → aplicar → verificar**: onde o terceiro é quem manda. 12 pedidos ×
3 colunas, 0 falhas.

**Prior art**: o `H-smart-rounding` (2026-04-10, `status: OPEN`, congelado) desenhou
`EncodeConfig(max_error_pct=...)` com *"precisão derivada de tolerância (inovação)"*, **as 4
tarefas seguem desmarcadas**. Nunca testado até agora.

**O que a medição corrigiu no desenho de 2026-04:**

| o ticket supunha | medido |
|---|---|
| um eixo (`max_error_pct`) basta | **`rel` é inútil em money real**: um item de `0,001` obriga a coluna a 4 casas, e o pedido vira no-op. Para dinheiro o eixo é `quantum`, que é o que a ISO 4217 define |
| erro é um número | a mesma perda vale 0,5% por valor e 0,024% na soma |
| (sem `mode`) | **o `mode` muda a fórmula da derivação, não só o viés**: `down` erra 1 passo inteiro, `half-*` erram meio. Com a fórmula errada, `mode="down"` prometeu 1% e entregou ~1,01%, e **a verificação recusou** |
| (sem `agg`) | é o único eixo que obriga alocação, e o único que 3 das 5 áreas normativas exigem |

Outros números: `wine.density` com `rel=1%` cai **93,0%**; `agg` sozinho economiza **0%**
(realoca, não corta, o valor dele é o contrato); `quantum=0,1 + agg` custa **118 B** e derruba
o erro da soma **37×**; truncar pode **custar** bytes; e pedido apertado demais **degrada para
lossless** (no-op) em vez de quebrar.

### 4.4 `agg="soma"` e streaming: a pergunta do owner, respondida

*"Dependendo da forma que eu peça, tem que ver se ele fica stream compatível."* Está certo, e há
**três formas do mesmo contrato**:

| forma | soma exata | **lidos antes do 1º emitido** | bytes |
|---|---|---:|---:|
| **maior resto** (Hamilton) | sim | **2000** (a coluna inteira) | 3028 |
| **difusão de erro** (1 passe) | sim | **1** | 3090 (+2,0%) |
| **âncora** (à parte) | não *(nas linhas)* | 1 | **2955** |

**`agg="soma"` é stream-compatível, mas só na forma de difusão**, que carrega o resíduo para o
próximo (`carry = x − round(x)`), mantém **um float** de estado, e entrega a soma exata na
escala de `d`. O preço é ~2% em bytes e o dobro do erro por linha.

Duas separações que isso obriga:

- **prefixo do encoder ≠ prefixo do decoder.** Neste lab o prefixo do *decoder* foi **19 B nas
  três formas**, idêntico. Toda a diferença está no produtor.
- **a âncora é outro contrato**, não uma terceira forma do mesmo: as linhas **não somam** ao
  total. É o caso mais forte para o aviso obrigatório. E a variante "âncora em trailer", que
  seria streamável, já está **reprovada** (`T-PULSO-SINGLE-COL`: trailer mata o streaming de
  decode).

**A classificação pelo critério que o repo já aplica**: prefixo de encoder = 100% da fonte é a
mesma assinatura algébrica do `bN` modo `C` e do split embutido, os dois **decodáveis, não
emitidos por default, opt-in**. E o ADR-0002 já refuta "buffer > O(1)" mesmo com ganho. Logo o
maior resto é **variante declarada, nunca default silencioso**: o que faz `agg` precisar de um
segundo eixo:

```python
Tolerancia(agg="soma", agg_forma="exata")      # maior resto — prefixo encoder = n
Tolerancia(agg="soma", agg_forma="streaming")  # difusão     — prefixo encoder = 1, +2,0% B
Tolerancia(agg="soma", agg_forma="ancora")     # à parte     — contrato distinto
```

---

## 5. O aviso obrigatório: a regra que falta

O owner: *"tanto no encode como no decode temos que ter algum tipo de warning ou status, pois
modificar o dado pode causar confusão nas leituras de quem consome."*

**No encode o precedente é farto.** A `SideOutputs` tem 16 campos e **seis** já sinalizam "algo
não ideal": `nature_apply['used']=False`, `multi_info['nature_lost']`, `by_status` (a taxonomia
de recusa por valor), `fallback_cols`, `cadence_info['reason']`, e `body_bytes ≠ emitted_bytes`.

**Mas todos descrevem uma decisão de REPRESENTAÇÃO, nunca alteração de VALOR**, porque hoje
isso não existe: o fallback da nature é `MARKER_LITERAL + v`, lossless por construção. Um campo
de valor ajustado seria **a primeira ocorrência da classe**.

**No decode não há canal de telemetria nenhum.** `decode()` devolve `list`/`dict` e nada mais; o
`decoder.py` não escreve em `SideOutputs`. Existe **um** precedente de sinal fora-de-banda:
`warnings.warn(UserWarning)` em `syntax.py:114` (corpo sem o LF terminador canônico), no caminho
de **todo** decode single-col. É exatamente o molde de "aceita, decodifica, e avisa".

**A propriedade que decide o desenho**: o slot certo é o **`:id` do header**, e não porque é
bonito, porque `_resolve_header_spec` **falha alto em id desconhecido**. Um leitor novo lê e
sabe; **um leitor velho recusa em vez de entregar dado ajustado como se fosse exato**. Essa é a
falha segura, e nenhum campo de telemetria a oferece.

**A regra mínima**, reusando o que existe:

> Toda transformação que não satisfaz `decode(encode(x)) == x` (a) grava telemetria na mesma
> forma de `nature_apply`, indexada por coluna; (b) emite `UserWarning` uma vez por coluna no
> **encode**; (c) emite `UserWarning` no **decode** ao resolver um `:id` marcado como
> não-lossless; e (d) **o `:id` viaja**, sem ele, o dado ajustado é byte-indistinguível do
> exato.

O item (d) é o pré-requisito duro. Hoje o laudo do parâmetro é um objeto Python que morre no
processo de encode.

---

## 6. Revisão crítica: o que faz sentido e o que não

**Faz sentido:**

- **`quantum` + `mode`** para dinheiro. É a forma que a norma usa (ISO 4217 define *minor
  unit*; o modo decide o viés, e é a distinção jurídica do HMRC: arredondar para baixo é
  concedido a *invoice traders* porque **o erro cancela na contraparte**, e negado a retalhistas
  porque sem contraparte o viés vira perda de receita).
- **`agg` composto com `quantum`**: 118 B por 37× menos erro na soma é um trade que só existe
  porque é declarável.
- **Difusão de erro** como a forma streamável do `agg`.
- **A verificação como estágio**, não como teste sobre o mecanismo. Ela pegou três defeitos
  meus em três labs distintos.

**Não faz sentido (ou ainda não):**

- **`rel` sozinho em dinheiro**: a cauda inferior amarra e o pedido vira no-op.
- **Âncora em trailer**, já reprovada por matar o streaming de decode.
- **RLE intra-valor agora**: teto de −1,89% na melhor coluna e **custo** na família que domina
  o corpus; e os mesmos 40 valores já são atacados pela grafia fracional, que captura a *causa*
  (`n/30`) e não o *sintoma*.
- **Qualquer weld**: falta o `:id` de contrato, sem o qual não há aviso possível no decode.

---

## 6b. O ritual de fechamento, estendido (cobranca do owner, 2026-08-14)

> *"o .8 preza tanto pela funcionalidade, fechar gaps e possibilidades extras de comprimir
> tipos, ver se o wire interno fecha tudo, desde o spec ate' apos a saida… lembrando tambem
> da vertente de latencia, memoria, velocidade, compressao etc."*

Os 5 eixos estruturais nao bastam. O fechamento de tipo passa a ter **+4 vertentes de
execucao**, medidas para float e hora no lab `2026-08-14-2350-float-hora-vertentes-restantes` (0 falhas):

| vertente | float | hora | achado |
|---|---|---|---|
| **tabela + lazy** | `.8H` RT c/ tipo ✓; `view` ✗ | idem | **nenhuma coluna tipada tem caminho lazy**: o `view` so' abre `.8M` (strings); 5a divergencia da causa *single-col e' multi-col de UMA* |
| **latencia (fatiar)** | bN **2,62x** · literal 1,11x | polaridade **0,96x** (fica MENOR) | o custo de fatiar depende da **CLASSE do vencedor**: o pulso deveria ser ciente dela |
| **velocidade+memoria** (dev-run) | 13,5–133 µs/val | **154–218 µs/val (21x o int)**; pico **126x a entrada** | o caro nao e' o tipo, e' a **cardinalidade do texto**: evidencia p/ `T-BUDGET-DE-BUSCA` |
| **terminal × transporte** | +75% / **−176%** | +56% / −6% | **pos-gzip o sinal INVERTE nas 6 colunas**: o ganho e' terminal; declarar a leitura no fechamento |

`int` e `data` tem os 5 eixos e nao as 4 vertentes, completar e' barato com o `run.py` do
lab como gabarito.

## 7. A fila

1. **Fechar hora e datetime**: os dois tipos que faltam no `.8`.
2. **`T-RLE-COUNT-ZERO`**: o `*0|` declara e não emite, sem guarda, enquanto o mesmo padrão é
   fail-loud no `bN`. Independente de qualquer feature.
3. **`H-LOSS-00`**: o `:id` de contrato no wire, que é o que destrava o aviso no decode.
4. Depois: `T-SPLIT-SINGLE-COL`, e o resto.

---

## 8. Registrado para depois: constantes notórias (π, e, φ, √2)

> Owner: *"penso também em tipos notórios como PI e E (euler)… no mesmo esquema de dicionário
> previamente declarado interno. Mas isso pode esperar, só lembre pra depois."*

**Constantes como valor de dado: nunca foi discutido no repo.** Varredura de 41 ADRs, 84
tickets, todas as notas e o histórico do git: zero.

**Mas o esquema é seu, e está registrado três vezes**: inclusive com a sua palavra:

- **H-CODEBOOK-01 tier 3** (2026-06-24): *"para tipos **notórios** (sim/não, UF, true/false), a
  tabela é senso comum → não precisa estar no blob"*. Parkado para o `.9`.
- **H-TYPE-07, dict interno** (2026-07-08): *"dicionário INTERNO, petrificado no formato… até a
  referência fica interna"*. Conclusão de lá: o byte não justifica; justifica-se por
  self-description.
- **`T-TIPOS-CONFORTO-MAP`**: o mapa de tipos internos, com slots `4..13` livres e `14/15`
  marcados por você. ⛔ bloqueado no owner. **É o slot literal onde π cairia.**

**O precedente existe e é sólido**: `syntax.py:44-47`, *"os slots baixos vêm do FORMATO
(dicionário da versão, que **não viaja no arquivo**)"*. Hoje são 5 tabelas congeladas (slot nulo,
`b1`, `b2`, o core tipado, a cabeça do lazytype). Versionamento: **a estrutura congela, a tabela
é escolha revisável até o 1.0** (ADR-0041 + ADR-0024).

**E aqui está o problema específico das constantes, que o precedente não cobre.** As 5 tabelas
congeladas são **domínio fechado de 2–3 valores, fixo por tipo**. Uma constante não é isso, é
**um valor de precisão arbitrária**. E a lei do projeto já responde: **canonicidade por
re-emissão** (5 aplicações soldadas, 4 bugs históricos, e a frase normativa *"guard de
re-emissão é lei; todo eixo novo nasce com ele"*).

A consequência é direta: **um slot de constante é uma grafia exata, não um conceito.**
`3.14159` e `3.141592653589793` seriam entradas *distintas*. Um mapa que casasse "qualquer
prefixo de π" quebraria o round-trip byte-a-byte, a mesma classe de bug que a re-emissão foi
criada para matar.

E há uma evidência que fecha o argumento, do lab de hoje: ao testar a grafia fracional,
**`2.718281828`, o número de Euler truncado, foi recusado sozinho** pelo guard de re-emissão.
A ideia já encontrou a lei do projeto uma vez, e perdeu.

**Dois bloqueios formais antes de qualquer avanço**: `T-FLOAT-SLOTS` (a ordem canônica dos
slots baixos ainda não está fixada) e a pergunta não-escrita *"o `repr` de float é contrato de
formato?"*, que é literalmente "quantos dígitos". E o gate de corpus: **zero ocorrências de
constante matemática literal** em 186 colunas.

---

## Fontes

**Labs**: `2026-08-14-1616-fechamento-float` · `…-1745-grafia-fracional-e-escala-com-excecoes` ·
`…-2010-rle-intra-valor-medida` · `…-2010-perda-propagacao-de-erro` ·
`…-2110-parametro-de-tolerancia-float` · `…-2145-agg-soma-e-streaming` ·
`2026-07-27-2211-dominio-primeiro-streaming`

**Notas**: `2026-08-14-1739-loss-e-lossless-alterado-pesquisa` ·
`2026-08-14-2010-rle-intra-valor` · `2026-08-14-2010-perda-propagacao-de-erro` ·
`2026-06/loss-taxonomia` · `2026-06/rle-familia-estudo`

**Tickets/hipóteses**: `T-FLOAT-SPEC` · `T-RLE-COUNT-ZERO` · `T-FLOAT-SLOTS` ·
`T-TIPOS-CONFORTO-MAP` · `H-FLOAT-GRAFIA-01` · `H-INTRA-01/02/03` · `H-REF-03` ·
`H-LOSS-00/01/02/03` · `H-CODEBOOK-01` · `H-TYPE-07` · `H-smart-rounding`

**Externas**: [GUM JCGM 100:2008](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e) ·
[HMRC VATREC12020](https://www.gov.uk/hmrc-internal-manuals/vat-trader-records/vatrec12020) ·
[ECJ C-302/07](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62007CJ0302) ·
[ISO 4217](https://www.iso.org/iso-4217-currency-codes.html) ·
[ALP (SIGMOD 2024)](https://dl.acm.org/doi/10.1145/3626717) ·
[SZ3](https://github.com/szcompressor/SZ3) · [zfp](https://zfp.readthedocs.io/en/release1.0.1/modes.html) ·
[Cox 1987](https://www.tandfonline.com/doi/abs/10.1080/01621459.1987.10478456)
