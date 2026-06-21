# dirty/ — workbench experimental TCF

**Reorganizado em 2026-05-16**: M0-M14 (TCF-CORE / canonical
src/tcf, fase v0.6 inicial) movidos para [`old/`](old/) preservando
historia git. **Faxina 2026-06-21**: lab `2026-05-15-naturezas-e-camada/`
movido para `old/welded/` (absorvido no Pacote 1, ADR-0008/0010/0011).

## Layout atual

```
experiments/lab/dirty/
├── README.md                              # este arquivo
├── notas/                                 # narrativas cross-cutting
│   ├── historia-dirty-lab.md              # narrativa M0-M9 (M10+ em ADRs+checkpoints)
│   ├── welding-plan.md                    # HISTORICO (faxina 2026-06-21)
│   └── naming-compactacao-composicional.md
├── 2026-05-24-benchmark-formats-compression/ # ativo — csv/json/tcf x gzip/brotli/zstd
├── 2026-05-27-baseline-consolidado/       # ativo — baseline de referencia
├── 2026-06-19-lazy-testbank/              # ativo — banco de testes lazy A1/A2/A3
└── old/                                   # historico
    ├── M0-M14-series/                     # pre-canonical (NAO USAR)
    ├── welded/                            # 11 labs welded em src/tcf
    └── refuted/                           # 6 labs refutados/insufficient-gain
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
2. Labs ativos: `2026-05-24-benchmark-formats-compression/`, `2026-05-27-baseline-consolidado/`, `2026-06-19-lazy-testbank/`.
3. Leia o README.md de cada nivel pra contexto.
4. Para historia anterior (M0-M14), entre em [`old/`](old/).
