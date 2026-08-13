# Entrega incremental do núcleo — as 3 afirmações do owner, medidas

> **Owner, 2026-08-13** (reforçando algo já dito antes):
>
> **(A)** *"o núcleo tem maleabilidade para parar a busca e entregar pedaços. ao menos tem
> condições — enquanto vai coletando e fazendo a busca e comparação, se em algum momento
> passar um tempo, é possível pegar o que já foi coletado, entregar adiante. obviamente
> existe o risco dele não conseguir melhores comparações"*
>
> **(B)** *"depois que ele para pra entregar, ele fica com dicionários cada vez mais
> fechados, pois ele precisou congelar o que deu pra entregar em cada etapa"*
>
> **(C)** *"quando se acha coisas como uma cadeia de true e false, mandar pedaços não faz
> diferença, pois o decode fica coletando e descomprimindo de acordo com a demanda. Ele só
> falha se tiver algo no final."*

## Estado — era / foi / é / será

- **Era**: o lab das 17h40 mediu fatiamento como **p wires independentes** (cada fatia
  re-encodada do zero). Responde "quanto custa emitir p wires" — pergunta legítima, mas
  **não** é o modelo acima.
- **Foi**: as 3 afirmações. (C) é testável pela API pública; (A) e (B) são sobre o encoder.
- **É**: este lab mede (C). O wire é encodado **uma vez** e entregue em prefixos de linhas
  íntegras — custo em bytes zero, e a pergunta vira *quantos pedaços úteis o wire dá*.
  Resultado em [`result.md`](result.md): a granularidade varia de **1 a 5 pontos de
  entrega** conforme o mecanismo de compressão que venceu, e **nada fica no final** — o
  dicionário do bN vem na frente, as referências (`^1`) apontam para trás.
- **Será**: (A) e (B) dependem de auditoria do encoder e de instrumentação nova. E a
  entrega **dentro** de uma linha densa de índices (bN) é o que separaria o booleano
  aleatório de 1 para ~N pontos.

## Como rodar

```
python run.py     # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se todos os round-trips fecharem **e** nenhum prefixo devolver valor errado sem
erro. `src/tcf` não é tocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `intermediates/<c>.entrega-incremental.json` | a curva: linhas recebidas → bytes → valores entregues, com a linha que chegou |
| `outputs/<c>.tcf` | o wire (inteiro — é ele que é cortado, não re-encodado) |
| `outputs/<c>.roundtrip.json` | contra-prova: `diff` contra `inputs/<c>.entrada.json` |
| `outputs/INDEX.md` | tabela com pontos de entrega por caso |

## Ressalva

Dirty: conclusão **orientativa**. O que produz de duro é (a) a curva de entrega por
mecanismo, reproduzível por `python run.py`, e (b) a correção de método sobre o lab
anterior.

## Vínculo

`T-PULSO-SINGLE-COL` · `T-LAZY-BYPASS-ARITMETICO` · `H-ENCODE-DEADLINE-01` · `V2-J`
(ADR-0018) · ADR-0036 (bN de domínio) · ADR-0040 (seq-RLE periódico).
Lab irmão: [`…-1740-latencia-como-eixo`](../2026-08-13-1740-latencia-como-eixo/).
