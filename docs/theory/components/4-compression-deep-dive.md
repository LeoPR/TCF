# Componente 4 — Compressao do TCF (deep dive)

Este documento detalha **as estrategias de compressao** atuais do TCF v0.2,
seus limites empiricos, e as propostas para v0.3.

Para visao geral do projeto ver [../README.md](../README.md). Para a
spec formal do formato ver
[../../article/appendices/A-tcf-spec.md](../../article/appendices/A-tcf-spec.md).

---

## Filosofia da compressao TCF

TCF nao tenta ser **gzip** — busca **compressao legivel por LLM**.
A diferenca e crucial:

| Criterio | gzip / zstd | TCF |
|----------|-------------|-----|
| Reduz bytes? | sim | sim |
| LLM consegue ler comprimido? | nao | sim |
| Round-trip exato? | sim | sim |
| Adiciona contexto util? | nao | sim (STATS) |
| Streaming? | sim | parcial |

A meta e **reduzir o numero de tokens consumidos pelo LLM** mantendo
ou melhorando accuracy. Isso justifica os 4 mecanismos atuais.

---

## Os 4 mecanismos atuais (v0.2)

### 1. Layout columnar (base do formato)

CSV/JSON sao **row-oriented**: cada linha repete os nomes das colunas
(JSON) ou e ordenada por posicao (CSV).

TCF e **column-oriented**: nome da coluna aparece **uma vez** seguido
de N valores em sequencia.

```
CSV (4 linhas, 3 cols):
id,name,age
1,Alice,30
2,Bob,30
3,Carol,31

JSON (mesma coisa):
[{"id":1,"name":"Alice","age":30},
 {"id":2,"name":"Bob","age":30},
 ...]

TCF L0:
## tabela n=4
id:
1
2
3
4
name:
Alice
Bob
Carol
age:
30
30
31
```

**Ganho**: ~30-40% de reducao em datasets com muitas colunas (cada
nome aparece N vezes em CSV, 1 vez em TCF).

**Custo**: LLM precisa "lembrar" alinhamento posicional. Nossos
experimentos mostraram que isso funciona bem ate ~500 linhas (qwen3:14b
e gpt-5.x acertam alinhamento mesmo com 500 valores).

### 2. RLE — Run-Length Encoding (nivel L2)

Valores consecutivos iguais sao agrupados como `N*val`:

```
TCF L0:
sex:
Male
Male
Male
Female
Female
Male

TCF L2:
sex:
3*Male
2*Female
Male
```

**Ganho empirico** (Adult Census, 100 linhas):

| Coluna | Cardinalidade | RLE benefit (L0→L2) |
|--------|---------------|---------------------|
| `class` (2 valores) | baixa | -60% (excellent) |
| `sex` (2 valores) | baixa | -55% |
| `workclass` (~9 valores) | baixa-media | -25% |
| `age` (varios) | alta | 0% (RLE nao aciona) |
| `fnlwgt` (todos unicos) | maxima | 0% |

RLE so ajuda quando `runs >= rle_threshold` (default 2). Tipicamente
**colunas categoricas com baixa cardinalidade** dominam.

**Truque importante**: combinar com `sort_by` cria runs artificiais.

```python
# Sem sort: classe distribuida aleatoriamente — RLE quase 0%
encode_rows("adult", rows, config=EncodeConfig(level=2))

# Com sort por class (76% <=50K / 24% >50K):
# RLE comprime para 1 run de 76 + 1 run de 24
encode_rows("adult", rows,
    config=EncodeConfig(level=2, sort_by="class"))
# Reducao adicional: -15% no payload total
```

**Sort_by ideal** em ordem decrescente de impacto:
1. Coluna categorica de **baixa cardinalidade** (class, sex)
2. Coluna numerica **discreta** (year, age_group)
3. Coluna **ordinal** (rating 1-5)

### 3. STATS — agregacoes pre-computadas (nivel L2 e L3)

A linha `# STATS` e adicionada no topo de cada tabela com agregacoes
ja calculadas:

```
## adult n=100 sorted_by=class
# STATS age: n=100 sum=3772 min=17 max=90 avg=37.72
# STATS hours-per-week: n=100 sum=4243 min=7 max=99 avg=42.43
# STATS class: cardinality=2 samples=[<=50K, >50K]
# STATS workclass: cardinality=6 samples=[Private, Self-emp, ...]
```

**Por que existe**: F-Q8 (origem) mostrou que LLMs erram aritmetica
sobre 100+ valores em texto. STATS resolve esse problema **fora do
LLM** — Python calcula, LLM apenas le.

**Tamanho do overhead**: ~30-80 bytes por coluna. Para 100 linhas e
15 colunas, ~750 bytes adicionais (5-10% do payload).

**Ganho de accuracy**: dramatico. F-Q8 mediu +20-30pp em agg full-table
em modelos locais 7-14B.

**Limitacao** (F-Q28): STATS so resolve **agregacoes full-table**.
Para `q_avg_hours_male` (filter+agg), o STATS de `hours-per-week`
e `sex` separados nao ajuda — o LLM precisa cruzar mentalmente.

**Proposta v0.3 (Stratified STATS)**: emitir STATS condicionado por
subgrupos categoricos:

```
# STATS hours-per-week|sex=Male: n=68 avg=44.98
# STATS hours-per-week|sex=Female: n=32 avg=37.21
```

Isso atacaria filter+agg em Linha A para subgrupos pre-definidos.
Custo: +50-100 bytes por subgrupo. Vale apenas se subgrupos sao
conhecidos antecipadamente.

### 4. Schema-only (nivel L3)

Para Linha B (LLM gera SQL), apenas o schema e relevante:

```
## adult n=100
# STATS age: n=100 sum=3772 min=17 max=90 avg=37.72
# STATS hours-per-week: ...
# STATS class: cardinality=2 samples=[<=50K, >50K]
# (sem dados — schema-only)
```

**Tamanho**: 10-20× menor que L2 (470 bytes vs 7188 para Adult vol=100).

**Use case**: SQL gen. LLM nao precisa dos dados; usa schema + STATS
para decidir SQL, executa via SQLite, retorna resultado.

---

## Comparativo empirico (Adult Census vol=100)

| Formato | Bytes | Tokens (gpt) | Accuracy Linha A (gpt-5.4-nano) |
|---------|-------|--------------|--------------------------------|
| JSON | ~14000 | ~5500 | (nao testado) |
| CSV | ~9000 | ~3500 | (nao testado) |
| TCF L0 (raw columnar) | ~9000 | ~3300 | comparavel CSV |
| **TCF L2 (RLE+STATS+sort)** | **~7188** | **~2500** | **86.9%** |
| TCF L3 (schema-only) | ~470 | ~150 | n/a (Linha B) |

**Reducao TCF L2 vs CSV**: -20% em bytes, -29% em tokens. Diferenca
aumenta quando colunas sao tipicamente repetitivas (geographic data,
time series).

---

## Espectro de compressao real-world

Compressao TCF L2 varia conforme o dataset:

| Dataset | Caracteristica | Reducao L2 vs CSV |
|---------|----------------|-------------------|
| Time series sensor data | alto RLE potential | -50% a -70% |
| OLAP fact table com FKs | media RLE + ints | -25% a -40% |
| User profiles (heterogeneous) | baixo RLE | -10% a -20% |
| Wide tables (50+ cols) | nomes col dominam | -30% a -50% |
| Long random strings | RLE nao ajuda | 0 a -10% |

**Heuristica**: TCF brilha quando ha redundancia categorica/posicional.
Para dados completamente aleatorios sem padroes, ganho e marginal vs
CSV.

---

## Tradeoffs por nivel

```
   Compactness          Accuracy LLM        Roundtrip
        ↑                    ↑                  ↑
   L3 ████              L2 ████              L0 ████
   L2 ███               L1 ███               L1 ████
   L1 ██                L0 ██                L2 ████
   L0 █                 L3 -- (schema only)  L3  ❌
```

Decisao:
- **Quer accuracy maximo + dados embutidos** → L2
- **Quer payload minimo + LLM gera SQL** → L3
- **Quer roundtrip + debug** → L0
- **L1**: pouco diferenca pratica; manter mas nao destacar

---

## Limitacoes conhecidas (v0.2)

### 1. Numeric precision (ticket 23)

Floats sao serializados como `repr(value)` em Python. Para
roundtrip exato em valores muito longos, pode haver perda de
precisao implicita (`0.1 + 0.2`).

**Mitigacao atual**: scoring usa tolerancia 1% (`max(|x|*0.01, 0.1)`).
Para datasets cientificos onde precisao bit-exact importa, TCF v0.2
**nao** garante.

### 2. Decoder freetext (ticket 29)

Strings com newlines, ou caracteres `*` ou `:` em conteudo, podem
quebrar o decoder L0. Encoder escapa em alguns casos mas nao todos.

**Mitigacao atual**: input precisa ser sanitizado upstream. Bug nao
afeta Linha A nem Linha B (LLM nao decodifica; SQL roda no DB).

### 3. Tipos perdidos no decode

`decode(encode_rows(...))` retorna valores como `str`. O encode
recebe `int`/`float`/`bool` mas decode nao recupera.

**Mitigacao atual**: usuario reconverte manualmente. Inconveniente
para workflows que esperam roundtrip puro.

### 4. Multi-table no decode

`decode(text)` retorna `dict[table_name, list[dict]]` para multi-table,
mas `list[dict]` para single-table. Inconsistente.

### 5. RLE so para iguais consecutivos

Nao detecta padroes mais complexos (ex: ABABAB repetido). Algoritmos
mais sofisticados (LZ77, Huffman) nao foram explorados — provavelmente
prejudicariam legibilidade LLM (foco do TCF).

---

## Propostas v0.3

Cada uma com tradeoffs. Cabe avaliar em [R-tcf-core-revisit](../../workbench/tickets/open/R-tcf-core-revisit.md).

### A. Stratified STATS

Emitir STATS condicionado por categoricals:

```
# STATS age|sex=Male: n=68 avg=39.5
# STATS age|sex=Female: n=32 avg=34.2
```

**Pros**: ataca filter+agg em Linha A (gargalo F-Q28)
**Cons**: custo bytes; explosao se ha varias categoricas; usuario
precisa decidir quais cruzamentos

### B. Type-preserving decode

Decoder recupera tipos originais usando STATS (ou metadata explicito):

```python
# Encoder grava tipos no header
# TCF v0.3 level=2
# TYPES id=int name=str age=int

# Decoder reconverte
restored = decode(text)
assert isinstance(restored[0]["age"], int)  # nao str
```

**Pros**: roundtrip mais rigoroso
**Cons**: header maior, complica encoder

### C. Delta encoding para numeric ordenados

Se coluna numerica esta sorted, gravar deltas:

```
TCF L2:
timestamp:
1700000000
1700000060
1700000120
...

TCF L3 (proposta):
timestamp:
@delta start=1700000000 step=60
... (zero bytes per linha apos primeira)
```

**Pros**: dramatico em time series
**Cons**: complica decode; require detection automatico ou hint

### D. Frame-of-Reference (FOR)

Para inteiros num range pequeno (ex: ages 17-90), gravar como offset
do min:

```
age (FOR base=17):
13   (=30)
13   (=30)
14   (=31)
```

**Pros**: 50% menos digitos para ranges pequenos
**Cons**: LLM precisa entender o offset (probable issue)

### E. DICT global vs por-coluna

DICT atual e por coluna. DICT global compartilharia entre colunas com
valores comuns:

```
GLOBAL_DICT: {US, BR, ...}
country_origin: G[0] G[1] G[0]
country_dest: G[1] G[0] G[2]
```

**Pros**: ganho em datasets com cols de mesma cardinalidade
**Cons**: complica encoder; menos legivel para LLM

### F. Sortedness hint automatico

Encoder detecta automaticamente a melhor `sort_by` analisando RLE
potential de cada coluna categorica:

```python
encode_rows("table", rows, config=EncodeConfig(level=2))
# Se sort_by nao especificado, encoder testa cada categorical e
# escolhe aquela que produz mais bytes-saved
```

**Pros**: usuario nao precisa pensar
**Cons**: encoder lento (test cada candidate); pode escolher errado
em datasets onde sort altera semantica

### G. Schema_qualifier integrado (F-Q38)

Encoder aceita `schema_level` parameter:

```python
encode_rows("partsupp", rows, config=EncodeConfig(
    level=2,
    schema_level="minimal",  # F-Q38 evidence
))
```

E omite tabelas relacionadas / colunas redundantes para wordings
naturais. Conecta TCF com pipeline NL2SQL.

**Pros**: F-Q38 mostra +33pp em N3
**Cons**: pode ser melhor como camada externa (schema_qualifier
package), nao no encoder

---

## Priorizacao tentativa para v0.3

(Decisao final em [R-tcf-core-revisit](../../workbench/tickets/open/R-tcf-core-revisit.md))

| Proposta | Impacto | Custo | Decisao tentativa |
|----------|---------|-------|-------------------|
| A. Stratified STATS | alto (Linha A filter+agg) | medio | **incluir** |
| B. Type-preserving decode | medio (DX) | baixo | **incluir** |
| C. Delta encoding | alto p/ time series | alto | **futuro** |
| D. FOR | baixo | medio | **descartar** (LLM friendly?) |
| E. DICT global | baixo | alto | **descartar** |
| F. Auto sortedness | medio (DX) | medio | **incluir** |
| G. Schema_qualifier | alto (F-Q38) | alto | **separar** (camada externa) |

Plus:
- Fix bug 29 (decoder freetext) — **incluir**
- Endurece numeric precision — **incluir** (com flag opt-in para
  bit-exact)

---

## Como medir compressao em novos datasets

Script utilitario proposto:

```python
from tcf import encode_rows, EncodeConfig

def compression_report(name: str, rows: list[dict]):
    cfg_levels = [
        EncodeConfig(level=0, include_stats=False),
        EncodeConfig(level=2, include_stats=True),
        EncodeConfig(level=2, include_stats=True, sort_by=None),  # auto
        EncodeConfig(level=3, include_stats=True),
    ]
    csv_size = sum(len(",".join(map(str, r.values()))) + 1 for r in rows)

    for cfg in cfg_levels:
        text = encode_rows(name, rows, config=cfg)
        ratio = len(text) / csv_size if csv_size else 0
        print(f"  L{cfg.level} stats={cfg.include_stats}: "
              f"{len(text):,} bytes ({ratio*100:.1f}% of CSV)")
```

Para automatizar relatorio em novos datasets, ver
[../../workbench/tickets/open/T-compression-bench-tool.md](#) (a criar).

---

## Referencias relacionadas

- F-Q3, F-Q8 — origens da decisao por columnar + STATS
- F-Q24 — synthetic ≈ canonical em compressao + accuracy
- F-Q38 — schema pruning empirico (motiva proposta G)
- [storage.md](../architecture/storage.md) — onde ficam os dados
- [data-pipeline.md](../architecture/data-pipeline.md) — fluxo Shaper
  → encode
- [Apendice A](../../article/appendices/A-tcf-spec.md) — spec formal
  (placeholder hoje)
