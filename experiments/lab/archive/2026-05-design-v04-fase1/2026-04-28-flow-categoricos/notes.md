# Workbench: flow-categoricos (2026-04-28)

## Pergunta

Os padroes consolidados em `flow-pessoas` (cabecalho minimal v0.4,
auto-bypass, encoding implicito) **funcionam** quando o dado e
**categorico de baixa cardinalidade com repeticao**? Ou seja:
cenario MAX para TCF (onde RLE/DICT deveriam brilhar).

## Hipotese

Em dados categoricos com repeticao:

- **TCF L2 (RLE) sorted** vence CSV em bytes
- **TCF L3 (DICT) auto-bypass** NAO bypassa — DICT ajuda aqui
- **Cabecalho minimal `# TCF v0.4 lv=N`** continua adequado
- **Encoding utf-8 implicito** continua valido (sem caracteres exoticos)

## Material

Dataset: TPC-H supplier (sf001) — 100 rows. Colunas categoricas:
- `s_nationkey` (int, 25 valores distintos, ~4x repeticao por valor)

Combinacao MAX:
- 100 rows x 1 col categorica
- ordenacao por `s_nationkey` ANTES de encode (simula sort_by ideal)

Se TCF nao vencer aqui, **tem problema serio**. Se vencer mas com
overhead (cabecalho), confirma minimal style.

## Cenarios

| # | Dataset | Strategy |
|---|---------|----------|
| A | 100 supplier.s_nationkey (random order) | baseline — sem sort |
| B | 100 supplier.s_nationkey (sorted asc) | manual sort = melhor caso |
| C | 100 supplier (s_nationkey + s_name) | mix categorico + unico |

## Expectativas (a confirmar)

- **A vs B**: TCF L2 deve cair MUITO em bytes apos sort (RLE longo)
- **C**: s_name (unico) limita ganho — TCF L3 DICT deveria ajudar
- **Cabecalho v0.4 minimal**: deve permanecer ~7B do payload total
  em datasets pequenos, irrelevante em medios

## O que valida o flow

Se as 3 hipoteses acima forem confirmadas, o padrao v0.4 cabecalho
minimal eh **robusto** para os 2 cenarios extremos:
- MIN (flow-pessoas): nomes unicos, cabecalho ~7% do payload
- MAX (flow-categoricos): repeticao, cabecalho irrelevante

Saida: `./output/`

---

## Resultados (run.py executado 2026-05-05)

### Numeros chave

| Cenario | CSV | TCF v0.2 L2 | TCF v0.4 L2 | TCF v0.2 L3 |
|---------|-----|-------------|-------------|-------------|
| A: 100 x s_nationkey (natural) | 275B | 274B (-0.4%) | **240B (-12.7%)** | 274B |
| B: 100 x s_nationkey (sorted) | 275B | 274B (-0.4%) | **240B (-12.7%)** | 274B |
| C: 100 x (nationkey, name) natural | 2182B | 2182B (0.0%) | **2148B (-1.6%)** | 2487B (+14%) |
| C: 100 x (nationkey, name) sorted | 2182B | 2182B (0.0%) | **2148B (-1.6%)** | 2487B (+14%) |

### Hipoteses revisadas

- **H1) TCF L2 sorted vence CSV em bytes:** confirmado, mas margem
  pequena (-12.7% na coluna pura, -1.6% no mix). v0.4 envelope
  **economiza 34B** vs v0.2 (cabecalho minimal `# TCF v0.4 lv=2`
  vs `# TCF v0.2 level=2\n# N*val = ...`).
- **H2) TCF L3 (DICT) auto-bypass NAO bypassa em categoricos:**
  na coluna pura nao bypassa (240B = 240B); no mix com s_name unico
  o DICT vira overhead (+14%) e **smart bypassa para L2**. Funciona.
- **H3) Cabecalho minimal v0.4 adequado:** confirmado em ambos.

### Findings inesperados (importantes para v0.4)

#### Finding F-cat-1 — TCF v0.2 L2 SEMPRE ordena internamente

Encoder ignora ordem original do input. A natural e B sorted dao
**bytes IDENTICOS** (274B). Isso e otimo para compressao, mas:

- **Quebra roundtrip se a ordem do input era semantica**
  (ex: serie temporal, ranking) — testado: 3-6/100 match.
- Decoder retorna em ordem ordenada-por-nationkey, nao na ordem
  original.
- **Implicacao v0.4**: precisa flag `preserve_input_order` ou
  documentar claramente que L2 reordena.

#### Finding F-cat-2 — Sort lexicografico em valores numericos

Coluna s_nationkey e int (0..24), mas encoder ordena
**lexicograficamente**:

```
0, 1, 10, 11, 12, ..., 19, 2, 20, 21, ..., 9
```

`"10" < "2"` em string. RLE ainda funciona (agrupa runs identicos)
mas a ordem e contraintuitiva. **Implicacao v0.4**: detectar tipo
numerico e ordenar como int/float quando aplicavel.

#### Finding F-cat-3 — DICT e contraproducente em colunas unicas

s_name (100 distintos em 100 rows) com L3 produz dict de ~1900B +
indices de ~190B. Total **+14% pior que L2**. Auto-bypass do
envelope v0.4 detecta e cai para L2 corretamente.

**Implicacao v0.4**: usar cardinality threshold para decidir DICT
por coluna (ex: `cardinality / n < 0.3` -> dict; senao plain).

#### Finding F-cat-4 — sort_by reordena TODAS as colunas

Quando L2 sorta por s_nationkey, s_name e reordenado **na mesma
permutacao**, preservando correspondencia row-wise. Comportamento
correto (esperado), mas vale documentar explicitamente.

#### Finding F-cat-5 — RLE so brilha quando 1 col tem ratio < 0.5

Cardinality ratio deste cenario: 25/100 = 25%. RLE deveria comprimir
muito. Mas ganho real foi -0.4% (v0.2) ate -12.7% (v0.4 envelope).

Razao: cada valor unico tem **2-8 repeticoes em media**, mas em runs
**curtos** (sem agrupamento natural). Apos sort interno, runs viram
contiguos e RLE consegue comprimir. **Mesmo assim, CSV ja eh muito
denso** (1-2 chars por inteiro), entao a margem fica pequena.

**Implicacao v0.4**: TCF brilha em **strings repetidas medias-grandes**
(ex: "USA" 50x), nao em ints curtos. Para validar, criar cenario com
`s_name` repetido (e.g. categoria 'small'/'medium'/'large').

### Validacao final dos padroes v0.4

Os padroes do flow-pessoas **se mantem** em flow-categoricos:

| Padrao v0.4 | flow-pessoas (MIN) | flow-categoricos (MAX) |
|-------------|--------------------|-----------------------|
| Cabecalho `# TCF v0.4 lv=N` | OK (15B = 7% payload) | OK (15B = irrelevante) |
| Encoding utf-8 implicito | OK | OK |
| Line-ending LF (decoder detecta) | OK | OK |
| Auto-bypass L3->L2 | nao testado | **CONFIRMADO** (mix C) |
| Body v0.2 (transparente) | OK | OK |
| @llm-hint opt-in | OK | OK (nao usado) |

### Issues novas para v0.4 (alem do flow-pessoas)

1. **F-cat-1**: comportamento `preserve_input_order` precisa ser
   explicito (flag ou doc).
2. **F-cat-2**: sort numerico em colunas detectaveis como int/float.
3. **F-cat-3**: cardinality threshold per-coluna para DICT auto.
4. **F-cat-5**: testar cenario com strings repetidas para confirmar
   "TCF brilha onde ha repeticao real".

---

## Ciclo 2 — analise profunda de "so categoricos" (run-2.py)

**Pedido do user**: antes de mexer no core e antes de voltar ao mix,
refletir sobre como nao deixar ambiguo o tratamento de categoricos.
Pensar sobre tipos, ordenacao, agrupamento — tudo deduzivel ao maximo.

**Insight do user que motivou esta analise:**

> "RLE e orientado por ordenacao, mas ao mesmo tempo ele tem
> caracteristicas de agrupamento. Logo, na parte do output so de
> categoricos, o `sorted_by` faz sentido na parte nao-RLE, mas na
> RLE ele tem um carater MISTO sorted/grouped, certo?"

### Prova empirica: SORT vs GROUP para RLE

Testei 5 estrategias de organizar `s_nationkey` (100 valores, 25
distintos) **antes** de aplicar RLE:

| Estrategia | runs | bytes payload | Comentario |
|-----------|------|---------------|------------|
| sort-lex (TCF v0.2 atual) | 25 | 110B | bug visual: 0,1,10,...19,2,20,... |
| sort-numeric | 25 | 110B | corrige ordem visual |
| sort-by-frequency | 25 | 110B | top-k primeiro |
| group-only (preserva ordem original) | 25 | 110B | mantem semantica do input |
| natural (sem reordenar) | 96 | 260B | RLE quase nao comprime |

**Resultado matematicamente forte**: as 4 primeiras dao
**EXATAMENTE 25 runs e 110 bytes** — bit-identico em compressao.

### Conclusao: vocabulario correto para v0.4

O user estava certo: **GROUPED e o que RLE precisa**, nao SORT.

| Conceito | Necessario p/ RLE? | Quando usar |
|----------|--------------------|-----------------|
| `grouped` | SIM | RLE precisa de runs contiguos |
| `sorted` | NAO | overkill p/ RLE; util p/ STATS condicionados, diff, leitura LLM |

**Decisao para o header v0.4**: usar `grouped_by` quando a coluna foi
agrupada, e `sorted_by` apenas quando houve **ordem total** real.
Nunca dizer `sorted_by` quando so ha agrupamento.

### Tipo vs Papel (categoria vs numero)

`s_nationkey` e int (Python entrega int). Mas:
- Como **numero**: `STATS avg=13.22` faz sentido (media de medicoes)
- Como **categoria**: media de IDs e nonsense; quer-se top-k freq

A heuristica `cardinality/n < 0.3 + cardinality <= 50` detecta
`cat-numeric` (caso ambiguo). Heuristica sozinha nao decide — precisa
sinal explicito do usuario.

**API proposta v0.4**:

```python
EncodeConfig(
    auto_detect_types=True,           # detecta int/float/str
    column_roles={                    # role explicito quando ambiguo
        "s_nationkey": "categorical",
        "hours-per-week": "numeric",
    },
)
```

- `auto_detect_types`: seguro (int/float/str sao deterministicos)
- `column_roles`: opt-in, resolve ambiguidade caso a caso

### O que o decoder ganha com type+role no header

| Header info | Decoder retorna | Uso |
|-------------|-----------------|-----|
| sem info (v0.2) | `str("0")`, `str("10")` | usuario converte manual |
| `type=int role=cat` | `int(0)`, `int(10)` + flag categorical | nao calcula avg, oferece freq |
| `type=int role=numeric` | `int(0)`, `int(10)` + flag numeric | STATS faz sentido |

### Variantes de header v0.4 testadas

| Variante | Bytes | Comentario |
|----------|-------|------------|
| v0.2 atual: `sorted_by=` | 39B | mente quando e so grouped |
| v0.4-A verboso: `# col x: type=int role=cat layout=gs sort=num` | 73B | autoexplicativo, mas pesado |
| v0.4-B compacto: `s_nationkey:int:cat:gs/n:` | 43B | siglas curtas |
| v0.4-C minimal: `grouped=s_nationkey` | 37B | assume defaults |

**Tendencia**: v0.4-C minimal alinha com a filosofia ja consolidada
("cabecalho minimal e principio, nao otimizacao"). Detalhes finos
(role, sort_kind) so quando NAO sao default.

### Decisoes pendentes para registro em ticket

| Q | Pergunta | Tendencia atual |
|---|----------|-----------------|
| Q1 | `sorted_by` ou `grouped_by`? | grouped_by; sorted_by so quando aplicavel |
| Q2 | Sort lex vs numeric? | detectar tipo, usar sort numerico em int/float |
| Q3 | Tipo: auto vs flag? | auto p/ tipo basico; flag p/ role (cat vs num) |
| Q4 | STATS em categoricas? | trocar avg/sum por count+cardinality+top-k |
| Q5 | Preservar ordem original? | flag `preserve_input_order=True` opt-in |

### O que NAO foi resolvido nesta analise

- **Como o decoder LE o tipo do header de forma robusta**
  (grammar formal, escape, retrocompat com v0.2 sem type)
- **Como STATS para categoricas se chamam** (`# FREQ s_nationkey: ...`?
  `# CAT-STATS s_nationkey: cardinality=25 ...`?)
- **Cenarios mix** — proximo ciclo, conforme pedido do user

### Proximos passos

1. Adicionar Q1-Q5 como sub-itens em
   [H-compression-v04-roadmap](../../../../docs/workbench/tickets/open/H-compression-v04-roadmap.md)
2. Voltar ao **mix** (s_nationkey + s_name) com vocabulario novo
3. Eventualmente: cenario com strings repetidas (status='active'/'inactive')
   para validar que TCF realmente brilha em repeticao.

