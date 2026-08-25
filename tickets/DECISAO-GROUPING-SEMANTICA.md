---
title: "DECISAO-GROUPING-SEMANTICA: onde o agrupamento do TCF diverge de SQL, pandas e polars"
status: open
priority: P3
severity: R4 (nao ha' erro; ha' escolhas a confirmar antes do 1.0)
created: 2026-08-25
updated: 2026-08-25
gate: decisao do dono do projeto. A funcionalidade esta' fechada e testada; o que falta e' confirmar as escolhas.
blocked-by: []
related:
  - src/tcf/view.py
  - docs/reference/view-usos.md
---

# DECISAO-GROUPING-SEMANTICA

Agrupar tem decisoes que nao tem resposta unica no mercado, e cada ferramenta escolheu
diferente. O TCF ja' responde alguma coisa em todas elas, e o que esta' escrito abaixo e'
o que ele responde HOJE, medido, nao o que se pretende.

Diretriz do dono do projeto (2026-08-25):

> *"os outros manipuladores de dados ate' mesmo o numpy, pandas e polars, sql e afins
> servem como orientacao para as respostas, mas o tcf pode ter um comportamento
> documentado diferente em ultimo caso. apenas precisamos levantar e decidir depois."*

## A matriz

| questao | SQL | pandas | polars | **TCF hoje** |
|---|---|---|---|---|
| nulo na chave forma grupo? | sim | **nao** (`dropna=True`) | sim | **sim, DECIDIDO** |
| string vazia forma grupo? | sim | sim | sim | **sim** |
| grupo sem valor: `sum` | `NULL` | `0` | `null` | **`0.0`** |
| grupo sem valor: `min`/`max`/`avg` | `NULL` | `NaN` | `null` | **`None`** |
| ordem das chaves no resultado | indefinida | ordenada | aparicao | **aparicao** |
| valor nao-numerico na soma | erro | erro ou `NaN` | erro | **levanta `ValueError`** |
| chave sai em que tipo | o da coluna | o da coluna | o da coluna | **o da coluna** |

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

## O que fica em aberto

1. **`sum` de grupo vazio: `0.0` ou `None`?** Hoje `0.0` (pandas). O SQL daria `NULL`.
   O argumento a favor do `None` e' a coerencia com `min`/`max`/`avg`, que ja' devolvem
   `None`; o argumento contra e' que a soma vazia tem resposta e ela e' zero.
2. **Ordem: manter aparicao, ou oferecer ordenada?** Nenhuma consulta hoje pede ordem.
   Se o `.9` trouxer `sort_by` de resultado, isto vira parametro em vez de escolha fixa.
3. **Valor nao-numerico: levantar ou pular?** Hoje levanta, coerente com `sum()`. Um modo
   tolerante (pular o que nao converte, como o `errors='coerce'` do pandas) seria util em
   dado sujo, mas mudaria o contrato de "nao silenciar dado sujo" que o projeto adotou.

## Criterio de aceite

- [x] Linha 1 (nulo na chave) confirmada: forma grupo, sem flag. Razao escrita acima.
- [ ] As demais linhas da matriz confirmadas ou alteradas, com a razao escrita.
- [ ] O que divergir do mercado fica documentado como divergencia deliberada, nao como
      omissao.
- [ ] Sem re-pin de gate byte-canonico (a rota e' read-only).

## Levantamento

`experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0100-grouping-semantica/`: 12 questoes
medidas uma a uma, mais 3159 agregacoes de diversidade conferidas contra a mesma conta
feita em Python puro.
