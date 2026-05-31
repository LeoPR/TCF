# Resultado — Sub-exp 06 (H-DA-09 auto-hint regression D1-D9)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Tabela**: [summary.md](summary.md)

## Resumo executivo

**H-DA-09 forma simples (always-on) REFUTADA.** Hint
`prefer_shape_consistency=True` regride bytes em 5 de 9 datasets
quando aplicado a dados sem cadencia explicita (D1-D9). Total
regressao: +275 bytes (+17%) sobre baseline.

Hint **NAO pode ser default-on**. Caller (Pre stage) precisa
decidir quando habilitar.

## Tabela

| Dataset | bl | fork | Δ | Resultado |
|---|---:|---:|---:|---|
| D1-emails-simples | 118 | 104 | **-14** | ganho |
| D2-emails-quote-id | 166 | 169 | +3 | regressao leve |
| D3-stress-substring | 177 | 185 | +8 | regressao leve |
| D4-caos-mix | 113 | 113 | 0 | empate |
| D5-padroes-multiplos | 281 | 484 | **+203** | **regressao alta** |
| D6-poucos-em-ruido | 287 | 354 | +67 | regressao moderada |
| D7-aninhamento | 215 | 315 | +100 | regressao moderada |
| D8-cabeca-cauda | 100 | 100 | 0 | empate |
| D9-frequencia-alta | 158 | 66 | **-92** | **ganho grande** |
| **Total** | **1615** | **1890** | **+275** | **regressao +17%** |

RT 9/9 OK (sem corrupcao, so' bytes piores).

## Padrao observado

**Hint AJUDA quando**: strings tem shape natural consistente
(D9 wrapper `@@@KEY=valueX@@@` — ja' tem mesma shape) → -58%.

**Hint ATRAPALHA quando**: strings tem shapes variadas (D5 email
+ UUID coexistentes) → +72%. Forca OBAT a usar sources/lens
sub-otimos.

## Conclusao operacional

Hint precisa ser **opt-in pelo caller**, OU Pre stage precisa
**auto-detectar** se data tem cadencia.

Heuristicas possiveis pra auto-detection (nao testadas neste
sub-exp):
1. **Length uniformity**: se todas strings tem mesma length →
   sinal de cadencia → enable
2. **LCP-LCS pattern stability**: medir LCP entre primeiros pares;
   se constante → enable
3. **Hybrid**: tentar com hint nos primeiros N, comparar com
   tentativa sem; escolher melhor (mas perde single-pass!)

Hipotese complementar **H-DA-09b** (registrar): auto-detection
sofisticada e' POSSIVEL mas requer mais design. Por enquanto,
hint fica opt-in.

## Achado adicional — D9 e D5 sao casos extremos

**D9 wrapper pattern**: ganho enorme (-58%) sugere que H-DA-07
opera muito bem em dados "wrapper + slot variavel". Caso pra
estudar mais.

**D5 mixed patterns**: regressao massiva (+72%) — H-DA-07 quebra
muito quando shapes sao genuinamente diferentes. Caso pra
documentar como "anti-padrao".

Ambos registrados como hipoteses futuras:
- **H-DA-11**: H-DA-07 e' especialmente eficaz em "wrapper + slot"
  patterns (D9 testou; investigar mais)
- **H-DA-12**: detectar quando shapes sao genuinamente diferentes
  pra desabilitar hint (anti-pattern detector)

## Status H-DA-09 no roadmap

**refutada parcial** — forma simples (always-on) regride 5/9
datasets stress. Forma auto-detect (com Pre heuristic) fica
em aberto como **H-DA-09b**.

## Arquivos

```
06-auto-hint-regression-D1-D9/
├── README.md
├── run.py
├── summary.md
├── result.md
└── outputs/D1..D9/
    ├── 1-tokens-canonical.txt
    ├── 2-tokens-fork.txt
    ├── 3-body-baseline.tcf
    ├── 4-body-fork.tcf
    └── 5-rt-status.txt
```
