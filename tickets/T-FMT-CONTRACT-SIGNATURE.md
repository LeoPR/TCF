---
title: T-FMT-CONTRACT-SIGNATURE — assinatura de contrato para os knobs que não reconstroem a entrada (drop_names, sort_by)
status: open
priority: P2
created: 2026-08-20
updated: 2026-08-20
gate: ".9 / pré-1.0 (muda o wire quando o knob está ligado)"
blocked-by: []
related:
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - docs/adr/0029-version-format-identification-semi-implicit.md
  - docs/adr/0041-spec-id-tres-planos.md
  - experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md
  - experiments/lab/dirty/notas/2026-08/2026-08-17-2400-h-13-03-encode-streaming.md
---

# T-FMT-CONTRACT-SIGNATURE — assinatura para os knobs de classe CONTRATO

**Fecha a H-13-13** do Pacote 13 (`roadmap-hipoteses`), convertendo-a de hipótese em ticket.
**[dispositivo → registro. Nada em `src/tcf` sem aprovação.]**

## Origem

Direção do owner (2026-08-20), sobre o `drop_names`:

> *"a ideia é justamente pra opção em que se tem um contrato formatado entre o encode e
> decode nas duas pontas… os nomes não precisam ser transportados pois serão entendidos
> pelas pontas porque foram declaradas nas funções… **e não só o drop_names, mas outras
> coisas** que, se não precisarem ser transportadas é porque o decode já sabe o que fazer.
> A única diferença é que se o bloco de dados não tiver, ele tem que **esperar que ao menos
> o decode tenha isso declarado** para poder resolver."*

O `contrato-externalizado` §3.1 já nomeia a classe: **CONTRATO (semântica)** — *"sem ele um
wire stripped **não decodifica**. Logo a **assinatura é load-bearing**: wire stripped DEVE
carregar assinatura curta do contrato, e o decode DEVE verificá-la fail-loud"*.

## O problema, medido (2026-08-20)

Testei **todos** os kwargs de `encode`. Exatamente **dois** produzem um wire cujo `decode`
**não devolve a entrada** — e **nenhum dos dois** declara isso no wire:

```
drop_names=True   header '#TCF.8M!f,!'            decode {'0':…, '1':…}      ≠ orig
sort_by='uf'      header '#TCF.8M!f=nome,!uf'     linhas REORDENADAS         ≠ orig
```

Os demais (`min_header`, `stamp`, `fallback`, `layers`, `min_len`, `parallel`) mudam a
representação mas o `decode` devolve o original — são escolha de representação, não contrato.

### `sort_by` é o caso mais grave

O header fica **byte-idêntico** ao de um wire normal. Um `.8M` ordenado é
**indistinguível** de um íntegro: quem receber não tem como saber que a ordem das linhas foi
trocada, nem meio de reclamar. O `drop_names` ao menos *sinaliza* (falta o `=nome`), mesmo
sem assinatura.

### O precedente que já faz certo

A nature: o wire carrega `:cpf` (a **assinatura**), o contrato (spec) vem por fora, e o
`_resolve_header_spec` (`decoder.py:62-79`) **só aceita se o `wire_id` coincidir** — senão
`ValueError`. É a forma industrializada da declaração obrigatória.

## O que este ticket propõe (a desenhar, não decidido)

1. **`drop_names`** — o wire passa a carregar uma **assinatura curta dos nomes**; o decode
   exige o contrato por fora e **falha alto** se a assinatura não bater. Medido: um
   fingerprint de 4 chars (`blake2s` → base-36) custa **4 B por wire**, espaço 36⁴ ≈ 1,68 M
   — suficiente para pegar **contrato trocado**, e declaradamente **não** é checksum de
   integridade.
2. **`sort_by`** — decidir entre (a) declarar no wire que houve reordenação (e por qual
   coluna), ou (b) tratar como **contrato de conjunto** explícito na API, ou (c) manter como
   está e **documentar em letra garrafal** que o wire não é ordem-preservante.
3. **A regra geral**: todo knob futuro que faça `decode(encode(x)) != x` entra nesta classe
   por construção — **assinatura + fail-loud**, nunca degradação silenciosa.

## Perguntas em aberto

| # | pergunta |
|---|---|
| Q1 | A assinatura cobre **os nomes** ou **o contrato inteiro** (nomes + ordem + tipos)? |
| Q2 | Onde ela mora no meta? (o `:id` da nature já ocupa o último `:` não-escapado) |
| Q3 | `sort_by` merece assinatura, ou é caso de API (contrato de conjunto declarado)? |
| Q4 | Isto **supersede** a ADR-0029 no ponto do `drop_names` posicional, ou convive (posicional continua o default, assinatura é opt-in)? |
| Q5 | Colide com o `T-FMT-OMIT-OR-DECLARE`? Aquele ticket define as três categorias (dedutível / convenção-default / declaração-obrigatória) — este é a **implementação** da terceira para dois casos concretos. |

## O que NÃO é

- **Não é** checksum de integridade (`BUG-12`/`T-FMT-META-STRICT` cobrem corrupção).
- **Não é** proposta de tirar o comportamento posicional da ADR-0029 — é dar a ele um modo
  **verificável** ao lado.
- **Não** toca `src/tcf` sem aprovação: liga o wire quando o knob está ligado, logo
  **re-pina** qualquer baseline que use `drop_names` (hoje: nenhum gate usa).

## Critérios de aceite

- [ ] Q1–Q3 decididas pelo owner
- [ ] Lab (mock, `src/tcf` intocado) medindo: custo da assinatura, e prova de que contrato
      trocado **falha alto** em vez de devolver dado errado
- [ ] Se aprovado: ADR que registre a relação com ADR-0029 e com `T-FMT-OMIT-OR-DECLARE`
- [ ] Gates byte-canônicos verdes (nenhum usa `drop_names` hoje — verificar antes)
