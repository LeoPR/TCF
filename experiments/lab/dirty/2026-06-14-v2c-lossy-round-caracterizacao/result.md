# Result — V2-C lossy-round: nicho pequeno (alta-precisao decimal)

**Data**: 2026-06-14 · **Status**: confirmada-empirica (decisao do owner pendente) ·
confianca: Alta · **Tipo**: [probatorio] · FORK (nao toca src/tcf)

## Contrato medido

Lossy-round como **pre-transform pedido pelo usuario**: arredonda colunas
numericas-decimais a D casas (1x, explicito), TCF armazena/recupera EXATO o
arredondado. `decode == round(x, D)`. Erro maximo absoluto = 0.5*10^-D
(deterministico, declarado). So' arredonda colunas >=90% float E precisao > D.

Mede o headroom SOBRE o estado welded (split+V2-B ja' capturam o lossless).

## Resultado (8 datasets reais, ROWS=5000)

```
WEIGHTED (corpus):  d=3: 1.0%   d=2: 1.5%   d=1: 4.6%
```

| dataset | d=2 | d=1 | #cols hi-prec |
|---|---:|---:|---:|
| wine | **15.2%** | 34.3% | 4 |
| beijing | 0.0% | 6.6% | 0 |
| online | 0.0% | 4.8% | 0 |
| tpch | 0.0% | 1.8% | 0 |
| adult / br / receita / ibge | 0.0% | 0.0% | 0 |

Onde vive o nicho (colunas >=3 casas, >=90% float) — **so' wine**:

| coluna | prec | baseSC | d=2 | d=1 |
|---|---:|---:|---:|---:|
| wine.density | 5 | 23403 | 7998 | 12 |
| wine.chlorides | 3 | 21583 | 15346 | 5824 |
| wine.volatile_acidity | 3 | 20340 | 19200 | 13005 |
| wine.alcohol | 14* | 17790 | 17879 | 17735 |

(*alcohol prec=14 = artefato float "9.4000..."; round nao ajuda, ate' piora.)

## Leitura

1. **Nicho pequeno e concentrado**: 1.5% weighted @ d=2 (precisao defensavel),
   **inteiramente de wine** (dados de medicao cientifica). Os outros 7 datasets
   = 0% @ d=2. O split+V2-B ja' welded resolvem o decimal de negocio (preco `.00`,
   qtd) losslessly -> lossy nao adiciona la'.
2. **Ganhos a d=1 sao agressivos**: online 4.8% / beijing 6.6% @ d=1 = arredondar
   preco/medicao a 1 casa, mudanca semantica real. Nao e' "quase-lossless".
3. **Dentro do wine, concentrado em density** (0.99xx -> 1.00 quase-constante).
4. **Cruza a linha filosofica**: e' o unico lever que quebra o RT-exato (mesmo no
   enquadramento "round explicito", o dado recuperado != original).

## Decisao (do owner)

Trade-off: ~1.5% weighted (so' dados cientificos de alta-precisao) vs. a pureza
lossless como diferencial do TCF. **Recomendacao**: a pureza lossless vale mais
que 1.5% num nicho unico — manter TCF estritamente lossless por default e
documentar o limite (alta-precisao decimal nao comprime losslessly). SE welder,
estritamente opt-in nature (nunca automatico, header declara precisao). Decisao
do owner.

## Artefatos
- `analyze.py` — headroom lossy-round por dataset/casas + nicho hi-precisao
