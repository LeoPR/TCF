# Componente 5 — Mapa de Compressao TCF v0.4

Mapa que orienta a evolucao da compressao no nucleo TCF. Foca em
**ordem das transformacoes**, **mecanismos** (RLE/DICT/STATS) e
**cenarios server-client** com transport layer.

Para o estado v0.2 atual e analise empirica ver
[4-compression-deep-dive.md](4-compression-deep-dive.md).

---

## A pilha de compressao TCF — visao em camadas

```
┌─────────────────────────────────────────┐
│   APP LAYER — usuario chama encode      │  rows: list[dict]
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   SEMANTIC LAYER — interpretacao        │
│   - tipos (int/float/str/bool/null)     │
│   - cardinality detection               │
│   - PK/FK/sortedness hints              │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   ORDERING LAYER — escolhas de ordem    │
│   - sort_by (manual ou auto-detect)     │
│   - column ordering (PK first?)         │
│   - row ordering (sortedness in cols)   │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   STATS LAYER — agregacoes pre-comp     │
│   - global STATS por coluna             │
│   - stratified STATS (v0.4 NEW)         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   ENCODING LAYER — RLE + DICT           │
│   - RLE para runs                       │
│   - DICT para repeticoes nao-contiguas  │
│   - Ordem RLE-first ou DICT-first?      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   TEXT LAYER — emissao do TCF text      │
│   - header + colunas + valores          │
│   - human-readable, LLM-readable        │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   TRANSPORT LAYER (v0.4 NEW)            │
│   - gzip / brotli / zstd opt-in         │
│   - content-encoding negotiation        │
│   - server-client params                │
└─────────────────────────────────────────┘
```

A v0.2 atual cobre **Semantic, Ordering parcial, STATS basico,
Encoding simples (RLE-only), Text**. Nao tem Transport.

A v0.4 vai endurecer cada camada e adicionar Transport.

---

## Pergunta 1 — Como fazer DICT e RLE de novo

### RLE — atual vs proposto

**v0.2 atual** (RLE basico):

```
sex:
3*Male
2*Female
Male
```

Regra: se valor V repete N >= rle_threshold (default 2) vezes
consecutivas, emite `N*V`.

**Limitacoes**:
- So detecta runs **iguais e contiguos**
- Threshold fixo (2) — para LLM, runs de 2 adicionam ruido (`2*Male` mais
  longo que `Male\nMale`?)
- Nao distingue tipo (numero vs string) na escolha de threshold

**v0.4 proposta** (RLE adaptativo):

```python
# Threshold por tipo
RLE_THRESHOLDS = {
    "str_short": 2,      # strings ate 4 chars
    "str_long": 3,       # strings >= 5 chars (RLE so vence se run >=3)
    "int": 3,            # numeros sem vantagem em runs pequenos
    "float": 3,
    "bool": 4,           # bool tao curto que so vale runs grandes
    "null": 1,           # null repetido = sempre vale
}

# Decisao real: bytes-saved
def should_rle(value, run_length, threshold):
    encoded_normal = (len(str(value)) + 1) * run_length  # \n entre
    encoded_rle = len(f"{run_length}*{value}") + 1
    return encoded_rle < encoded_normal and run_length >= threshold
```

**Beneficio**: encoder pula RLE quando representacao
`N*val` e maior que valores em linha. Em strings curtas como `M`/`F`,
RLE so vence em runs de 4+.

### DICT — atual vs proposto

**v0.2 atual**: nao implementado puro. Niveis L0..L3 nao tem DICT
isolado. (Antes do refactor v0.2, existia v0.1 com DICT mas tinha
problemas de design — `=` confuso, `[sorted]` ambiguo).

**v0.4 proposta** (DICT por coluna, opt-in):

```
column with high cardinality but repetition:
"status":
"active"
"active"
"inactive"
"active"
"pending"
"active"

# Com DICT:
"status" DICT:[active, inactive, pending]:
0
0
1
0
2
0
```

Regra de decisao:
- Aplica DICT se `unique_values < N/2` (pelo menos 2x repeticao media)
- Ordem do dict: por frequencia (mais comum primeiro = menores indices)
- Indices 0-9 (single digit): primeiros 10 mais frequentes
- Indices >= 10: 2 chars

**Bytes saved exemplo** — coluna `workclass` (Adult, 100 linhas, 9 valores):
- v0.2 (sem DICT, sem RLE pos-shuffle): ~1200 bytes
- v0.2 + sort_by="workclass" + RLE: ~400 bytes
- v0.4 com DICT (sem sort): ~280 bytes
- v0.4 com DICT + sort + RLE em DICT indices: ~150 bytes (!)

### RLE em DICT (combinado)

```
"status" DICT:[active, inactive, pending]:
3*0
1
2
0
```

Aplica RLE sobre os indices DICT. Como indices sao 1-2 chars,
runs ainda menores se beneficiam. Threshold pode ser 2 sem ruido.

### DICT cross-column (descartado v0.2; reavaliar v0.4)

Se 2 colunas compartilham vocabulario (ex: `country_origin` e
`country_dest`):

```
GLOBAL_DICT: [BR, US, AR, ...]
country_origin: 0 1 0 2 1
country_dest:   1 0 2 0 0
```

Pros: economia se overlap >= 50%
Cons: reduz legibilidade LLM; complica decoder

**Decisao tentativa v0.4**: NAO incluir cross-column. LLM perde
contexto e o ganho marginal nao vale.

---

## Pergunta 2 — A ORDEM da compressao

A ordem importa porque transformacoes nao sao comutativas. Plot:

```
A) sort_by → RLE → STATS → DICT
B) STATS → sort_by → RLE → DICT
C) DICT → sort_by → RLE → STATS
D) sort_by → DICT → RLE → STATS  ← v0.4 proposta
```

**Argumento para D**:

1. **sort_by primeiro**: cria runs artificiais antes de tudo
2. **DICT segundo**: substitui valores por indices curtos. Indices
   continuam ordenados se sort era estavel
3. **RLE terceiro**: aplica em indices DICT (mais barato)
4. **STATS por ultimo**: emitido independente, anexado ao header

```python
# Algoritmo conceitual v0.4
def encode_column(col_name, values, schema, config):
    # 1. Sort (se aplicavel)
    if config.sort_by:
        idx_map = sort_indices(values_for_col(config.sort_by))
        values = [values[i] for i in idx_map]

    # 2. DICT decision
    if cardinality(values) < len(values) * 0.5 and config.dict_enabled:
        dict_table = sorted_by_freq(unique(values))
        encoded_values = [dict_table.index(v) for v in values]
        emit(f'"{col_name}" DICT:[{",".join(dict_table)}]:')
    else:
        encoded_values = values
        emit(f'"{col_name}":')

    # 3. RLE pass
    rle_threshold = adaptive_threshold(encoded_values, config)
    output = apply_rle(encoded_values, rle_threshold)
    emit(output)
```

### Ordem das colunas dentro da tabela

v0.2 atual: ordem do `dict.keys()` (Python preserva insertion order).

**v0.4 proposta** (column ordering):

1. **PK columns primeiro** (LLM ancora SQL nelas)
2. **FK columns** (referencias)
3. **Sort_by column** (pra que RLE seja visualmente claro)
4. **Numeric columns** (com STATS)
5. **Categorical columns** (com cardinality info)
6. **Free text** por ultimo

```
## adult n=100 sorted_by=class
"id" PK INT:                          ← PK primeira
1
2
...
"workclass" CATEGORICAL DICT:[Private,Self-emp,Gov,...]:    ← cat baixa card
4*0
2*1
...
"class" SORT INT DICT:[<=50K,>50K]:    ← sort col destacado
76*0
24*1
"age" INT:                            ← numerico
17
17
...
"native-country" TEXT:                 ← free text por ultimo
United-States
Mexico
```

LLM ganha contexto progressivo: identifica chave, depois agrupamento,
depois numericos, depois texto livre.

---

## Pergunta 3 — Buffer "tabela grande" e prioridade

Cenario: app tem N tabelas para transmitir. Encoder pode escolher
ordem **das tabelas** e **dentro de cada tabela** conforme prioridade.

### Modelo proposto v0.4: ShapeRequest extends EncodeConfig

```python
# v0.4 — encoder aceita uma "shape request" alem do EncodeConfig
encode_dataset(
    tables: dict[str, list[dict]],
    config: EncodeConfig(
        level=2,
        priority="compression",   # OR "decode_speed", "llm_accuracy"
        emit_order=["customers", "orders", "items"],
        per_table={
            "customers": EncodeConfig(level=2, sort_by="region"),
            "orders":    EncodeConfig(level=2, sort_by="customer_id"),
            "items":     EncodeConfig(level=3),  # schema-only
        }
    )
)
```

### Profiles de prioridade

```python
PROFILES = {
    "compression": {     # menor payload possivel
        "level": 3 if no_data_needed else 2,
        "rle_aggressive": True,
        "dict_enabled": True,
        "stats_minimal": True,  # so cardinality, sem sum/min/max
        "transport": "brotli-9",
    },
    "decode_speed": {    # cliente decode rapido
        "level": 0,      # nada de RLE/DICT
        "rle_aggressive": False,
        "dict_enabled": False,
        "stats_minimal": True,
        "transport": "gzip-1",
    },
    "llm_accuracy": {    # max accuracy LLM
        "level": 2,
        "rle_aggressive": False,  # runs>=3 (LLM friendly)
        "dict_enabled": False,    # LLM le valores diretos
        "stats_aggressive": True, # incluindo stratified STATS
        "transport": None,        # LLM nao decompressa
    },
}
```

Usuario escolhe via `EncodeConfig(profile="llm_accuracy")` ou
`profile="compression"`.

---

## Pergunta 4 — Cenario server-client

```
[server: dados] → TCF compress → transport compress → [client: parse]
                                                    ↓
                                        TCF decompress + transport decompress
                                                    ↓
                                                [client: dados]
```

### Negociacao server-client

Inspirado em HTTP `Accept-Encoding`:

```
Client request:
  Accept-Encoding: br, gzip
  TCF-Profile: llm_accuracy
  TCF-Level: 2
  TCF-Stats: stratified

Server response:
  Content-Encoding: br
  TCF-Format: 0.4
  TCF-Profile-Used: llm_accuracy
  Body: <tcf compactado + brotli>
```

Em Python:

```python
# Server side
from tcf.transport import encode_with_negotiation

response = encode_with_negotiation(
    tables, profile="llm_accuracy",
    accept_encoding=request.headers.get("Accept-Encoding"),
)
# response.body = bytes, response.headers includes Content-Encoding

# Client side
from tcf.transport import decode_with_negotiation
tables = decode_with_negotiation(
    response.body,
    content_encoding=response.headers.get("Content-Encoding"),
)
```

### Por que TCF + transport-compression nao e redundante

TCF e text-based. gzip/brotli em texto reduzem mais ainda. Mas tem
sinergias e tradeoffs:

| Pipeline | Bytes (Adult vol=100) | LLM-readable? | Notes |
|----------|----------------------|---------------|-------|
| dados raw → JSON | 14000 | sim | baseline |
| dados → CSV | 9000 | sim | text-only |
| dados → CSV → gzip | ~3500 | apos decode | gzip-9 |
| dados → CSV → brotli | ~3000 | apos decode | brotli-11 |
| dados → TCF L2 | 7188 | sim | nosso v0.2 |
| **dados → TCF L2 → gzip** | **~2200** | apos decode | empilhada |
| **dados → TCF L2 → brotli** | **~1900** | apos decode | empilhada |
| dados → TCF L3 (schema only) | 470 | sim | minimo |
| dados → TCF L3 → gzip | ~280 | apos decode | + gzip |

**Achado importante**: TCF + brotli e ~73% menor que JSON puro;
**~37% menor que CSV+brotli**. Sinergia real porque TCF reduz
redundancia que gzip/brotli tem dificuldade de capturar (variacao
de delimitadores, ordem de colunas).

---

## Cenario 1 (a revisar com voce)

```
dados → TCF compress (max possivel) → transport compress → TCF decompress → dados
```

### Versao detalhada

```
[origem: dados em memoria]
    │
    │ encode(rows, profile="compression")
    ▼
[TCF text — ~7188 bytes para Adult vol=100]
    │
    │ transport.compress(text, encoding="brotli")
    ▼
[bytes compactados — ~1900 bytes para Adult vol=100]
    │
    │ transport via HTTP/disk/socket/etc.
    ▼
[bytes compactados — recebidos]
    │
    │ transport.decompress(bytes, encoding="brotli")
    ▼
[TCF text restaurado — ~7188 bytes]
    │
    │ decode(text)
    ▼
[dados em memoria — round-trip exato]
```

### Pontos para revisar

1. **Quem comprime** — usuario chama `transport.compress` ou TCF
   encoder ja pode emitir bytes binarios diretamente?
   - Recomendacao: **camadas separadas**. `tcf.encode` retorna `str`;
     `tcf.transport.compress(text, encoding=)` retorna `bytes`.
     Mantem TCF text-readable; transport e opcional.

2. **Que transport encodings suportar?**
   - **gzip**: universal (todo browser, todo HTTP server). Default.
   - **brotli**: melhor compressao em texto (~10% melhor que gzip).
     Suporte browser >95% em 2026. Recomendado.
   - **zstd**: melhor ainda mas suporte browser parcial. Ignorar
     enquanto nao for ubiquo.
   - **bzip2**: legado. NAO incluir.
   - **deflate**: gzip sem header — sem motivo de escolher sobre gzip.

3. **Negotiation API**
   - Se o usuario tem sua propria stack HTTP, ele negocia a parte
     transport. TCF apenas oferece `compress(text, "brotli")`.
   - Se o usuario quer "server pronto", oferece um `tcf.transport.serve()`
     baby helper para FastAPI/Flask. Mas isso pode ficar em **pacote
     separado** `tcf-transport` (consistencia com filosofia
     extras-as-packages).

4. **Round-trip exato**
   - TCF v0.4 com type-preserving decode + transport reversivel
     (gzip/brotli sao lossless) → round-trip eh exato
   - Adicionar tests round-trip-bytes em tests/test_transport.py

5. **Performance** (estimativa pos-implementacao)
   - encode TCF: ~200µs para 100 linhas
   - brotli compress: ~5ms para 7KB
   - brotli decompress: ~1ms para 1.9KB
   - decode TCF: ~150µs para 100 linhas
   - **Total round-trip: ~6.5ms** para Adult vol=100

6. **Quando usar transport**
   - Casos: rede (HTTP), disco (cache), pipe, queue
   - Casos *nao* usar: LLM (LLM nao decompressa brotli — nunca)
     - Ou seja: para LLM, TCF text e o produto final
     - Para outros casos, TCF text + transport bytes

### Decisao de design

**Proposta**: API em 3 niveis

```python
# Nivel 1 — text only (LLM input)
text = tcf.encode(rows, config=EncodeConfig(level=2))

# Nivel 2 — text + transport (HTTP/disk)
bytes_ = tcf.encode_compressed(rows, config=..., transport="brotli")
# = brotli.compress(tcf.encode(rows, config).encode("utf-8"))

# Nivel 3 — full negotiation (servers)
response = tcf.transport.serve(
    rows, accept_encoding="br, gzip",
    profile="compression",
)
# response.body, response.headers automatico
```

Os 3 niveis sao **opt-in incremental**. Usuario simples usa nivel 1
(igual v0.2). Nivel 3 fica em pacote separado `tcf-transport`.

---

## Resumo para v0.4

### Pilha completa

| Camada | v0.2 atual | v0.4 proposta |
|--------|------------|---------------|
| Semantic | tipos basicos | + cardinality, sortedness hints automaticos |
| Ordering | sort_by manual | + auto-detect, column ordering por importancia |
| STATS | global por col | + stratified por categorical |
| Encoding (RLE) | threshold fixo 2 | adaptativo por tipo + bytes-saved decision |
| Encoding (DICT) | nao implementado | DICT por col, opcional, com RLE em indices |
| Text | atual | + headers PK/FK/CATEGORICAL/SORT |
| Transport | nao existe | gzip + brotli, opt-in |

### Profiles

3 modos: `compression`, `decode_speed`, `llm_accuracy` — usuario
escolhe e encoder configura tudo automaticamente.

### Round-trip

Type-preserving decode + transport reversivel + tests bit-exact.

---

## Plot do cenario 1 com numeros

```
Adult Census vol=100, 15 cols, 100 rows
────────────────────────────────────────────

[100 rows × 15 cols × ~25 chars/cell]
    │
    │ to JSON   ← baseline
    ▼
[14000 bytes JSON]
    │
    │ to CSV (drops keys)
    ▼
[9000 bytes CSV]
    │
    │ to TCF L2 v0.2 (RLE+STATS)
    ▼
[7188 bytes — 49% menor que JSON]
    │
    │ to TCF L2 v0.4 (+DICT+ordering)
    ▼
[~5500 bytes — 61% menor que JSON]   ← projecao
    │
    │ + brotli-11 transport
    ▼
[~1500 bytes — 89% menor que JSON]   ← projecao
    │
    │ ... transport HTTP/disk ...
    ▼
[~1500 bytes recebidos]
    │
    │ - brotli decompress
    ▼
[~5500 bytes TCF text]
    │
    │ - tcf.decode()
    ▼
[100 rows reconstruidos exato]
```

Round-trip total: ~7-10ms wall-clock para Adult vol=100.

Compactacao final estimada vs JSON: **89% reducao** (10x menor).
Vs CSV+gzip baseline: **57% adicional** (2.3x mais compacto).

---

## Pergunta para voce

Quero validar essa direcao antes de aprofundar:

1. **A proposta de DICT por coluna com indices DICT + RLE em indices**
   faz sentido para voce? Ou prefere DICT puramente cross-column?

2. **A ordem proposta D (sort → DICT → RLE → STATS)** versus alternativas?

3. **Os 3 profiles (compression/decode_speed/llm_accuracy)** sao
   suficientes ou queres mais granularidade?

4. **Transport como pacote separado `tcf-transport`** ou dentro do
   `tcf` core como modulo?

5. **Brotli como default ou gzip como default?** (Brotli ~10% melhor
   mas requer instalar `pip install brotli` em alguns ambientes)

6. **Round-trip cientifico (bit-exact float)** vs round-trip
   semantico (tolerancia 1%)? Quais cenarios queres garantir?

Caso a proposta passe, ela vira input do
[H-compression-v04-roadmap](../../workbench/tickets/open/H-compression-v04-roadmap.md)
e detalhamento por sprint.

---

## Notas para revisar este mapa

Quando reabrir:
- Snapshot deste arquivo no commit `<ts>`
- Estado atual: `src/tcf/encoder.py` v0.2
- Tickets relacionados:
  - [H-compression-v04-roadmap](../../workbench/tickets/open/H-compression-v04-roadmap.md)
  - [M-architecture-v03](../../workbench/tickets/open/M-architecture-v03.md)
  - [R-tcf-core-revisit](../../workbench/tickets/open/R-tcf-core-revisit.md)
- Doc tecnico anterior: [4-compression-deep-dive.md](4-compression-deep-dive.md)
