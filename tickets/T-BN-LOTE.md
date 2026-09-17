---
title: T-BN-LOTE, opt-in de emissão do modo `C` do bN de domínio
status: open
created: 2026-09-16
updated: 2026-09-16
target: ".9 (otimização)"
blocked-by: []
related:
  - docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md
  - docs/reference/familia-bn-bits.md
  - docs/reference/encode-knobs.md
---

# T-BN-LOTE

**[registro. Nada em `src/tcf` sem aprovação.]**

## Por que este arquivo existe

O nome era citado sem arquivo desde 2026-07-27, quando o weld do bN de domínio (commit
`35be493b`) o pôs numa tabela de pendentes do `STATUS.md`. A desfragmentação de 2026-08-23
(commit `3f9fbbe8`) tirou a tabela da superfície. Três citações que não se editam ficaram sem
destino: duas no [ADR-0036](../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md) e o
comentário em `src/tcf/encoder.py:716`. Este ticket registra só o que os documentos já dizem.

## O que é

O bN de domínio tem dois modos: `B`, com o domínio antes dos bits, e `C`, com o domínio depois.
O `C` custa cerca de 1 B a menos e não streama, porque o leitor precisa do payload inteiro antes
do primeiro valor. A troca e a medição do prefixo estão no ADR-0036 e em
[`familia-bn-bits.md`](../docs/reference/familia-bn-bits.md).

No código, `candidatos` devolve os dois modos (`src/tcf/composicional/dominio_bn.py:118-122`), e
os três pontos do encoder que consultam o bN ficam só com o primeiro, o `B`
(`src/tcf/encoder.py:665`, `:718` e `:815`). O decode lê o `C`, e o
`test_C_continua_decodavel` cobre isso (`tests/test_dominio_bn.py:102`).

## O que já está decidido

`B` é o default e `C` só entra quando declarado (owner, 2026-08-07, commit `ee807c09`). A escolha
entre os dois não está em aberto; falta a superfície que permite declarar.

## O que resta decidir

A forma da declaração: um knob próprio (`bn_modo="B"|"C"`) ou um valor que cai de um perfil. As
duas estão na nota de previstos de [`encode-knobs.md`](../docs/reference/encode-knobs.md). Os
perfis são a hipótese H-PROFILE-01 do
[registry](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md).

## Critério de aceite

- [ ] o encoder emite o modo `C` quando declarado, e só então
- [ ] sem declaração, o wire sai byte a byte igual ao de hoje
