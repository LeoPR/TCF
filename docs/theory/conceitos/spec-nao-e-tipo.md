---
title: "Spec não é tipo: o que uma nature faz, e por que o decode não precisa dela"
type: explanation
parent: conceitos
subsystem: conceitos
---

# Spec não é tipo

Uma *nature* (ou *spec*) parece um tipo e não é. Confundir os dois leva a esperar coisas que
o TCF não faz, e a estranhar coisas que ele faz. Esta página separa os dois.

## O que ela é

Uma spec é um **filtro semântico**: ela remove do valor a parte que é **derivável**, guarda
o resto, e reconstrói o original no `decode`. O que entra e o que sai é sempre `str`.

```python
from tcf import encode, decode, SPEC_CPF

cpfs = ["111.444.777-35", "529.982.247-25", "111.444.777-35"]

encode(cpfs)                    # 42 B: '#TCF.8!!\n111.444.777-35\n529.982.247-25\n^1\n'
encode(cpfs, schema=SPEC_CPF)   # 29 B: '#TCF.8 :cpf\n%gc\\9g\n\\2y/h-\n^1\n'
```

Um CPF tem 11 dígitos, e os 2 últimos são **calculáveis** a partir dos 9 primeiros. A
pontuação é fixa. Então a spec guarda 9 dígitos num número curto e joga fora o que sabe
refazer: a pontuação e os dígitos verificadores.

## O que ela não é

**Não é um tipo Python.** O que volta do `decode` é `str`, sempre, com ou sem spec. A spec
não faz `int`, não faz `date`, não valida no sentido de recusar entrada. Ela só sabe
reescrever de um jeito menor o que ela reconhece.

**Não muda o que o dado significa.** O round-trip é exato: `decode(encode(x)) == x`. Se a
reconstrução não fosse exata, a spec não entraria.

## Por que o `decode` não precisa receber a spec

Porque o cabeçalho a registra:

```python
encode(cpfs, schema=SPEC_CPF)
'#TCF.8 :cpf\n...'
#        ^^^^ o header diz qual filtro foi usado

decode(blob) == cpfs      # True, sem passar nada
```

Esse `:cpf` é o que torna o wire **auto-descritivo**: quem recebe o blob não precisa saber
nada além do blob. Para uma spec **customizada**, sua e não registrada no pacote, o `decode`
precisa receber um filtro com o mesmo nome, porque o nome sozinho não diz o que fazer.

## Ela é candidata, não ordem

Este é o ponto que mais surpreende: **passar uma spec não garante que ela será usada**.

O encoder compara o **blob serializado completo**, com cabeçalho, tamanhos e o identificador
do filtro, contra a codificação comum da mesma coluna. Se a versão filtrada não ficar menor,
a coluna original permanece e **nenhum `:id` é emitido**. Você pediu, e o encoder mediu.

A consequência prática é que a spec pode não aparecer no wire, e isso não é falha: é o
encoder recusando pagar por ela. Quando ela ganha, ganha inclusive num único valor:

```python
encode(["111.444.777-35"])                    # 24 B, sem spec
encode(["111.444.777-35"], schema=SPEC_CPF)   # 19 B, e o header traz `:cpf`
```

## A leitura que fica

Um tipo diz **o que o valor é**. Uma spec diz **o que dá para não guardar**. O TCF não tem a
primeira coisa, e a segunda é opt-in, medida, e registrada no próprio wire.

## Onde continuar

- a receita: [`docs/how-to/use-natures.md`](../../how-to/use-natures.md)
- a decisão de projeto: [ADR-0015](../../adr/0015-natures-templated-checked-weld.md)
- a direção de para onde as specs vão:
  [spec orienta, não manda](../tipos-e-naturezas/spec-orienta-nao-manda-triagem.md)
