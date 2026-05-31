# dirty/ — workbench experimental TCF

**Reorganizado em 2026-05-16**: M0-M14 (TCF-CORE / canonical
src/tcf, fase v0.6 inicial) movidos para [`old/`](old/) preservando
historia git. **Trabalho ativo** segue em
[`2026-05-15-naturezas-e-camada/`](2026-05-15-naturezas-e-camada/).

## Layout atual

```
experiments/lab/dirty/
├── README.md                              # este arquivo
├── notas/                                 # narrativas cross-cutting
│   ├── historia-dirty-lab.md              # narrativa M0-M14
│   ├── welding-plan.md                    # plano de welding pra src/tcf
│   └── naming-compactacao-composicional.md
├── 2026-05-15-naturezas-e-camada/         # ATIVO (T01 incremental em curso)
│   ├── README.md
│   ├── notas/
│   ├── pre-tx/                            # Track 1 (encoders por natureza)
│   │   └── T01-incremental-base-delta/    # macro ativo
│   │       ├── README.md
│   │       └── 01..06-...                 # sub-experimentos
│   └── algoritmo/                         # Track 2 (estudos OBAT/HCC — diferido)
└── old/                                   # M0-M14, historia v0.6 inicial
    ├── README.md
    ├── M0-fase-exploratoria-inicial/
    ├── M0.5-exploracao-sintaxe-pre-M1/
    ├── Mobsolete/
    ├── 2026-05-12-M1-marcacao-ambiguidade/
    ├── 2026-05-13-M2..M4-.../
    ├── 2026-05-14-M5..M6-.../
    ├── 2026-05-15-M7-refactor/
    ├── 2026-05-16-M8-virtual-refs-clean-output/
    └── 2026-05-17-M9..M14-.../            # nota: datas dos M9-M14 sao impossiveis (>=hoje); erro antigo de nomenclatura, preservado pra rastreabilidade git
```

## Compendio sempre-atualizado

Estado completo do projeto e proximas direcoes em
[`../../../STATUS.md`](../../../STATUS.md) (raiz do projeto).

## Convencoes do dirty lab

### Proposito

O dirty lab serve para **verificar comportamento**, nao para
"descobrir algo incrivel". Cada experimento responde a uma destas
perguntas:

1. **Esta ferramenta pode ser implementada?** (viabilidade tecnica)
2. **Este algoritmo tem o comportamento esperado?** (consistencia)
3. **Este formato funciona?** (roundtrip, edge cases)
4. **Como este experimento se compara, ponto a ponto, com o anterior?**
   (diferencas, nao juizo)

Analise de escala e complexidade algebrica indica **a possibilidade**
de vantagem em algum cenario. Nao estabelece superioridade.

### Vocabulario — disciplina obrigatoria

**Nao usar** nas notas, READMEs, ou qualquer artefato deste lab:
- "incrivel", "surpreendente", "muito melhor", "suipimpa"
- "onde brilha", "destaque", "vencedor", "campeao"
- "descoberta", "achado importante" (use: "comportamento observado")
- superlativos absolutos sem cenario ("melhor", "otimo", "ideal")

**Usar**:
- "diferenca", "variacao", "delta"
- "comportamento sob X", "no cenario Y"
- "menor/maior em N bytes que A em cenario B"
- "comparavel a / nao comparavel a"

### Naming pra novos experimentos

- Macros ativos sob `<datetime-YYYY-MM-DD>-<descritor>/` no nivel
  do dirty (data ate' aqui significa **inicio do projeto**, nao
  incremento por macro — erro do passado preservado em `old/`).
- Sub-experimentos dentro de macros: `NN-<descritor>/` com NN
  numerico crescente.
- Cada pasta tem README.md curto explicando proposito.

### gzip/bz2/brotli/zstd NAO fazem parte do TCF

Servem como sinal qualitativo de redundancia oculta — comparacao,
nao criterio de descarte.

---

## Como navegar (resumo pra um sistema novo)

1. Comece pelo [`STATUS.md`](../../../STATUS.md) raiz pra estado atual.
2. Entre no macro ativo [`2026-05-15-naturezas-e-camada/`](2026-05-15-naturezas-e-camada/).
3. Leia o README.md de cada nivel pra contexto.
4. Para historia anterior (M0-M14), entre em [`old/`](old/).
