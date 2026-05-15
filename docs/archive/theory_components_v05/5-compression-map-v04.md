# Componente 5 — Mapa de Compressao TCF v0.4

Mapa que orienta a evolucao da compressao no nucleo TCF. Foca em
**ordem das transformacoes**, **mecanismos** (RLE/DICT/STATS) e
**cenarios server-client** com transport layer.

Para o estado v0.2 atual e analise empirica ver
[4-compression-deep-dive.md](4-compression-deep-dive.md).

---

## ESCOPO DO TCF (atualizado 2026-04-27)

**Decisao do usuario**: TCF e *somente* encoder/decoder. Nao tem
server/client, nao tem camada de transport, nao instala compressores.

A validacao cientifica (gzip/brotli/comparacoes com CSV/JSON/TOON,
HTTP/UDP/server-client) acontece em um **meta-programa de teste**
externo que orquestra o pipeline:

```
[meta-programa de teste]
  → chama tcf.encode(rows)
  → chama gzip/brotli/etc (externos)
  → simula transporte (memoria/disco/socket)
  → chama gzip^-1/brotli^-1
  → chama tcf.decode(text)
  → compara com input original
```

Ver [6-test-harness.md](6-test-harness.md) para o design dessa
infraestrutura.

A pergunta cientifica que guia tudo:
> "Em quais cenarios minimos e maximos o TCF funciona bem?
>  Como ele se compara a CSV, JSON, TOON?"

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
│   - DICT por col, cross-col ou misto    │
│   - Ordem das transformacoes a estudar  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   TEXT LAYER — emissao do TCF text      │
│   - header + colunas + valores          │
│   - human-readable, LLM-readable        │
│   - SAIDA FINAL DO TCF                  │
└─────────────────────────────────────────┘

(Transport, gzip/brotli, network, comparison
 com outros formatos = META-PROGRAMA, fora daqui)
```

A v0.2 atual cobre Semantic, Ordering parcial, STATS basico,
Encoding simples (RLE-only), Text. **Nao tem Transport e nem ira
ter no core.**

A v0.4 vai endurecer cada camada existente. Transport fica em
meta-programa externo.

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

### DICT cross-column — opcional v0.4

**Decisao do usuario (2026-04-27)**: cross-column **e uma opcao**
controlada por `dict_scope`. Default `auto` (encoder decide); usuario
pode forcar `cross_column` ou `per_column` conforme o cenario.

```
# Per-column (default)
"country_origin" DICT:[BR,US,AR]:
0
1
0

"country_dest" DICT:[US,BR,CN]:    ← DICT proprio
1
0
2
```

```
# Cross-column (opt-in)
GLOBAL_DICT: [BR, US, AR, CN, ...]
"country_origin": 0 1 0 2 1        ← indices em DICT compartilhado
"country_dest":   1 0 2 0 0
```

| Cenario | Per-column | Cross-column |
|---------|-----------|--------------|
| 2 cols, overlap baixo | melhor | pior (DICT carrega valores nao usados) |
| 2 cols, overlap alto | medio | **muito melhor** (DICT compartilhado) |
| Muitas cols, overlap esparso | melhor | pior |
| Muitas cols, overlap alto | medio | **melhor** |
| LLM input | **melhor** (le valores) | pior (so indices) |
| Compactacao maxima | medio | **melhor** quando overlap |

Decisao automatica em `dict_scope="auto"`:
- Calcula overlap medio entre colunas categoricas
- Se overlap > 30% e ha 2+ cols com cardinalidade similar → cross_column
- Senao → per_column

Usuario pode sempre forcar com `dict_scope="cross_column"` ou
`dict_scope="per_column"`.

**Tipo composto**: `dict_columns=["country_origin", "country_dest"]`
forca cross-column **so para essas duas colunas**, deixa as outras
em per-column. Permite controle fino.

---

## Pergunta 2 — A ORDEM da compressao (estudo combinatorial)

A ordem importa porque transformacoes nao sao comutativas. **Decisao do
usuario: estudar combinacoes empiricamente, nao decidir teoricamente.**

Ver [7-combination-study.md](7-combination-study.md) para o plano
completo do experimento combinatorial.

### Combinacoes plausiveis

```
A) sort_by → RLE → STATS                       (v0.2 atual)
B) sort_by → DICT → RLE → STATS                (proposta inicial)
C) sort_by → RLE → DICT → STATS                (alternativa)
D) DICT → sort_by → RLE → STATS                (DICT primeiro)
E) STATS → sort_by → RLE → DICT                (STATS primeiro)
F) sort_by → DICT_per_col → RLE → DICT_cross → STATS  (DICT em camadas)
... varias outras possiveis
```

Nao escolheremos teoricamente. Em vez disso:

1. Implementar pipeline configuravel (cada transformacao plugavel)
2. Testar **N combinacoes × M datasets × K profiles**
3. Medir bytes finais + accuracy LLM (subset) + decode time
4. Reportar **melhor combinacao por cenario**

Argumentos teoricos serao usados para **eliminar** combinacoes
obviamente ruins (ex: STATS depois de RLE/DICT — nao faz sentido pois
STATS opera sobre dados originais), nao para escolher a melhor.

### Ordem das colunas dentro da tabela

Independente da ordem das transformacoes acima, ha decisao sobre
**como ordenar as colunas**:

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

### Profiles de prioridade — granularidade expandida

Profiles sao **presets** de combinacoes pre-validadas. Usuario pode
sempre **override individual** de qualquer parametro.

```python
PROFILES = {
    "minimal_bytes": {       # payload minimo absoluto
        "level": 3,           # schema-only
        "rle_threshold": "aggressive",   # bytes-saved decision
        "dict_scope": "cross_column",    # economia maxima
        "stats": "cardinality_only",     # sem sum/avg
        "column_ordering": "by_compressibility",
    },
    "compact_text": {        # compactacao mas legivel
        "level": 2,
        "rle_threshold": "adaptive",
        "dict_scope": "per_column",
        "stats": "global",
        "column_ordering": "by_importance",
    },
    "balanced": {            # default v0.4
        "level": 2,
        "rle_threshold": "bytes_saved",
        "dict_scope": "auto",   # decide por coluna
        "stats": "global",
        "column_ordering": "natural",
    },
    "llm_input": {           # max accuracy LLM (mantem F-Q33+)
        "level": 2,
        "rle_threshold": "conservative",   # runs>=3
        "dict_scope": "none",              # LLM le valores diretos
        "stats": "stratified",             # ataca filter+agg
        "column_ordering": "schema_aware", # PK first, etc
    },
    "decode_speed": {        # parser rapido
        "level": 0,
        "rle_threshold": "off",
        "dict_scope": "none",
        "stats": "off",
        "column_ordering": "natural",
    },
    "debug": {               # max human-readable
        "level": 0,
        "rle_threshold": "off",
        "dict_scope": "none",
        "stats": "verbose",   # tudo + samples + cardinality
        "column_ordering": "natural",
    },
}
```

### Parametros override (granularidade individual)

Qualquer parametro pode ser overrided sem profile:

```python
EncodeConfig(
    # Pode escolher um profile como base
    profile="compact_text",
    # E override individual
    rle_threshold=4,           # forca threshold fixo
    dict_scope="cross_column", # forca cross-col mesmo no profile
    sort_by="region",          # ordem fixa
    stats="stratified",        # ativa stratified mesmo se profile diz global
)
```

Cada parametro mapeia para uma camada da pilha — usuario pode
"misturar e combinar" ate encontrar o ponto otimo do seu cenario.

### Decisoes paralelas (perpendiculares aos profiles)

| Eixo | Valores | Default v0.4 |
|------|---------|--------------|
| `level` | 0, 1, 2, 3 | 2 |
| `rle_threshold` | off / fixed N / adaptive / aggressive / bytes_saved | bytes_saved |
| `dict_scope` | none / per_column / cross_column / auto | auto |
| `dict_columns` | list[str] (subset para cross-col) | None |
| `stats` | off / cardinality_only / global / stratified / verbose | global |
| `stats_strata` | list[str] (categoricals para cruzar) | None |
| `column_ordering` | natural / by_importance / by_compressibility / schema_aware | natural |
| `sort_by` | None / col_name / "auto" | None |
| `preserve_types` | bool (header com tipos) | False (compat v0.2) |

**6 profiles × 9 eixos** = espaco grande para experimentar.

---

## Pergunta 4 — Cenario server-client (resolvido em meta-programa)

A validacao server-client NAO entra no TCF core. Em vez disso, o
meta-programa de teste simula esses cenarios. Ver
[6-test-harness.md](6-test-harness.md).

A questao que importa para o TCF: **quanto sinergia ha entre TCF e
compressores genericos** (gzip/brotli) em diferentes cenarios?
Resposta vem de experimentos, nao de implementacao TCF.

### Por que TCF + compressao generica nao e redundante

TCF e text-based. gzip/brotli em texto reduzem mais ainda. Mas tem
sinergias e tradeoffs que precisamos medir:

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

### Decisao de design — TCF API minima

**TCF expoe somente 1 API**:

```python
# UNICA API do TCF
text: str = tcf.encode(rows, config=EncodeConfig(...))
rows = tcf.decode(text)
```

`encode_compressed`, `transport.serve` etc. **nao** existem no TCF.

A validacao em multiplos cenarios (transport, network, comparacao com
outros formatos) acontece no **meta-programa de teste**, em modulo
separado:

```python
# Meta-programa (FORA do tcf core)
from harness import simulate_pipeline, compare_formats

result = simulate_pipeline(
    rows,
    encoder="tcf",         # OR "csv", "json", "toon"
    config=tcf_config,
    transport="brotli",    # OR "gzip", None (raw)
    network="memory",      # OR "disk", "tcp", "udp" (futuro)
)
# result.bytes_total, result.encode_ms, result.decode_ms, ...
```

Isso garante:
- TCF se mantem **encoder/decoder puro** sem dependencia em compressores
- Comparacoes cientificas sao reproduziveis em qualquer formato
- Trocar TCF por CSV/JSON/TOON e so mudar `encoder=`

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
