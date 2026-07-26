---
title: min_len — há ganho dinâmico, mas o custo é serialização/buferização
type: nota
status: aberta
created: 2026-07-26
related:
  - src/tcf/auto_min_len.py (detect_min_len_from_features)
  - src/tcf/core/online.py (OBAT — tokenizador ONLINE)
  - experiments/lab/dirty/2026-07/2026-07-26/2026-07-26-0038-delimitador-do-flip-opcoes/
---

# min_len — ganho dinâmico existe; o custo é o problema

Achado do owner olhando `com-delim-wire-normal.tcf`: *"o `a;b`, apesar de ser separado como
referência, não foi usado nos outros?"*

## A causa

`min_len = 4` (auto-detectado nessa coluna). O OBAT só extrai afixo compartilhado com **pelo
menos `min_len` caracteres**. O prefixo `a;b` tem 3 e o sufixo `;c` tem 2 — os dois ficam
abaixo do limiar, nunca viram átomo compartilhado, e cada linha reescreve o prefixo inteiro.

**Não é bug.** O limiar existe para que um fragmento minúsculo não custe mais em referência do
que economiza em literal. Nesta coluna ele errou o alvo.

```
min_len=4 (auto)   3708 B    2ª linha: a;b*\6*\4*\2;c    ← reescreve o prefixo
min_len=3          3396 B    2ª linha: 1\6*\4*\2;c       ← `1` = referência ao a;b
```

**−312 B (−8,4%)** só baixando o limiar de 4 para 3.

## Quanto está na mesa — e onde

| corpus | deixa na mesa |
|---|---:|
| 10 formas sintéticas de afixo curto | **+1426 B** (versão +359, moeda +358, com-delim +312) |
| **D1-D9 (gate)** | **+30 B** |
| **real-world (adult, beijing, empresas, pessoas)** | **+54 B** |

A heurística está **bem calibrada para o corpus real do projeto** — o que faz sentido, já que
foi ajustada nele. Quem sofre é coluna com **afixo compartilhado curto (2–3 chars)**, que é
justamente o que as formas sintéticas têm em excesso porque foram construídas para exercitar
caracteres, não para representar uso real.

> Ou seja: **o ganho é real mas ainda não demonstrado em dado realista.** Antes de mexer,
> valeria achar um dataset real com afixo curto — CEP, sigla+número, código de produto curto.

## O custo, que é a pergunta do owner

**Varrer candidatos custa ~5×** (medido, mediana de 5 execuções):

| n | auto | varrendo 7 candidatos | |
|---:|---:|---:|---|
| 500 | 172 ms | 887 ms | **5,2×** |
| 5000 | 867 ms | 4372 ms | **5,0×** |

E há um problema **estrutural** além do CPU, que é o que a intuição do owner sobre
"serialização e buferização" aponta:

**O OBAT é um tokenizador ONLINE** — o primeiro valor semeia o vocabulário, e o `min_len` é
parâmetro de entrada dele. Isso significa que um `min_len` "dinâmico", que se ajustasse no
meio da coluna, **mudaria retroativamente a tokenização do que já passou**. As saídas são:

1. **buferizar a coluna inteira** antes de tokenizar, para decidir o limiar com a coluna toda
   à vista — mata o streaming;
2. **re-tokenizar** quando a estimativa mudar — paga o custo N vezes, que é a varredura acima
   com outro nome;
3. **preditor melhor** a partir das features do pré-pass (que já são computadas) — mantém uma
   passada só, mas é heurística sobre heurística, com risco de regressão nos gates.

A (3) é a única que não muda o modelo de execução. As (1) e (2) só cabem sob um perfil que
aceite pagar — o que remete a [[H-PROFILE-01]] (perfil API/transmissão × armazenamento).

## Estado

**Anotado, nada soldado.** Não é a mesma correção barata do FLOOR do seq-RLE: lá era um
pós-processo com 2 candidatos já materializados; aqui são 7 execuções do **pipeline inteiro**
(pré-pass + OBAT + HCC).

Pendências, em ordem:

1. achar **dado real** com afixo curto — sem isso o ganho é sintético
2. medir se o preditor (3) alcança o ótimo sem varrer, usando as features já existentes
3. só então decidir se vira parâmetro, perfil ou nada
