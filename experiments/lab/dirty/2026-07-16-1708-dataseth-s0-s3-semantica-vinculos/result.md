# Resultado — DatasetH S0–S3

**[probatório]** A fonte numérica é [outputs/24-resultado.txt](outputs/24-resultado.txt), regenerada por `run.py`. O round-trip completo é comparado byte a byte com [intermediates/01-corpus-canonico.json](intermediates/01-corpus-canonico.json).

## Hipóteses sob teste

1. Um codec explícito pode funcionar como oráculo sem antecipar o wire canônico.
2. Um IR de nós/arestas/lanes separa semântica da representação física.
3. `counts`, `offsets`, `parent-index` e `steps` são conversíveis quando compartilham domínio ordenado de pais e payload ordenado de arestas.
4. Bits de início sem skip/step não preservam pais vazios intermediários.

## Resultado observado

- RT semântico: **20/20**;
- equivalência dos portadores de vínculo: **20/20**;
- contraprovas fail-loud: **8/8**;
- wires `.tcf`: **20**, 801 B totais apenas como observação;
- round-trip do corpus: **byte-idêntico** ao canônico;
- import ou alteração de `src/tcf`: **não**.

As três primeiras hipóteses sobreviveram ao corpus. A quarta recebeu contraprova construtiva:
parent-index `[0,2,2]` e `[0,1,1]` geram os mesmos bits `[start,start,continue]`; sem step/skip ou
outro portador dos vazios, a topologia não é injetiva.

## Leitura conservadora

Passar o gate confirma somente capacidade no corpus sintético e equivalência algébrica das quatro formas implementadas. Não decide header, forma física default, bytes, paralelismo ou weld. Essas decisões pertencem a S4–S7 e exigem perfis realistas/real-world.
