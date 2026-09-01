# ADR-0049 — O `R` reserva a forma **registros**: a grafia da entrada é metadado, não rota

- **Status**: **aceito** (2026-09-01, decisão do owner). **Muda o wire**: reserva o
  discriminador `R` no índice 6 e passa a emiti-lo.
- **Origem**: ideia do owner (2026-08-31), *"assim como os dados, a estrutura também pode ser
  hard e soft. Um formato `[{v:d},{v:d}]` e `{v:[d,d]}` podem emprestar a mesma coisa pra
  comprimir, e só ter alguma dica de cabeçalho pra reconstruir corretamente."*
- **Fecha**: a série de labs 2026-08-31 `0330` → `0430` → `0530` → `0630`.
- **Não altera**: `#TCF.8`, `#TCF.8M` e `#TCF.8H`, que continuam byte-idênticos no que já
  emitiam.

## O fato

A mesma tabela, escrita de três jeitos que significam a mesma coisa, custava três preços:

| coluna (50 valores) | `list[str]` | `dict[1 col]` | `list[dict]` |
|---|---:|---:|---:|
| booleanos | **30 B** | 68 B | 159 B (**+430%**) |
| baixa cardinalidade | **42 B** | 75 B | 165 B (+293%) |

A causa é que **a forma da entrada escolhia o arsenal**, não o dado:

```
list[str]      #TCF.8    #TCF.8!   #TCF.8B…      tcf · raw · bN de domínio
dict[1 col]    #TCF.8M   #TCF.8M@  #TCF.8M%      tcf · dict · split
list[dict]     #TCF.8H                           tcf, e só
```

O `.8H` emite `_encode_col(coluna)`, que é **só** a rota `tcf`: ele não tem a camada que
escolhe entre candidatos. Uma lista de dicionários retangular não é dado hierárquico, mas caía
na família hierárquica por causa da grafia.

## A decisão

**Canonizar a forma retangular e registrar a forma de origem num caractere do header.**

Uma `list[dict]` retangular e plana é convertida em `dict[str, list]` e segue pela rota `.8M`,
com o mesmo corpo e o mesmo meta. O único byte diferente é o discriminador, que sai `R` em vez
de `M`. O `decode` lê o `R`, decodifica como multi e remonta a lista de dicionários.

```
encode([{"uf": "SP"}, {"uf": "RJ"}])   ->  '#TCF.8R@uf…'
decode('#TCF.8R@uf…')                  ->  [{"uf": "SP"}, {"uf": "RJ"}]
```

**O marcador custa zero byte.** O índice 6 já é o discriminador de família, e já é de um
caractere: `R` ocupa o slot que o `M` ocuparia, não soma nada.

### Por que isso não pode piorar

Não é aposta, é **dominância**, e o argumento é estrutural:

> **corpo**: o `.8H` emite `_encode_col(coluna)`, que é a rota `tcf`. O `.8M` emite
> `min(tcf, raw, dict, split)`, e o `tcf` é **um dos candidatos** desse mínimo. Logo
> `corpo(.8M) ≤ corpo(.8H)`, sempre, por construção.
>
> **meta**: as duas famílias declaram nome e tamanho por coluna. Seis casos adversariais
> desenhados para inflar o meta do `.8M` (30 colunas curtas, nomes longos, 1 linha × 20
> colunas, 1×1, colunas de 1 caractere, valores únicos longos) deram **zero** pioras.

Medido no conjunto roteado: **−44,9%** (513 B de 1143 B), round-trip exato em todos os casos, e
ganha ou empata em **7 de 7** tipos escalares, nulo incluso.

### O que continua no `.8H`

A canonização **recusa** o que não é tabela, e o recusado não muda de rota nem de bytes:

| entrada | continua em |
|---|---|
| ragged (`[{a,b}, {a}]`) | `#TCF.8H` |
| aninhado (`[{a: {x}}]`) | `#TCF.8H` |
| array na célula (`[{a: [1,2]}]`) | `#TCF.8H` |
| lista vazia | `#TCF.8` |

O `.8H` segue sendo a família de quem é genuinamente hierárquico. A decisão tira o **retangular**
de dentro do problema; ela não conserta o problema do aninhado, e isso é deliberado.

## As alternativas não escolhidas

- **Dar ao `.8H` a camada de escolha por coluna.** Resolveria também o aninhado, que é o que
  esta decisão não alcança. Mas mexe no codec de uma família inteira, e o retangular, que é o
  caso comum, sai mais barato pelo roteamento. Fica aberto para depois.
- **Unificar os arsenais** (bN, `@dict` e `%split` disponíveis a qualquer coluna). É a correção
  completa, e a maior: mexe no header das três famílias. É trabalho de `.9`.
- **Não fazer nada e documentar.** Recusada porque o custo medido não é de borda: 430% numa
  coluna de booleanos é a diferença entre o formato cumprir e não cumprir o que promete, e o
  usuário não tem como saber que a grafia dele escolheu o arsenal.

## Consequências

**Um wire `#TCF.8R` não é lido por nenhuma versão anterior.** Pré-1.0 esse é o regime declarado
(git-as-compat, [ADR-0024](0024-versionamento-pre-1-0-git-as-compat.md)), então não é bloqueio,
mas é fato que precisa estar escrito.

**A detecção custa 4,4% do que o encode já custa** (12,5 ms contra 285,4 ms em 10.000 × 3), e
esse é o pior caso da implementação ingênua: a varredura de chaves e tipos é a mesma que o
encoder faz depois, então ela se funde com a passada que já existe.

**O `sort_by` passa a ser aceito onde hoje levanta**, porque registros agora chegam ao ramo
flat. Isso é mudança de contrato e foi **deliberadamente não liberada** nesta solda: o
`sort_by` é order-free, e transformar um erro alto numa reordenação silenciosa da lista do
usuário é a classe de silêncio que este projeto combate. Ele continua recusado em registros, e
a liberação, se vier, é decisão própria com aviso próprio.

**O `schema=` não muda nenhuma decisão ao rotear**: medido em três specs (`data-iso`, `cpf`,
`ip`), as três mantiveram a decisão de aplicar ou descartar, com o wire menor nas três.

**Sete kwargs que levantavam em registros passam a funcionar**, porque a canonização leva a
entrada ao ramo flat, que é onde eles valem. São `layers`, `min_len`, `stamp`, `parallel`,
`fallback`, `min_header` e `drop_names`. A mudança é aditiva, na direção segura: o que dava
erro passa a fazer o que o nome promete, e nada que funcionava mudou de resultado. Continuam
recusados o `sort_by`, pelo motivo acima, e o `name`.

O `drop_names=True` merece nota, porque ele muda o que o `decode` devolve: sem os nomes, a
volta é `[{'0': ...}, {'0': ...}]`. Não é surpresa nova, é a mesma coisa que ele já fazia no
`.8M` (onde a volta vira `{'0': [...]}`), agora visível na forma de registros.

**A capacidade de carregar `\n` e `\r` continua sendo do `.8H` e só dele.** O hierárquico
escapa folhas e nomes; o flat os recusa, porque o wire é LF-only e o LF separa o meta. Por isso
a canonização recusa quem tem quebra de linha em nome ou valor, e deixa passar para o `.8H`.
Sem essa guarda o roteamento **tiraria** uma capacidade que a entrada já tinha, trocando um
round-trip que funciona por um `ValueError`, que é a pior regressão possível aqui: silenciosa
do ponto de vista de quem escreveu o código, e fatal para quem depende dela.

## Evidência

Labs (fora do git, `experiments/lab/dirty/` é ignorado):
`2026-08-31-0330-8h-descarta-nature-por-header-que-nao-emite`,
`2026-08-31-0430-a-mesma-tabela-em-duas-rotas`,
`2026-08-31-0530-a-forma-e-metadado-nao-estrutura`,
`2026-08-31-0630-a-forma-vira-marcador-prototipo`,
`2026-08-31-0730-marcador-com-sort-by-e-schema`.
