# META-EXP-FORMAT — Template de experimento (validacao vs comparativo)

**Status**: CLOSED (2026-05-15)
**Criado**: 2026-05-15
**Fechado**: 2026-05-15 (mesmo dia)
**Escopo**: formalizar 2 templates distintos pra experimentos
clean — `validacao` (single-axis) e `comparativo` (multi-axis) —
e aplicar `comparativo` em EXP-008.

## Motivacao

EXP-008 (compressao raw vs TCF × 5 compressores × 15 datasets)
saiu desorganizado: 165 binarios em flat `outputs/`, report unico
com tabelas de 13+ colunas sem formatacao, sem contra-prova de
input formats (csv-com-header / json / jsonl) e sem classificacao
dos compressores por natureza de uso.

**Causa raiz**: reaproveitei template do EXP-007 (validacao
byte-canonica, 1 metrica, 1 dataset-set) em EXP-008 que e' multi-eixo.
Template errado pro proposito.

Dirty lab M9 ja' tinha estrutura mais saudavel (subpastas por
aspecto: `output/`, `debug/`, `decoded/`, `detector_trace/`,
`redes/` + `resultados/matriz_comparativa.md` consolidado) — perdi
essa organizacao ao migrar pro clean. Erro foi meu, nao do clean
lab.

## Dois templates distintos

### Template 1 — `validacao` (single-axis)

Pergunta cientifica responde **uma metrica em um ponto**
(ex: EXP-007 = `src/tcf` reproduz byte-canonical de M14?).

```
EXP-NNN-<nome>/
├── README.md                # pergunta + hipotese + metodo
├── config.json              # parametros
├── run.py                   # script unico (orquestrador + medicao)
├── report.md                # 1 relatorio (resposta direta)
├── manifest.jsonl           # log de execucoes
└── outputs/                 # artefatos (gitignored, regenerable)
```

EXP-007 e' exemplar deste template. Manter.

### Template 2 — `comparativo` (multi-axis)

Pergunta cientifica responde **multiplas metricas em multiplas
dimensoes** (ex: EXP-008 = bytes × latencia × roundtrip × 5
compressores × 4 input formats × 15 datasets).

```
EXP-NNN-<nome>/
├── README.md                # entrada: pergunta + indice de reports
├── ORGANIZATION.md          # mapa da estrutura (este arquivo)
├── config.json
├── run.py                   # orquestrador (chama lib/)
├── lib/                     # codigo modular
│   ├── __init__.py
│   ├── formats.py           # input formats + serialize/parse
│   ├── compressors.py       # compressors + classes/metadata
│   ├── measure.py           # bytes + RT + timing
│   └── reporting.py         # tabelas formatadas (markdown)
├── results/                 # dados numericos
│   ├── manifest.jsonl
│   └── per-dataset/         # 1 JSON por dataset
├── reports/                 # markdown reports (1 por pergunta)
│   ├── 00-resumo.md
│   ├── 01-bytes-por-formato.md
│   ├── 02-bytes-por-classe-compressor.md
│   ├── 03-latencia.md
│   ├── 04-roundtrip.md
│   └── 05-campeao-por-dataset.md
├── notes/                   # mini-docs (decisoes/observacoes)
│   ├── classificacao-compressores.md
│   ├── contra-prova-formatos.md
│   └── limites-de-escala.md
└── outputs/                 # binarios (gitignored)
    ├── raw/<formato>/<ds>.<ext>
    └── compressed/<formato>/<compressor>/<ds>.<ext>
```

## Regras pro template comparativo

### R1 — Subpastas por aspecto

`outputs/raw/{csv,json,jsonl,tcf}/<ds>.<ext>` e
`outputs/compressed/{formato}/{compressor}/<ds>.<ext>`.

Nao misturar 165 arquivos no mesmo nivel — confunde inspecao
manual e leitura via `ls`.

### R2 — Contra-prova de input

Pelo menos 4 formatos textuais do mesmo dado:

| Formato | Conteudo |
|---|---|
| `csv` | `val\n<l1>\n<l2>\n...\n` (com header) |
| `jsonl` | `{"val":"<l1>"}\n{"val":"<l2>"}\n...` |
| `json` | `["<l1>","<l2>",...]` (array) |
| `tcf` | `encode(linhas)` |

Sem isso, "TCF reduz bytes" pode ser comparativo apenas com CSV
inflado — nao prova que TCF reduz **redundancia semantica**.

### R3 — Classificacao de compressores

Cada compressor tem metadata `classes: list[str]`:

| Classe | Descricao | Exemplos |
|---|---|---|
| `web/http` | Content-Encoding HTTP/1.1+ e HTTP/3 | gzip, brotli, zstd |
| `file/archive` | Compressao de arquivo/streaming arquivado | lzma/xz, bz2, zstd |
| `parquet` | Padrao em columnar storage | snappy, gzip, zstd, lz4, brotli |
| `general` | Standalone, sem caso de uso especifico | gzip, zstd |

Compressor pode estar em multiplas classes. Reports devem agrupar
por classe quando relevante.

### R4 — Reports multiplos

Um arquivo por pergunta. Indice em `README.md`. Nao colocar 200
linhas em report unico — usuario nao consegue ler.

### R5 — Tabelas formatadas

- Numeros: alinhados a direita (`|---:|`).
- **Bold** pro menor valor por linha (campeao da linha).
- `_italico_` pro segundo menor (runner-up).
- Ordenacao logica: por dataset ID ou por metrica (justificar).
- Escala visual quando ajuda: `███░░ 60%` ou similar.

### R6 — Codigo modular

`run.py` orquestrador (≤100 linhas idealmente). Logica em `lib/`.
Funcoes puras quando possivel, testaveis em isolamento.

### R7 — Mini-docs em `notes/`

Decisoes nao-obvias (criterio de classificacao, niveis de
compressor escolhidos, datasets excluidos, etc.) viram mini-docs
proprios — nao enterrar em notas de rodape de report.

## Criterio de aceite

1. [x] Salvar feedback em memoria — `feedback_exp_format_for_comparative.md`
2. [x] Este ticket criado e commitado — commit `8c84415`
3. [x] EXP-008 reorganizado pra template comparativo:
   - [x] `lib/` extraida do run.py inline — `formats.py`, `compressors.py`, `measure.py`, `reporting.py`
   - [x] Inputs csv + jsonl + json + tcf adicionados (com RT 60/60 OK)
   - [x] Compressores classificados (web/http, file/archive, parquet, general)
   - [x] `outputs/` hierarquizado (`raw/<fmt>/`, `compressed/<fmt>/<comp>/`)
   - [x] `reports/` multiplos — 6 documentos focados (00-resumo, 01-bytes-por-formato, 02-bytes-por-classe, 03-latencia, 04-roundtrip, 05-campeao-por-dataset)
   - [x] `notes/` com 3 mini-docs (classificacao-compressores, contra-prova-formatos, limites-de-escala)
   - [x] Tabelas com **bold** menor + _italico_ segundo + alinhamento direita
4. [x] Re-rodar EXP-008 → RT 60/60 (formato) + 300/300 (compressor bytes) + 300/300 (full chain) OK
5. [x] Push para GitHub — commit `8c84415` em `main`
6. [ ] (opcional, futuro) Template `_template-comparativo/` em
   `experiments/lab/clean/` pra reuso — adiado; criar quando proximo
   experimento comparativo nascer

## Conexoes

- Memoria: [feedback-exp-format-for-comparative](../memory/feedback_exp_format_for_comparative.md)
- Experimento alvo: [EXP-008](../experiments/lab/clean/EXP-008-compressao-comparada/)
- Modelo organizacional anterior: [M9 dirty](../experiments/lab/dirty/2026-05-17-M9-stress-adversarial/)
