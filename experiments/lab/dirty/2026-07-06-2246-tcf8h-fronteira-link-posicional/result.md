# Resultado — fronteira do link posicional + fix nullable/presença (Ciclo 1c) [probatório]

Números: `artifacts/` (`python run.py`). Fecha o Ciclo 1 (funcionalidade).

## As 4 fronteiras no codec tabular (`01-fronteiras-no-tabular.txt`)

| # | forma | no tabular (C-híbrida do 1b) | canal que falta |
|---|---|---|---|
| **B1** | chave-ausente `[{a,b},{a}]` | **CRASH** KeyError | presença (def-level) |
| **B2** | null-em-coluna `[{x:1},{x:null}]` | **CRASH** ValueError | null-mask (def-level) |
| **B3** | array-em-array `{grupos:[{itens:[…]}]}` | **CORROMPE** (coluna vira lista) | repetition level |
| **B4** | N:N `[{aluno,curso}×3]` | **RT-OK (flat)** | normalização/ponte (não é gap de RT) |

Achado-chave: **as fronteiras não são iguais**. B1/B2 são falta de *presença* (mesma coisa); B3 é
*repetição* (mais fundo); B4 nem é gap de RT (o plano fecha — é escolha de estrutura).

## O fix da família nullable/presença (`02-fix-mascara-presenca.txt`) — RT OK

Máscara 3-estados por célula: `.`=valor · `0`=null · `-`=ausente. Dense body = só as células com valor.

```
B1 chave-ausente  in : [{'a':1,'b':2},{'a':3}]
   col(a): dense=[1,2]... col(b): dense=[2] máscara='.-'   out: [{'a':1,'b':2},{'a':3}]   RT-OK
B2 null-em-coluna in : [{'x':1},{'x':None}]
   col(x): dense=[1]     máscara='.0'                       out: [{'x':1},{'x':None}]      RT-OK
```

A máscara é o **definition level do Dremel** (níveis de nulo/presença) em forma **textual inspecionável**
(pilar explicabilidade): vê-se `.-` = "presente, ausente" sem materializar buracos. Custo = 1 char/linha
por coluna esparsa, comprimível por RLE se regular.

## Caracterização (o que fica pro welding)

- **B1 + B2 = um mecanismo** (def-level / máscara) — **provado tratável** aqui, RT-exato.
- **B3 array-em-array** = **repetition level** (onde o array aninhado reinicia). É a peça 10 do EXP-015
  (`report.md`: "array-em-array / N raízes precisa de link posicional"). Não é máscara simples. Deferido.
- **B4 N:N** = o array plano **fecha RT** (é uma tabela). A fronteira é **normalização** (fatorar aluno×curso
  pede tabela-ponte) — escolha de compressão/estrutura, liga com @dict / H-CARD-05/07. Não é gap de RT. Deferido.

Mapeamento a prior-art (já no repo): **Dremel rep/def levels** (Melnik 2010), factorized DBs,
[teoria-cardinalidade](../notas/teoria-cardinalidade.md) H-CARD-06 (order dependency).

## Fecha o Ciclo 1 (funcionalidade)

- **1a** tipos (RT lossless) · **1b** estratégia de tipo A/B/C decidida (C-híbrida default) + escala de formas
  · **1c** fronteiras caracterizadas + nullable/presença provado tratável.
- **RT-alvo comum COBERTO**: aninhamento arbitrário, tipos escalares, esparsidade (nullable/ausente).
- **Próximo salto de estrutura** (welding): repetition level (B3) + ponte N:N (B4).
- → **Ciclo 2 (organização de fluxo S1/S2/S3)**.
