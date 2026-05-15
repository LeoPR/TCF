# 2026-05-15 — Naturezas dos dados + estudos da camada de algoritmo

**Estado**: aberto (Onda 1 em planejamento)
**Plano-mestre**: [`tickets/META-TYPE-ENCODERS.md`](../../../../tickets/META-TYPE-ENCODERS.md)
**Origem**: gap identificado no [EXP-008](../../clean/EXP-008-compressao-comparada/) — D10-D15 (variety datasets) e D6 (logs) sem ferramenta no TCF v0.6 atual; pre-tx por natureza + estudos da camada respondem.

## Estrutura

```
2026-05-15-naturezas-e-camada/
├── README.md                          # este arquivo
├── notas/
│   ├── historia-naturezas-camada.md   # narrativa cronologica
│   └── conclusoes_*.md                # 1 por macro fechado
├── pre-tx/                            # Track 1
│   ├── T01-incremental-base-delta/
│   ├── T02-templated-extract/
│   ├── T03-enumerated-dict/
│   ├── T04-checked-elide/
│   ├── T05-high-entropy-passthrough/
│   ├── T06-composite-split/
│   └── T07-hierarchical-shared/
└── algoritmo/                         # Track 2
    ├── L01-comparacao-token-vs-byte/
    ├── L02-slot-detection-online/
    ├── L03-markers-tipados/
    ├── L04-composicao-tree-based/
    └── L05-pre-filter-candidatos/
```

Cada **T0X** (pre-tx) ou **L0X** (algoritmo) e' um macro pequeno
(1-3 dias) com **pergunta cientifica focada**, hipotese, metodo,
dados, conclusao. Quando macro fecha com hipotese confirmada, sub-experimento clean nasce em `EXP-009.X` ou `EXP-010+`.

## Ordem (realinhada 2026-05-15)

**Foco unico:** uma natureza por vez.

- **Ativo**: [`pre-tx/T01-incremental-base-delta/`](pre-tx/T01-incremental-base-delta/) — primeira natureza confirmada.
- **Diferidos**: T02-T07 pre-tx + L01-L05 algoritmo. Pastas nao
  criadas ainda — abrem quando vier a vez.

Apos T01 fechar (com hipotese confirmada ou refutada), revisar
plano-mestre pra escolher proxima natureza ou redirecionar.

## Principios metodologicos

- **Pequeno e focado**: cada macro responde **uma pergunta**.
- **RT obrigatorio**: encoder + decoder reproduz input bit-a-bit.
- **Stress test antes de fechar**: dataset adversarial + favoravel
  (memoria [feedback-stress-test-antes-de-fechar-micro]).
- **Comparar bytes + unidades** (memoria [feedback-metrica-marcadores]).
- **Vocabulario disciplinado**: "diferenca em cenario X",
  nao "incrivel/onde brilha" (memoria [feedback-vocabulary-discipline]).
- **Track 2 nao mexe em canonical OBAT/HCC**: fork local pra
  experimentar; canonical fica intocavel.

## Conexoes

- [`tickets/META-TYPE-ENCODERS.md`](../../../../tickets/META-TYPE-ENCODERS.md) — plano-mestre
- [`docs/theory/perspectiva-triplice-e-pre-tx.md`](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md) — roadmap 3 estrategias
- [`experiments/lab/clean/EXP-008-compressao-comparada/`](../../clean/EXP-008-compressao-comparada/) — motivacao
- [`experiments/lab/dirty/notas/historia-dirty-lab.md`](../notas/historia-dirty-lab.md) — analogo metodologico (M0-M14 do lab anterior)
