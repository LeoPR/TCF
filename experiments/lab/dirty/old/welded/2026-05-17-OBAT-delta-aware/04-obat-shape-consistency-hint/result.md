# Resultado — Sub-exp 04 (H-DA-07 OBAT shape-consistency hint)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Tabela**: [summary.md](summary.md)
**Detalhes**: `outputs/<ds>/`

## Resumo executivo

**H-DA-07 confirmada empiricamente.** OBAT com hint generica
`prefer_shape_consistency=True` reduz mais 93 bytes em D11a-h
alem do ganho da tentativa 02. RT 8/8 OK.

| Pipeline | Total bytes | vs baseline |
|---|---:|---:|
| Baseline (OBAT canon + HCC canon) | 958 | — |
| Tentativa 02 (OBAT canon + HCC fork seq-RLE) | 745 | -22.2% |
| **Sub-exp 04** (OBAT fork shape-preserve + HCC fork) | **652** | **-32.0%** |

Ganho de 04 vs t02: **-93 bytes (-12.5%)**.

## Tabela por dataset

| Dataset | baseline | t02 | sub-exp 04 | Δ vs t02 | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| D11a (dias) | 87 | 84 | 71 | **-13** | -16 |
| D11b (bordas) | 173 | 173 | 153 | **-20** | -20 |
| D11c (mensal) | 109 | 78 | 72 | -6 | -37 |
| D11d (min) | 110 | 73 | **61** | -12 | **-49** |
| D11e (mes-dt) | 121 | 90 | 84 | -6 | -37 |
| D11f (ms) | 115 | 78 | 66 | -12 | -49 |
| D11g (us) | 120 | 83 | 71 | -12 | -49 |
| D11h (ns) | 123 | 86 | 74 | -12 | -49 |

## Bug-fix decorrente do experimento

Durante sub-exp 04, identifiquei bug no detector `compare_for_seq` do
`hcc_fork.py` (tentativa 02): exigia que TODAS posicoes dentro de
escape-digit runs estivessem em diffs. Quebrava o caso onde literal
multi-digit muda so' um char (ex: `\10` → `\11`, diff posicao 3 so',
mas run inteira interpretada como int 10 → 11).

**Fix aplicado em `02-.../hcc_fork.py`** (escopo: relaxar checagem,
agora aceita "todas diffs DENTRO de runs + delta unico entre runs").

**Impacto no t02**: 0 bytes (OBAT canonical nao produz literais
multi-digit, entao bug nunca disparava). Tentativa 02 re-rodada
post-fix produz mesmos 745 bytes. Nenhuma regressao.

**Impacto no sub-exp 04**: antes do fix, ganho era -46B; apos
fix, -93B (dobrou). O fix era pre-requisito pra H-DA-07 funcionar
plenamente, ja' que a hint produz literais multi-digit como "10",
"11", "12" — exatamente o caso que o bug bloqueava.

## Mecanismo (concreto, D11d)

### Tokens

Canonical OBAT (s11-s13):
```
[11] P(1,14) + L('1') + S(1,4)   ← shape mudou (P=14, S=4)
[12] P(11,15) + S(2,4)            ← shape diferente (P+S, sem L)
[13] P(11,15) + S(3,4)            ← shape diferente
```

Fork OBAT com shape-preserve (s11-s13):
```
[11] P(1,14) + L('10') + S(1,3)  ← shape (P=14, L, S=3)
[12] P(1,14) + L('11') + S(1,3)  ← MESMA shape
[13] P(1,14) + L('12') + S(1,3)  ← MESMA shape
```

### Body resultante

t02 (D11d, 73 bytes):
```
\2026-\05-\15 \09:*\0*\0*:\00
1~2\1*4
*8+1|5\2*4
1\1*3,4            ← s11 (estrutura propria)
1~15,6,4           ← s12 (estrutura propria com virtual)
16,7,4             ← s13 (estrutura propria)
```

Sub-exp 04 (D11d, 61 bytes):
```
\2026-\05-\15 \09:*\0*\0*:\00
1~2\1*4
*8+1|5\2*4
*3+1|1\10*4        ← s11-s13 compactados em 1 run
```

12 bytes economizados (24 → 12), e 4 linhas viram 4 (uma a menos
no body fisico, mas com mesma cobertura).

## Ganho inesperado em D11b (bordas)

D11b foi previsto como "0 ganho" pelo sub-exp 03 (sem cadencia
clara). Mas H-DA-07 deu **-20 bytes**.

Mecanismo: shape-preserve forca OBAT a usar mesma SOURCE STRING
em s2-s5 (todos referenciam s1, prefix=6). Isso gera padrao mais
uniforme nos bodies, mesmo sem seq-RLE compactando.

Canonical OBAT escolhia greedy max LCP por par, encadeando refs
s1→s2→s3→s4 (chain). Fork OBAT mantem todos referenciando s1
(parallel). Pattern parallel reusa mais frags de s1, reduzindo
overhead total.

Insight: hint shape-preserve melhora bodies mesmo SEM seq-RLE
compactacao. **Beneficio secundario nao previsto.**

## Validacao

- **RT 8/8 OK** (decode fork reconstroi rows exatos)
- **0 regressoes**: nenhum dataset piorou
- **Ganho em 8/8 datasets** (mesmo D11b ganhou)
- **Outputs inspecionaveis** em `outputs/<ds>/` (5 arquivos
  por dataset incluindo diff lado-a-lado)

## Implicacoes pras outras hipoteses

- **H-DA-07 confirmada**, com magnitudes maiores que previstas
- **Q15** (OBAT quase pronto) — confirmada com nuance: HCC sozinho
  extrai 22%, mas OBAT + HCC integrados extraem 32%. O "quase
  pronto" precisa de pequena ajuda direcionada.
- **H-DA-02** (dica generica) — confirmada como viavel.
  `prefer_shape_consistency=True` e' dica generica, type-agnostic,
  e funciona. Q16/Q17 (API da dica) respondidas: dica boolean
  simples e' suficiente, sem viciar.
- **Tripartite Pre/OBAT/HCC** valida: Pre pode emitir hint, OBAT
  permanece type-agnostic, HCC materializa.

## Limitacoes conhecidas

1. **Hint global**: aplica a coluna inteira; nao adapta por linha
2. **Sem detecao automatica de cadencia**: hint vem do caller
3. **Detector ainda restritivo**: rejeita pares onde runs tem
   deltas mistos (ex: D11b lines 3-4 `9\2-\28` vs `9\2-\29` —
   uma run delta=0, outra delta=1 — rejeita)
4. **Cardinality transitions multiplas**: testado so' uma transicao
   por coluna (9→10). Multiplas (99→100, 999→1000) nao testadas.

## Hipoteses decorrentes (registrar)

- **H-DA-08**: detector que aceita per-run delta encoding poderia
  capturar pares como `9\2-\28` / `9\2-\29` (-6B em D11b)
- **H-DA-09**: hint pode ser inferida pelo Pre-stage observando
  primeiras N strings (sem caller explicitar)

## Status H-DA-07 no roadmap

**confirmada** — magnitude maior que estimada (~93B vs estimativa
~60B), beneficio secundario em D11b nao previsto.

## Arquivos gerados

```
04-obat-shape-consistency-hint/
├── README.md
├── obat_fork.py       (processar_with_hint)
├── run.py             (executor + 3 pipelines comparativos)
├── summary.md         (tabela rapida)
├── result.md          (este)
└── outputs/<ds>/
    ├── 1-tokens-canonical.txt           (OBAT canonical greedy)
    ├── 2-tokens-fork.txt                 (OBAT fork shape-preserve)
    ├── 2-tokens-fork-log.txt             (log do processar_with_hint)
    ├── 3-body-fork-canonical-obat.tcf    (canonical OBAT + HCC fork = t02)
    ├── 4-body-fork-fork-obat.tcf         (fork OBAT + HCC fork = sub-exp 04)
    ├── 5-rt-status.txt                    (numerico)
    └── 6-diff-bodies.md                   (diff lado-a-lado pra t02 vs 04)
```
