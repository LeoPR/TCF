---
title: "T-CODE-VIEW-SUBTCF-RECORTE: promover H-QUERY-06 a saída TCF da view"
status: open
priority: P2
created: 2026-08-26
updated: 2026-09-01
target: ".9; nova API, não patch de 0.8.2"
gate: contrato do owner e aprovação explícita antes de tocar src/tcf (I5)
blocked-by: []
related: [
   docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md,
   experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md,
   experiments/lab/dirty/notas/2026-08/2026-08-25-subtcf-por-recorte-viabilidade.md,
   experiments/lab/dirty/notas/2026-08/2026-08-25-recorte-estudo-de-implementacao.md,
   experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-1200-mecanismo-do-recorte/,
   src/tcf/view.py,
   docs/reference/lazy-view.md,
   tickets/T-HTTP-QUERY-E-VIEW.md,
   tickets/DECISAO-GROUPING-SEMANTICA.md,
   experiments/lab/dirty/notas/2026-08/2026-08-26-1944-revisao-fechamento-08-view-encode.md,
]
---

# T-CODE-VIEW-SUBTCF-RECORTE

**[dispositivo → execução]** A autoridade conceitual continua sendo `H-QUERY-06` e
`H-QUERY-07` no registry. Este ticket não abre uma direção paralela: ele possui somente a
promoção do mecanismo provado para uma API pública, com os contratos que a auditoria da
superfície mostrou que ainda faltam.

## O mesmo princípio, aplicado à saída

`to_tcf()` estende o princípio oportunista da `view`: obter o blob filho correto pela
**menor transformação suficiente** do blob pai. O resultado é determinado pelo filtro e
pela projeção; a rota escolhida só altera quanto do pai precisa ser interpretado.

A ordem de preferência é:

1. projetar o header e não tocar colunas descartadas;
2. recortar linhas raw;
3. recortar o stream `@dict`, podar únicos mortos e recodificar somente os K sobreviventes;
4. preservar o template `%split` e recorrer nas sub-tabelas;
5. materializar apenas a coluna e as posições que a estrutura não permite recortar;
6. usar `decode` + `encode` da tabela como último fallback de correção.

O filho precisa ser lossless, decodável e consultável por `view(filho)` em todas as rotas.
Canonicidade de bytes é uma decisão separada. Nenhum caminho rápido pode mudar vazio,
nulo, tipo, ordem, multiplicidade, `distinct` ou agrupamento para economizar trabalho.

“Mínimo” aqui também é uma obrigação demonstrável, não um slogan: a rota usada precisa ser
observável, e uma alegação de caminho mais barato exige contraprova contra o fallback. Onde
o recorte estreito ainda não está provado, o fallback correto entra primeiro e a otimização
vai para lab.

## Entrega candidata

```python
filtrado = view(blob).where("regiao", "norte")
filho = filtrado.to_tcf(cols=["id", "valor"])
assert view(filho).count() == filtrado.count()
```

`select()` continua devolvendo valores materializados. A saída em blob é outra operação;
escondê-la atrás de uma flag de `select` apagaria a diferença de custo que justifica o
recurso. `LazyTCF.slice(idx, cols=None)` pode ser a primitiva interna; só deve virar API se
houver uso direto além do terminal de `Filtered`.

## O que está provado

O lab `2026-08-25-1200-mecanismo-do-recorte` foi reproduzido sobre `v0.8.2`:

- contrato manual verde em 20/20 casos, mais recorte do recorte;
- caminho rápido em 13/20; os demais usam o oráculo `decode` + `encode`;
- diferencial de 400 entradas válidas sem divergência entre cirurgia e oráculo;
- no caminho rápido, 120/171 filhos ficaram byte-idênticos ao canônico e a mediana do
  delta foi zero; os bytes são comparados só depois de `decode` e `view(filho)` validarem
  o conteúdo.

O domínio efetivamente provado é **`#TCF.8M`, inclusive com uma única coluna, índices
válidos e ao menos uma coluna projetada**. Os casos chamados `single` nos labs usam
`encode({"x": valores})`; não são a rota single-column real `encode(valores)`.

| modo do corpo `.8M` | caminho |
|---|---|
| raw | recorta as linhas delimitadas por LF |
| `@dict` | recorta o stream, poda únicos mortos e recodifica só os K sobreviventes |
| `%split` | preserva o template e recorre nas subcolunas |
| core | fallback pelo oráculo |
| recorte vazio ou dicionário degenerado | fallback pelo oráculo |

A poda do dicionário é requisito de correção: sem ela, `decode` continua certo, mas
`distinct` e `n_unique` do filho contam entradas mortas.

## Bordas ainda abertas

A auditoria de 2026-08-26 encontrou contratos fora das 400 entradas válidas. Eles não
invalidam a prova acima, mas impedem soldar o protótipo como está:

| borda | comportamento atual do protótipo |
|---|---|
| índice `n` numa coluna `@dict` | caminho rápido devolve a primeira chave em vez de `IndexError` |
| índice `-1` em `@dict` | caminho rápido devolve a primeira chave; o oráculo Python devolveria a última |
| `cols=[]` | emite `#TCF.8M\n`, que `decode` e `view` rejeitam |
| `cols=["k", "a"]` | caminho rápido conserva a ordem física `a, k`, diferente do pedido e do oráculo |
| rota single-column real | fallback assume `dict` e levanta `TypeError` sobre a lista |
| `.8H` retangular | funciona pelo fallback e volta como `.8M`; não há cirurgia rápida |

Índices precisam ser validados **antes** de qualquer cirurgia. Negativos devem ser
explicitamente aceitos com a semântica do oráculo ou rejeitados; não podem variar por modo.
Projeção vazia precisa ser recusada com erro ensinante ou ganhar representação que preserve
o número de linhas. A ordem de `cols` deve seguir a mesma regra de `select`.

## Decisões antes do weld

1. **Canonicidade**: o contrato exige blob lossless e consultável; decidir se também exige
   bytes iguais a `encode(subconjunto)` ou se a rota não-canônica é uma forma de trabalho.
2. **Superfície**: `Filtered.to_tcf(cols=None)` é o terminal necessário; decidir se
   `LazyTCF.slice` fica interno.
3. **Telemetria**: preservar a rota (`recorte`, `encode`, `encode-vazio`) em canal explícito,
   para uma regressão ao fallback não passar como sucesso de desempenho.
4. **Cobertura de formato**: single-column e `.8H` precisam ao menos de fallback correto;
   caminho rápido próprio é otimização posterior.

Nenhuma dessas decisões muda o wire emitido pelo `encode`. Marcar o filho no formato para
indicar que é derivado não é necessário e só deve ser considerado com evidência nova.

### Atualizado 2026-09-01 (0.8.4): entra o `#TCF.8R`, e com ele uma pergunta de desenho

A cobertura de formato do item 4, e o critério de aceite abaixo, foram escritos quando
`list[dict]` retangular caía no `.8H`. Desde a
[ADR-0049](../docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md), soldada na 0.8.4, ela
não cai mais: retangular e plana vira `#TCF.8R`, que é o corpo do `.8M` com outro discriminador
no índice 6. Verificado na 0.8.4: `encode([{'id': '1', 'regiao': 'norte', 'valor': '10'}, ...])`
emite `#TCF.8R!7=id,13=regiao,valor`, e os mesmos dados escritos como `dict[str, list]` dão
65 B nos dois casos, iguais em tudo fora do caractere 6 (`M` contra `R`).

Isso move o alvo do ticket, porque o `.8R` é hoje onde cai a maior parte da entrada em
registros. Continuam no `.8H` o ragged, o aninhado, o array na célula e o valor com `\n`; a
chave não-str levanta; e `[]` continua `#TCF.8`.

A `view` já abre `.8R`, sem nada de novo (verificado na 0.8.4): `view(blob)` devolve um
`LazyTCF`, e `count`, `select`, `distinct`, `n_unique`, `group_count` e `where` respondem igual
ao `.8M`. O que ainda não existe é o terminal deste ticket. `Filtered.to_tcf` e `LazyTCF.slice`
não estão em `src/tcf` na 0.8.4, então o ticket segue com objeto inteiro.

**A pergunta de desenho, registrada e não decidida: o recorte de um `.8R` deve sair `.8R` ou
`.8M`?** Ela não é cosmética, porque o que este ticket desenha é justamente qual wire o RECORTE
emite:

- o filho `.8R` preserva a forma de lista que o `decode` remonta. O filho `.8M` devolve
  `dict[str, list]`, e quem chama `decode(filho)` recebe outra coisa que `decode(pai)`;
- para a `view` os dois são equivalentes. No recorte medido (linhas 0 e 2, colunas `id` e
  `valor`) os dois filhos têm 28 B, diferem só no índice 6, e `view(filho).select()` devolve o
  mesmo resultado nos dois;
- as duas rotas do protótipo puxam para lados opostos. O oráculo `decode` + `encode` devolve
  `.8R` sozinho, porque `decode` de um `.8R` já entrega `list[dict]`. A cirurgia sobre o corpo
  multi devolve `.8M`, porque é o corpo do `.8M` que ela recorta. Sem decisão escrita, quem
  decide o tipo do filho é a rota que calhou de rodar, que é a classe de silêncio que este
  ticket existe para fechar.

Uma borda ganha material novo nessa leitura. O `cols=[]`, que no `.8M` só sabia emitir
`#TCF.8M\n` (recusado por `decode` e por `view`), tem representação na forma de registros:
`encode([{}, {}])` emite `#TCF.8H#D2\n` e volta `[{}, {}]`, preservando o número de linhas.
Não decide nada sozinho, mas é evidência para o item da projeção vazia.

## Critério de aceite

- [ ] Contrato público decidido para índices negativos, fora da faixa, repetidos e fora de ordem.
- [ ] `cols` reutiliza a resolução nome/posição da `view`, preserva a ordem pedida e trata
      lista vazia e duplicatas explicitamente.
- [ ] Single-column, `.8M` e `.8H` retangular produzem filho correto, ainda que por fallback.
- [ ] Caminho rápido preserva raw, `@dict` com poda e `%split` recursivo; core cai no oráculo.
- [ ] Teste diferencial compara `decode(filho)`, `view(filho)` (`count`, `select`, `distinct`,
      `n_unique`, `where`, `group_count`) e a rota usada.
- [ ] Fuzz inclui entradas inválidas e exige a mesma falha no caminho rápido e no oráculo.
- [ ] Projeção pode evitar uma coluna core sem materializá-la.
- [ ] Documentação separa “sem encode das N linhas” de “zero encode”: podar `@dict`
      recodifica K; fallback recodifica a tabela.
- [ ] Suíte completa verde; `src/tcf/` só após aprovação explícita.
- [ ] (2026-09-01) `#TCF.8R` produz filho correto, ainda que por fallback. O item acima que
      diz `.8H` retangular passa a valer para o hierárquico que sobrou, não para o retangular.
- [ ] (2026-09-01) Decidido por escrito se o filho de um `.8R` sai `.8R` ou `.8M`, e o teste
      diferencial passa a checar o discriminador do filho, não só o conteúdo.

## Classificação de release

É capacidade nova e adiciona API, política de canonicidade e contratos de índice/projeção.
Portanto pertence ao `.9`. O bug já publicado de uma única string vazia é independente e
está em `BUG-VIEW-UMA-STRING-VAZIA` como correção de `0.8.x`.

No fechamento do `.8` cabem o contrato, a correção de respostas erradas e a declaração dos
comportamentos já determinados. No `.9` entram a API pública, fallback por coluna,
pushdown posicional, integração com o plano latente e novos caminhos rápidos. Cirurgia de
core, `.8H` ou canonicidade sem resposta evidente começa em lab.
