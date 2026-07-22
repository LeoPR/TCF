# dirty/ — workbench experimental TCF

**Reorganizado em 2026-05-16**: M0-M14 (TCF-CORE / canonical
src/tcf, fase v0.6 inicial) movidos para [`old/`](old/) preservando
historia git. **Faxina 2026-06-21**: lab `2026-05-15-naturezas-e-camada/`
movido para `old/welded/` (absorvido no Pacote 1, ADR-0008/0010/0011).
**Nichado por data em 2026-07-22**: os macros (66 nessa data) viraram
grandes demais numa pasta so' flat; passaram a viver sob
`<YYYY-MM>/<YYYY-MM-DD>/` (nome do macro **inalterado**, so' a posicao
mudou) — mesma logica aplicada a `notas/` (~85 notas soltas → por mes
de 1o commit). `old/`, `clean/` (numeracao EXP-NNN propria) e `archive/`
ficaram de fora (esquemas ja' deliberados, ou baixo volume).

## Layout atual

```
experiments/lab/dirty/
├── README.md                                   # este arquivo
├── notas/                                       # narrativas cross-cutting
│   ├── 2026-05/ · 2026-06/ · 2026-07/           # por mes do 1o commit
│   ├── diario/                                  # 1 arquivo por dia (YYYY-MM-DD.md)
│   └── checkpoints/                             # pausas/retomadas datadas
├── 2026-05/2026-05-24/2026-05-24-benchmark-formats-compression/
├── 2026-05/2026-05-27/2026-05-27-baseline-consolidado/
├── 2026-06/2026-06-19/2026-06-19-lazy-testbank/
├── ...                                          # <YYYY-MM>/<YYYY-MM-DD>/<macro>/
└── old/                                         # historico (layout proprio, nao nichado)
    ├── M0-M14-series/                           # pre-canonical (NAO USAR)
    ├── welded/                                  # labs welded em src/tcf
    └── refuted/                                 # labs refutados/insufficient-gain
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

- Nome do macro continua `<YYYY-MM-DD-HHMM>-<descritor>/` — **so' o dia
  NAO basta** (macros do mesmo dia ficam sem ordem); HHMM (ou `-vNN-`)
  + descricao do que esta' sendo feito (detalhe em
  [`notas/dirty-lab-convencoes.md`](notas/2026-07/dirty-lab-convencoes.md) §1).
- **Posicao no disco** (desde 2026-07-22): `<YYYY-MM>/<YYYY-MM-DD>/<nome-do-macro>/`
  — a data ja' esta' no nome, os 2 niveis de pasta so' evitam uma `dirty/`
  flat com 60+ entradas. Ao criar um macro novo, crie (ou reuse) esses
  2 niveis de pasta ANTES; o nome do macro em si nao muda.
- Sub-experimentos dentro de macros: `NN-<descritor>/` com NN
  numerico crescente.
- Cada pasta tem README.md curto explicando proposito.

### gzip/bz2/brotli/zstd NAO fazem parte do TCF

Servem como sinal qualitativo de redundancia oculta — comparacao,
nao criterio de descarte.

---

## Como navegar (resumo pra um sistema novo)

1. Comece pelo [`STATUS.md`](../../../STATUS.md) raiz pra estado atual (lista os macros/notas
   relevantes do momento, ja' com o caminho `<YYYY-MM>/<YYYY-MM-DD>/` correto).
2. Pra achar um macro por data: `<YYYY-MM>/<YYYY-MM-DD>/<nome-completo-do-macro>/`.
3. Leia o README.md de cada nivel pra contexto.
4. Para historia anterior (M0-M14), entre em [`old/`](old/) (layout proprio, nao nichado por data).
