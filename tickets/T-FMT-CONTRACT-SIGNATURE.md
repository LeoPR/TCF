---
title: T-FMT-CONTRACT-SIGNATURE, assinatura de contrato para os knobs que não reconstroem a entrada (drop_names, sort_by)
status: open
priority: P2
created: 2026-08-20
updated: 2026-09-01
gate: ".9 / pré-1.0 (muda o wire quando o knob está ligado)"
blocked-by: []
related:
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - docs/adr/0029-version-format-identification-semi-implicit.md
  - docs/adr/0041-spec-id-tres-planos.md
  - experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md
  - experiments/lab/dirty/notas/2026-08/2026-08-17-2400-h-13-03-encode-streaming.md
  - docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md
  - docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md
  - experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md
---

# T-FMT-CONTRACT-SIGNATURE: assinatura para os knobs de classe CONTRATO

**Fecha a H-13-13** do Pacote 13 (`roadmap-hipoteses`), convertendo-a de hipótese em ticket.
**[dispositivo → registro. Nada em `src/tcf` sem aprovação.]**

> **Atualizado 2026-09-01 (0.8.4)**: metade deste ticket foi confirmada, e a outra metade
> trocou de pergunta. O `drop_names` continua exatamente como descrito, e agora derruba os
> nomes em **duas** famílias, não numa só. O `sort_by` deixou de reordenar sempre
> ([ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md)), então a pergunta
> *"como declarar que reordenei"* virou *"como declarar que **posso** ter reordenado"*, que
> é um bit **condicional** e não um carimbo fixo. O exemplo que fundamentava a medição de
> 2026-08-20 foi refutado ao ser re-rodado: hoje ele devolve a entrada.
>
> O texto antigo fica onde está, com as notas datadas ao lado, porque o passo errado é
> justamente o que explica a pergunta nova. **Status proposto: continua `open`**, com o
> objeto reformulado. Nenhum critério de aceite foi cumprido, e o ticket ganhou trabalho em
> vez de perder.

## Origem

Direção do owner (2026-08-20), sobre o `drop_names`:

> *"a ideia é justamente pra opção em que se tem um contrato formatado entre o encode e
> decode nas duas pontas… os nomes não precisam ser transportados pois serão entendidos
> pelas pontas porque foram declaradas nas funções… **e não só o drop_names, mas outras
> coisas** que, se não precisarem ser transportadas é porque o decode já sabe o que fazer.
> A única diferença é que se o bloco de dados não tiver, ele tem que **esperar que ao menos
> o decode tenha isso declarado** para poder resolver."*

O `contrato-externalizado` §3.1 já nomeia a classe: **CONTRATO (semântica)**, *"sem ele um
wire stripped **não decodifica**. Logo a **assinatura é load-bearing**: wire stripped DEVE
carregar assinatura curta do contrato, e o decode DEVE verificá-la fail-loud"*.

## O problema, medido (2026-08-20)

Testei **todos** os kwargs de `encode`. Exatamente **dois** produzem um wire cujo `decode`
**não devolve a entrada**, e **nenhum dos dois** declara isso no wire:

```
drop_names=True   header '#TCF.8M!f,!'            decode {'0':…, '1':…}      ≠ orig
sort_by='uf'      header '#TCF.8M!f=nome,!uf'     linhas REORDENADAS         ≠ orig
```

Os demais (`min_header`, `stamp`, `fallback`, `layers`, `min_len`, `parallel`) mudam a
representação mas o `decode` devolve o original, são escolha de representação, não contrato.

> **Atualizado 2026-09-01 (0.8.4)**: a linha do `sort_by` nesta tabela está errada hoje, e
> quem a refuta é o próprio exemplo dela. Re-rodado sobre
> `t = {'nome': ['ana','bia','cau','duo'], 'uf': ['SP','RJ','SP','RJ']}`, o `encode(t)` e o
> `encode(t, sort_by='uf')` devolvem o **mesmo** wire, 45 B nos dois, e o `decode` devolve
> `t` intacto:
>
> ```
> encode(t)                 '#TCF.8M!f=nome,!uf\nana\nbia\ncau\nduoSP\nRJ\nSP\nRJ'
> encode(t, sort_by='uf')   '#TCF.8M!f=nome,!uf\nana\nbia\ncau\nduoSP\nRJ\nSP\nRJ'   (idêntico)
> ```
>
> A causa é o [ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md): o
> encoder passou a emitir as duas versões e a ficar com a menor, e nesta tabela a menor é a
> ordem de entrada. Ordenar por `uf` não agrupa nada de útil aqui, porque a coluna `nome` é
> toda de valores distintos.
>
> Com isso o **"exatamente dois"** também cai. Hoje só o `drop_names` produz **sempre** um
> wire cujo `decode` não devolve a entrada. O `sort_by` produz **às vezes**, e quem decide
> é o dado. Numa tabela em que as companheiras são função da chave ele ainda reordena, e o
> `decode` devolve a permutação:
>
> ```
> t2 = {'uf':     ['SP','RJ','SP','RJ','MG','SP','RJ','MG'],
>       'regiao': ['SE','SE','SE','SE','SE','SE','SE','SE'],
>       'cap':    ['sao paulo','rio','sao paulo','rio','bh','sao paulo','rio','bh']}
>
> encode(t2)                  81 B     decode devolve t2
> encode(t2, sort_by='uf')    76 B     decode devolve uf = MG MG RJ RJ RJ SP SP SP
> ```
>
> Ou seja, o kwarg não mudou de classe, mudou de **regime**. Ele saiu de "quebra o
> round-trip" para "pode quebrar o round-trip, e o wire não conta qual dos dois foi". Para
> o receptor, que nunca viu o kwarg, o segundo regime é pior.

### `sort_by` é o caso mais grave

O header fica **byte-idêntico** ao de um wire normal. Um `.8M` ordenado é
**indistinguível** de um íntegro: quem receber não tem como saber que a ordem das linhas foi
trocada, nem meio de reclamar. O `drop_names` ao menos *sinaliza* (falta o `=nome`), mesmo
sem assinatura.

> **Atualizado 2026-09-01 (0.8.4)**: o diagnóstico continua de pé, e ficou mais afiado. O
> que o [ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md) mudou foi a
> **frequência** do reordenamento, não a **visibilidade** dele. A indistinguibilidade se
> prova sem falar de header: pegue a `t2` acima, encode com `sort_by`, decode, e encode o
> resultado **sem** `sort_by`. Os dois wires saem byte-idênticos.
>
> ```
> encode(t2, sort_by='uf')  ==  encode(decode(encode(t2, sort_by='uf')))     True
> '#TCF.8M12=uf,6=regiao,cap\n*2|MG\n*3|RJ\n*3|SP\n*8|SE\n*2|bh\n*3|rio\n*3|sao paulo\n'
> ```
>
> Um wire permutado é, byte a byte, o wire honesto da tabela já permutada. Não existe lugar
> nele onde a diferença pudesse aparecer.
>
> **A pergunta nova é mais difícil que a antiga.** Antes era carimbar um fato que o encoder
> sempre soube. Agora o fato só existe depois de encodar as duas versões e comparar, então
> as duas formas do aviso deixaram de ser equivalentes:
>
> - **condicional** (o wire diz "ordenei" só quando a versão ordenada venceu): é a
>   declaração exata, e custa byte só onde há o que declarar. Em troca, a ausência do
>   carimbo vira informação sobre o **dado**, e não sobre o contrato: quem recebe um wire
>   sem carimbo aprendeu que ordenar não ajudava naquela tabela.
> - **fixo** (todo wire pedido com `sort_by` carrega a marca): diz só *"não confie na
>   ordem"*, que é o contrato order-free já vigente, e paga o byte inclusive nos wires em
>   que a ordem foi preservada.
>
> O que decide entre as duas é **para quem** o aviso serve. Quem passou o `sort_by` já abriu
> mão da ordem, e não precisa ser avisado de nada. Quem precisa é o **receptor**, que nunca
> viu a chamada, e para ele o fixo já basta: ele quer saber se pode confiar na ordem, não
> qual caminho o encoder tomou. Isso empurra a decisão para o fixo, mas é argumento, e não
> medição, por isso a pergunta segue aberta.

### O precedente que já faz certo

A nature: o wire carrega `:cpf` (a **assinatura**), o contrato (spec) vem por fora, e o
`_resolve_header_spec` (`decoder.py:62-79`) **só aceita se o `wire_id` coincidir**: senão
`ValueError`. É a forma industrializada da declaração obrigatória.

> **Atualizado 2026-09-01 (0.8.4)**: o precedente continua valendo, só andou de lugar. O
> `_resolve_header_spec` está hoje em `src/tcf/decoder.py:103-127`, e a comparação estrita
> contra o `wire_id` é a mesma. Ele já distingue os dois modos de falha que este ticket
> vai precisar: id que o registry não conhece **e** ninguém declarou por fora, e id que
> alguém declarou por fora mas **não bate**. A segunda é exatamente a de contrato trocado.

## O que este ticket propõe (a desenhar, não decidido)

1. **`drop_names`**: o wire passa a carregar uma **assinatura curta dos nomes**; o decode
   exige o contrato por fora e **falha alto** se a assinatura não bater. Medido: um
   fingerprint de 4 chars (`blake2s` → base-36) custa **4 B por wire**, espaço 36⁴ ≈ 1,68 M:
   suficiente para pegar **contrato trocado**, e declaradamente **não** é checksum de
   integridade.

   > **Atualizado 2026-09-01 (0.8.4)**: o desenho está certo e o **escopo** dobrou. Com o
   > [ADR-0049](../docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md), uma
   > `list[dict]` retangular passou a sair em `#TCF.8R`, e lá o `drop_names` faz a mesma
   > perda:
   >
   > ```
   > regs = [{'nome':'ana','uf':'SP'}, {'nome':'bia','uf':'RJ'}, ...]
   >
   > encode(regs)                   '#TCF.8R!f=nome,!uf\n…'   decode  [{'nome':'ana','uf':'SP'}, …]
   > encode(regs, drop_names=True)  '#TCF.8R!f,!\n…'          decode  [{'0':'ana','1':'SP'}, …]
   > ```
   >
   > O corpo sai igual nos dois; o que muda é o discriminador e o `=nome` que some. Logo a
   > assinatura é dos **nomes**, não da família, e o discriminador não entra nela. Quem
   > implementar tem de cobrir `M` **e** `R`, e no `R` o `decode` precisa exigir o contrato
   > antes de remontar os dicionários, senão a lista volta com chaves posicionais.

2. **`sort_by`**: decidir entre (a) declarar no wire que houve reordenação (e por qual
   coluna), ou (b) tratar como **contrato de conjunto** explícito na API, ou (c) manter como
   está e **documentar em letra garrafal** que o wire não é ordem-preservante.

   > **Atualizado 2026-09-01 (0.8.4)**: o
   > [ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md) tomou uma
   > **quarta** saída, que não estava nesta lista: **deixar o FLOOR decidir**. O kwarg
   > deixou de significar *"reordene por esta coluna"* e passou a significar *"você pode
   > reordenar se ajudar"*, com o encoder emitindo as duas versões e ficando com a menor.
   >
   > Ela resolve um problema **vizinho**, não este. O que o FLOOR fecha é o custo em bytes:
   > ordenar não faz mais o wire crescer (o ADR mediu +52,1% numa tabela de 6 colunas
   > independentes, perda que hoje não acontece mais). O que este ticket pergunta continua
   > sem resposta, porque o wire segue sem dizer o que aconteceu com a ordem.
   >
   > As três saídas seguem sobre a mesa, com os pesos trocados. A (a) ficou **mais cara**,
   > porque agora precisa de um bit condicional. A (c) ficou **mais barata**, porque "o wire
   > não é ordem-preservante" deixou de ser aviso e virou a descrição literal do que o
   > encoder faz.

3. **A regra geral**: todo knob futuro que faça `decode(encode(x)) != x` entra nesta classe
   por construção, **assinatura + fail-loud**, nunca degradação silenciosa.

## Perguntas em aberto

| # | pergunta |
|---|---|
| Q1 | A assinatura cobre **os nomes** ou **o contrato inteiro** (nomes + ordem + tipos)? |
| Q2 | Onde ela mora no meta? (o `:id` da nature já ocupa o último `:` não-escapado) |
| Q3 | `sort_by` merece assinatura, ou é caso de API (contrato de conjunto declarado)? |
| Q4 | Isto **supersede** a ADR-0029 no ponto do `drop_names` posicional, ou convive (posicional continua o default, assinatura é opt-in)? |
| Q5 | Colide com o `T-FMT-OMIT-OR-DECLARE`? Aquele ticket define as três categorias (dedutível / convenção-default / declaração-obrigatória), este é a **implementação** da terceira para dois casos concretos. |
| Q6 | **(2026-09-01)** O aviso do `sort_by` é **condicional** (só quando ordenou) ou **fixo** (todo wire pedido com o kwarg)? É a Q3 depois do FLOOR, e o argumento do receptor puxa para o fixo. |
| Q7 | **(2026-09-01)** A assinatura do `drop_names` é a mesma nas duas famílias, `#TCF.8M` e `#TCF.8R`, ou o `R` precisa assinar também a **remontagem** (que a volta é lista, e não dict)? |

> **Atualizado 2026-09-01 (0.8.4)**: a Q3 recebeu meia resposta. O ADR-0050 decidiu que o
> `sort_by` **não** é caso de API (não virou contrato de conjunto declarado) e também não
> ganhou assinatura: virou candidato. A metade que falta, a declaração, é a Q6.

## A tensão H-14-11, registrada 2026-09-01

Os dois ADRs de 2026-09-01 entraram no **mesmo commit** e se puxam em direções opostas
neste ponto exato.

O [ADR-0049](../docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md) leva a
`list[dict]` retangular para o ramo flat, o que faria o `sort_by` passar a funcionar lá, e
**recusa isso de propósito**: numa lista, reordenar calado seria trocar um erro alto pela
classe de silêncio que o projeto combate. O
[ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md), no mesmo commit,
tornou a reordenação **opcional**. O argumento da recusa enfraqueceu no dia em que foi
escrito, porque *"pode reordenar"* é bem menos agressivo que *"reordena sempre"*.

A recusa está de pé hoje, verificada:

```
encode([{'nome':'ana','uf':'SP'}, {'nome':'bia','uf':'RJ'}], sort_by='uf')
ValueError: sort_by nao vale em lista de registros: ele e' order-free e devolveria a
lista REORDENADA, silenciosamente. …
```

E ela deve continuar de pé até este ticket decidir, não o contrário. O motivo é que o FLOOR
mexeu na frequência do reordenamento, e não na visibilidade: a mensagem de erro promete
*"silenciosamente"*, e isso continua verdade, porque nada no wire assina a permutação. Um
reordenamento **raro** é mais difícil de depurar que um constante, já que ele só aparece em
alguns dados.

A hipótese está registrada como **H-14-11** (aberta, sem lab) no
[`roadmap-hipoteses`](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md), que já
aponta de volta para cá. A ordem certa é: decidir a Q6, e só depois avaliar a liberação no
`.8R`.

## O que NÃO é

- **Não é** checksum de integridade (`BUG-12`/`T-FMT-META-STRICT` cobrem corrupção).
- **Não é** proposta de tirar o comportamento posicional da ADR-0029: é dar a ele um modo
  **verificável** ao lado.
- **Não** toca `src/tcf` sem aprovação: liga o wire quando o knob está ligado, logo
  **re-pina** qualquer baseline que use `drop_names` (hoje: nenhum gate usa).

## Critérios de aceite

- [ ] Q1–Q3 decididas pelo owner
- [ ] Lab (mock, `src/tcf` intocado) medindo: custo da assinatura, e prova de que contrato
      trocado **falha alto** em vez de devolver dado errado
- [ ] Se aprovado: ADR que registre a relação com ADR-0029 e com `T-FMT-OMIT-OR-DECLARE`
- [ ] Gates byte-canônicos verdes (nenhum usa `drop_names` hoje: verificar antes)

**Acrescentado 2026-09-01 (0.8.4)**, sem tirar nada de cima: nenhum dos quatro itens acima
foi cumprido, e o ticket ganhou três.

- [ ] Q6 decidida: aviso condicional ou fixo para o `sort_by`, com o custo em byte medido
      nos dois regimes (o condicional só paga onde ordenou, o fixo paga sempre)
- [ ] A assinatura do `drop_names` cobre `#TCF.8M` **e** `#TCF.8R` (ADR-0049), com prova de
      que a lista de registros volta com os nomes ou **falha alto**, nunca com `'0'`/`'1'`
- [ ] H-14-11 (liberar o `sort_by` no `.8R`) só é avaliada **depois** da Q6

Verificado hoje na suíte: o único pino de gate que toca o `drop_names` é a assinatura
congelada de `encode` (`tests/test_regression_v1_baseline.py`, `ENCODE_SIGNATURE_FROZEN`),
que lista o kwarg como `KEYWORD_ONLY` com default `False`. Nenhum gate byte-canônico encoda
com ele ligado, então a assinatura de contrato pode ser desenhada sem re-pinar baseline,
desde que não acrescente kwarg novo à porta pública.
