# Grafia fracional e escala com exceções — onde o float ainda tem folga

> **Owner (2026-08-14)**: *"tinha o caso desses floats serem colocados em loss mode, ou
> lossless alterando a distribuição numérica… 0.2, 0.4… e aparece um 0.333333333 no meio,
> daria pra arredondar pra caber com o resto. ainda no lossless alterado… 0.333333333333 →
> `1/3…12`… técnicas de arredondamento financeiro que numa possível soma ele não muda."*
>
> E: ***"crie o lab primeiro para ver esses casos, pode começar mais lentamente pra ver os
> efeitos em casos particulares do estudo, depois expandimos."***

Começo lento, de propósito: **casos particulares com par de contra-prova**, não varredura.

## As duas ideias — e por que os gates são diferentes

| | contrato | o que muda | gate |
|---|---|---|---|
| **lossless alterado** | exato | só a **grafia** no corpo | **nenhum** — é candidato de `min()` como outro qualquer |
| **loss mode** | exato-no-agregado | o **valor** | **gateado**: Pacote 10, formato lossless-puro por decisão do owner (2026-06-15) |

Por isso M1–M3 (lossless) passam pelo RT estrito e competem no FLOOR, e **M4 é só medido** —
nunca proposto. Nada aqui toca `src/tcf/`.

## Os quatro mecanismos

| | o quê | estágios |
|---|---|---|
| **M1** | grafia fracional: `0.333333333333` → `1/3~12` | identify (é dízima?) → normalize (fração contínua) → **verify (re-emite igual?)** |
| **M2** | escala pura: `0.25` → `25`, k=2 — **o candidato de hoje** | tudo-ou-nada por coluna |
| **M3** | escala **com exceções** (a ideia do ALP/SIGMOD-2024) | k para a maioria; o resto vai literal |
| **M4** | round com **soma preservada** (maior resto / Hamilton) | **GATEADO — só medição** |

## Estado — era / foi / é / será

- **Era**: eu tinha escrito que a precisão suja *inviabiliza* a escala (`wine.alcohol` perde o
  candidato inteiro). E a ideia da fração estava só registrada, sem lab.
- **Foi**: a pesquisa de literatura mostrou que decimal-como-inteiro **não é tudo-ou-nada** — o
  ALP escala e faz *patching* dos que não fecham.
- **É**: os quatro mecanismos rodam em 7 sintéticos + 8 bordas + 5 colunas reais, **0 falhas**
  no RT estrito. Resultado em [`result.md`](result.md). **Dois defeitos meus foram achados
  pelo próprio lab**, e os dois eram a mesma classe — *um "lossless" que não verifica vira
  lossy calado*.
- **Será**: expandir (o owner já sinalizou), com a varredura do corpus atrás dos regimes que
  estes 5 casos reais não cobrem.

## Os dois defeitos que o lab pegou (1ª rodada, 8 falhas)

1. **A escala testada com tolerância** (`abs(esc-round(esc)) < 1e-9`) aceita
   `0.30000000000000004` em k=1 e devolve `0.3`. **Perda calada num mecanismo lossless.**
   Corrigido: a escala agora **verifica por re-emissão**, via `Decimal(repr(v))` — a mesma
   disciplina do M1, e a multiplicação binária nunca entra na decisão.
2. **A tag-união `int|float` quebra a escala.** Escalar apaga a distinção (`1` em k=12 vira
   `1000000000000`, e volta `1.0`); e se o int virar **exceção**, a grafia literal dele (`1`)
   fica idêntica à de um valor escalado — o decoder não distingue. Corrigido: a escala
   **recusa coluna de tipo misto**. É a peculiaridade #1 do fechamento do float, cobrando.

O truque de "exceção não precisa de lista de posições" **sobrevive**, mas só sob a hipótese
de coluna float pura — porque aí todo `repr` de float traz `.` ou `e`, e todo escalado é
inteiro puro. A hipótese virou guarda explícita, não suposição.

## Como rodar

```
python run.py     # sai 0 só se todo mecanismo lossless fizer RT estrito em todos os casos
```

Roda **sem `Z:`** (as colunas reais são puladas). Não toca `src/tcf/`.

## O RT que vale

Herdado do fechamento do float: `type()` **e** valor **e** sinal do zero — `-0.0 == 0.0` é
`True`, só `math.copysign` distingue. Para M4 o contrato é outro (**exato-no-agregado**) e
está declarado como tal, não disfarçado de RT.

## Contabilidade

Um spec sobre float emitiria `#TCF.8n :xx`; `encode([str,…])` emite `#TCF.8`. A diferença é
`n :xx` = **5 B**, cobrada em `CUSTO_SPEC_ID`; M2/M3 pagam também o expoente k. A grafia
ilustrativa do M1 usa `~`, que **é operador composicional** no formato — o encoder escapa
(`1/3\~12`), e esse byte de escape **está dentro** dos números medidos. Ou seja: os ganhos do
M1 são conservadores; um caractere livre os melhoraria em 1 B por valor.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | o dado e a procedência (gerador, params, ideia) |
| `outputs/<caso>.<mecanismo>.tcf` | os wires |
| `outputs/<caso>.*.roundtrip.json` | a contra-prova (diff vazio contra a entrada) |
| `outputs/<caso>.meta.json` | quem venceu, quantos bytes, quais wires |
| `intermediates/<caso>.M1-diario.json` | a decisão do M1 **valor a valor**, por estágio |
| `intermediates/<caso>.M3-varredura-de-k.json` | o custo de cada k — o budget de busca, aberto |
| `intermediates/M4-loss-gateado.json` | a medição do loss, com o contrato declarado |

## Vínculo

`T-FLOAT-SPEC` · **H-FLOAT-GRAFIA-01** (registrada hoje) · Pacote 10 `H-LOSS-01`/`H-LOSS-03`
(gateados) · fechamento do float [`…-1616`](../2026-08-14-1616-fechamento-float/) ·
PoC do maior resto [`…v2c-lossy-round`](../../../2026-06/2026-06-14/2026-06-14-v2c-lossy-round-caracterizacao/) ·
[`loss-taxonomia.md`](../../notas/2026-06/loss-taxonomia.md) ·
pesquisa [`…-1739`](../../notas/2026-08/2026-08-14-1739-loss-e-lossless-alterado-pesquisa.md)
