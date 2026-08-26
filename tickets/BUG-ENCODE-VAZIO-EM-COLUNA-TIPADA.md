---
title: "BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA: coluna mista perde valor, e em dois casos emite wire que não decodifica"
status: open
priority: P1
severity: R0 (round-trip lossy e silencioso na API pública)
created: 2026-08-26
updated: 2026-08-26
gate: correção em src/tcf só com aprovação explícita do owner (I5). Metade do contrato é determinada (a soma não inventa; sem tipo declarado, mista vira texto); a outra metade, coerção sob tipo declarado, tem 3 perguntas a medir
blocked-by: []
related:
  - src/tcf/multi/core.py
  - src/tcf/hierarchical.py
  - src/tcf/view.py
  - docs/how-to/mimetizar-pandas-sql-polars.md
  - tickets/BUG-VIEW-UMA-STRING-VAZIA.md
---

# BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA

**[probatório → avaliação de regra]** Uma coluna que mistura `""` com números ou booleanos passa pelo
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

## A regra do encode: sem tipo, cai para texto; com tipo, o tipo manda

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

### O outro lado: com tipo declarado, o tipo manda

Aqui a proposta muda o comportamento de hoje, e vale medir antes:

```python
encode({"d": ["2025-01-01", "2025-01-02"]}, schema={"d": "data-iso"})  # aplica: '!d:dt'
encode({"d": ["2025-01-01", "xx"]},         schema={"d": "data-iso"})  # ignora: '!d', texto puro
```

Hoje uma spec que não serve é **silenciosamente descartada**. Isso é lossless, e é calado:
o chamador pede um tipo, não recebe, e não fica sabendo.

A regra proposta, forçar o não-membro a nulo, é a convenção de coerção da área
(`pd.to_numeric(errors="coerce")`, `cast(strict=False)` do Polars) e é matematicamente
defensável: um tipo declarado é uma **restrição de domínio**, e valor fora do domínio não
tem representação nele; virar ausência é a leitura natural. Declarar o tipo é o ato
deliberado que autoriza a perda.

As três perguntas que essa metade abre, e que eu não responderia sem medir:

1. **Membro é por valor ou por tipo de Python?** Numa coluna declarada numérica, `"12"`
   denota um número. Coagir isso a nulo seria perda gratuita; aceitar exige dizer que a
   pertinência se decide pelo valor.
2. **Silencioso ou avisado?** Coerção que apaga dado sem dizer nada é a classe de defeito
   que este ticket combate. O mínimo é contar quantas células foram coagidas.
3. **A rota single-column acompanha?** Ela hoje levanta `MISTOS`, e a regra 1 pede texto.
   Alinhar é o certo, mas mexe no `.8H` e amplia o raio da correção.

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

### A tabela fixada

| variação | comportamento | por quê |
|---|---|---|
| coluna mista, sem tipo declarado | **texto**, com aviso | preserva todo valor |
| `""` em coluna mista | `""`, nunca `None` | vazio não é ausência |
| `None` | continua `None` | ausência é ausência |
| `["1", "2"]` | continua texto | nada declarado, nada adivinhado |
| `[1, 1.5]` | numérica | mesmo domínio, não é mista |
| spec que serve a todos | aplicada | caso feliz |
| spec que não serve a algum | **dado mantido, spec descartada, com aviso** | ver a tensão abaixo |
| soma com não-número | `ValueError` | não-número não soma |
| soma de conjunto vazio | `0.0` | identidade aditiva |

### A única linha que ainda é sua

Para a spec que não serve, as duas orientações apontam para lados diferentes, e prefiro
dizer isso a escolher calado. *"Spec força não-membro a nulo"* é a convenção do pandas
(`errors="coerce"`) e do Polars (`strict=False`). *"O TCF não é um ETL"* vai contra, porque
**coagir para nulo é transformar dado**, que é o que um ETL faz.

Pela segunda, que é a mais forte, o coerente é manter o dado, descartar a declaração que não
se sustenta e avisar. Quem quiser coerção pede por ela, com nome próprio, e aí é um ato
explícito de transformação, não efeito colateral de declarar um tipo.

## Alcance

- **Publicado**: presente na `0.8.2` no PyPI.
- **Fixture do how-to**: a página
  [`mimetizar-pandas-sql-polars.md`](../docs/how-to/mimetizar-pandas-sql-polars.md) usa
  `"v": [10, 5, None, 20, "", 7, None]`, que cai exatamente neste caso. Por isso as receitas
  de `COUNT(col)` da página **levantam** ao rodar, e `select("v")` e `sum("v")` também. Não
  é efeito da revisão de 2026-08-26: a fixture já era essa, e as duas versões da receita, a
  antiga e a corrigida, quebram igual. A página precisa de uma fixture que rode, e a troca
  entra junto da correção.
- **Gates byte-canônicos**: intactos (33 verdes). Nenhuma fixture de gate mistura tipos.

## Critério de aceite

- [ ] Coluna mista **sem tipo declarado** vira texto, sempre, independente de qual valor
      aparece primeiro; `decode` devolve todos os valores, nenhum vira nulo.
- [ ] `decode` deixa de converter `""` em `None` numa coluna cuja tag foi **inferida**.
- [ ] Com tipo ou spec declarado, o contrato de não-membro está decidido e documentado
      (coagir a nulo, com as três perguntas da avaliação respondidas), e deixa de ser
      "descarta a spec em silêncio".
- [ ] A rota single-column e a multi-column concordam sobre coluna mista.
- [ ] `decode` e `view` param de discordar sobre o mesmo wire.
- [ ] `sum` sobre coluna com não-número levanta `ValueError`, e não `HierarchicalError`,
      igualando `[1, ""]` a `["a", "b"]`.
- [ ] `sum` de conjunto vazio devolve `0.0`, como o contrato escrito e como o `group_sum`.
- [ ] Cobrir `[1, ""]`, `["", 1]`, `[True, ""]`, `[1.5, ""]`, `["a", ""]` (que deve
      continuar passando) e a mesma coluna em posição não inicial numa tabela larga.
- [ ] Fixture do how-to trocada por uma que rode, e as receitas da página reverificadas por
      execução.
- [ ] Suíte completa e gates verdes; sem re-pin de bytes, porque nenhum wire válido muda.

## Estado

Repro confirmado em `v0.8.2`. Nenhuma alteração em `src/tcf/` foi feita nesta auditoria.
