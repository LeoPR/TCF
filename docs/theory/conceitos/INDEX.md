---
title: "Conceitos: o degrau entre o tutorial e a especificação"
type: explanation
parent: theory
subsystem: conceitos
---

# Conceitos

> Quem termina o [tutorial](../../tutorials/getting-started.pt-BR.md) sabe usar o TCF e não
> sabe o que está vendo. Esta pasta é o degrau entre aquilo e a
> [especificação](../../algorithms/TCF-format.md), que tem 624 linhas e abre por política de
> versionamento. Aqui está o que você **já viu sair** e ainda não entendeu.

Estas páginas descrevem o que o `0.8` **faz**, não hipótese. O resto de `docs/theory/`
registra direção e estudo; aqui é o presente.

| página | a pergunta que ela responde |
|---|---|
| [O wire em uma página](o-wire-em-uma-pagina.md) | *o que é esse texto que saiu do `encode`?* Cabeçalho, coluna, modo, e os marcadores `*N\|` e `^N` |
| [Spec não é tipo](spec-nao-e-tipo.md) | *o que é uma nature, e por que eu não passo ela no `decode`?* |
| [O custo da consulta](custo-da-consulta.md) | *por que a `view` responde barato, e o que "barato" quer dizer* |

## A ordem sugerida

Na ordem da tabela. O wire vem primeiro porque as outras duas se apoiam nele: a spec é uma
reescrita do valor **antes** de o wire ser montado, e o custo da consulta é uma consequência
de o cabeçalho declarar o que declara.

## Onde continuar

- a **receita** para uma tarefa: [`docs/how-to/`](../../how-to/)
- o **contrato** de uma chamada: [`docs/reference/`](../../reference/)
- a **especificação** do formato: [`docs/algorithms/TCF-format.md`](../../algorithms/TCF-format.md)
- o **porquê** das decisões: [`docs/adr/`](../../adr/)
