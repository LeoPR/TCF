# Resultado — Sub-exp 05 (H-DA-06: numeric IDs)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Tabela**: [summary.md](summary.md)
**Detalhes**: `outputs/<ds>/`

## Resumo executivo

**H-DA-06 confirmada.** Pipeline OBAT fork shape-preserve + HCC
fork seq-RLE generaliza para IDs numericos sequenciais. RT 3/3 OK.

| Dataset | baseline | t02 | sub-exp 05 | Δ vs t02 | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| D16a (3-digit) | 65 | **11** | 11 | 0 | **-54 (-83%)** |
| D16b (4-digit) | 62 | 35 | **28** | -7 | -34 (-55%) |
| D16c (prefixados) | 70 | 47 | **38** | -9 | -32 (-46%) |
| **Total** | **197** | **93** | **77** | **-16** | **-120 (-61%)** |

## Observacao IMPORTANTE — refinamento de H-DA-04

Sub-exp 03 (audit) concluiu que **H-DA-04 (cadence-break recovery)
era refutada com grammar atual**. Sub-exp 05 mostra que essa
conclusao precisa ser **qualificada**:

H-DA-04 era refutada SOMENTE no caso **com refs ao redor do varying
literal** (estrutura `P + L + S` do D11d). Quando o varying part e'
o **string inteiro** (sem refs), o seq-RLE detector ja' atravessa
transicoes de cardinalidade limpo, porque trata escape-digit runs
como **inteiros** (nao char-a-char).

### Evidencia D16a

Tokens canonical:
```
[1..13] L('100') ... L('112')  — todos literais puros, sem refs
        (LCP entre adjacentes = 2 < min_len 3, OBAT nao cria ref)
```

Body fork t02 (canonical OBAT + HCC fork):
```
*13+1|\100
```

UMA linha! Decodifica:
- k=0: `\100` (lit "100" = 100)
- k=1: shift "100"+1 = "101" → `\101`
- k=2: "102"
- ...
- k=9: "109"
- **k=10**: shift "109"+1 = "110" → `\110` ✓ (atravessa transition!)
- k=11: "111"
- k=12: "112"

A transicao 109→110 (cardinality 3→3, mas digit-by-digit muda 2
posicoes) e' atravessada porque `int("109") + 1 = 110`, formatado
como string com mesmo width = "110".

### Por que D11d nao funcionava assim

D11d body fork (s11) = `1\1*3,4` (com refs 1, 3, 4 ao redor). A
shape muda na transicao (P+L+S → P+L+S com tamanhos diferentes →
S+P diferente, etc.) porque OBAT escolhe diferentemente quando
LCP/LCS mudam. NAO e' o seq-RLE que falha — e' a SHAPE que muda.

Quando OBAT mantem shape (H-DA-07 / sub-exp 04), o seq-RLE consegue.

### Decisao re-revisao

**H-DA-04 status atualizado**: `refutada (com grammar atual) PARA
cenarios com refs ao redor; CONFIRMADA NATURALMENTE pra strings
totalmente-literais (resolvida pelo seq-RLE existente)`.

## Comportamento por dataset

### D16a — IDs 3-digit "100".."112"

- OBAT canonical: 13 literais puros (sem refs)
- HCC fork t02: **1 linha** `*13+1|\100`
- OBAT fork: mesmo resultado (nao ha' refs pra otimizar)
- **Ganho extra do fork OBAT: 0 bytes**

**Insight**: quando OBAT nao consegue criar refs (strings curtas),
HCC fork sozinho ja' resolve tudo via seq-RLE de literais.

### D16b — IDs 4-digit "1000".."1012"

- OBAT canonical: s2-s10 tem refs (P(1,3)+L = "100"+digit), s11-s13
  re-arrumam (carry 9→10 com mais refs)
- HCC fork t02: captura s2-s10 em run, s11-s13 separados → 4 linhas body
- OBAT fork: s11-s13 forcados a shape igual → captura em run extra
- **Ganho extra do fork OBAT: -7 bytes**

Mesmo padrao do D11d com datetime.

### D16c — IDs prefixados "USR-100".."USR-112"

- Prefix "USR-" forca refs longos
- OBAT canonical: similar a D16b mas com prefix
- HCC fork t02: captura s3-s10 em 1 run
- OBAT fork: captura s11-s13 em run extra
- **Ganho extra do fork OBAT: -9 bytes**

Body final:
```
USR-\1*\0*\0       (line 1, s1)
1~2\1              (line 2, s2 com composicao)
*8+1|4\2           (line 3, run s3-s10)
*3+1|1\10          (line 4, run s11-s13)
```

Mesmo padrao estrutural de D11d. Generaliza.

## Implicacoes pras hipoteses

### Confirma generalidade

- **H-DA-06 confirmada**: pipeline funciona em IDs numericos.
- **H-DA-01, H-DA-07** generalizam pra alem de datetime.
- **Vantagem prefixo**: prefixos uniformes ajudam OBAT a criar
  refs grandes, dando mais espaco pra HCC fork compactar.

### Refina H-DA-04

H-DA-04 nao e' refutada em geral — e' refutada **somente quando ha'
refs estruturais ao redor do varying lit**. Sem refs (D16a), seq-RLE
ja' atravessa transicoes de cardinalidade pela aritmetica integer.

**Atualizar roadmap**: H-DA-04 status mais matizado.

### Hipotese decorrente

**H-DA-10**: existe um trade-off entre OBAT criar refs longos
(reduz overhead inicial) vs. nao criar refs (deixa seq-RLE
trabalhar livre). Em D16a (curto), seq-RLE livre = melhor. Em
D11d (longo), refs + seq-RLE = melhor. Decidir quando preferir
qual depende de min_len e tamanho de string.

Nao testar agora — registrar pra futuro.

## Casos limite testados

- **Sem refs (D16a)**: funciona, ganho maximo
- **Com refs + transition (D16b, D11d)**: funciona com OBAT fork
- **Com prefix + transition (D16c)**: funciona similar ao D11d
- **Sem transition**: nao testado nesta sub-exp, mas D11c (mensal)
  ja' provou ganho em datasets sem transition

## Limitacoes

- 3 datasets nao cobrem todo o espaco (random IDs, IDs nao-sequenciais,
  signed deltas com sinais negativos, etc.)
- Nao testado: strings com mistura prefix-suffix variando

## Status H-DA-06 no roadmap

**confirmada** — pipeline generaliza pra IDs numericos sequenciais
com varias estruturas (puros, com prefix, com/sem transition).

## Hipoteses novas decorrentes (registrar)

- **H-DA-10**: trade-off OBAT refs vs HCC seq-RLE puro depende de
  comprimento de strings
- (potencial) **H-DA-11**: strings curtas (< 2*min_len) podem
  beneficiar de min_len menor

## Arquivos gerados

```
05-numeric-ids-h-da-06/
├── README.md
├── run.py             (reusa obat_fork.py do sub-exp 04 + hcc_fork.py do sub-exp 02)
├── summary.md         (tabela rapida)
├── result.md          (este)
└── outputs/<ds>/
    ├── 1-tokens-canonical.txt
    ├── 2-tokens-fork.txt
    ├── 2-tokens-fork-log.txt
    ├── 3-body-fork-canonical-obat.tcf
    ├── 4-body-fork-fork-obat.tcf
    ├── 5-rt-status.txt
    └── 6-diff-bodies.md
```

## Datasets criados (registrar em datasets/synthetic/README.md)

- D16a-ids-3digits.csv
- D16b-ids-4digits.csv
- D16c-ids-prefixados.csv
