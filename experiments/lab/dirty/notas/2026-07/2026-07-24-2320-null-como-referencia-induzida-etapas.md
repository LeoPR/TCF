---
title: null no fluxo GERAL explícito→implícito (não é caso particular)
type: analise
status: aberta
created: 2026-07-24
related:
  - experiments/lab/dirty/notas/2026-07/2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md
  - experiments/lab/dirty/2026-07/2026-07-24/2026-07-24-2210-null-indice0-coluna-string/
  - experiments/lab/dirty/notas/2026-07/2026-07-24-2140-levantamento-null-e-tipos.md
  - experiments/lab/dirty/notas/2026-07/substituicao-indices-especiais-plano.md
---

# null no fluxo geral explícito→implícito

Correção de enquadramento (owner, 2026-07-24):

> *"Não precisa registrar o null num fluxo personalíssimo. TODOS os processos passam pelo
> fluxo de explícito depois a camada implícita — não é apenas o header, as outras também. Não
> tem novidade. O null só parece mais especial porque parece um coringa conceitual, mas para o
> TCF é mais um tipo com tratamentos."*

Está certo, e a nota anterior desta mesma data enquadrava mal (descrevia um plano em etapas
*para o null*, como se fosse um pipeline próprio). Reescrita.

---

## 1. O fluxo é UM só, e já está em produção

Todo mecanismo do formato tem a mesma forma: uma **grafia explícita canônica** (o valor
escrito por extenso) e uma ou mais **substituições implícitas** que expandem de volta para
ela. O core nunca muda; quem traduz é o pré-avaliador.

Verificado contra o `src/tcf` real — a forma explícita de cada mecanismo decodifica para
**exatamente** os mesmos valores que a forma otimizada que o encoder emite:

| mecanismo | forma EXPLÍCITA | forma IMPLÍCITA (emitida) | o que deduz |
|---|---|---|---|
| repetição adjacente | `x⏎x⏎x` | `*3\|x` | contador |
| repetição não-adjacente | `ab⏎cd⏎ab` | `ab⏎cd⏎^1` | ref de **linha** |
| prefixo/sufixo comum | `pedido-\1⏎pedido-\2` | `pedido-*\1⏎1\2` | ref de **fragmento** |
| tipo bool | `#TCF.8b` + `true`/`false` | `#TCF.8b1<n>` + bits | dicionário da **versão** |
| modo (o `~`) | variável `modo` | posição (índice 7) | posicional |
| contagem `n` do denso | decimal | hex | radix |
| cabeçalho | `#TCF.8` (default) | órfão = **escape** explícito | ADR-0034 |

Todas as linhas da coluna "explícita" foram decodificadas e conferidas: **5/5 idênticas** à
saída da forma otimizada. Não é teoria — é o comportamento atual.

## 2. Onde o null entra (e por que não é coringa)

A tabela de referências tem **duas metades**:

- **slots altos** — vêm do **DADO**: literais descobertos no encode desta coluna
- **slots baixos** — vêm do **FORMATO**: o dicionário da versão, que não viaja no arquivo

Essa segunda metade **já existe e já está soldada**: é exatamente o que o modo denso do bool
usa. O domínio `{false, true}` não está no wire — vem da versão do formato, e o corpo carrega
só os índices. Foi o weld #4b.

**null é outra entrada da mesma metade.** Não é um tipo com regra própria: é um valor cuja
grafia literal não existe numa coluna de string, então ele mora no dicionário do formato em
vez do dicionário do dado — igual a `true`/`false` no denso.

Isso responde a pergunta "o quanto ele segue o fluxo normal": **segue inteiro**. A única
assimetria real, e vale nomear:

> Para qualquer outro valor a escada começa em "escreva o literal". null não tem literal numa
> coluna de string — é por isso que ele começa a escada já como referência. Não é privilégio:
> é a consequência de não ter grafia própria, a mesma de `true`/`false` no modo denso.

## 3. A escada, que é a mesma de todo mundo

| degrau | grafia | quem já usa isso |
|---|---|---|
| valor por extenso | *(não existe p/ null)* | literais |
| referência a nó existente | `^N` | repetição não-adjacente |
| referência a slot do formato | `^0` | **novo p/ null**; conceito = bool denso |
| grafia otimizada | `0` | mesma classe do `~` (posicional) |

Cada degrau é o mecanismo que já existe, aplicado a mais um valor. Nenhum degrau é exclusivo
do null.

## 4. Evidência: seguir o fluxo normal não custa código

Se null é "mais um valor no sistema de referências", implementá-lo não deveria adicionar
tratamento. Testei no `src/tcf` real (experimento **aplicado e revertido**).

O decode hoje faz `nos_decl[idx - 1]`. Esse `- 1` existe só para compensar a lista começar
vazia enquanto o wire conta a partir de 1. Pré-semeando o slot reservado, a compensação some:

```python
nos_decl = []                  ->   nos_decl = [NULO]
s_no = nos_decl[idx - 1]       ->   s_no = nos_decl[idx]
```

| | resultado |
|---|---|
| diff | **5 inserções, 3 remoções**, 1 arquivo |
| suíte | **915 passed**, 1 failed |
| gates byte-canônicos | passam (D1-D9, D17a, real-world) |
| única falha | `test_ref_zero_nao_e_aceite_silencioso` — o teste que fixa "`^0` é inválido" |

`^1` segue apontando para o primeiro nó declarado; `^0` vira o slot do formato; fora de faixa
segue fail-loud. **Nenhum ramo novo, nenhum `if null`.** O encode não muda (o `eid` já é
1-based, então indexa certo na tabela pré-semeada).

A única falha é o teste que pina exatamente a regra sendo substituída — o que confirma a
leitura: não há tratamento novo, há uma tabela que nasce com um slot ocupado.

## 5. Otimização — também sem regra própria

A grafia `0` (linha inteira igual a `0` → `^0`) é uma normalização no mesmo pré-avaliador onde
as outras já vivem, com desambiguação **posicional**, mesma classe do char de modo no índice 7.

Medido no lab 2210 (17 casos, RT 51/51): **−479 B** contra a forma que declarava nó, e a
economia escala com a densidade de null.

Colapsar `0` direto em null internamente **não economiza byte** (o wire já é `0`) — só
esconderia o degrau. Descartado, não adiado.

## 6. O que a generalização abre

Se a metade baixa da tabela é o dicionário do formato, então a pergunta deixa de ser "como
tratar null" e vira **"o que mais mora lá"** — que é a pergunta que o plano de índices
reservados já fazia:

- `true`/`false` **já moram** (bool denso, weld #4b) — mas por um caminho diferente (tag `b`
  no header, domínio fixo) do que o plano propõe (índices 1 e 2). **Essa é a tensão registrada
  no levantamento §5 e continua sem decisão.**
- NaN / ±Inf: hoje fail-loud por RFC 8259; o plano já reserva espaço.
- ausência (`-`): hoje máscara, declarada como "forma de trabalho".
- **ordem canônica dos slots baixos**: não fixada. É pré-requisito de determinismo para
  qualquer um deles, não só o null.

## 7. Limites desta análise

- O experimento provou o **decode**. O encode **nem recebe `None`** na rota flat
  (`_lista_flat` exige todos `str`) — a coluna é desviada para o `.8H` antes. Abrir a rota
  para `str | None` é o que captura os 84% de ganho de envelope medidos no lab 2210, e é
  trabalho separado.
- `decode` de single-col passaria a poder devolver `list[str | None]` — mudança de contrato
  público, provável ADR.
- Escala: **uma coluna de um tipo**. Multi-coluna e `.8H` fora.
