# EXP-008 — Compressao comparada (raw vs TCF) com 5 compressores

**Data**: 2026-05-15
**Tipo**: experimento clean **comparativo** (multi-axis)
**Ciclo**: v0.6 (segundo experimento clean, apos EXP-007)
**Estado**: aberto (reorganizado segundo [META-EXP-FORMAT](../../../../tickets/META-EXP-FORMAT.md))

## Pergunta cientifica

Como o TCF se posiciona em **bytes** e **latencia** contra
compressores de fluxo geral (gzip, brotli, zstd, lzma, bz2), em
3 cenarios:

1. **Stand-alone**: bytes de `tcf(D)` vs `C(D)` (cada compressor `C` aplicado direto ao raw).
2. **Como pre-tx**: bytes de `C(tcf(D))` vs `C(D)` — TCF complementa o compressor?
3. **Contra-prova de formato**: TCF vs **CSV, JSON e JSONL** (mesmo dado em
   formatos textuais diferentes) — pra distinguir reducao de redundancia
   de mera escolha de delimitador. Ver [`notes/contra-prova-formatos.md`](notes/contra-prova-formatos.md).

## Como ler este experimento

**Comece pelo resumo executivo**: [`reports/00-resumo.md`](reports/00-resumo.md).

| # | Report | O que responde |
|---|---|---|
| 00 | [resumo](reports/00-resumo.md) | Totais globais + vencedor + RT |
| 01 | [bytes-por-formato](reports/01-bytes-por-formato.md) | Sem compressao: csv vs json vs jsonl vs tcf por dataset |
| 02 | [bytes-por-classe](reports/02-bytes-por-classe.md) | Bytes agregados por classe de compressor (web/http, file/archive, parquet, general) |
| 03 | [latencia](reports/03-latencia.md) | Tempo serialize/parse/compress/decompress |
| 04 | [roundtrip](reports/04-roundtrip.md) | Verificacao de identidade nas 360 combinacoes |
| 05 | [campeao-por-dataset](reports/05-campeao-por-dataset.md) | Menor (formato, compressor) por dataset + ranking |

**Notas conceituais** (decisoes nao-obvias):

- [`notes/classificacao-compressores.md`](notes/classificacao-compressores.md) — porque cada compressor esta em quais classes
- [`notes/contra-prova-formatos.md`](notes/contra-prova-formatos.md) — porque csv/json/jsonl como baseline e qual mudou narrativa
- [`notes/limites-de-escala.md`](notes/limites-de-escala.md) — escala dos datasets afeta interpretacao

## Estrutura do diretorio

```
EXP-008-compressao-comparada/
├── README.md                # este arquivo
├── config.json              # parametros (datasets, compressores, reps)
├── run.py                   # orquestrador (≤200 linhas)
├── lib/                     # codigo modular
│   ├── formats.py           # csv/jsonl/json/tcf (serialize + parse)
│   ├── compressors.py       # 5 compressores + classes
│   ├── measure.py           # bytes + RT + latencia
│   └── reporting.py         # geracao de tabelas markdown formatadas
├── results/
│   ├── manifest.jsonl       # log de execucoes (run-level summary)
│   └── per-dataset/         # 1 JSON com dados crus por dataset
├── reports/                 # 6 reports markdown (1 por perspectiva)
├── notes/                   # 3 mini-docs (decisoes/interpretacao)
└── outputs/                 # binarios gerados (gitignored)
    ├── raw/<fmt>/<ds>.<ext>
    └── compressed/<fmt>/<comp>/<ds>.<ext>.<comp_ext>
```

## Datasets

15 datasets de controle (single-column CSV em `datasets/synthetic/`):

- **D1-D9** — TCF-CORE controles (padroes estruturais)
- **D10-D15** — tipos ERP/CRM (datas, datetime, CPF, UUID, base64)

## Compressores (com classificacao)

| Compressor | Nivel | web/http | file/archive | parquet | general |
|---|---:|:---:|:---:|:---:|:---:|
| `gzip` | 9 | ✓ | ✓ | ✓ | ✓ |
| `brotli` | 11 | ✓ |  | ✓ |  |
| `zstd` | 22 | ✓ | ✓ | ✓ | ✓ |
| `lzma` | 9 (preset) |  | ✓ |  |  |
| `bz2` | 9 |  | ✓ |  |  |

Detalhes em [`notes/classificacao-compressores.md`](notes/classificacao-compressores.md).

## Formatos input

| Formato | Descricao | Tamanho relativo CSV |
|---|---|---:|
| `csv` | Com header `val`, LF separator | 100% (baseline) |
| `jsonl` | 1 objeto JSON por linha | 144% (overhead `{"val":""}` por linha) |
| `json` | Array unico `["...","..."]` | 111% |
| `tcf` | `encode(linhas)` v0.6 (OBAT + HCC) | 64% |

## Como rodar

```bash
python experiments/lab/clean/EXP-008-compressao-comparada/run.py
```

Saidas regeneradas:
- `results/manifest.jsonl` — append nova linha
- `results/per-dataset/*.json` — sobrescritos
- `reports/*.md` — sobrescritos
- `outputs/` — sobrescrito

Pre-requisitos:
- `src/tcf/` welded (EXP-007 valida);
- `pip install brotli zstandard` (gzip/lzma/bz2 sao stdlib);
- Python 3.10+.

## Resumo de resultados (D1-D15)

Ver reports pra detalhe. Cabecalho:

- **RT**: 60/60 (formato) + 300/300 (compressor bytes) + 300/300 (full chain) OK.
- **TCF stand-alone**: reduz vs CSV em 14/15 datasets (D10 falha, dado de variety extrema).
- **Campeao por dataset**: `csv/brotli` em 10/15, `csv/zstd` em 2/15, `json/brotli` em 2/15, `tcf/brotli` em 1/15.
- **Limite empirico**: 1700 bytes (soma do menor por dataset) = 34.9% do CSV total raw.

**Importante**: escala dos datasets (100-540 bytes raw) favorece
compressores com dicionario estatico (brotli) sobre TCF. Ver
[`notes/limites-de-escala.md`](notes/limites-de-escala.md).

## Significado

EXP-008 caracteriza TCF no espaco de compressores gerais em
**regime de controle**. Resultados:

1. **TCF reduz redundancia em formato textual** (4872 → 3131 bytes, -36%) — comprovado;
2. **TCF como pre-tx** raramente complementa brotli/zstd nessa escala — mostra sobreposicao de mecanismos;
3. **D10-D15** identificam dados onde TCF v0.6 atual nao tem ferramenta (type encoders, Estrategia 1.A em [EXP-009 pendente]).

## Conexoes

- [META-EXP-FORMAT](../../../../tickets/META-EXP-FORMAT.md) — template aplicado aqui
- [EXP-007](../EXP-007-prototipo-tcf-core/) — validacao byte-canonical precedente
- [datasets/synthetic/](../../../../datasets/synthetic/) — D1-D15
- [docs/theory/perspectiva-triplice-e-pre-tx.md](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md) — analise de 3 estrategias (1.A, 1.B, 3.B)
- [docs/algorithms/](../../../../docs/algorithms/) — especificacao OBAT/HCC/TCF
