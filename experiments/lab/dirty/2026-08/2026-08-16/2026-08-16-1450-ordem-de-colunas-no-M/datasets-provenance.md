# Procedência — o mesmo cadastro do lab 1400, e o wire adversarial

## O dado

**Importado** de `../2026-08-16-1400-cadastro-popular-header-do-M/run.py::cadastro()` —
os MESMOS 500 registros, mesma seed (20260815). Precedente de import entre labs: `0530`←`0400`.

**A CONSTANTE**: os valores nunca mudam neste lab. Muda só a ORDEM das colunas (Bloco 1), a
presença de nomes (Bloco 2) e a grafia dos nomes (Bloco 3). Qualquer delta de byte é
atribuível à variável única.

## O wire adversarial (Bloco 3b)

`inputs/colisao-anonima-vs-0.wire-de-entrada.tcf` é **escrito à mão** (fluxo invertido — lab
de decoder): 3 colunas raw de 3 valores, a primeira anônima e a segunda nomeada `"0"`. O
encode não produz essa forma; a pergunta é o que o DECODE faz com ela.

## Vieses declarados

- **Permutações amostradas, não exaustivas**: 5 de 7! = 5040 (canônica, reversa, alfabética,
  por tamanho, rotação) + as 7 escolhas de última. Os corpos são independentes por construção
  (`core.py:417-418`), então a amostra cobre o mecanismo; não cobre interações que não
  existem no código.
- **Os 3 B de teto da "última coluna" são deste dado** — dependem do size em hex de cada
  coluna. Tabela com colunas maiores tem teto maior (até `len(hex)+1` da maior).
- **O custo de 1,9 B/coluna dos nomes numéricos** é com índices de 1 dígito (≤10 colunas);
  passa a 2,9 B/coluna da 11ª em diante.
