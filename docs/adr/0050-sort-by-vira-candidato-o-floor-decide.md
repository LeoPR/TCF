# ADR-0050 — O `sort_by` vira **candidato**: quem decide ordenar é o FLOOR, não o usuário

- **Status**: **aceito** (2026-09-01, decisão do owner). **Não muda o wire**; muda o que o
  encoder emite para uma mesma entrada, e portanto é mudança de comportamento.
- **Origem**: dúvida do owner sobre o propósito do `sort_by`, *"ele está me parecendo mais
  estético pro TCF por enquanto"*, e a observação de que forçar uma ordenação pode custar
  compressão porque existem combinações melhores.
- **Fecha**: H-14-06 e H-14-08 do registro de hipóteses.
- **Corrige junto**: quatro defeitos de superfície do mesmo kwarg.

## O fato

O `sort_by` reordenava **sempre**, e o efeito em bytes depende inteiramente do dado:

| tabela (60 linhas) | sem | com | saldo |
|---|---:|---:|---:|
| 6 colunas independentes da chave | 432 B | 657 B | **+52,1%** |
| 3 colunas todas função da chave | 307 B | 175 B | **−43,0%** |

O saldo vira negativo já na **segunda** coluna quando as companheiras são independentes. A
razão é simples: a permutação agrupa os iguais da **chave** e desarruma **todas** as outras
colunas de uma vez. A referência registrava a faixa como "pode ganhar ou perder ~2-15%", medida
em corpus real (`adult` −10%, `online-retail` +2,3%); o sintético mostra que a cauda é bem maior
que isso nos dois sentidos.

Quem tinha de adivinhar de que lado a tabela estava era o **usuário**, e ele não tem como saber
sem encodar as duas versões.

## A decisão

**Tratar a ordenação como mais um candidato, do jeito que o `.8M` já trata `tcf`/`raw`/`@`/`%`:
encoda as duas versões e emite a menor.**

O fundamento é que a autorização já existia. Passar `sort_by` **já** significava abrir mão da
ordem das linhas (o contrato é order-free desde sempre), então o encoder já estava autorizado a
reordenar. Nada nesse contrato o obrigava a reordenar **quando isso piora**.

Na prática o kwarg deixa de significar *"reordene por esta coluna"* e passa a significar *"você
pode reordenar por esta coluna se ajudar"*. Nos sete casos medidos isso evita **734 B** de perda
sem abrir mão de ganho nenhum, porque o menor dos dois nunca é pior que qualquer um deles.

**Custo**: um encode a mais, e só quando o `sort_by` é pedido.

## A tensão que isso cria, e como ela foi resolvida

**O layout ordenado tinha um consumidor**: o `view.group_ranges(key)`, que exige a coluna
contígua e levanta quando não está, e o `view.agg_by` construído sobre ele. Com o FLOOR, um blob
pedido com `sort_by` pode legitimamente chegar fora de ordem, e o `agg_by` levantaria de forma
imprevisível para quem não escolheu o layout.

**Resolvido fazendo o `agg_by` cair no caminho order-free** quando a chave não está contígua. Ele
nunca mais levanta por causa do layout. O `group_ranges` **continua estrito de propósito**: ele é
o inspetor de layout, e a pergunta "esta coluna está agrupada?" precisa de resposta honesta.

Isso não custa nada, e a medição é o motivo: o caminho por intervalos **não é mais barato** que o
order-free. Medidos lado a lado sobre a mesma tabela, os dois materializam as mesmas colunas,
decodificam as mesmas 120 linhas e devolvem o mesmo resultado, e o que exige contiguidade saiu
**3,6% mais lento**. A docstring do `group_sum` afirmava que o `agg_by` era "mais barato", e a
afirmação foi corrigida.

## O que esta decisão custa, e é honesto declarar

**A forma canônica deixa de ser alcançável pelo `sort_by`.** Ordenar torna o wire independente da
ordem em que o produtor montou as linhas, o que serviria dedupe, cache por conteúdo e endereço
por hash. Com o FLOOR, a ordenação não é mais garantida, então esse uso morre aqui.

A perda é menor do que parece, por duas razões medidas. A forma canônica só valia com **chave
única** (com empates o `sorted` é estável, e as linhas empatadas mantêm a ordem de entrada:
8 embaralhamentos do mesmo conjunto deram 8 wires distintos), e chave única é exatamente o caso
em que agrupar não serve para nada. E a forma correta desse uso seria ordenar por **todas** as
colunas, que é um operador diferente do `sort_by`. Fica registrado como H-14-10, para quando
alguém precisar dele de verdade.

## Os quatro defeitos de superfície, corrigidos junto

1. **Em `list[str]` o kwarg era ignorado calado**, e o silêncio estava **pinado em teste**,
   enquanto as outras quatro rotas o recusavam alto. Agora recusa, com mensagem que ensina o
   que fazer. É a regra "nunca ignorar calado" com o furo fechado.
2. **Código morto removido**: o `ValueError` de colunas de tamanhos diferentes era inalcançável,
   porque `_tabela_flat` já recusa tabela ragged antes dele.
3. **A chave de ordenação é `str(valor)`**, então `'10'` vem antes de `'2'` e um `None` compara
   como a string `'None'`. **Documentado, e não corrigido**, deliberadamente: a ordenação aqui
   existe para agrupar iguais, qualquer ordem total agrupa igualmente bem, e a ordem em si
   deixou de ser promessa quando o contrato virou order-free.
4. **Não havia ADR** do `sort_by`, embora todos os vizinhos do mesmo ciclo de solda tenham
   (0022, 0023, 0025, 0026). Este documento é ele.

## As alternativas não escolhidas

- **Avisar em vez de decidir** (emitir warning quando ordenar piora). Empurra para o usuário uma
  decisão que o encoder pode tomar melhor, porque só ele já tem as duas versões na mão.
- **Remover o kwarg.** Ele comprime de verdade quando as companheiras correlacionam com a chave,
  e −43,0% não é ruído. O problema nunca foi ele existir, foi ele obedecer cegamente.
- **Deixar como estava e documentar a faixa.** Foi o que existia, e a faixa documentada
  (±2-15%) subestimava a cauda em mais de três vezes.

## Evidência

Labs (fora do git, `experiments/lab/dirty/` é ignorado):
`2026-09-01-0010-sort-by-o-que-ele-compra` (as duas pontas, o FLOOR hipotético, a paridade
`agg_by`/`group_sum`) e `2026-09-01-0130-entrega-agrupavel-ja-e-o-default` (os quatro vetores
ortogonais, e o achado de que ordenar tira a chave do `@dict`).
