---
title: T-FMT-QUOTING-STUDY — estudo de quoting/escaping de nomes além do backslash interim (filho de T-FMT-NAME-ESCAPING)
status: open
priority: P3
created: 2026-07-10
updated: 2026-07-10
gate: ".9"
blocked-by: []
related:
  - tickets/T-FMT-NAME-ESCAPING.md
  - tickets/T-FMT-META-STRICT.md
  - tickets/T-FMT-TCF8H-HEADER.md
  - src/tcf/multi/core.py
---

# T-FMT-QUOTING-STUDY — o estudo que o interim deixou pra depois

**[dispositivo→registro]** Filho de [T-FMT-NAME-ESCAPING](T-FMT-NAME-ESCAPING.md) (fechado
`closed-parcial` no Passo 1 do [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md)). Decisão do owner
(2026-07-09, M2): "por enquanto só barra, deixando o estudo de outros casos para depois (até pra
ver se tem quebras ou se apenas o barra já resolve tudo)". Alvo: **.9** (junto da hierarquia,
que adiciona chaves `{}[]` ao meta — o caso que mais pressiona o quoting).

## O que o interim (backslash) já provou no .8

- Escapa `,=:\` + prefixo `!@%` inicial; tokenizer split em separador NÃO-escapado; só `\n`
  proibido. Welded em M2 (`58f7dee`), fuzz ~310 checks sem falso-positivo (verificação F0 lote 3);
  whitelist estrita no decode (`_ESC_OK`, BUG-11b `a0f30ae`).
- Custo observado: 1 byte por char estrutural no nome (raro em dado real; medível no material
  comprobatório F2 — nomes com separador são caso de controle).

## Perguntas do estudo (.9)

1. **O barra resolve tudo?** — evidência do .8 diz que sim pro FLAT (fuzz + material F2). A
   hierarquia (`#TCF.8H`, chaves `{}[]` no colchete-meta) adiciona colisões novas — o interim
   escala ou precisa de quoting?
2. **CSV-quoting** (nome entre aspas, aspas dobradas escapam): melhor legibilidade pra nomes
   cheios de separador (1 par de aspas vs N barras); pior pro caso comum (2 bytes sempre).
   Medir o trade em dados reais (headers do mundo: Adult/TPC-H/retail têm quantos nomes "sujos"?).
3. **Quoting implícito/smart** (a ideia original do owner): quotar SÓ quando compensa — o meta
   ganharia 2 formas de nome (grammar cost) em troca de bytes; avaliar contra T-FMT-OMIT-OR-DECLARE
   (toda forma nova precisa ser não-ambígua e dedutível).
4. Interação com **T-FMT-META-STRICT**: qualquer forma nova mantém a propriedade "só aceita o que
   o encoder emite" (dedução do cânone) — nada de leniência.

## Critérios de aceite

- [ ] Medição em headers reais (frequência de nomes com separador) — decide se o estudo avança.
- [ ] Se avançar: proposta única (barra vs CSV-quote vs smart) com bytes medidos + gramática
  não-ambígua + RT fuzz, gated pelo material da era .9.
- [ ] Decisão registrada em ADR se mudar o formato do meta.
