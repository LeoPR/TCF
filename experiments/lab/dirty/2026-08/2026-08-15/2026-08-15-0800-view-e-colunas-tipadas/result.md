# Resultado — o `view` não alcança coluna tipada, e o motivo não está no `view`

10 formas de wire × 1 tabela realista (5000 × 5) × 3 variantes, **0 falhas** de RT.
Orienta, não fecha.

---

## O resumo em uma linha

**O `view` abre 2 de 10 formas — só as `.8M`.** Qualquer coluna tipada manda a tabela para
`.8H`, e `.8H` é 100% fechado ao `view`. Então *"view para colunas tipadas"* **não é uma
lacuna do `view`**: é consequência do dispatch, um nível acima. E o preço dessa consequência é
**+101,7% de bytes** e **5,3× de tempo** para a mesma pergunta.

---

## 1. O que o `view` abre

| forma | rota | `view` |
|---|---|:--:|
| MULTI `.8M` (todo string) | multi `.8M` | **ABRE** |
| MULTI `.8M` + spec `:dt` | multi `.8M` | **ABRE** |
| single string (bN/OBAT) | single | recusa |
| single + spec `:dt` | single | recusa |
| tipado `n` (int) · `n` (float) · `b` (bool) · `nB` (denso) | single | recusa |
| stamp / vazio | single | recusa |
| HIER `.8H` | hier `.8H` | recusa |

**2 de 10**, e as duas são `.8M`. A mensagem é a mesma para as oito: *"não é `#TCF.8M`
multi-col"* (`view.py:68`).

O lado **single-col** já está mapeado e prototipado no `T-LAZY-BYPASS-ARITMETICO`
(*"single-col no view é DISPATCH-ONLY, ~20-25 linhas"*, com RT/where/sum rodando inclusive em
wire pulsado). **O lado `.8H` nunca foi medido — e é ele que este lab fecha.**

---

## 2. A fronteira: onde a tabela deixa de ser `.8M`

`_tabela_flat` (`encoder.py:134-147`) termina em:

```python
return all(isinstance(x, str) for v in vals for x in v)
```

**Um único valor não-`str` em qualquer coluna manda a tabela inteira para o `.8H`** — e a
própria docstring registra que é deliberado: *"dict com valor escalar/aninhado, colunas tipadas
ou ragged → .8H. Precedência flat (parecer 2340 §2)"*.

Medido na mesma tabela de 5000 × 5:

| variante | rota | bytes | vs `.8M` | `view` |
|---|---|---:|---:|:--:|
| todo string (dict) | multi `.8M` | 76.803 | — | **ABRE** |
| todo string (list[dict]) | hier `.8H` | 154.937 | **+101,7%** | recusa |
| **2 colunas tipadas** | hier `.8H` | 154.521 | **+101,2%** | recusa |

---

## 3. O par de contra-prova: o custo é o ENVELOPE, não a tipagem

Esta era a predição que podia virar a conclusão, e por isso foi declarada antes de rodar. A
constante é dura: **os mesmos valores nas três variantes** — muda só a forma de chamada e o
tipo Python.

| o que muda | delta |
|---|---:|
| forçar `.8H` **sem tipar nada** | **+78.134 B** ← o envelope |
| tipar 2 colunas **dentro do `.8H`** | **−416 B** ← a tipagem |

**Tipar é de graça — é até levemente melhor.** O que custa +101,7% é o envelope hierárquico
aplicado a uma tabela que é retangular.

Isso muda quem é o culpado. A frase intuitiva *"tipar dobra o tamanho"* está **errada**: o que
dobra é **atravessar o `.8H`**, e tipar é apenas o gatilho que empurra para lá.

---

## 4. O que a tabela tipada perde

O `view` sobre `.8M`, respondendo *"quantas linhas com `data >= 2020`"* (verdade: 2675):

- toca **uma** coluna (`['data']`) e materializa **19,9%** do blob;
- `select` de uma coluna: **16,2%** do blob;
- `column_bytes()` dá o perfil por coluna **tocando `[]`** — perfila sem descomprimir nada.

| rota | tempo | razão |
|---|---:|---:|
| `view` sobre `.8M` | 18,7 ms | — |
| decode completo `.8M` | 32,8 ms | 1,8× |
| **decode completo `.8H`** | **99,4 ms** | **5,3×** ← única opção se a tabela é tipada |

Dev-run declarado: **razões, não absolutos**.

Então a tabela tipada paga **duas vezes**: o dobro de bytes no wire, e a perda do acesso
parcial — para qualquer pergunta ela materializa 100%.

---

## 5. Achado colateral: uma armadilha de API no `where()`

Assinatura: `where(col, value=None, *, pred=None)`. Passar o predicado **posicionalmente** é
sintaticamente válido, e produz **resposta errada sem erro nenhum**:

| chamada | resultado |
|---|---:|
| verdade (`decode`) | **2675** |
| `where('data', lambda x: x >= '2020-01-01')` | **0** ← calado |
| `where('data', pred=lambda x: x >= '2020-01-01')` | 2675 |

Mecanismo: o `lambda` entra como `value` e cai no ramo `v == value`; uma string nunca é igual a
uma função, então o filtro casa zero linhas e devolve um `Filtered` vazio. O predicado **nunca
é chamado** (verificado: acumulador vazio, n=0).

É a **mesma família** do `T-NATURE-IGNORADA-CALADA` — a API aceita algo, não faz o que o
chamador pediu, e não avisa. E aqui é pior que lá: naquele o wire sai certo e só a expectativa
quebra; **aqui a resposta da consulta é errada**. Um `raise` de uma linha (`callable` em
`value` → `TypeError` explicando que é `pred=`) fecha.

Este lab caiu nela sozinho, o que é o argumento: se eu caí escrevendo o lab do próprio `view`,
o usuário cai.

---

## 6. Ressalvas honestas

- **Uma tabela, sintética.** Retangular, sem nulls, 5 colunas, 5000 linhas. Os +101,7% do
  envelope são desta forma; tabela com aninhamento real usaria o `.8H` por necessidade, e aí
  não haveria comparação a fazer.
- **`.8M` só existe para tabela retangular.** A comparação é justa exatamente onde a tabela
  cabe nas duas rotas — que é o caso deste lab e o caso comum de dado tabular.
- **Não medi o `.8H` com aninhamento**, onde o envelope se paga.
- **Nada aqui é proposta de weld.** `src/tcf` intocado.

---

## 7. O que isto orienta

1. **A pergunta do owner (*"view para colunas tipadas"*) tem resposta estrutural**: não é
   trabalho no `view`, é decidir se tabela retangular tipada deve continuar indo para o `.8H`.
   As duas saídas possíveis:
   - **(a)** dar gramática de tipo ao `.8M` e rotear tabela retangular tipada para lá — o
     `view` passa a alcançá-la **sem nenhuma mudança no `view`**;
   - **(b)** ensinar o `view` a ler `.8H` — resolve o acesso, **não** resolve os +101,7%.
   A **(a)** resolve os dois; a **(b)** resolve um. E a (a) é o mesmo movimento que o
   `T-UM-CAMINHO-SO` já nomeia.
2. **O número que decide não é o do `view`, é o do envelope**: +101,7% em tabela retangular.
   Se ele cair, a pergunta do `view` fica muito menor.
3. **A armadilha do `where()` é barata e independente** — fecha sozinha, não espera decisão
   nenhuma, e hoje devolve resposta errada calada.
4. **O lado single-col do `view` continua o que já estava escrito** (`T-LAZY-BYPASS-ARITMETICO`:
   dispatch-only, ~20-25 linhas). Este lab não o toca — só confirma que as 7 formas single-col
   seguem fechadas.
