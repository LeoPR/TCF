---
title: T-DENSO-PADDING, o padding `=` do base64 nos densos `b1` e `b2`
status: open
created: 2026-09-16
updated: 2026-09-16
target: ".9 (otimização)"
blocked-by: []
related:
  - docs/adr/0037-denso-b2-ternario-dominio-implicito.md
  - docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md
  - docs/reference/familia-bn-bits.md
---

# T-DENSO-PADDING

**[registro. Muda bytes do wire; nada em `src/tcf` sem aprovação.]**

## Por que este arquivo existe

O nome nasceu em 2026-07-31 (commit `c47d2a3a`), numa tabela de pendentes do `STATUS.md` removida
em `3f9fbbe8`. A citação que não se edita é o
[ADR-0037](../docs/adr/0037-denso-b2-ternario-dominio-implicito.md), que na seção de consequências
estende o item ao modo `b2`. O inventário do bN de 2026-08-07 o pôs entre o que fica para o `.9`
(commit `44a7be47`). Este ticket registra só o que os documentos e o código já dizem.

## O que é

Os densos de bool emitem o base64 com padding `=` (`src/tcf/encoder.py:830` e `:834`), e o decode
exige essa grafia (`padded=True`, `src/tcf/decoder.py:594-596`). O bN de domínio emite sem padding
(`src/tcf/composicional/dominio_bn.py:130`), porque o comprimento do bloco se deduz de `n` e `w`
(`_b64_len`, no mesmo arquivo, linha 192).

O padding custa 1 ou 2 B sempre que o payload não tem um múltiplo de 3 bytes, o que acontece em
cerca de 2/3 dos comprimentos. O ADR-0037 registra que a dedução proposta vale para `b1` e `b2`.

Não confundir com os bits mortos do último byte, que são outro item da tabela de abertos do
ADR-0036.

## Critério de aceite

- [ ] a grafia sem `=` decidida como mudança de formato antes do weld, porque o decode de hoje recusa o denso sem padding
