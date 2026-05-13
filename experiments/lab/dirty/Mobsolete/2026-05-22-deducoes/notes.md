# Lab 22: deduções — análise honesta

## Resultados

| Cenario | literal | base | D-all | D-all vs base |
|---------|--------:|-----:|------:|--------------:|
| C1 emails-10 | 180 | 95 | 95 | 0% |
| C2 codigos | 280 | 131 | 131 | 0% |
| C3 dups | 80 | 64 | 62 | -3.1% |
| C4 emails-dom-unico | 380 | 176 | 176 | 0% |
| C5 26-idx | 312 | 166 | 166 | 0% (RT FAIL D-all) |

**Avg D-all vs base: -0.62%** — ganho marginal.

## Achados honestos

**D1 (idx por contagem)**: zero efeito nesses cenarios. So
ajudaria onde ha muitos literais numericos no meio — caso raro.

**D2 (alfabeto a-z)**: bug detectado. Ambiguidade fundamental:
com letras como idx, decoder NAO sabe se "a" no body eh ref ou
literal — precisaria do `_` justamente para desambiguar (oposto
da intencao). Em C5 (26 strings com letras como middle: `PROD-a-
2026`), conflito direto.

**D3 (eq omitido)**: ganho -3.1% em C3 (dups puros). Mas adiciona
header `#mode:lineRle` que custa 13B — em datasets pequenos,
zera.

## Conclusao

Deduções **NAO escalam** como esperavamos:
- Em datasets pequenos/medios (50-200 vals), ganho < 5% em melhor caso
- Em casos com letras como middle, D2 (alfabeto) introduz ambiguidade
- D1 e D3 sao casos especiais raros

**Decisao**: deduções ficam como **flags opt-in para ablacao**, nao
default. O custo de complexidade nao se justifica no encoder.

Cenarios futuros gigantes (>1000 vals) podem mostrar ganho diferente
— validar em lab 23.

## Bug em D2 — registrar

```
strings: PROD-a-2026, PROD-b-2026, ..., PROD-z-2026

D-all output:
*PROD- a *-2026     ← idx 1=PROD-, mid "a", idx 2=-2026
a b b                ← idx a (= 1, PROD-) + mid "b" + idx b (= 2, -2026)
                     ↑                ↑
                     |                ambiguidade: "b" eh literal?
                     ref idx a OK
```

Decoder ve `a b b` e nao sabe se "b" middle eh literal ou ref. Como
nao ha `_b`, interpreta como ref (que da PROD- + -2026 + -2026 errado).

**Solucao**: deduções de alfabeto so valem se nao ha letras
ambiguas no middle. Detectar isso em runtime adiciona complexidade —
NAO vale.

## Status

- [x] D1, D2, D3 implementados
- [x] 4/5 RT OK (D2 falha em C5 por ambiguidade)
- [x] Ganho marginal: -0.62% medio
- [x] Achado honesto: deduções nao escalam
- [ ] Validar em escala (lab 23)
