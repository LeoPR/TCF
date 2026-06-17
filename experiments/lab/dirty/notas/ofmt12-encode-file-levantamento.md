# Levantamento — O-FMT-12 (`encode_file` / auto-detect CSV) [análise, pré-decisão]

**Data**: 2026-06-16 · **Tipo**: análise pra decisão (não implementa nada). Owner avalia.

## O que é
`encode_file(path)` conveniente: lê um CSV, **auto-detecta** dialect (delimitador/quote) +
encoding, transpõe linhas→colunas e chama `encode()`. Opcionalmente detecta tipos por coluna.
**Tangencial ao core** — não muda o formato `#TCF.7`; é conveniência de entrada (DX). **Não é versão.**

## Discoverability (o que já existe — pra não reinventar)
- **`encode()`** aceita as 3 estruturas genéricas: `list[dict]` (linhas), `dict[str,list]`
  (colunas), `list[tuple]+colunas`. `encode_file` **não existe** hoje.
- **`scripts/dataset_reader.py`** — reader do hub SQLite, **SUPPORT CLIENT, explicitamente NÃO core**.
  O docstring é categórico: *"Anyone installing TCF can write their OWN reader for their OWN sources
  (Postgres, Parquet, pandas, Arrow, HTTP API, whatever)... They don't need this module."*
  → **filosofia do projeto: leitura-de-input fica FORA do core.**
- **`scripts/schema_gadget/`** — já faz detecção de **tipo/qualidade por coluna** (type_drift,
  date_check, etc.). Detecção de "tipos" do O-FMT-12 é **território do gadget**, não do encode.
- **`scripts/csv_to_sqlite.py`, `setup_*.py`** — já leem CSV pra montar os hubs.
- **~12 labs** reinventam um `load()` (csv.reader + fallback utf-8→latin-1). DRY real, mas em
  código descartável de lab.
- **Libs**: `csv.Sniffer` (stdlib), `charset_normalizer` (detecção de encoding, **já instalado**),
  `pandas` (já instalado). `chardet` ausente (charset_normalizer é o sucessor).

## Design (se for fazer)
- **dialect**: `csv.Sniffer().sniff()` (stdlib). Frágil em CSV pequeno/ambíguo → fallback `,`.
- **encoding**: `charset_normalizer` (já disponível) ou o try utf-8→latin-1 dos labs (mais simples).
- **transpose**: CSV é row-oriented; TCF é column-oriented → ler rows, transpor → `dict[str,list]`.
  Cuidado com linhas de nº de campos errado (os labs fazem `if len(row)==len(header)`).
- **tipos**: o TCF é **string-agnóstico** — tipos só importam pra *natures* (opt-in) ou pro
  schema_gadget. **`encode_file` NÃO precisa de tipos pra funcionar.** Detecção de tipo = escopo
  do schema_gadget (já existe), não desta conveniência.
- **roundtrip**: CSV→TCF→CSV **não** é byte-idêntico (dialect/quoting/encoding podem normalizar).
  O lossless do TCF é dos **valores** (`decode(encode(x))==x`), **não** do arquivo CSV bruto.
  Isso precisa ficar explícito (senão alguém espera RT do arquivo).

## Custo / risco / valor
- **Custo**: baixo (S) — wrapper de ~30-50 linhas com stdlib.
- **Risco**: **zero pro formato/RT** (não toca `src/tcf`, não muda bytes). Risco só em edge cases
  de CSV (campos multiline, quoting, encoding errado, Sniffer falhar) → contornável com overrides.
- **Valor**: conveniência/DX (`encode_file(path)` em 1 linha) + DRY (substituiria os `load()` dos
  labs). **Não muda bytes nem ratio** — é ergonomia, não compressão.

## Recomendação
1. **Fazer como GADGET em `scripts/` (ex.: `scripts/tcf_io/`), NÃO no core** — respeita a filosofia
   já escrita no `dataset_reader` (input-reading fora do core). Mantém `src/tcf` enxuto.
2. **Escopo mínimo**: `encode_file(path, *, delimiter=None, encoding=None)` — auto-detect com
   override + fallback, transpõe, chama `encode()`. **SEM detecção de tipo** (deixa pro
   schema_gadget). Bônus opcional: `decode_to_csv(blob, path)` pra simetria.
3. **Não prometer** roundtrip byte-idêntico do CSV — só dos valores. Documentar.
4. **Alternativa "fazer nada"**: é defensável — o `encode(dict)` + um `csv.DictReader` de 3 linhas
   já resolvem; a filosofia diz que o usuário traz o reader. O ganho é só ergonomia.

## Decisão do owner
- (a) gadget `scripts/tcf_io/encode_file` (escopo mínimo, sem tipos) — recomendado se quer a DX.
- (b) helper fino no core (`tcf.encode_file`) — contraria a filosofia; só se DX no core for prioridade.
- (c) park — `encode(dict)` + DictReader já bastam; o valor é marginal (ergonomia, 0 bytes).
