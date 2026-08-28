---
title: "BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA: coluna mista perde valor, e em dois casos emite wire que não decodifica"
status: closed-fixed
priority: P1
severity: R0 (round-trip lossy e silencioso na API pública)
created: 2026-08-26
updated: 2026-08-28
gate: "solda autorizada pelo owner em 2026-08-27 (onda 0 da auditoria de consistência); a política coerciva foi RETIRADA, não implementada"
blocked-by: []
related: [
      src/tcf/multi/core.py,
      src/tcf/hierarchical.py,
      src/tcf/view.py,
      docs/how-to/mimetizar-pandas-sql-polars.md,
      tickets/BUG-VIEW-UMA-STRING-VAZIA.md,
      experiments/lab/dirty/notas/2026-08/2026-08-26-1944-revisao-fechamento-08-view-encode.md,
      experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md,
      experiments/lab/dirty/2026-08/2026-08-28/2026-08-28-0100-portao-de-homogeneidade/,
]
---

# BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA

**[probatório → execução]** Uma coluna que mistura `""` com números ou booleanos passa pelo
`encode` sem reclamar e **não volta igual**. A perda é silenciosa, atinge a `0.8.2`
publicada, e viola o invariante mais duro do projeto: ou o round-trip devolve o mesmo dado,
ou falha alto.

Irmão de [`BUG-VIEW-UMA-STRING-VAZIA`](BUG-VIEW-UMA-STRING-VAZIA.md), e o mesmo tema de
fundo: **vazio não é ausente**. Lá o dano é a contagem na camada read-only; aqui é o dado
em si, no `encode`/`decode`.

Achado ao executar o exemplo corrigido do how-to, que é onde a fixture da página vive.

## Repro mínimo

```python
from tcf import decode, encode

assert decode(encode({"v": [1, ""]}))    == {"v": [1, None]}    # o "" virou nulo
assert decode(encode({"v": ["", 1]}))    == {"v": ["", "1"]}    # o int virou texto
assert decode(encode({"v": [True, ""]})) == {"v": [True, None]}
```

Nenhuma das três levanta. Todas mentem.

A rota single-column, sobre o mesmo dado, **recusa**:

```python
encode([1, ""])   # HierarchicalError: tipos escalares MISTOS {'s', 'n'} numa coluna
```

Duas rotas, o mesmo dado, dois comportamentos: uma falha alto, a outra perde calada. É a
divergência que classifica isto como R0 e não como limitação documentável.

Coluna de texto não é afetada: `["a", "", "b"]` volta exata.

## Causa

Três pontos, e cada um sozinho é defensável; juntos produzem a perda.

**1. O tipo da coluna é decidido pelo PRIMEIRO valor não nulo**
([`multi/core.py`](../src/tcf/multi/core.py), no bloco `col_types`):

```python
primeiro = next((v for v in values if v is not None), None)
tag = _TAG_DO_TIPO.get(type(primeiro))
```

Não há conferência de homogeneidade. `[1, ""]` vira coluna `N` por causa do `1`; `["", 1]`
vira texto por causa do `""`. A rota `.8H` faz essa conferência e é dela que sai o
`MISTOS` ([`hierarchical.py`](../src/tcf/hierarchical.py)).

**2. No decode de coluna tipada, payload vazio É a grafia do nulo**
([`multi/core.py`](../src/tcf/multi/core.py)):

```python
result[col] = [None if v is None or v == "" else _dec_scalar(v, tipo) for v in result[col]]
```

Ou seja, numa coluna `N`/`B` a string vazia **não tem representação**: o lugar dela no wire
já pertence ao nulo. Aceitar o valor no encode não podia dar certo.

**3. A `view` não tem a mesma cláusula** ([`view.py`](../src/tcf/view.py), em `_col`):

```python
vals = [None if v is None else _dec_scalar(v, stype) for v in vals]
```

Então, sobre o **mesmo wire**, `decode` devolve `None` em silêncio e a `view` levanta
`HierarchicalError: corpo number inválido ''`. Duas leituras da mesma coisa, discordando.
Isso é paridade quebrada, e vale como defeito próprio mesmo depois de resolvido o resto.

## A determinação, pela soma

Não há escolha a fazer aqui: **a matemática já responde, e o resto é consequência.**

`""` não é um número. Somar um conjunto que contém um não-número não tem resultado; tem
erro. E a `view` já se comporta assim quando o não-número é visível:

```python
view(encode({"v": ["a", "b"]})).sum("v")     # ValueError, e está certo
```

O que a soma faz hoje, caso a caso, é coerente e não precisa mudar:

| entrada | `sum` hoje | por quê |
|---|---|---|
| `[1, 2, 3]` | `6.0` | soma dos presentes |
| `[1, None, 3]` | `4.0` | nulo é ausência: fica fora da soma, não zera |
| `[None, None]` | `0` | soma vazia é a identidade aditiva |
| grupo sem nenhuma linha | `0` | mesma identidade |
| `["a", "b"]` | `ValueError` | não-número não soma |
| `["1", "2"]` | `3.0` | texto que denota número soma |
| **`[1, ""]`** | **`HierarchicalError`** | **a única fora do lugar**: devia ser o mesmo `ValueError` de `["a", "b"]` |

E o `decode` é pior que a `view`, porque **inventa a resposta**: ele converte `""` em
`None`, e com isso um conjunto que não tem soma passa a ter, valendo `1`. Trocar
"não é número" por "não está presente" é a única operação, entre todas as citadas, que
muda o resultado matemático em vez de recusá-lo.

Daí sai a primeira metade, sem preferência no meio: **o `decode` não pode trocar
"não é número" por "não está presente"**, porque é a única operação, entre todas as
citadas, que muda o resultado matemático em vez de recusá-lo. E a `view` recusar está
certo; errada é a classe do erro, que deve ser `ValueError`, igual ao de `["a", "b"]`, e é
o que [`DECISAO-GROUPING-SEMANTICA`](DECISAO-GROUPING-SEMANTICA.md) já fixou para
não-numérico na soma. `HierarchicalError` fala de wire corrompido, e o wire não está
corrompido: o dado é que não pertence à coluna.

### Um desalinhamento menor, do mesmo tema

`sum` de conjunto vazio devolve `0` (int), enquanto `sum` com valores devolve `float`, e o
contrato escrito promete `0.0`. `group_sum` já devolve `0.0`. Matematicamente é o mesmo
número; para quem consome, é outro tipo. Vale alinhar junto, e não precisa de decisão:
o contrato já está escrito.

## Proposta sob inspeção: sem tipo, cai para texto; com tipo, o tipo manda

> **Status: SUPERADA em 2026-08-28, e preservada por causa do racional.** Esta proposta não
> foi implementada. Medida caso a caso na onda 0, ela cobre sete dos nove defeitos e mente
> nos outros dois, por isso a decisão foi o fail-loud que `api.md` já publicava. O que segue
> é o raciocínio como estava escrito; a conclusão está em *"A decisão, e por que não foi a
> que o ticket propunha"*, mais abaixo.

Direção do owner (2026-08-26):

> *"o encode/decode se não tiver um tipo que oriente acaba fazendo fallback pra string.
> podemos tentar avaliar uma forma de que o blob tcf caia em string se o dataset ficar
> misto, já que o tcf não consegue ser seletivo por célula (...). e se eu colocar um spec ou
> tipar, ele forçar os elementos que não fazem parte do conjunto para nulo/none."*

**Avaliei, e essa regra é melhor que a recusa que eu tinha recomendado.** A recusa protege o
dado rejeitando a tabela inteira; o fallback para texto protege o dado **guardando todos os
valores**. Entre uma saída que não entrega nada e outra que entrega tudo com o tipo
rebaixado, a segunda perde menos.

E ela quase não é novidade: **já acontece metade do tempo**, e é a metade que funciona.

```python
decode(encode({"v": ["", 1]}))   # {'v': ['', '1']}    fallback para texto: nada se perde
decode(encode({"v": [1, ""]}))   # {'v': [1, None]}    tag inferida: o "" desaparece
```

Os dois casos têm o mesmo dado; o que os separa é **qual valor apareceu primeiro**. Ou seja,
o defeito não é a coerção em si, é **inferir uma declaração de tipo a partir de uma célula**.
Tirando a inferência, a assimetria some e o caso bom vira o único caso.

A grafia do rebaixamento já existe e é canônica, então não há decisão nova aqui:

| entrada | como já vira texto |
|---|---|
| `[1, ""]` | `["1", ""]` |
| `[1.5, ""]` | `["1.5", ""]` |
| `[True, ""]` | `["true", ""]` (a grafia do wire, não o `True` do Python) |

O que se perde no rebaixamento é a **anotação de tipo**, que o chamador nunca declarou: ela
tinha sido adivinhada. O que se perdia antes era o **valor**, que ele tinha declarado ao
passar o dado. A troca é boa, e o `encode` deixa de ser injetivo em entrada mista, o que
precisa estar escrito na página do formato.

### O outro lado: com tipo declarado (CORRIGIDO em 2026-08-26)

> **Eu tinha escrito que "uma spec que não serve é silenciosamente descartada", e generalizei
> de uma fixture de dois valores. Está errado.** Naquele caso a spec não foi descartada por
> causa do alienígena: ela perdeu a **competição de bytes**, que é outra coisa, e o dado
> voltou exato de qualquer jeito.

Medido com uma coluna de 80 datas, onde a spec paga:

| coluna | spec aplicada | bytes | round-trip |
|---|---|---:|---|
| 80 datas válidas | **sim** (`v:dt`) | 229 | exato |
| 79 datas + `"nao-e-data"` | **sim** (`v:dt`) | 320 | **exato** |
| 79 datas + `""` | **sim** (`v:dt`) | 310 | **exato** |
| 79 datas + `None` | **sim** (`v:dt`) | 285 | **exato** |

A spec **continua aplicada** e o valor que não casa volta **literal**. É exatamente o que o
owner lembrava do CPF, e o que a nota de 2026-08-08 já registrava para a origem soft:
*"tenta, e o que não casar vira literal"*, com escape de um byte.

**Consequência direta: a proposta de coagir o não-membro para nulo está retirada.** Ela
substituiria um comportamento que já é lossless por um que perde dado, e quebraria o pino de
round-trip das natures. O achado A3 da revisão está certo, e por uma razão mais forte do que
a que eu tinha escrito: não é só que coagir *seria* lossy, é que o caminho lossless **já
existe e funciona**.

### O enquadramento que faltava: hard e soft

O owner apontou o vocabulário que o projeto já tem
([nota de 2026-08-08](../experiments/lab/dirty/notas/2026-08/2026-08-08-origem-hard-e-soft-modelo-vs-implementado.md)):

| origem | o que é | o que acontece com o alienígena |
|---|---|---|
| **hard** | o dado chega já tipado (`int`, `bool`, `float`) | o TCF não revalida; o conjunto aceito é o dos escalares JSON |
| **soft** | string com um tipo **declarado** por spec | tenta; o que não casa vira **literal**, sem drama |

Com isso, as três situações se separam, e cada uma tem um dono diferente:

1. **soft**, tudo string, com ou sem spec: já resolvido e lossless. Nada a fazer.
2. **hard misto**, `int` e `str` na mesma coluna (`[1, ""]`, `[1, "1"]`, `[True, 1]`): a
   entrada declarou dois tipos numa coluna só. É onde mora o defeito, e onde
   `docs/reference/api.md` já promete fail-loud.
3. **coerção prescritiva**, "force esta coluna a int, e o inválido vira nulo ou zero": não
   existe hoje, e é o `schema` prescritivo que a revisão manda desenhar no `.9`.

**O ponto que ainda precisa de você** está na linha 2. A sua regra diz que sem spec o
implícito cai para string, o que resolveria `[1, "1"]` como `["1", "1"]`. O modelo hard diz
o contrário: se entrou `int`, volta `int`, e o TCF não converte origem hard. E `api.md`
promete fail-loud para union fora de bool+str.

As duas leituras são defensáveis, e a diferença é sobre o que uma coluna hard-mista
significa: *"o dev misturou, então trate como texto"* ou *"o dev misturou, então o dado está
errado e eu aviso"*. A segunda é a que o formato já publicou.

## O ciclo das variações (2026-08-26)

Premissa do owner que orientou o ciclo: *"o TCF não é um ETL de tratamento de dados (...) o
máximo que dá pra fazer é fallback, ignorar elementos e warnings (...) pegar um comportamento
conveniente, ver da perspectiva matemática e orientar a resposta a isso."*

17 variações medidas em
[`2026-08-26-0100-entrada-suja-variacoes`](../experiments/lab/dirty/2026-08/2026-08-26/2026-08-26-0100-entrada-suja-variacoes/).
**11 já estão certas.** As 6 que falham se separam em três classes, e o ciclo achou uma pior
do que este ticket registrava:

| classe | variações | dano |
|---|---|---|
| **wire não decodifica** | `[1, "a"]`, `[True, 1]` | o `encode` aceita e emite blob que o **próprio `decode` não lê** |
| valor destruído | `[1, ""]`, `[True, ""]` | o `""` volta `None` |
| tipo rebaixado | `["", 1]`, `["a", 1]` | o `1` volta `"1"`; nenhum valor se perde |

A regra do fallback para texto resolve **as três de uma vez**, porque em todas elas o
problema é a tag inferida de uma célula:

| variação | hoje | com a regra |
|---|---|---|
| `[1, "a"]` | wire não decodifica | `["1", "a"]` |
| `[1, ""]` | `[1, None]` | `["1", ""]` |
| `[True, 1]` | wire não decodifica | `["true", "1"]` |
| `[True, ""]` | `[True, None]` | `["true", ""]` |

E **nenhuma das 17 emite aviso**, que é a peça que a premissa do owner exige. O
`warnings.warn` já é usado em `view.py` e `composicional/syntax.py`, então não é mecanismo
novo.

### A tabela proposta

| variação | comportamento | por quê |
|---|---|---|
| coluna mista de tipos disjuntos, sem tipo declarado | texto, com aviso | preserva os valores |
| coluna mista com colisão valor/grafia (`[1, "1"]`) | **falha alto** | nenhuma regra recupera a distinção perdida |
| `""` em coluna mista | `""`, nunca `None` | vazio não é ausência |
| `None` | continua `None` | ausência é ausência |
| `["1", "2"]` | continua texto | nada declarado, nada adivinhado |
| `[1, 1.5]` | numérica | mesmo domínio, não é mista |
| spec que serve a todos | aplicada | caso feliz |
| spec que não serve a algum | **não-membro vira nulo, com aviso**; nunca zero nem `False` | nulo é o único cast que não muda resposta |
| preenchimento (zero, `False`, default) | fora do `encode` | é decisão de leitura, e precisa de rastro |
| modo estrito | levanta em vez de coagir, sob flag | integridade em CI e depuração |
| soma com não-número | `ValueError` | não-número não soma |
| soma de conjunto vazio | `0.0` | identidade aditiva |

### A proposta para o tipo declarado

A proposta parte da seguinte orientação do owner:

> *"o TCF não é ETL de fato, mas dar dados sujos obriga o TCF a transformar o dado de
> qualquer forma, e não tem saída (...) cada tipo pode ter algum fallback que ignora os
> outros tipos misturados."*

Essa orientação sustenta o racional proposto. O `encode` **já transforma**: stringifica, escolhe modo,
rebaixa tipo. Recusar-se a escolher a transformação não faz o TCF parar de transformar, só
faz a transformação ser acidental em vez de projetada, que é exatamente o defeito deste
ticket. "Não é ETL" quer dizer **não repara dado**, não "nunca converte".

**Mas nem todo cast serve, e a aritmética separa.** Medido em
[`2-fallback-por-tipo.py`](../experiments/lab/dirty/2026-08/2026-08-26/2026-08-26-0100-entrada-suja-variacoes/):

| coluna com 7 válidas e 3 sujas | count | sum | avg | min | max |
|---|---:|---:|---:|---:|---:|
| **a verdade** | 7 | 93 | 13,29 | 11 | 16 |
| sujas → **nulo** | 7 | 93 | 13,29 | 11 | 16 |
| sujas → **zero** | 10 | 93 | **9,3** | **0** | 16 |

Nulo não estraga nada; zero estraga três das cinco. E a armadilha é fina: **a soma não
muda**, e é o número que se confere primeiro. Em booleano, coagir para `False` infla o grupo
`False` com dado que nunca foi `False`.

A razão é a que o contrato do agrupamento já fixou: **ausência não participa de agregação;
zero e `False` são valores, e participam**. Nessa proposta, o cast do não-membro seria
**nulo**.
Zero, `False` e afins não somem do mapa: viram **preenchimento**, decisão de quem consome,
com nome próprio (`fillna`, `fill_null`, `COALESCE`) e rastro visível.

### O modo estrito

> *"ele poderia até dar warning ou erro em alguns casos estritos (...) isso ajuda a depurar
> caso um dataset acabe sendo construído por algum erro anterior."*

De acordo, e o vocabulário já existe no repo: `LazyTCF.strict()` faz isso do lado da leitura,
justificado no próprio código como *"código que se quer rígido (revisão, CI, conformidade)"*.
O estrito do `encode` é a mesma ideia na outra ponta e deve levar o mesmo nome.

Nomenclatura a evitar: **`encode(fallback=...)` já existe** e significa candidatos de modo
por coluna (ADR-0022/0025/0026). O botão novo precisa de outro nome.

## Alcance

- **Publicado**: presente na `0.8.2` no PyPI.
- **Fixture do how-to**: a fixture vigente de
      [`mimetizar-pandas-sql-polars.md`](../docs/how-to/mimetizar-pandas-sql-polars.md) não
      mistura `""` com número. Ela não reproduz este bug; qualquer fixture mista futura precisa
      passar pelo gate de round-trip antes de sustentar uma receita.
- **Gates byte-canônicos**: intactos (33 verdes). Nenhuma fixture de gate mistura tipos.

## A decisão, e por que não foi a que o ticket propunha

O ciclo das variações recomendava **fallback para texto**. O lab da onda 0
([`2026-08-28-0100-portao-de-homogeneidade`](../experiments/lab/dirty/2026-08/2026-08-28/2026-08-28-0100-portao-de-homogeneidade/))
mediu os nove casos um a um e mostrou que essa regra **cobre sete dos nove**. Os dois que
sobram são os que nenhum rebaixamento alcança:

| par | o que o `decode` devolvia | por que texto não resolve |
|---|---|---|
| `[1, "1"]` | `[1, 1]` | as duas células escrevem a mesma coisa no wire; depois disso nada diz qual era `int` |
| `[True, "true"]` | `[True, True]` | idem |

Não são perdas de anotação de tipo: são **dois valores colapsados num só**. O ticket
previa a colisão de grafia como classe, mas não tinha medido que ela já acontece no
`decode` de hoje. Uma regra que resolve sete de nove e mente nos outros dois é pior do que
recusar, porque a mentira fica dentro do caminho feliz.

Então valeu a recomendação conservadora da revisão crítica, e ela é a que **`api.md` já
publicava**: *"array de tipos mistos (union) fora da união bool+str → fail-loud"*. O `.8M`
era a única das três famílias que não cumpria o contrato escrito. A correção não mudou o
contrato; alinhou a implementação a ele.

## O que foi soldado (2026-08-27, onda 0)

`_tabela_flat` ([`encoder.py`](../src/tcf/encoder.py)), o portão do `.8M`, passou a chamar
`_scalar_type` de [`hierarchical.py`](../src/tcf/hierarchical.py) por coluna antes de
aceitar a tabela. O juiz de homogeneidade passou a ser **um só** para as três famílias, em
vez de existir no `.8H` e faltar no `.8M`. Coluna mista cai para o `.8H`, que levanta com
a mesma frase.

Custo em bytes: **zero**. Nenhum wire válido muda, e os 33 gates byte-canônicos
continuam verdes sem re-pin.

## Critérios de aceite

- [x] Coluna mista **sem tipo declarado** deixa de emitir wire, independente de qual valor
      aparece primeiro. ~~Vira texto~~: **retirado**, medido que texto perde `[1, "1"]` e
      `[True, "true"]` do mesmo jeito.
- [x] `decode` não converte mais `""` em `None` por tag inferida: o wire que fazia isso
      deixou de ser emitível.
- [x] ~~Com tipo ou spec declarado, o não-membro vira **nulo**.~~ **Retirado em 2026-08-26:**
      medido que a spec continua aplicada e o não-membro volta **literal**, com round-trip
      exato. Coagir substituiria um caminho lossless que já funciona.
- [x] A rota single-column, a multi-column e a hierárquica concordam sobre coluna mista,
      **com a exceção conhecida** da união bool+str, registrada abaixo.
- [x] Cobrir `[1, ""]`, `["", 1]`, `[True, ""]`, `[1.5, ""]` e `["a", ""]` (que continua
      passando), mais a mistura em posição não inicial de coluna longa, NaN/Inf, e a ordem
      das células deixando de decidir. Em
      `tests/test_f0_boundary_fixes.py::TestPortaoHomogeneidadeMultiCol`.
- [x] A fixture do how-to passa por round-trip e tem as receitas verificadas por execução.
- [x] Suíte completa (1580) e 33 gates verdes; sem re-pin de bytes.
- [x] Lab de evidência em disco (I2), com o antes vindo do `git HEAD` e não da memória.
- [x] ~~`sum` sobre coluna com não-número levanta `ValueError`, igualando `[1, ""]` a
      `["a", "b"]`.~~ **Retirado em 2026-08-26 (achado A5, conferido):** numa coluna de
      texto, `sum(["1", "", "2"])` devolve **3.0**, ou seja `""` já é *pulado* na agregação,
      como o nulo. O que restava do item some sozinho: `[1, ""]` deixou de existir como wire.
- [x] ~~`sum` de conjunto vazio devolve `0.0`, como o contrato escrito.~~ **Retirado em
      2026-08-27:** conferido por execução que o contrato escrito **não** promete isso. A
      página do `lazy-view` documenta `0` (int) no agregador **escalar**, e `0.0` na família
      **`group_*`**, com escopo explícito nas duas linhas. O código honra os dois. Este item
      nasceu de uma leitura errada da própria doc.

## Modo estrito: a pergunta se inverteu

O ticket pedia um modo estrito que levantasse em vez de coagir. Com fail-loud como
**default**, o estrito é o comportamento normal, e o botão que faria sentido é o oposto: um
modo tolerante, que aceite coluna mista rebaixando para texto e avisando.

Ele não entra no `.8`, por duas razões medidas: rebaixar não recupera `[1, "1"]` nem
`[True, "true"]`, e o nome `fallback=` já está tomado por candidatos de modo por coluna
(ADR-0022/0025/0026). Fica como desenho do `.9`, junto com o `schema` prescritivo de
[`T-API-SCHEMA-PRESCRITIVO`](T-API-SCHEMA-PRESCRITIVO.md).

## O que sobrou, e onde foi parar

| resto | onde |
|---|---|
| união **bool+str**: o `.8` aceita e faz round-trip (`#TCF.8bB`), o `.8M` e o `.8H` recusam | decisão de dono, `.9`. Pinada em `TestPortaoHomogeneidadeMultiCol::test_uniao_bool_str_e_a_divergencia_QUE_SOBRA` |
| `decode` e `view` discordando sobre o mesmo wire | só sobrevive em wire **não emitível** (escrito à mão ou corrompido). Ex.: `'#TCF.8M1B=v

'`, onde `decode` devolve `[None]` e a `view` levanta |
| modo tolerante no `encode` | `.9`, com nome que não colida com o `fallback=` existente |

## Estado

**FECHADO em 2026-08-28.** O R0 acabou: nas três famílias, coluna mista levanta, nenhuma
perde valor calada e nenhuma emite wire que o próprio `decode` não lê. Das 39 rotas medidas,
9 estavam erradas e as 9 viraram recusa; os 14 round-trips corretos ficaram idênticos, o que
é o que separa consistência de "recusar tudo".

A `0.8.2` publicada no PyPI **contém o defeito**. A correção sai na próxima, e é mudança de
comportamento visível: entrada que antes passava calada agora levanta. Isso é o pretendido,
e a `0.8.2` é marcador de desenvolvimento (ADR-0024), não compromisso de compatibilidade.
