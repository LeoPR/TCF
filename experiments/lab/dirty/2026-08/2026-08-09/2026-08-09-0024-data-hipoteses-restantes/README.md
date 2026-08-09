# Data — hipóteses restantes (esboço de triagem)

**2026-08-09 · dirty/esboço** · `python run.py`

Reavaliação depois dos 5 labs de data: o que **não** foi coberto? Sete hipóteses saíram;
este lab é a triagem sintética de controle — as que sobrevivem ganham lab próprio e depois
vão pro clean.

## Como achar pelo nome

```
run.py                      as 7 hipóteses, geradores determinísticos (LCG semente fixa)
inputs/geradores--*.json    higiene + amostra de cada família
outputs/medicoes.md         as tabelas por hipótese
outputs/h2-uteis--*.tcf     os wires de dias-úteis (spec vs delta) pra inspeção
outputs/h6-*--h-delta.tcf   o wire do delta no espalhado-ordenado
result.md                   O PLACAR: 2 sobrevivem forte, 1 weld pequeno, 1 morta
```

## O placar em uma linha

**H6+H2 (alvo DELTA de coluna)** é a maior oportunidade restante — 5,8–6,8× em dias-úteis e
espalhado-ordenado. **H1 (spec→bN no candidato)** é weld pequeno com lacuna até 298 B.
**H7 (colunas irmãs) morreu**: 3% de lacuna não paga mecanismo. H3/H4/H5 confirmados OK.

`src/tcf` **não é tocado**.
