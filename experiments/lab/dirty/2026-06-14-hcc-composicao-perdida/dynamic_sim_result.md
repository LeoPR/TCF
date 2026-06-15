# Result — custo DINAMICO H-HCC (a "matemagica"): Re-Pair sobre a sequencia completa

**Data**: 2026-06-14 · **Status**: confirmada-empirica (decisao: **adiar weld**) ·
confianca: Alta · **Tipo**: [probatorio] · FORK (nao toca src/tcf)

## Pergunta do owner

"pegar a estrutura abstrata pra ver se e' possivel fazer uma matemagica" — um
detector dinamico que pegue a composicao que o detector atual perde (H-HCC-01),
com custo recalculado conforme as composicoes sao montadas (H-HCC-02).

## A estrutura abstrata (a "matemagica" identificada)

O problema E' **grammar compression (Re-Pair)** sobre a sequencia completa de
atoms por linha (lit-def + refs), com net medido em BYTES textuais (nao
frequencia). O detector atual e' um Re-Pair restrito que (a) so' conta
adjacencias ref-ref (perde a def-as-lit) e (b) ja' reconta a cada pick.

`dynamic_sim.py` simula o Re-Pair completo: recontagem a cada pick (trata
**overlap**), id composto crescendo (**width dinamico**), comparando sob o MESMO
modelo de custo `extended` (todas adjacencias) vs `refs-only` (~ detector atual).
`realized_extra = extended - refs-only` = ganho novo, controlado pelo modelo.

## Resultado (8 datasets reais, ROWS=2000, RT OK em todas)

```
realized_extra = 1.30% weighted (TODAS as colunas) / 2.08% (so' as afetadas)
```
Concentrado 100% em FREE-TEXT (numerico/categorico/curto = 0):

| coluna | %body | rules | r@80% | net/rule |
|---|---:|---:|---:|---:|
| tpch l_comment | 3.12% | 752 | 428 | 2.10 |
| br-pessoas data_cadastro | 2.63% | 612 | 320 | 0.87 |
| ibge municipio | 2.61% | 451 | 154 | 1.39 |
| br-pessoas nome | 2.59% | 1093 | 227 | 0.64 |
| retail Description | 2.28% | 382 | 203 | 1.65 |
| receita cnae_principal | 1.52% | 136 | 77 | 1.15 |
| br-pessoas email | 1.29% | 1521 | 419 | **0.34** |
| ibge microrregiao | 1.21% | 73 | 45 | 1.81 |

## Leitura — o ganho e' CAUDA LONGA, nao 80/20

1. **A matemagica funciona** (RT limpo): o Re-Pair estendido captura as
   composicoes que o detector perde. Confirmado.
2. **Mas o ganho e' modesto E fragmentado**: 1.3% weighted (teto), e exige
   **centenas-milhares de regras** de fracoes de char cada (net/rule 0.34-2.10).
   `r@80%` mostra que nem 80% do ganho vem de poucas regras: email precisa de 419
   regras, l_comment 428, nome 227. **Nao ha' subconjunto barato** (threshold por
   net/rule mantem poucas regras mas captura quase nada — a media ja' e' baixa).
3. **Ainda e' TETO**: nao enforca feasibility de body-order (decoder) nem o custo
   real de definir milhares de aliases inline. O ganho welded ficaria ABAIXO.

## Decisao: ADIAR o weld (`closed-insufficient-gain` por ora)

Welder isto no **detector core** (codigo mais sensivel, sob o GATE real-world,
com emit de body-order pra milhares de aliases) por um teto de ~1.3% weighted
que se fragmenta em cauda longa = **ROI baixo, risco alto**. Anti-incidente
2026-05-21 (Pacote 2 escape: 15.7% sintetico -> 0.13% real -> closed): aqui o
real-world ja' diz 1.3% teto, antes de feasibility.

**Reavaliar SE**: surgir um emit de composicao barato o suficiente pra mudar o
net/rule, ou se free-text dominar um caso de uso real (hoje o fallback V2-A +
V2-B ja' cobrem low-card; free-text e' o resto). Melhores alvos agora: **V2-D
strip sufixo** (barato, lossless) e **V2-C lossy** (teto maior) — roadmap ADR-0018.

## Artefatos
- `analyze.py` — upper-bound estatico (1.21% weighted, ignora overlap/width)
- `dynamic_sim.py` — Re-Pair dinamico (overlap+width), 1.30% weighted, RT OK
- `result.md` — H-HCC-01 (a composicao perdida, diagnostico no detector)
