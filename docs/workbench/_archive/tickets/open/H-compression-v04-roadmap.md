---
title: H-compression-v04-roadmap — propostas tecnicas de compressao para v0.4
type: hypothesis
status: OPEN
priority: HIGH
created: 2026-04-27
updated: 2026-04-27
origin: Foco no nucleo TCF como compressor/descompressor (conversa pos-reorg)
user_quote_1: "as compressoes novamente detalhar mais essa parte"
user_quote_2: "nao quero que o tcf tenha capacidade de server/client ou compressoes"
see_also:
  - docs/theory/components/4-compression-deep-dive.md (deep dive v0.2)
  - docs/theory/components/5-compression-map-v04.md (mapa v0.4)
  - docs/theory/components/6-test-harness.md (meta-programa, FORA TCF)
  - docs/theory/components/7-combination-study.md (estudo combinatorial)
  - docs/workbench/tickets/open/R-tcf-core-revisit.md (audit)
  - docs/workbench/tickets/open/M-architecture-v03.md (split)
  - docs/workbench/tickets/open/H-advanced-compression-v03.md (proposta antiga, superseded)
---

## Update 2026-04-27 (decisao do usuario)

**Removido deste roadmap:**
- ~~Transport layer~~ — vai para meta-programa (harness), fora do TCF
- ~~Server/client APIs~~ — fora do TCF
- ~~Compressao gzip/brotli embutida~~ — orquestrado pelo harness externo

**Adicionado:**
- DICT cross-column como **opcao** (era descartado); usuario controla
  via `dict_scope` parameter
- Estudo combinatorial de ordem (em vez de escolher teoricamente)
- Granularidade expandida: 6 profiles × 9 eixos parametrizaveis
- Foco cientifico: "TCF funciona em quais cenarios min/max?"

**Refocado**: este ticket cobre apenas **mudancas internas no TCF**
(`packages/tcf/src/tcf/`). Toda infraestrutura de teste/comparacao
vai para tickets separados (T-test-harness-mvp, E-compression-combinations).

---

# Roadmap de compressao para TCF v0.4

Substitui/refina o ticket antigo `H-advanced-compression-v04` (de
2026-04-15) com base nos achados de M-Acomm (F-Q28, F-Q31, F-Q38) e
no novo foco arquitetural (TCF nucleo + extras).

Detalhamento tecnico em
[../../theory/components/4-compression-deep-dive.md](../../../theory/components/4-compression-deep-dive.md).

## 7+1 propostas avaliadas

| Id | Proposta | Impacto | Custo | Decisao tentativa |
|----|----------|---------|-------|-------------------|
| **A** | Stratified STATS | alto (Linha A filter+agg) | medio | **incluir** |
| **B** | Type-preserving decode | medio (DX) | baixo | **incluir** |
| C | Delta encoding | alto p/ time series | alto | futuro |
| D | Frame-of-Reference (FOR) | baixo | medio | **descartar** |
| **E** | DICT global cross-coluna | **medio (-22% em casos com overlap)** | medio | **REABERTO 2026-05-05** |
| **F** | Auto-detect sortedness | medio (DX) | medio | **incluir** |
| G | Schema_qualifier | alto (F-Q38) | alto | separar (extras) |
| **H** | Affix-aware DICT (prefixo/sufixo comum) | condicional | baixo | **registrar c/ porens** |
| **I** | Lossless key elimination (chaves maleaveis PK/FK) | alto em schemas relacionais | medio | **registrar c/ porens** |

Tres propostas selecionadas: **A, B, F**. Plus 2 fixes conhecidos:
**bug 29 (decoder freetext)** e **issue 23 (numeric precision)**.

Propostas **E, H, I** registradas para validacao em escala (ver
secoes dedicadas abaixo) — implementacao opcional opt-in.

## Proposta A — Stratified STATS

### Motivacao

F-Q28 mostra que Linha A local cai para 0% em filter+agg. STATS atual
ajuda apenas em agg full-table. Stratified STATS emite agregacoes
condicionadas por categorical:

```
# v0.2 atual:
# STATS hours-per-week: n=100 sum=4243 min=7 max=99 avg=42.43

# v0.4 proposta:
# STATS hours-per-week: n=100 sum=4243 min=7 max=99 avg=42.43
# STATS hours-per-week|sex=Male: n=68 avg=44.98
# STATS hours-per-week|sex=Female: n=32 avg=37.21
```

### API proposta

```python
encode_rows("adult", rows, config=EncodeConfig(
    level=2,
    include_stats=True,
    stratify_stats=["sex", "class"],   # NOVO
))
```

### Estimativa de impacto

- Locais Linha A `q_avg_hours_male`: 0% atual → projeto 60-80% com
  stratified STATS (LLM le `STATS hours-per-week|sex=Male` direto)
- Custo bytes: ~50-100 bytes por (coluna × subgrupo). Para Adult com
  2 subgrupos × 4 numericas: +400-800 bytes (~10% do payload)

### Riscos

- Explosao se ha varias categoricals com alta cardinalidade
- Usuario precisa decidir quais cruzamentos
- LLM pode ignorar stratified STATS se prompt nao orienta

### Criterio de aceite

- [ ] Implementar parametro `stratify_stats: list[str]` em EncodeConfig
- [ ] Limitar a categoricas com cardinality <= 10 (evitar explosao)
- [ ] Round-trip exato: decoder ignora STATS no recover
- [ ] Test em Adult: q_avg_hours_male local sobe de 0% para >50%
  com stratified STATS

## Proposta B — Type-preserving decode

### Motivacao

`decode(encode_rows(rows))` retorna valores como `str`. Quem chama
`encode_rows` com `int`/`float`/`bool` espera roundtrip puro.

### API proposta

```python
# Encoder grava tipos no header (opcional)
text = encode_rows("t", rows, config=EncodeConfig(
    level=2, preserve_types=True,
))

# text contem:
# # TCF v0.4 level=2
# # TYPES id=int name=str age=int active=bool

restored = decode(text)
assert isinstance(restored[0]["age"], int)  # AGORA preserva
```

### Implementacao

Encoder coleta `type(rows[0][col])` para cada coluna. Encoder grava
linha `# TYPES col1=int col2=str ...` no header.

Decoder le essa linha e converte com `int()`, `float()`, `bool()`,
`json.loads()` (para None / nested).

### Backwards compat

Sem `preserve_types=True`, formato fica identico ao v0.2. Decode
funciona com tcf v0.2 e v0.4.

### Criterio de aceite

- [ ] Header opcional `# TYPES col1=type1 col2=type2 ...`
- [ ] Decoder reconverte usando essa linha quando presente
- [ ] Fallback para str quando linha ausente (compat v0.2)
- [ ] Test: `decode(encode_rows(rows, preserve_types=True)) == rows`
  para tipos primitivos

## Proposta F — Auto-detect sortedness

### Motivacao

`sort_by` parameter exige usuario decidir manualmente. Tipicamente
existe escolha obvia (categoria de baixa cardinalidade), e detectar
isso automaticamente melhora DX.

### Algoritmo

```python
def detect_best_sort_by(rows: list[dict]) -> str | None:
    candidates = []
    for col in rows[0].keys():
        values = [r[col] for r in rows]
        cardinality = len(set(values))
        if cardinality > len(rows) * 0.5:
            continue  # alta cardinalidade — RLE nao ajuda
        # Estimativa: bytes ganhos com sort
        sorted_runs = count_runs(sorted(values))
        unsorted_runs = count_runs(values)
        gain = unsorted_runs - sorted_runs
        candidates.append((col, gain, cardinality))
    if not candidates:
        return None
    # Maior ganho prevalece; tie-break por cardinality menor
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return candidates[0][0]
```

### API

```python
# Auto-detect
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by="auto",  # default ou opt-in
))

# Manual continua funcionando
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by="class",
))

# Sem sort
encode_rows("table", rows, config=EncodeConfig(
    level=2, sort_by=None,
))
```

### Tradeoff

- **Pros**: usuario nao precisa pensar; encoder otimiza ele mesmo
- **Cons**: encoder mais lento (precisa contar runs em N candidatos);
  pode escolher sort que **altera semantica** (ordem original era
  significativa para usuario)

### Criterio de aceite

- [ ] Funcao `detect_best_sort_by(rows) -> str | None`
- [ ] EncodeConfig aceita `sort_by="auto"`
- [ ] Default permanece `sort_by=None` (nao quebra v0.2 behavior)
- [ ] Adult Census: auto detect deve retornar `class` ou `sex`
- [ ] Logging opcional: log que coluna foi escolhida

## Bug 29 — decoder freetext fix

### Motivacao

Strings com `*`, `:`, `\n` em conteudo confundem decoder L0.

### Solucao

Encoder ja escapa `:` em values. Estender para `*` no comeco
(conflito com RLE) e `\n` (newlines em valores).

```
# v0.2 issue:
name:
A:B           ← parse error
3*foo         ← interpretado como RLE
multi
line          ← split em 2 valores

# v0.4 fix:
name:
"A:B"           ← strings com chars conflitantes ficam quoted
"3*foo"
"multi\nline"
```

### Criterio de aceite

- [ ] Encoder detecta caracteres conflitantes e quota o valor
- [ ] Decoder le valores quoted (handle `"..."` no L0)
- [ ] Test: roundtrip exato para strings arbitrarias
- [ ] Bug 29 fechado

## Proposta E — REABERTA 2026-05-05: cross-column DICT

### Origem da reabertura

Lab dirty `2026-04-30-cross-column-dict-mesa` mediu ganho de
**-21% a -26%** em 5 de 7 cenarios sinteticos. Justificativa
original ("baixo impacto") nao se sustenta. Achados:

| Cenario | Ganho cross vs L3 |
|---------|-------------------|
| Voc compartilhado (3 cols, 100% overlap) | -21.7% |
| FK em 2 tabelas (overlap 52%) | -25.1% (-347B abs) |
| Status enum (3 cols) | -26.0% |
| Categorias-pares (2 cols) | -22.2% |
| Voc igual, dist diferente | -21.1% |
| Tipos disjuntos (overlap 0%) | +3.2% (perde) |
| Texto livre (overlap 0%) | -1.7% (ambos perdem p/ naive) |

### Modelo formal

Para K colunas com vocabularios V_1..V_K, vocabulario unificado
V_total = union(V_k):

```
Per-column DICT (L3 atual):
  sum_k(|V_k| · |valor_k|) + sum_k(N_k · |idx_k|) + K · overhead

Cross-column DICT (proposta):
  |V_total| · |valor_avg| + sum_k(N_k · |idx_total|) + 1 · overhead

Δ = sum_k(|V_k| · |valor_k|) - |V_total| · |valor_avg|
    + (K-1) · overhead
    - sum_k(N_k · (|idx_total| - |idx_k|))
```

Quando overlap=100%: V_total = V_k para todo k. Aproximacao:
Δ ≈ (K-1) · |V| · |valor| + (K-1) · overhead

Ganho linear em K-1.

### Quando ATIVA vs quando DESATIVA

```
overlap_ratio = |intersection(V_1..V_K)| / |union(V_1..V_K)|

ATIVA cross-DICT se:
  K >= 2
  E overlap_ratio >= 0.5  (threshold a calibrar)
  E |V_total| < N_total / 2  (cardinality justifica DICT)

SENAO: fallback para L3 per-column.
```

### Casos onde vence (com forca)

1. **Schema relacional com FK explicita**: 2+ tabelas/colunas
   referenciam mesmo conjunto de IDs (S2 do lab: -25%)
2. **Status/flags enum repetidos**: campos de status em multiplas
   colunas com mesmo vocabulario (S3: -26%)
3. **Categorias hierarquicas**: principal/secundaria/terciaria com
   mesmo vocabulario (S4: -22%)
4. **Tipos enum padronizados**: yes/no, true/false em varias colunas

### Casos onde NAO vence

1. **Texto livre**: vocabularios disjuntos, cardinality = N (S7)
2. **Tipos completamente disjuntos**: nome+idade+status (S5)
3. **K=1**: caso trivial, fallback para L3

### API proposta

```python
EncodeConfig(
    level=3,
    dict_scope="auto",  # "per_column" (atual) | "cross" | "auto"
    cross_overlap_threshold=0.5,  # so ativa cross se overlap >= isto
)
```

Comportamento `auto`:
- Calcula overlap_ratio entre colunas
- Se overlap >= threshold E K >= 2: cross
- Senao: per_column (L3 atual)
- Auto-bypass quando ambos perdem para naive (vocab=N)

### Sintaxe proposta

```
# v0.4 com cross DICT:
## supplier n=100
# dict GLOBAL: pago,pendente,cancelado,ok,erro
status_pagamento:
0
1
0
2
status_envio:
1
3
1
0
status_cliente:
0
0
2
0
```

Cada coluna emite so indices; o DICT GLOBAL eh declarado uma vez.

### Riscos / poréns

1. **Datasets sinteticos artificialmente alinhados** — em dados reais,
   frequencia de overlap eh desconhecida (D1)
2. **Multi-tabela cross-tabela**: lab so testou cross-coluna na mesma
   tabela; cross-tabela depende do schema (D2)
3. **gzip do transporte pode comer ganho**: nao medido (D3)
4. **Detecao de overlap** eh O(K · |V|) — pode ser custosa em
   datasets com K grande (D4)
5. **Sintaxe**: `# dict GLOBAL:` precisa formalizar (vs scope mais
   granular como `# dict CROSS [col1, col2, col3]:` para misturar
   cross e per-column quando alguns subsets compartilham)

### Lab proposto (formal)

`E-cross-column-real-datasets`:
1. Coletar 5+ datasets reais com schema variado (TPC-H, Northwind,
   Adult Census, GitHub events, e-commerce orders)
2. Para cada par/grupo de colunas, calcular overlap_ratio
3. Histograma de overlap em datasets reais
4. Aplicar cross-DICT; medir ganho
5. Decidir threshold otimo de auto-detect

Custos: 1-2 dias.

### Decisao para o usuario

- Incluir Proposta E no Sprint 1+2 do v0.4?
- Ou implementar opt-in apenas (default = per_column)?
- Ou aguardar lab formal `E-cross-column-real-datasets`?

---

## Proposta H — Affix-aware DICT (registrada 2026-05-05)

### Origem

Conversa 2026-05-05: ideia do user de "DICT em pedacos parciais dos
dados — visao de dict ou ate RLE so que em pedacos parciais, olhando
nao apenas o registro, mas partes do registro" + alerta metodologico
"nao adianta falar em ganhou 12 bytes a mais; precisa evidencia
matematica indutiva ou testar em escala".

### Modelo formal

Para coluna com N linhas, prefixo comum P de tamanho |P|, cobertura
c (fracao das linhas que tem o prefixo):

```
Bytes original   = N · |valor|
Bytes com affix  = |P| + overhead_decl + c·N·(|valor|-|P|)
                 + (1-c)·N·(|valor| + |marker_excecao|)

Ganho liquido Δ  = (c·N - 1)·|P| - overhead_decl - (1-c)·N·|marker|
```

### Certezas matematicas (independem de dataset)

| # | Afirmacao |
|---|-----------|
| C1 | Ganho e linear em N (dado c proximo de 1) |
| C2 | Ganho e linear em \|P\| (dado c·N > 1) |
| C3 | Ganho assintotico c=1: (N-1)·\|P\| - overhead |
| C4 | Ponto de equilibrio (c=1): N = 1 + overhead/\|P\| |
| C5 | Sempre perde quando c < overhead / (N·\|P\| + N·\|marker\|) |
| C6 | Deteccao via LCP (longest common prefix) e O(N·\|valor\|) — barato |

### Duvidas que so dados reais respondem

| # | Duvida | Como responder |
|---|--------|----------------|
| D1 | Distribuicao real de \|P\| em datasets tipicos | medir LCP em N datasets reais |
| D2 | Distribuicao real de c (cobertura) | idem |
| D3 | Frequencia de "afixos multiplos" (clusters) | sondar datasets |
| D4 | Interacao com gzip do transporte (camada 3) | medir TCF+gzip vs TCF-affix+gzip |
| D5 | Ganho de legibilidade para LLM | escopo separado (M-llm-integration-future) |
| D6 | Sufixo simetrico em prova mas custo de deteccao maior — vale? | medir |

### Cenarios previstos pela matematica

| Cenario | c | \|P\| | Veredito |
|---------|---|------|----------|
| Identificadores sinteticos (Supplier#001) | ~1.0 | 4-10 | GANHA (alto) |
| URLs (https://...) | 0.7-0.9 | 7-20 | GANHA (medio) |
| Emails (sufixo @domain) | clusters | 8-20 | GANHA SE sufixo tratado |
| Datas ISO (2026-05-) | clusters | 5-7 | MARGINAL |
| Nomes pessoais | ~0 | 0-1 | NEUTRO ou perde |
| Texto livre | ~0 | 0-1 | PERDE (deve desativar) |
| Hashes/UUIDs | 0 | 0 | NEUTRO (LCP=0) |

**Conclusao indutiva possivel**: ganho e ESTRITAMENTE CONDICIONAL.
Nao ha "X% sempre"; ha um espectro `[-overhead, (N-1)·|P|]` que
depende da estrutura do dado.

### Hierarquia "DICT em niveis"

```
Nivel 0 — sem DICT          (L0/L1/L2 atuais)
Nivel 1 — DICT por valor    (L3 atual)
Nivel 2 — DICT por afixo    (Proposta H — ganho condicional, mensuravel)
Nivel 3 — DICT por substr   (n-grama interno — sobrepoe gzip; DESCARTAR)
```

Nivel 3 e territorio de gzip/brotli/zstd (camada 3 do M-chunks-v04).
Nao reimplementar.

### API proposta (opt-in)

```python
EncodeConfig(
    level=3,
    dict_mode="value",  # "value" (atual) | "affix" | "auto"
    affix_threshold=20, # bytes minimos de \|P\|·N para ativar; senao bypass
)
```

Comportamento `auto`:
- Detecta LCP por coluna
- Calcula ganho previsto via formula acima
- Se ganho > threshold, usa affix; senao, fallback para "value"
- Auto-bypass identico ao usado em L3 atual

### Sintaxe proposta no formato

```
# v0.4 (proposta H ativa):
## supplier n=100 grouped_by=s_nationkey
# affix s_name: prefix="Supplier#000000"
s_name:
001
002
...
```

Decoder reconstrui: `prefix + valor` por linha. Exceções (linhas sem
o prefixo) emitidas com marker:

```
# affix s_name: prefix="Supplier#000000"
s_name:
001
002
\!Other Vendor 001  # ! = exceção
003
```

### Criterio de aceite

- [ ] Implementar `detect_lcp(values, threshold)` em src/tcf/affix.py
- [ ] EncodeConfig.dict_mode aceita 3 valores
- [ ] Auto-bypass quando ganho previsto < threshold
- [ ] Roundtrip exato com afixos + excecoes
- [ ] Lab E-affix-real-datasets: medir D1-D6 em N datasets reais
- [ ] Documentar quando ativar manualmente vs deixar auto

### Por que registrar e implementar mesmo sem prova de ganho universal

- Implementacao e leve (~100 linhas)
- Auto-bypass garante zero custo quando nao se aplica
- Ter no arsenal permite **testes em escala**
  (1 tabela 5 rows ate centenas de tabelas, milhoes de rows)
- Sem ferramenta, todas as duvidas D1-D6 ficam especulativas

### Por que NAO incluir no Sprint 1+2 do v0.4

- Propostas A, B, F tem ganho mensurado (M-Acomm, F-Q*)
- Proposta H so vale apos D1-D6 medidos em escala
- Decisao: implementar **opcionalmente** apos validar A/B/F
- Considerar para v0.4.x ou v0.5

### Lab proposto (futuro)

`E-affix-real-datasets`:
1. Coletar 5-10 datasets reais variados (TPC-H, NYC taxi, GitHub events,
   Wikipedia, e-commerce)
2. Medir LCP por coluna em cada
3. Histograma de \|P\| e c
4. Calcular ganho previsto por coluna via formula
5. Se ganho mediano > X% em pelo menos K cenarios, implementar

Custos do lab: 1-2 dias de coleta + analise.

### Riscos / poréns explicitos

1. **gzip do transporte pode comer ganho**: se TCF+affix+gzip ≈ TCF+gzip,
   nao vale complexidade
2. **Multi-prefix clusters** (50% prefix-A, 50% prefix-B) requerem
   algoritmo mais sofisticado — fora do escopo inicial
3. **Sufixo** dobra complexidade de deteccao para ganho similar
4. **LLM legibilidade**: pode confundir; precisa validar em LLM
   integration phase (escopo ⚫ separado)
5. **Auto-bypass mal calibrado**: threshold errado pode ativar em
   casos onde perde — testes em escala necessarios

---

## Proposta I — Lossless key elimination (chaves maleaveis)

### Origem

Conversa 2026-05-05 (user): "as chaves de relacionamento nao sao
artefatos atomicos de negocio. Sao convencao computacional para
otimizar relacoes. Em teoria de bancos, voce pode ter PK/FK
semanticamente sem numeros — eles sao secundarios."

Estudo parcial anterior (referido pelo user): 3 tabelas — pessoa,
produto, pedido — onde se "sumiu" com chaves e regenerou
preservando relacao. **"Lossless key elimination"** — bytes
economizados sem perder informacao relacional.

### Tese

Chaves PK/FK tem **graus de maleabilidade**. Algumas podem ser
eliminadas pelo TCF (substituidas pelo indice DICT, que ja eh
uma chave interna canonica) e regeneradas no decode preservando
**a relacao** — nao necessariamente os valores literais.

### Classificacao em 4 graus

| Grau | Tipo | Caracteristica | Operacao TCF |
|------|------|----------------|---------------|
| **0** | Universal | UUID, hash, identificador external-facing | **PRESERVAR** valor exato |
| **1** | Natural com semantica externa | CPF, CNPJ, codigo produto, slug URL | **PRESERVAR** valor exato |
| **2** | Sintetica local | auto-increment INT, surrogate key | **ELIMINAR** + regenerar |
| **3** | Derivada/composta interna | hash composto, FK sem uso externo | **RECONSTRUIR** sob demanda |

**Princípio central**: graus 2 e 3 podem ser substituidos pelo
indice do DICT (que ja existe na compressao L3+). A relacao
referencial entre tabelas eh preservada via essa indexacao
canonica. Roundtrip preserva **relacao**, nao bytes literais.

### Exemplo concreto

Schema original:
```
pessoas (PK auto-increment grau 2)
  id  | nome
  1   | Ana
  2   | Bruno

pedidos (FK grau 2 → pessoas.id)
  pedido_id | pessoa_id | produto_id
  10        | 1         | 100
  11        | 2         | 101
  12        | 1         | 102

produtos (PK auto-increment grau 2)
  id  | nome
  100 | Abacaxi
  101 | Banana
  102 | Cereja
```

Com TCF eliminando chaves grau 2:

```
# dict pessoas: Ana,Bruno
# dict produtos: Abacaxi,Banana,Cereja

pessoas:
0  ← Ana
1  ← Bruno

pedidos: (sem id explicito; ordem implicita)
0,0   ← pessoa[0] x produto[0] = Ana x Abacaxi
1,1   ← pessoa[1] x produto[1] = Bruno x Banana
0,2   ← pessoa[0] x produto[2] = Ana x Cereja

produtos:
0  ← Abacaxi
1  ← Banana
2  ← Cereja
```

Decoder regenera ids (1, 2 ou outros) — relacao preservada.

### Modelo de bytes

Para tabela com PK grau 2, K linhas, |id_size| chars:

```
Bytes ECONOMIZADOS = K · |id_size| - overhead_recovery
```

Para FKs grau 2 com cardinalidade C (vocab da PK referenciada):
```
Bytes ECONOMIZADOS = K · (|id_size| - log10(C)) - overhead
```

(o indice eh `log10(C)` chars; id original era `|id_size|`)

### Casos onde vence

1. **Schemas relacionais com auto-increment** (caso comum em SQL):
   PK/FK sao grau 2 → eliminacao mass
2. **Datasets normalizados estrelarmente** (fact + dimensions):
   FKs predominam, todas grau 2
3. **CSVs exportados de banco** com colunas `id`, `entity_id`:
   Identificaveis por nome de coluna

### Casos onde NAO vence (preserva valor)

1. **UUIDs** (grau 0): nao eliminar
2. **Codigos de negocio** (grau 1: CPF, EAN, ISBN): nao eliminar
3. **Identificadores api-facing** (grau 0/1): preservar para
   retrocompat
4. **Datasets desnormalizados** (CSV plano sem FK): nada a eliminar

### API proposta

```python
EncodeConfig(
    level=3,
    key_elimination="auto",  # "off" | "manual" | "auto"
    preserve_keys=["uuid", "cpf", "external_id"],  # grau 0/1 explicitos
    schema={
        "pessoas": {"pk": "id", "pk_grade": 2},
        "pedidos": {"pk": "pedido_id", "pk_grade": 2,
                     "fks": {"pessoa_id": "pessoas",
                             "produto_id": "produtos"}},
    },
)
```

Comportamento `auto`:
- Detecta colunas auto-increment (sequenciais 1..N) — provavelmente grau 2
- Detecta colunas com nome `*_id`, `*_key`, `id` — candidatas a eliminacao
- UUIDs/hashes detectados pelo formato → grau 0 (preserva)
- Codigos com formato CPF/CNPJ/ISBN → grau 1 (preserva)

### Sintaxe proposta no formato

```
# v0.4 com key elimination:
## pessoas n=2 pk_eliminated
# dict pessoas: Ana,Bruno
nome:
0
1

## pedidos n=3 pk_eliminated fk_resolved={pessoa_id:pessoas, produto_id:produtos}
pessoa_id_idx:
0
1
0
produto_id_idx:
0
1
2

## produtos n=3 pk_eliminated
# dict produtos: Abacaxi,Banana,Cereja
nome:
0
1
2
```

Decoder:
- Le `pk_eliminated` → regenera ids 1..N
- Le `fk_resolved` → mapa indice → nome via DICT da tabela referenciada
- Reconstrucao de schema relacional valido

### Riscos / poréns

1. **Roundtrip preserva relacao, NAO valor**: quem depende de id
   especifico (ex: API externa que devolve `pedido_id=42`) nao pode
   usar — flag `preserve_keys=[...]` resolve mas requer schema
2. **CSV sem schema**: detectar PK/FK eh heuristico — fragil
3. **Multi-tabela sem FK explicita**: TCF precisa do schema; sem ele
   nao tem como saber qual coluna referencia qual tabela
4. **Chaves compostas** (PK = (a, b, c)): complexo; adiar
5. **Chaves "naturais" mascaradas como sinteticas**: ex: `user_id`
   sequencial pode na verdade ser referenciado externamente. Sem
   marcacao explicita, eliminacao pode quebrar contratos
6. **Interacao com Proposta E (cross-DICT)**: convergem — FK que
   referencia tabela X com DICT, e a PK eliminada de X, e a chave
   eh o indice do DICT. Coerente

### Lab proposto (formal)

`E-key-elimination-real-datasets`:
1. Coletar 3-5 schemas reais (TPC-H normalizado, Northwind, AdventureWorks)
2. Classificar PKs/FKs em graus
3. Aplicar eliminacao em graus 2/3
4. Medir bytes + reconstrucao de relacao
5. Validar roundtrip de relacoes (joins reproduzem mesmos resultados)

Custos: 2-3 dias.

### Decisao para o usuario

- Incluir Proposta I no Sprint 1+2 do v0.4?
- Em v0.4 expor so via schema explicito (sem auto-detect inicialmente)?
- Aguardar lab formal antes de implementar?

**Recomendacao**: aguardar lab `E-key-elimination-real-datasets`,
mas registrar agora a tese teorica + sintaxe proposta para nao
perder o conceito.

### Resultados do lab dirty (2026-05-05)

Lab `2026-05-01-key-graus-mesa` mediu em 3 cenarios:

| Cenario | naive | L3 | L3+elim | Ganho elim vs L3 |
|---------|-------|-----|---------|------------------|
| C1 3tables (FKs grau 2) | 737B | 803B | 704B | **-12.3%** |
| C2 TPC-H supplier (so PK) | 2505B | 2810B | 2531B | **-9.9%** |
| C3 desnormalizada | 934B | 650B | 650B | 0% (no-op) |

**Achado contraintuitivo**: L3 normal **PIORA** naive em C1 e C2
porque emite DICT em colunas de IDs unicos (overhead puro). Eliminacao
resolve duplamente — nao emite DICT inutil + nao emite os ids. Em
escala real (milhoes de rows), economia seria dominante em databases
relacionais.

Limites: datasets sinteticos pequenos (N=50); roundtrip de relacao
nao validado (so bytes); auto-detect de grau nao testado.

### Convergencia com outras propostas

| Proposta | Relacao com I |
|----------|---------------|
| E (cross-column DICT) | I usa indices DICT como chave; E define DICT compartilhado entre colunas com mesmo vocab. Quando combinam, FK vira so um indice |
| H (affix-DICT) | Identificadores estruturados (`Supplier#NNN`) sao tipicos de PK grau 2 — H comprime, I elimina (escolher) |
| B (type-preserving decode) | Decoder que regenera ids precisa preservar tipo (int) — coerente |

---

## Issue 23 — numeric precision

### Motivacao

Floats podem perder precisao em roundtrip (`repr(0.1+0.2)` = `'0.30000000000000004'`).

### Solucao opt-in

Flag `numeric_precision` em EncodeConfig:

```python
EncodeConfig(level=2, numeric_precision="repr")    # padrao v0.2 (rapido)
EncodeConfig(level=2, numeric_precision="str")     # padrao Python str()
EncodeConfig(level=2, numeric_precision="json")    # json.dumps
EncodeConfig(level=2, numeric_precision="hex")     # bit-exact (float.hex())
```

`hex` garante bit-exact mas e ilegivel para LLM. Util apenas para
roundtrip cientifico.

### Criterio de aceite

- [ ] EncodeConfig.numeric_precision aceita 4 valores
- [ ] Decoder detecta automaticamente (ex: hex starts with `0x`)
- [ ] Tolerancia 1% no scoring continua default (pra LLM eval)
- [ ] Bit-exact opcional para tests cientificos
- [ ] Issue 23 fechado

## Roadmap consolidado

### Sprint 1 (1 semana)
- [ ] B — type-preserving decode
- [ ] Bug 29 — decoder freetext fix
- [ ] Issue 23 — numeric precision opt-in

### Sprint 2 (1 semana)
- [ ] F — auto-detect sortedness
- [ ] A — stratified STATS

### Sprint 3 (validacao)
- [ ] Test stratified STATS em Adult Linha A — verificar +50pp claim
- [ ] Atualizar Apendice A (TCF spec) com v0.4
- [ ] Update CHANGELOG.md
- [ ] Tag git `v0.4.0`

## Total estimado

3 semanas focadas para core v0.4.

## Notas para revisar este ticket

Quando reabrir:
- Snapshot deste arquivo no commit `<ts>`
- Codigo atual: `src/tcf/encoder.py` v0.2
- Tests atuais: `tests/test_encode_decode.py` (se existir)
- Ticket relacionado [H-advanced-compression-v04](H-advanced-compression-v04.md)
  (proposta antiga, subset deste)

## Decisao para o usuario

1. **Sprint 1 e suficiente** para v0.4, ou queres tudo (1+2+3)?
2. **Stratified STATS**: API exigir lista explicita ou auto-detect
   (igual sortedness)?
3. **Bug 29 e Issue 23**: incluir em v0.4 ou postpor?
