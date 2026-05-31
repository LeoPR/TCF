# Lab dirty — Revalidacao Categoria B (2026-05-21)

**Ticket**: [T-REVAL-H-DA-01-06-10](../../../../tickets/T-REVAL-H-DA-01-06-10.md)

**Origem**: revisao conceitual de 2026-05-21 classificou H-DA-01,
H-DA-06, H-DA-10 como `confirmada-empirica` mas nao testadas em
real-world.

**Risco**: Pacote 2 (escape deduction) mostrou que sintetico 15.7%
colapsa pra 0.13-1.13% real-world. Mesmo padrao pode estar latente
nas hipoteses categoria B.

## Sub-exps

1. **`01-h-da-06-subsumida-em-09b-v2/`** — inspecao se H-DA-09b-v2
   (numeric high-cardinality welded ADR-0008) ja' captura colunas-alvo
   de H-DA-06 (numeric IDs) em real-world.
2. **`02-h-da-01-hcc-seqrle-realworld/`** — medicao isolada do ganho
   HCC seq-RLE near-identical em Adult+TPC-H (vs pipeline canonical
   sem fork).
3. **`03-h-da-10-min-len-realworld/`** — varredura min_len ∈ {3,4,5,6}
   em Adult+TPC-H.

## Metodologia

Cada sub-exp segue template anti-incidente (5 perguntas do CLAUDE.md
"Antes de declarar confirmada-empirica"):
1. Real-world testado (Adult Census + TPC-H)?
2. N >= 5 datasets de fontes diferentes?
3. Sintetico vs real comparados?
4. Vies de teste declarado?
5. Bytes absolutos relevantes (>=5% real-world weighted)?

## Resultado esperado por hipotese

- **H-DA-06**: alta probabilidade de SUBSUMIDA (H-DA-09b-v2 mais
  geral cobre numeric IDs em real-world)
- **H-DA-01**: media probabilidade de REFUTADA-REAL-WORLD (D11a-h
  enviesados pra cadencia explicita)
- **H-DA-10**: alta probabilidade de REFUTADA (amostra N=3 sem
  teoria)

Se confirmadas as expectativas, lab fecha 2-3 hipoteses categoria B
e libera foco pra novos pacotes (H-PERF-05d, T02-T07 META-TYPE-ENCODERS).

## Conexoes

- [Ticket T-REVAL-H-DA-01-06-10](../../../../tickets/T-REVAL-H-DA-01-06-10.md)
- [Revisao conceitual](../notas/revisao-conceitual-2026-05-21.md)
- [Roadmap hipoteses](../notas/roadmap-hipoteses.md)
- [Pacote 2 incidente motivador](../2026-05-21-escape-deduction/)
