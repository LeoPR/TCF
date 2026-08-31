---
title: "DECISAO-GROUPING-SEMANTICA: onde o agrupamento do TCF diverge de SQL, pandas e polars"
status: closed-decided
priority: P3
severity: R4 (contrato semantico; nenhuma mudanca de wire)
created: 2026-08-25
updated: 2026-08-26
gate: fechado; otimizacoes futuras pertencem a H-QUERY-04, nao reabrem a semantica
blocked-by: []
related:
  - src/tcf/view.py
  - docs/how-to/consultar-sem-decodificar.md
  - docs/how-to/mimetizar-pandas-sql-polars.md
  - experiments/lab/dirty/notas/2026-08/2026-08-26-1944-revisao-fechamento-08-view-encode.md
---

# DECISAO-GROUPING-SEMANTICA

Agrupar tem decisoes que nao tem resposta unica no mercado, e cada ferramenta escolheu
diferente. Este ticket fixa o contrato do TCF: primeiro a resposta logica ou matematica
minima; depois, quando necessario, uma adaptacao explicita para a convencao de outra
ferramenta.

Diretriz do dono do projeto (2026-08-25):

> *"os outros manipuladores de dados ate' mesmo o numpy, pandas e polars, sql e afins
> servem como orientacao para as respostas, mas o tcf pode ter um comportamento
> documentado diferente em ultimo caso. apenas precisamos levantar e decidir depois."*

## Principio: oportunista no custo, deterministico na resposta

A `view` tenta obter a **maxima resposta pela menor evidencia suficiente** que o wire ja'
oferece. Header, contadores, tabelas de unicos, streams de indices e alinhamento posicional
devem ser consultados antes de materializar valores. Se a estrutura nao basta para provar a
resposta, a rota faz fallback; ela nunca adivinha.

Esse oportunismo e' de **execucao**, nao de semantica. Caminho estrutural, materializacao de
uma coluna e fallback completo precisam devolver a mesma resposta. Trocar de modo de
compressao pode mudar o custo, nunca o significado de nulo, vazio, grupo ou agregado.

O contrato minimo segue quatro regras:

1. nao apagar linha ou grupo em silencio;
2. usar a resposta matematica quando ela existe;
3. quando ela nao existe, representar a ausencia (`None` no resultado agrupado) ou falhar
  claramente (agregador escalar), em vez de inventar um valor;
4. deixar convencoes externas fora do default quando uma transformacao explicita de uma
  linha produz o comportamento desejado.

## A matriz

| questao | SQL | pandas | polars | **TCF hoje** |
|---|---|---|---|---|
| nulo na chave forma grupo? | sim | **nao** (`dropna=True`) | sim | **sim, DECIDIDO** |
| string vazia forma grupo? | sim | sim | sim | **sim, DECIDIDO** |
| grupo sem valor: `sum` | `NULL` | `0` | `0` | **`0.0`, DECIDIDO** |
| grupo sem valor: `min`/`max`/`avg` | `NULL` | `NaN` | `null` | **`None`, DECIDIDO** |
| ordem das chaves no resultado | indefinida | ordenada | aparicao | **aparicao, DECIDIDO** |
| valor nao-numerico na soma | erro | erro ou `NaN` | erro | **levanta `ValueError`, DECIDIDO** |
| chave sai em que tipo | o da coluna | o da coluna | o da coluna | **o da coluna, DECIDIDO** |

## O que ja' esta' decidido de fato, e por que

**Nulo forma grupo.** Segue SQL e polars. O default do pandas (descartar) surpreende:
somar por grupo e perder linhas em silencio e' pior que ver um grupo `None` no resultado.

**`sum` de grupo sem valor da' `0.0`, e `min`/`max`/`avg` dao `None`.** Nao e'
inconsistencia, e' a distincao entre "a soma do conjunto vazio" e "o menor de nenhum
valor". A primeira tem resposta matematica; a segunda nao tem, e devolver `0.0` inventaria
um valor que a coluna nao contem. Fazer o grupo SUMIR seria pior nos dois casos: esconderia
que a chave estava la'.

**Ordem de aparicao.** Cai de graca do dicionario do Python e da' um resultado
deterministico para o mesmo blob, o que a ordenacao do pandas tambem daria, mas sem custo.

**String vazia e' elemento; nulo e' ausencia.** Ambos ocupam uma linha e ambos podem formar
chave de grupo. `count()` e `group_count()` contam linhas, logo nao descartam nenhum dos
dois. Para contar valores presentes, filtra-se apenas `None`; tratar `""` como missing e'
uma convencao adicional e precisa aparecer no predicado.

**Valor nao-numerico levanta.** Pular silenciosamente um valor mudaria o conjunto sobre o
qual a operacao foi pedida. Um modo tolerante pode existir no futuro, mas sera' uma politica
explicita, nao o significado de `sum`.

## DECIDIDO em 2026-08-25: nulo forma grupo, e nao ha' flag `dropna`

Palavras do dono do projeto:

> *"manter e' bom, e criar um dropna e' simples ja' que bastaria colocar um filtro, logo
> ja' tem solucao, e criar um flag torna ate' confortavel mas e' uma forma de esconder o
> filtro por uma semantica diferente."*

O argumento fecha os tres eixos de uma vez:

- **ja' tem solucao**: `where(col, pred=lambda x: x is not None).group_count(col)` produz
  exatamente o que o `dropna=True` do pandas produziria. Conferido contra a conta feita a'
  mao;
- **e' mais honesto**: o filtro escrito deixa a' vista o que esta' sendo jogado fora, e uma
  flag esconderia o descarte atras de uma palavra;
- **nao custa mais caro**: numa coluna dicionario o predicado roda sobre os K unicos, nao
  sobre as N linhas. Medido: 3 avaliacoes para 600 linhas.

O que precisa continuar valendo para a decisao se sustentar, e por isso virou teste: o
`None` tem de CHEGAR ao predicado. Se ele fosse filtrado antes, a alternativa explicita
sumiria e o usuario ficaria sem saida.

Pinado em `tests/test_tcf_lazy.py::TestNuloNaChaveDeGrupo`.

## DECIDIDO em 2026-08-25: `sum` da' 0.0 por MATEMATICA, e o resto e' convencao de fora

> *"sou a favor de manter 0.0 por matematica, qualquer coisa fora disso e' convensao de
> programacao e pode ser feita fora. basta convencionar isso [...] vamos seguir a logica e
> a matematica e apenas documentar comportamento."*

A soma do conjunto vazio e' zero, e isso nao e' escolha: e' definicao. Ja' o menor de
nenhum valor nao existe, e devolver `0.0` ali inventaria um numero que a coluna nao contem.
Nao ha' incoerencia entre as duas respostas; ha' duas perguntas diferentes.

### O que a exploracao mediu antes da decisao

Sete formas de "sem valor aproveitavel" (todos nulos, todos vazios, nulo e vazio
misturados, uma linha so' nula, todos os grupos vazios, mais dois CONTROLES com zero
legitimo). As sete respondem igual, e os controles confirmam que **zero nao e' tratado
como vazio**: `[0, 0]` da' `min` 0.0, e `[0, None]` tambem.

O argumento de que o `0.0` esconderia informacao foi testado e e' **parcialmente
verdadeiro**: `group_sum` nao distingue `[0, 0]` de `[None, None]`, as duas dao 0.0. Mas a
informacao nao se perde, so' esta' noutra operacao: `group_min` devolve 0.0 no primeiro e
`None` no segundo, e `group_count` mostra que o grupo existe nos dois. Precisar de uma
segunda chamada nao e' o mesmo que perder o dado.

### O que a decisao produziu

`docs/how-to/mimetizar-pandas-sql-polars.md`: a linha de codigo que obtem o comportamento
de cada ferramenta, partindo do default do TCF. Cinco receitas, cada uma verificada por
execucao contra um oraculo manual em Python que materializa a semantica documentada
(`2026-08-25-0500-grupo-sem-valor/2-receitas.py`).

## Convencoes de outras ferramentas

NumPy, pandas, Polars e SQL sao referencias de interoperabilidade, nao autoridades sobre o
default. O guia `docs/how-to/mimetizar-pandas-sql-polars.md` mostra, por exemplo, como obter
`dropna=True`, `COUNT(col)`, `COUNT(NULLIF(col, ''))`, ordenacao de chaves e `NULL` no lugar
da soma vazia.

Na soma vazia, a
[referencia oficial de `Expr.sum`](https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.sum.html)
fixa `0` quando nao ha valores nao nulos; portanto o default do TCF coincide com ele nesse
eixo. O lab local nao importa as bibliotecas externas: ele valida as receitas contra
oraculos manuais, nao contra uma execucao dessas bibliotecas.

A preferencia e' pelo menor adaptador visivel depois da `view`: filtro, ordenacao ou
transformacao do resultado. Uma flag so' passa a ser melhor quando a convencao for comum e
houver um caminho direto que responda com menos trabalho; se ela apenas esconder o mesmo
filtro e a mesma pos-transformacao, acrescenta semantica sem reduzir custo.

## Preocupacao registrada pelo dono do projeto (2026-08-25)

> *"se eu precisar criar um flag para uma situacao ambigua, em que podem ter duas solucoes
> certas, se as duas terao caminhos otimizados para responder direto, ao inves de passar
> por um modo e depois fazer um filtro pos-leitura."*

E' o ponto que decide se uma flag futura vale a pena. Hoje as receitas passam por dois
caminhos: o filtro monta os indices, e a agregacao roda em cima deles. Uma flag que apenas
embrulhasse essa mesma sequencia seria acucar; uma flag que valesse a pena precisa de um
caminho proprio que responda numa passada.

Isso NAO e' trabalho do `.8`: a funcionalidade veio primeiro, como decidido. Fica
registrado como `H-QUERY-04e` no `roadmap-hipoteses.md`, junto com a pergunta de se
`where(...).group_count()` e `group_count` com filtro embutido sao complementares ou
fundiveis.

O criterio, quando a hora chegar: **uma flag so' entra com caminho otimizado atras dela**.

## O que fica para `.9` ou lab

O contrato esta' fechado. Restam somente caminhos de execucao ou conveniencias opcionais:

1. fundir filtro e agregacao numa passada (`H-QUERY-04e`);
2. ler apenas as posicoes filtradas da coluna agregada (`H-QUERY-04f/h`);
3. avaliar flag apenas quando ela tiver rota otimizada propria;
4. estudar ordenacao de resultado e modo numerico tolerante se houver caso de uso. O
  default continua ordem de aparicao e fail-loud.

## Criterio de aceite

- [x] Linha 1 (nulo na chave) confirmada: forma grupo, sem flag. Razao escrita acima.
- [x] Linhas 3 e 4 (grupo sem valor) confirmadas: `sum` da' 0.0 por matematica,
      `min`/`max`/`avg` dao `None` porque nao ha' resposta. Razao escrita acima.
- [x] Linha 2 (string vazia) confirmada: forma grupo e conta como elemento presente.
- [x] Linha 5 (ordem das chaves) confirmada: aparicao, deterministica e sem ordenacao extra.
- [x] Valor nao-numerico confirmado como erro fail-loud; modo tolerante nao e' default.
- [x] O que divergir do mercado fica documentado como divergencia deliberada, nao como
      omissao.
- [x] Sem re-pin de gate byte-canonico (a rota e' read-only).

## Levantamento

`experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0100-grouping-semantica/`: 12 questoes
medidas uma a uma, mais 3159 agregacoes de diversidade conferidas contra a mesma conta
feita em Python puro.
