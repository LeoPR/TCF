# Fechar TODOS os tipos no `.8` — o critério é padronização, não ganho

**2026-08-14** · correção do owner:

> *"a gente ainda vai ter que ver os tipos datetime, time e float ainda no .8 pra fechar,
> mesmo que alguns sintéticos, OK? acho que seria interessante fechar todos os tipos primeiro
> até pra ver se o fluxo de spec está padronizado e cada um tem suas peculiaridades
> declaradas, quanto mais coisa em comum melhor."*

---

## O erro que eu repeti

Recomendei **float para o `.9`** (8% agregado não paga) e **hora para o fim** (1,03% no real).
Os dois por **ROI de bytes**. É a mesma classe de erro que o owner já corrigira em 2026-08-14
(*"você pensa muito em compressão, eu penso em fluxo que funciona"*) — e o critério do `.8`
já estava escrito no enunciado dele: *"funcionalidades, specs, e que tudo ao menos construa
corretamente e de forma minimalista"*.

**Um tipo não fecha porque compensa; fecha porque foi verificado.** Um tipo com ganho de 1,03×
e peculiaridades declaradas está *fechado*; um com 2× e comportamento não caracterizado, não.

## O que "fechar um tipo" significa sob o critério certo

Nada disso é sobre bytes:

| eixo | pergunta |
|---|---|
| **dispatch** | o tipo é reconhecido, e por uma linha no lugar único? |
| **candidatos** | percorre o mesmo `min()` que os outros, ou tem caminho próprio? |
| **API** | `nature=` / `min_len=` são aceitos, recusados ou silenciosos? |
| **wire** | tem tag? convive com `:id`? o header é auto-contido? |
| **RT** | volta com o tipo certo, comparado por `type()`? |
| **peculiaridades** | o que este tipo tem de **irredutivelmente diferente** — declarado |
| **comunidade** | o que ele compartilha com os outros — maximizado |

## Onde cada tipo está, por esse critério

| tipo | natureza | dispatch | candidatos | API | wire | RT | peculiaridades declaradas | estado |
|---|---|---|---|---|---|---|---|---|
| **bool** | nativo | ✓ | ✓ +denso | ✓ | `b` | ✓ | domínio implícito (por isso o denso vence sempre) | **fechado** |
| **str** | nativo | ✓ | ✓ | ✓ | *(vazio)* | ✓ | é o default; sem tag | **fechado** |
| **int** | nativo | ✓ | ✓ +PAD | ✓ (aberta hoje) | `n` + `:ipad` | ✓ | largura variável quebra o marcador | **fechado hoje** |
| **data** | semântico | — | ✓ via spec | ✓ | `:dt` | ✓ | ordinal **absoluto**; guard de canonicidade | **fechado** |
| **float** | nativo | ✓ | ✓ | ✓ | `n` | ✓ | **precisão suja quebra a escala**; `IntPadSpec` não serve | **falta declarar** |
| **hora** | semântico | — | — | — | — | — | **cíclica** (volta a zero); só monotônica dentro do dia | **falta** |
| **datetime** | semântico | — | — | — | — | — | composto (data+hora); o **split** dá 7,13× | **falta** |

Os três que faltam já têm as **peculiaridades medidas** — o que falta é a caracterização
completa nos outros eixos, e o registro formal.

## A peculiaridade estrutural que só apareceu agora

Há **duas famílias de spec**, e o owner pediu exatamente para verificar se elas seguem o
mesmo fluxo:

| família | sobre o quê | wire | exemplo |
|---|---|---|---|
| spec sobre **tipo nativo** | `int`, `float`, `bool` | `#TCF.8n :ipad` — tag **e** id | `IntPadSpec` (soldado hoje) |
| spec sobre **string** | grafias: data, hora, CPF, IP | `#TCF.8 :dt` — só id | `data-iso`, `cpf`, `cnpj`, `ip` |

Até hoje só existia a segunda. O weld do `IntPadSpec` criou a primeira — e é justamente por
isso que vale fechar float/hora/datetime **agora**: eles se distribuem entre as duas famílias
(float é nativo; hora e datetime são grafias), e é o teste real de se o fluxo é um só.

## Plano de fechamento (o que falta, por tipo)

**float** — o mais perto. Já medido (30 colunas reais, 8% agregado, escala vence em 8/12).
Falta: rodar a matriz de conformidade nos 5 eixos (ele entrou no lab de conformidade e passou
em todos), e **declarar as peculiaridades** — a precisão suja que quebra a escala, e o fato de
o `IntPadSpec` não ser reaproveitável. Sem weld: o `.8` fecha com o comportamento
caracterizado e o spec adiado com razão escrita.

**hora** — já medido (1,03× real; 2× a 9× em regimes regulares; ciclicidade caracterizada).
Falta: os **sintéticos** que o owner pediu (campos de hora existem, ainda que não neste
corpus) e a passagem pelos 5 eixos.

**datetime** — o menos avaliado, e o de maior retorno estrutural (o split dá **7,13×**).
Falta tudo: caracterizar, decidir se é spec próprio ou composição (data + hora), e declarar a
peculiaridade de ser **composto** — o único tipo cuja melhor resposta hoje não é um spec, e
sim o split.

## O que isso muda na fila

A fila deixa de ser ordenada por ganho e passa a ser ordenada por **fechamento**:

1. **float** — completar a caracterização (mais perto de fechar)
2. **hora** — sintéticos + os 5 eixos
3. **datetime** — caracterizar do zero; é onde a peculiaridade "composto" mora
4. só então: `T-SPLIT-SINGLE-COL` e o resto

E o produto final do `.8` para tipos não é ganho agregado — é **uma tabela onde cada tipo tem
suas peculiaridades declaradas e o máximo de fluxo em comum**, que é literalmente o que o
owner pediu.
