---
title: "Presença, nulo e ausência: os três blocos"
type: explanation
parent: theory
subsystem: presenca-nulo-ausencia
---

# Presença, nulo e ausência: os três blocos

> O wire do TCF distingue **três** estados por célula, e a tabela que a `view` entrega só tem
> dois. Estas notas registram por que a distinção existe, como se nomeia cada bloco e o que
> cada caso de borda deve responder. **Nada está implementado**: a grafia de filtro é
> proposta, e o que a `view` faz hoje está dito em cada página.

## Quickuse: as cinco perguntas

Para uma coluna `k` de uma tabela de `n` linhas:

| a pergunta | a grafia proposta | como se faz **hoje** |
|---|---|---|
| tem valor | `block=V` | `where(k, pred=lambda x: x is not None)` |
| existe e é nulo | `block=N` | `where(k, None)` |
| não existe | `block=A` | só por `decode()`: a `view` recusa o wire que carrega ausência |
| existe | `block=~A` | é o total, `count()` |
| nulo ou ausente | `block=~V` | hoje coincide com `where(k, None)` |

Três primitivos e um complemento cobrem as **oito** uniões possíveis, inclusive a
`V ∪ A` (`~N`), que uma lista de nomes não alcançaria. A regra que gera todas as respostas
é uma só: **todo critério fornecido intersecta**.

Duas advertências que valem antes de escrever qualquer linha:

- `A` é **vazio em todo blob que a `view` abre hoje**, porque ela recusa ragged no header. As
  respostas sobre ausência são as do caso total, e isso é o comportamento certo, não uma
  lacuna. Ver [06](06-defaults-e-flags.md);
- `where(k, None)` responde `N`, e continuará respondendo só `N` quando a ausência existir. A
  união se pede por `~V`.

## As notas

| nota | o que ela fecha |
|---|---|
| [01 A partição e as oito uniões](01-a-particao-e-as-oito-unioes.md) | os três blocos, a tabela das oito uniões, e por que três nomes bastam |
| [02 Os termos firmados](02-os-termos-firmados.md) | `domain of definition`, `antidomain`, fibra, classificador, e a desambiguação contra o bN de domínio |
| [03 O que não serve](03-o-que-nao-serve.md) | o `support` refutado, o `missing` como falso cognato, e a ressalva da letra `V` |
| [04 O lift duplo](04-o-lift-duplo.md) | `X ⊔ 1 ⊔ 1`, e por que `null` é um valor e `ausente` não é |
| [05 Mimetismo e fontes](05-mimetismo-e-fontes.md) | o que Mongo, Postgres, Arrow, polars e R fazem, e a bibliografia |
| [06 Os defaults e as flags](06-defaults-e-flags.md) | o que cada caso de borda responde, de onde o default veio, e o que ainda não se pode afirmar |

## O estado

- **a matemática**: fechada. Os blocos são as fibras da máscara, e a partição é dado do wire.
- **o vocabulário**: fechado. `V`, `N`, `A`, união por `|`, complemento por `~`, com
  `domain of definition`, `antidomain` e `null` como glosa da prosa.
- **os defaults**: propostos, com origem por caso, e sem nenhum item na lista do que ninguém
  resolveu.
- **a implementação**: não existe, e o portão de desempenho depende de uma medição que ainda
  não foi feita.

## De onde isto veio

Labs de 2026-08-30, `0100` a `0500`, em `experiments/lab/dirty/2026-08/2026-08-30/`: as duas
leituras lado a lado, o buraco na grade, o `where` nos dois modos, a partição em três blocos
e o levantamento de nomenclatura com fonte por afirmação.
