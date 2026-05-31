# Range de indices — nota para futuro

Data: 2026-05-12
Origem: observacao do user durante M1.A.
Status: ideia anotada, **nao implementar antes de M1.B/C/D**.

## Observacao

Hoje refs em sequencia sao expressas como `1,2,3,4,5` — idx
separados por virgula. Em sequencias longas, essa notacao gasta
muitos bytes.

A virgula tem **dupla funcao no macro M1**:
1. Separador entre refs adjacentes (`1,2,3`)
2. Pode aparecer em literais (potencialmente — mas no contexto
   em que esta hoje, no meio de literal nao causa ambiguidade)

Uma otimizacao **independente** da escolha entre M1.A/B/C/D
seria: agrupar idx contiguos com sintaxe de range.

## Proposta

Sintaxe candidata: `[1-5]` para indicar idx 1, 2, 3, 4, 5 em
sequencia contigua. Ou `1..5`, `1~5`, etc.

Custo:
- Virgula tradicional: `1,2,3,4,5` = 9 chars
- Range: `[1-5]` = 5 chars (-44%)

Vale se range >= 3 idx contiguos.

## Quando ocorre range contiguo

Idx contiguos so' acontecem quando **um nó tem fragmentos
sequenciais** que sao todos referenciados em ordem por outra
string. Exemplo classico:

- s1 = "abcdefghij" (sem quebras internas)
- s2 referencia s1 inteira via slice [0:10]

Nesse caso, o fragmento unico de s1 recebe 1 idx — sem range.

Range emerge quando:
- s1 tem varios fragmentos (idx 1..N) devido a multiplas refs
  parciais
- s2 (ou outro) referencia uma sequencia contigua desses
  fragmentos

Exemplo concreto em D1-emails-simples (lookback no TCF do
M1.A):

```
pedr2,3,4,5,6
```

Refs `2,3,4,5,6` = 5 idx contiguos. Com range: `pedr[2-6]` (-3
chars).

## Onde poderia se aplicar

Olhando o TCF do M1.A:

| Dataset | Quantos ranges contiguos >=3? |
|---|---|
| D1-emails-simples | varias linhas com 5 contiguos |
| D2-emails-quote-id | algumas com 3-5 |
| D3-stress-substring | varias com 5-7 |
| D4-caos-mix | algumas com 3-5 |

Pode dar economia agregada significativa (talvez 10-30 bytes
por dataset).

## Conflito com escape

A sintaxe `[1-5]` usa `[` e `]` — que ja sao macros body. Mas
no meio de uma linha, `[` nao e' macro. Sem conflito real, igual
ao caso de `[` em literal de D4 (caos-mix). Parser distingue
pelo contexto (linha inteira `[` vs `[` no meio).

A sintaxe `1..5` evita `[`/`]` mas usa `.` que pode aparecer em
literais (emails, dominios).

A sintaxe `1~5` usa `~` — geralmente nao aparece em dados, mas
pode-se quebrar.

## Quando avaliar

Apos M1.A/B/C/D estarem implementados. Range e' **otimizacao
ortogonal** as 4 tecnicas. Pode ser aplicada em cima de
qualquer uma como **M1.E** (refinamento de refs) sem mexer na
estrategia de marcacao do literal.

## Decisao agora

Anotar e seguir. Nao desviar do plano M1 — implementar M1.B
agora.
