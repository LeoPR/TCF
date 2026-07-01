# Gate N>=5 do B2 cross-dict — resultado [probatório]

**Data**: 2026-07-01. Roda o prototype nas **5 fontes same-domain reais** (T-DATA-1 baixado).
`share` = B2 vs V1 (dict per-col) = o valor REAL do cross-dict, isolado do dict-vs-OBAT/HCC.
Grafos grandes amostrados (40k arestas). Script: [run_gate.py](run_gate.py).

## Resultado (5 fontes, 5 morfologias, 1 não-grafo)
```
fonte (morfologia)            share   gzip-share  pool?  nota
SNAP ca-GrQc (colaboracao)   -19.3%    -21.0%      sim   K=5242 -> col e uniao no MESMO bucket (w=2)
OpenFlights (transporte)      -4.6%     -7.6%      sim   sub-15% (K pequeno, dict pequeno vs N)
futebol (esporte, NAO-grafo)  -1.5%     -2.1%      sim   sub-15% (K~300 times, dedup minusculo)
cit-HepTh (citacao)          +30.6%    +22.7%      NAO   uniao CRUZA bucket (w 2->3) -> B2 PERDE
email-Enron (comunicacao)    +18.6%    -14.5%      NAO   uniao CRUZA bucket -> B2 PERDE
```

## Veredito: o cross-dict (B2) FALHA o gate N>=5
- **share >= 15%: 1/5** (só SNAP). O −19.3% NÃO era representativo — era o caso afortunado onde
  col e união caem no MESMO bucket de largura base-94 (K=5242 pequeno).
- **2/5 o B2 PERDE** (cit-HepTh +30.6%, email-Enron +18.6%): em grafos de citação/email reais, os
  conjuntos de nós são grandes o suficiente pra a **união cruzar o bucket** (w 2→3), o custo de
  largura dispara, e o greedy corretamente **recusa o pool** (grp=0). É exatamente a borda que o
  design previu — agora acontecendo em dado real, não sintético.
- **Padrão anti-incidente 2026-05-21 confirmado**: resultado forte num dataset (SNAP) que não
  generaliza. **O gate N>=5 pegou isso ANTES do weld** — funcionou como projetado.

### O que SE SUSTENTA do B2
- **Segurança**: o greedy é self-gating — só pool quando paga (B2 < baseline real). Onde perde,
  recusa. Então B2, se weldado opt-in, **nunca regride** — mas a REACH é estreita (só same-domain
  de K pequeno onde os buckets alinham: SNAP-like).
- **Porta estrutural** (decodes C→1) vale onde pool (3/5), mas o byte-ganho é ≥15% em só 1/5.
- **Conclusão**: não vale o custo de formato (#TCF.8 + prelúdio + modo `&<G>`) pra 1/5. **Não weldar
  como feature geral.** Fica como opt-in de nicho (greedy-gated) OU fechado
  `CLOSED-INSUFFICIENT-GENERALIZATION` (como o escape-deduction).

## O PIVÔ: o achado robusto é o dict per-col high-card (H-DICT-HIGHCARD), NÃO o cross-dict
A componente `dict` (dict-vs-OBAT/HCC) é robusta em 4/5:
```
SNAP -29.6% | OpenFlights -35.1% | cit-HepTh -23.4% | email-Enron -15.7%  (futebol +0: K<=1024 ja' era dict)
```
Ou seja: **um dict per-coluna SEM o cap 1024 vence OBAT/HCC em −16 a −36%** em TODA coluna
categórica high-card de alta-repetição — e sobrevive gzip. **Este é o ganho geral e robusto** que o
prototype descobriu, ortogonal e MAIOR que o cross-dict. cit-HepTh/email-Enron: dict ganha (−23/−16%)
mas cross-dict perde — a história se inverte.

## Recomendação
1. **B2 cross-dict**: NÃO weldar como geral. Fechar/encostar (niche opt-in greedy-gated, seguro mas
   estreito). Só SNAP-like (K pequeno, buckets alinhados) paga ≥15%.
2. **H-DICT-HIGHCARD**: PROMOVER — rever o gating do V2-B (`_V2B_MAX_CARD=1024`) por **N/K
   (repetição)**, não só K. Robusto em 4/5, −16..−36%, sobrevive gzip. Caracterizar + gate próprio.

O gate cumpriu o papel: separou o afortunado (SNAP cross-dict) do robusto (dict high-card).
