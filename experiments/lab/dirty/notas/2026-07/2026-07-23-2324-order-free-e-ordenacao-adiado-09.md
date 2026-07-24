# Order-free e ordenação — ADIADO pro `.9` [nota / direção registrada]

**Data**: 2026-07-23 23:24. Direção do owner: *"vamos deixar o order de lado por enquanto e deixar
talvez pro `.9`"*. Registrado aqui pra não se perder — o prêmio é grande, mas o caminho é caro.

## Por que vale a pena (evidência JÁ medida)

O reality-check ([lab `1832`](../../2026-07/2026-07-23/2026-07-23-1832-reality-check-lowcard-dados-reais/))
mediu o efeito de ordenar colunas REAIS de adult-census: `mean_run` sai de ~1–5 (ruído) para 625–5000
(runs), e o RLE passa a esmagar:

| coluna | como está | ordenada |
|---|---:|---:|
| education | 6.668 B | **102 B** (65×) |
| occupation | 6.668 B | 97 B |
| workclass | 6.668 B | 50 B |

Comparação de escala: o bN-dense (estudado o dia todo) dá **1,86×** na tabela real. Ordenar dá **65×**
numa coluna. **É a maior alavanca que encontramos** — e ela não é um algoritmo, é uma *permissão
semântica*.

## São DUAS coisas distintas (não confundir)

**(1) Ordenar POR uma coluna** — reordena TODAS as linhas juntas (preserva a correspondência de
registro). O ganho depende de QUAL coluna se escolhe como chave. O problema: descobrir a melhor exige
**ordenar e re-encodar muitas vezes** para comparar — custo combinatório proibitivo. Uma estratégia de
força bruta está fora de questão; precisaria de heurística/predição. **Isso é o caro.**

**(2) Declaração `order_free` do dev** — o dev indica que o dataset **não precisa de ordem definida**;
o TCF ganha liberdade de ordenar. **Isso é o barato** — não precisa adivinhar nada, só obedecer uma
permissão. É a parte que pode entrar primeiro.

## Os três custos que ainda precisam de estudo (por isso adia)

1. **CPU/memória da própria ordenação** — sort não é grátis; entra no fluxo mas pesa. Precisa ser
   medido nos vetores do projeto (não só bytes).
2. **O problema "premonitório"** — como saber se vale a pena **antes de olhar o dado**? Decidir depois
   de medir é o que custa caro (item 1 acima). Predizer é complexo e é o cerne do problema.
3. **Contrato de RT** — `order_free` muda a igualdade de RT para **multiconjunto** (não identidade, e
   NÃO conjunto: duplicatas preservadas). Há precedente no projeto (`rt_mode = identidade |
   idempotência-2ª-geração` para transforms declarados como `sort_by`), então é extensão de disciplina
   existente, não invenção. Exige também **permutação canônica** declarada (critério de canonicidade:
   um dataset + uma config → uma única grafia).

## Princípio que fica fixado

**A liberdade de ordem é propriedade do SIGNIFICADO, não do TIPO.** Uma coluna bool `is_active` por
usuário é rigidamente ordenada (cada posição é uma pessoa); uma lista bool solta é um saco de flags.
Mesmo tipo, contratos opostos. ⇒ **não é inferível — tem que ser declaração explícita do dev.**
**Default: preservar a ordem** (ordem-livre é informação que o dev DESCARTA; nunca presumir descarte).

## Estado

**ADIADO pro `.9`.** Não entra no Ciclo A (cabeçalho) — senão faríamos moldura e representação ao mesmo
tempo, que é justamente o que o owner pediu para evitar. Retomar junto com a discussão de custo
CPU/memória e do preditor.

Relaciona: [plano de revisão `.8`](../2026-06/tcf8-estrutura-plano.md) §4 (eixo `ordem`) ·
[reality-check `1832`](../../2026-07/2026-07-23/2026-07-23-1832-reality-check-lowcard-dados-reais/) ·
[convenções do dirty lab](dirty-lab-convencoes.md) (`rt_mode`).
