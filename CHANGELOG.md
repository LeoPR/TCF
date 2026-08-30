# Changelog

History of TCF condensed into logical versions. For commit-level detail see `git log`.

The project is **pre-1.0**. The package version is `0.<format>.<release>`: the minor tracks
the format number (`#TCF.8` today), and there is **no compatibility guarantee between
pre-1.0 versions**: an older format is reproduced by checking out the tag that emitted it,
not by carrying compatibility code ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md),
[ADR-0028](docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md)).
Semver starts when the format freezes at 1.0.

Entries below are dated and append-only: this is where the chronology lives, so the reference
documentation does not have to carry it. Headings that read "STABLE" or "frozen format" are
internal milestones of their moment, not contracts. Date in parentheses = when the milestone
was consolidated.

Lab narratives, kept outside the package: v0.5 per-experiment timeline in
[`docs/workbench/_archive/DEVELOPMENT.md`](docs/workbench/_archive/DEVELOPMENT.md); the
compositional cycle in
[`experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md`](experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md).

---

## 0.8.3 (2026-08-29): the three families answer the same question the same way

An audit measured the three wire families (`#TCF.8`, `#TCF.8M`, `#TCF.8H`) along five axes
and found them agreeing on clean, homogeneous data and disagreeing on almost every edge.
This release closes that gap: seven welds, six bug tickets, and one change to what the
encoder emits.

**Read this first if you already have data on disk.** A `.8H` column that is *dense with
nulls* (the key present in every row, some values `None`) now declares `?0:` instead of
`?:`. Version 0.8.3 reads every wire 0.8.2 wrote; version 0.8.2 does **not** read this one,
and fails loudly rather than reading it wrong. Nothing else about the wire changed, and the
byte-canonical gates are untouched.

**Mixed-type columns stop losing data silently.** A column mixing `int` and `str` used to
pass through `#TCF.8M` and come back wrong: `[1, ""]` returned `[1, None]`, `[1, "1"]`
collapsed both values into one, and `[1, "a"]` produced a wire the decoder itself could not
read. The multi-column gate now uses the same homogeneity judge as `#TCF.8H`, so all three
families refuse the same column, which is what the API reference already promised. Nine of
thirty-nine routes changed verdict; the fourteen that round-tripped correctly are byte-identical.

**Null is not absence, in the hierarchical family too.** `encode([{"a": "x"}, {"a": None}])`
is a rectangular table, and the view refused it as ragged: the header spelled "key missing"
and "key present, value null" the same way. The dense-with-nulls scalar column now carries
a two-state element mask, the same one arrays already used, so the view can tell a table
with nulls from a ragged one by the header alone. This is the emission change above.

**The union column can be filtered on both sides.** In `#TCF.8bB` (bool and str together)
the view read the tag at index 6 and declared the column pure bool, ignoring the `B` at
index 7 that marks the union. Filtering by a string returned the boolean's row, or nothing,
or raised. Four ways to ask are now available, and three of them already worked:
`where(col, True)` for the boolean, `where(col, "true")` for the string as it is, and
`pred=` for the semantic and case-insensitive sets.

**A mixed column now says so.** The union route emitted the wire silently, while the same
column is refused as a `dict` and as a dataset: the same data passed or not depending on
how it was written. It warns now, counting each type.

**Four more places where the view answered about a table that does not exist**: a `#O` with
columns of different lengths was accepted and then accused an intact blob of being corrupt;
a magic-less wire (`stamp=False`) was refused though `decode` reads it; a zero-row column
invented a `''`; and a truncated wire got a silent row count where a full `decode` would
refuse. The last one now warns instead of going quiet.

**Errors that teach.** The mixed-type message named a family the caller never invoked,
cited a date (none of the other 210 messages in the package do), and named neither the
column nor the value (182 of 211 do). It now names both and, more importantly, says what
each of the two ways out costs: separating by type preserves the type but scrambles the
order when types are interleaved, and converting to string preserves the order but erases
the type and merges values that differed only by it. A non-`str` dict key stops raising a
raw `TypeError` and gets the typed error the hierarchical route already had.

**Also**: the `.8H` gained the spec telemetry the other two families already had, and warns
when a spec is dropped because a value cannot be represented; the view undoes leaf escaping
in `.8H`, so text columns holding a backslash or CR are read as the data, not as the escape.

Suite: 1693 tests. Byte-canonical gates: 33, unchanged. Two navigation pins re-pinned
(`c05` 842→843, `c12` 1453→1454), both `.8H` synthetics with a dense-with-nulls column.

---

## 0.8.2 (2026-08-25): the view learns to read the structure

Ten welds on top of 0.8.1, all in the read-only query layer except one, which does change
what the encoder emits.

**Format change (emission)**: a typed column no longer pushes the whole table out of
`#TCF.8M` into `#TCF.8H`. The type now travels as a one-byte tag in the meta, so
`encode({"uf": [...], "qtd": [1, 2, 3]})` stays multi-column and keeps the
`min(tcf, raw, dict, split)` competition. Measured cost of the type: **+1 byte** when the
typed column sits anywhere but last, **+3** when it is last (the tag brings back the size
that `min_header` was omitting; the minimal wire would be +1, and that header optimisation
is not done).

**The view reads everything that is a table**: `#TCF.8M`, `#TCF.8H` when rectangular, and
the single-column route in all its forms. Until now a single `int` or `bool` column made
`view()` refuse the table outright.

**`count()` stopped materialising anything**, in every mode. Counting rows never needs the
values, and the structure already states them: dense routes write `n` in the header as hex;
the core body carries counters (`*N|`) declaring how many rows each one stands for; the raw
body is one line per value; the dictionary is `len(stream) // width`. `report()` reflects
it: after a plain `count()`, `materialized_bytes` is 0. The one exception is a table where
*every* column is `split`, which declares no count anywhere.

**`view(blob)` no longer decodes on open** in the single-column route. It used to call
`decode()` in `__init__`, so connecting to a blob already materialised 100% of the wire
before any question was asked.

**`where` answers the two extremes without scanning**: in a dictionary column, when no
unique matches the answer is empty, and when all match it is every row. The unique table is
the closed list of what the column holds, so it settles both ends by itself.

**Two silent bugs fixed**, both of the same class (two spellings of one marker, two
readers): the new counter reader missed the multi-delta `*29+0,1|` that the encoder emits
for any date or datetime column, which made `view` report 63 rows out of 1000 and, worse,
`select()` return the table truncated with no error; and the fast filter path agreed with
the slow one only on text columns.

**The grouping surface is complete.** `where(...).group_count(...)`, the most basic
`WHERE ... GROUP BY` in SQL, used to raise `AttributeError`: the filtered result knew how
to aggregate the whole set but not how to group it. Added along with `group_min`,
`group_max`, `group_avg` (only `count` and `sum` existed) and grouping by several columns,
where the key becomes the tuple of values. Where the market disagrees with itself, the
choices are documented rather than assumed: a null key **forms a group** (as in SQL and
polars, unlike pandas' default, which drops it); a group with no usable value sums to
`0.0`, because the empty sum has an answer, while `min`/`max`/`avg` return `None` there,
because they do not; and the group shows up either way instead of vanishing.

**`distinct` and `n_unique`**, the `SELECT DISTINCT` and `COUNT(DISTINCT col)`. In a
dictionary column both come off the unique table the body already carries, in O(K). They
cost different things and the docs say so: `n_unique` only needs its size and builds no
value at all, while `distinct` builds the K uniques, because that is what it returns.

**`None` no longer blows up the encoder.** A null anywhere in a column raised a raw
`TypeError` from three layers below `encode`, with no column or row named, whenever the
first value formed a digit template with 2+ fields. The `%split` candidate now declines
columns with nulls, the same refusal for the same reason the raw candidate already made:
the mode has nowhere to represent a null, and the tcf candidate, which has a proper null
slot, serves those columns. Measured before welding: across 6 strong-template shapes x 4
null fractions, the serving mode already beats the ceiling of a null-tolerant split in all
24 combinations, so declining costs zero bytes and no wire changes.

**Grouping semantics are now decisions, not defaults.** A null key forms a group and there
is deliberately no `dropna` flag: dropping the null is a filter, and
`where(col, pred=lambda x: x is not None)` already does it while keeping the discard
visible (on a dictionary column the predicate runs over the K uniques, so the explicit
form costs no more). A group with no usable value sums to `0.0` because the empty sum has
a mathematical answer, while `min`/`max`/`avg` return `None` there because they do not.
A new how-to (`docs/how-to/mimetizar-pandas-sql-polars.md`) gives the one-line recipe for
matching pandas, SQL or polars behaviour, each recipe verified by execution against what
the original tool would return.

**`where` now reads the filter value in the column's type** (soft by default, with a
warning and a record in `v.coercoes`), replacing the `TypeError` that 0.8.1 raised. A
`.strict()` opt-in keeps the old rigour.

Test suite 1252 → 1497. Byte-canonical gates green throughout, with a deliberate re-pin
only where the typed route changed emission.

---

## 0.8.1 (2026-08-23): fail-loud: wire concatenado, contador RLE, view posicional

Três comportamentos silenciosos eliminados do decode/view, cada um re-provado em lab
dedicado com verificação adversarial independente antes do fix. **Zero mudança de emissão**:
o encode está intocado e o wire é byte-idêntico ao 0.8.0 (gates verdes sem re-pin).

- **`decode` rejeita header no meio do corpo**: concatenar dois wires prontos corrompia
  **calado** (as refs do segundo resolviam na tabela acumulada do primeiro; na pior variante
  até `n_rows` batia). Agora `ValueError` nomeando a causa: cortar um wire é seguro,
  concatenar exige decode + re-encode. Falso-positivo zero em corpo tcf (literais escapam
  dígitos); **limite**: corpo raw é verbatim e a junção lá segue indetectável.
- **Contador RLE exige `N >= 2` em dígitos ASCII**: `*0|`, `*1|`, negativo e grafias com
  sinal eram aceitos: linha sumindo ou fantasma sem erro (no seq-RLE, `*0+1|` emitia o
  template: 1 linha que o contador declara não existir). Todo o espaço rejeitado é
  inemissível pelo encoder.
- **`view`: `int` = POSIÇÃO em toda a superfície**, a mesma regra e faixa do `schema=`
  (ADR-0047: `str` = nome, `int` = posição, `0 <= pos < n`, bool excluído), na terceira
  porta pública que faltava. Junto: `select(0)` não é mais engolido por truthiness (escalar
  = sobrecarga de 1 coluna; `select([])` passa a significar *nenhuma* coluna) e `where` com
  `value` não-`str` levanta `TypeError` ensinante (respondia 0 linhas calado; valores
  decodados são `str`, `None` casa nulo).

## 0.8.0 (2026-08-23): `#TCF.8` default

**Mudança de formato**: `#TCF.8` vira o formato **DEFAULT** de emissão
([ADR-0032](docs/adr/0032-tcf8-default-format.md); minor acompanha o formato, ADR-0028). O ciclo
`0.7.2` (lazy+poda) foi **absorvido** neste release (sem release intermediário). Publicado no
PyPI (`tcf-format`) em 2026-08-23 via Trusted Publishing, tag `v0.8.0`.

### Formato e rotas

- **`#TCF.8M` é o default multi-col**: todo `encode(dict)` sai `#TCF.8M`, meta INLINE na
  assinatura (sem prefixo `# `), byte-sizes em **HEX**, última coluna sem size (`min_header`).
- **Single-col ganha header por default, 100% dos casos** (`#TCF.8\n`,
  [ADR-0034](docs/adr/0034-header-default-100-porcento-single-col.md)): o arquivo se
  auto-explica em vez de depender de quem o produziu (+7 B, inevitável e assumido).
- **`#TCF.8H` hierárquico SOLDADO** ([ADR-0033](docs/adr/0033-hierarchical-codec-weld.md)): o
  dataset aninhado que sua linguagem monta do JSON (objetos/arrays aninhados, `null`
  (distinto de ausente e de `"null"`), registros ragged, qualquer raiz) faz round-trip
  exato pela MESMA porta `encode`/`decode` (rota por tipo de entrada, simétrica ao decode
  por magic). O objeto é fatiado em colunas: nomes de campo escritos UMA vez, não por
  registro. Paridade com a classe D_json mapeada em
  [`docs/reference/json-equivalence.md`](docs/reference/json-equivalence.md).
- **Rota TIPADA single-col**: `list[bool]` / `list[int|float]` preservam o TIPO no wire
  (`#TCF.8b`/`#TCF.8n`): bool denso a 1–2 bits/elemento
  ([ADR-0037](docs/adr/0037-denso-b2-ternario-dominio-implicito.md)), união bool+str lazy
  `#TCF.8bB` ([ADR-0039](docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md)), grafias
  canônicas congeladas ([ADR-0038](docs/adr/0038-indice-interno-default-core-tipado-bool.md)).
- **Candidatos novos no mesmo `min()` nunca-pior**: delimitador de POLARIDADE
  ([ADR-0035](docs/adr/0035-delimitador-de-polaridade-single-col.md); 1 byte por transição em
  vez de 1 por literal), **bN de domínio** para cardinalidade baixa
  ([ADR-0036](docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md); k distintos em
  ceil(log2 k) bits/linha), **seq-RLE periódico** `*N~d1,..,dp|`
  ([ADR-0040](docs/adr/0040-seq-rle-periodico.md); o delta CICLA: 600 dias úteis em 1 marcador).
- **Todo nome de coluna é representável**: separadores escapados com `\`
  (único proibido: `\n`); nome VAZIO `''` preservado via sentinela `\z`
  ([ADR-0046](docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md); fecha o único caso em que o
  TCF alterava o dado); coluna anônima/posicional SÓ via `drop_names`.
- **Legado `#TCF.6`/`#TCF.7` cortado** de `src/tcf` (emit E decode): fail-loud com dica de
  git. Git-as-compat ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)): versão
  antiga se reproduz por checkout, não por bagagem no código. Sem modos de compatibilidade
  até o 1.0 (decisão reafirmada do owner).

### Specs (natures)

- **`schema=` é o parâmetro ÚNICO de spec** nas duas portas
  ([ADR-0047](docs/adr/0047-schema-parametro-unico-de-spec.md)); `nature=`/`nature_per_col=`
  CORTADOS (seco, sem alias: mesmo regime do legado). Formas: `"cpf"` (name do registry) ·
  objeto spec · `{coluna: spec}` com chave str=NOME / int=POSIÇÃO. É **incremental**
  (default = string semântico; o schema muda um ou mais) e tem **sobrecarga** (tabela/wire de
  UMA coluna aceita a forma escalar). Exports novos: `SPEC_DATA_ISO`, `SPEC_INT_PAD`,
  `SPEC_REGISTRY`.
- **Registry com 5 specs**: cpf, cnpj, ip, **data-iso** (`:dt`, ISO→ordinal, casa com o
  seq-RLE) e **int-pad** (`:ipad`). Identidade em DOIS planos
  ([ADR-0041](docs/adr/0041-spec-id-tres-planos.md)): `name` legível na API, `wire_id` curto
  no header; fail-loud de grafia, colisão e mascarada; header autoritativo no decode.
- **CNPJ alfanumérico** (IN RFB nº 2.229/2024, vigente desde jul/2026): **UM spec só**
  ([ADR-0044](docs/adr/0044-cnpj-um-so-alfanumerico.md)); corpo 100% decimal segue emitindo
  os 7 chars **byte-idênticos** ao wire legado (compacto por valor,
  [ADR-0043](docs/adr/0043-cnpj-um-so-compacto-por-valor.md)); o decode discrimina pelo
  comprimento.
- **Bordas em valor de spec** ([ADR-0045](docs/adr/0045-bordas-em-valor-de-spec.md)): regex
  fechada com `\Z` (o `$` do Python também casa antes de um LF final; o RT perdia o
  caractere); telemetria `format_bordered` distingue "dado certo, pipeline sujo" de "forma
  desconhecida".
- Telemetria (`SideOutputs`) virou **opt-in**: 3,9–31,1% do tempo de encode devolvidos ao
  caminho comum; wire byte-idêntico.

### API e congelamento do `.8`

- **Porta única**: `encode()` roteia por tipo de entrada (list/dict/aninhado/tipado);
  `decode()` pelo magic. `encode_hierarchical` e afins fora da superfície pública.
- **Congelado por teste executável**: assinaturas de `encode`/`decode` (nome, ordem, kind e
  default de cada parâmetro) e a superfície de exports (`EXPECTED_PUBLIC_API`) pinadas em
  `tests/test_regression_v1_baseline.py`; header e corpo pinados pelos gates byte-canônicos.
- **Baselines na data desta entrada**: D1-D9 = **1545 B** · D17a = **300 B** (`#TCF.8M` hex
  inline) · real-world = **89 430 B** · suíte **1344 passed**. Números vivos SEMPRE nos
  testes; re-pináveis com registro (ADR-0024).
- `view()` lazy/consultável segue a API read-only do `.8M` (count/sum/where/select/group
  sem materializar o que a pergunta não toca).

> ADRs do ciclo: **0032–0047**. Narrativa por sessão: `experiments/lab/dirty/notas/diario/`.

## 0.7.x (pré-1.0, superado por 0.8.0): `#TCF.7` default (histórico)

Ciclo "perseguir bytes" (abertura do que era chamado v2.0; agora pré-1.0).
`encode(dict)` multi-col sai em `#TCF.7` por default. Single-col inalterado.

- **V2-A fallback identity** ([ADR-0022](docs/adr/0022-v2a-fallback-identity-weld.md)):
  por coluna `min(tcf, raw)`, marcador `!`.
- **Header minimo** ([ADR-0023](docs/adr/0023-v2-minimal-header-weld.md)):
  meta sem prefixo `# ` + ultima coluna sem size.
- **V2-B dicionario/categorico** ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md)):
  3o candidato do fallback `min(tcf, raw, v2b)`, marcador `@`. Coluna low-card
  vira [tabela de unicos]+[stream de indices]. 13.9% weighted em 8 datasets reais.
- **Split estrutural** ([ADR-0026](docs/adr/0026-structural-split-weld.md)):
  4o candidato `min(tcf, raw, dict, split)`, marcador `%`. Valor estruturado
  (decimal/data/datetime/id) com template uniforme vira campos (template 1x) ->
  cada campo low-card cai no V2-B. **19.39% weighted** (maior lever do ciclo).
- **`sort_by` order-free** (O-FMT-02): `encode(table, sort_by="col")` reordena
  linhas pela chave (decode retorna a ordem ordenada).
- **Knobs**: `fallback`/`min_header` (opt-out, default True), `min_len` (override).
- **0.7 default** ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)):
  baseline D17a re-pinado 322->303B (#TCF.6 legado lido pelo decoder). D1-D9=1523B
  (single-col) inalterado. Suite 398 passed.
- **Fechamento do ciclo (2026-06-15)**: decisao do owner, **0.7 permanece
  lossless-puro**; V2-C round e Pacote 10 (loss amplo) viram roadmap v2.0. Nome de
  distribuicao = **`tcf-format`** (mantendo `import tcf`); `pyproject` `1.0.0` ->
  `0.7.0` (alinha ADR-0024). [ADR-0018](docs/adr/0018-v2-format-roadmap.md) ->
  `accepted` (V2-D refutado; V2-C/J/K/L defer). Higiene de tickets: 3 fases welded
  fechadas + 5 parks v2.0/pos-0.7.
- **`0.7.1`, primeira release publicada no PyPI** (`tcf-format`): o **patch** e'
  contador de release/correcao, desacoplado do minor do formato (`#TCF.7`) e do
  comportamento (nao muda logica nem byte-output). D1-D9=1523B / D17a=303B intactos.

---

## 1.0.0 (2026-05-27): **STABLE**, format #TCF.6 + API congelados

Primeira versao estavel. Decisao formal de freeze em
[ADR-0017](docs/adr/0017-format-spec-v1-frozen.md).

### Estabilidade garantida (semver)

- **Format `#TCF.6` imutavel** ate' v2.0.0: nenhum byte de arquivo TCF
  v1 muda entre versoes 1.x.y
- **API publica congelada**: `encode`, `decode`, `SideOutputs`,
  `PipelineConfig`, `build_schema`, `TableSchema`, `ColumnSchema`,
  `TemplatedCheckedSpec`, `TemplatedPaddedSpec`, `SPEC_CPF`, `SPEC_CNPJ`,
  `SPEC_IP` (+ deprecated `encode_table`/`decode_table`)
- **Semver**: 1.0.x bug fixes / 1.x.0 additive / 2.0.0 breaking

### Validado

- D1-D9 sinteticos: 1523B (53.2% ratio), RT 9/9
- D17a multi-col: 322B INVARIANT (preservado em 16 ADRs)
- Real-world: Adult Census + TPC-H 9 tabelas (-33.02% weighted) + 3 UCI
  novos (wine 90.9%, beijing 71.7%, online-retail 23.7%)
- Benchmark vs csv/jsonl + gzip/brotli/zstd: TCF vence 7/9 datasets
- Suite: 262 passed + 2 xfailed (test_regression_v1_baseline.py: 24
  tests gate byte-canonical + API surface)

### Bug fixes incluidos (categoria 1, output era invalido)

- HCC seq-RLE multi-delta: marker `*N+-1,0|...` (primeiro delta negativo
  double-signed) era emitido mas decoder rejeitava com `ValueError`.
  Fix em `src/tcf/composicional/hcc_seqrle.py`. Descoberto em validacao
  real-world wine-quality (2026-05-27). 2 testes regressao.

### Packaging

- `pyproject.toml`: version 1.0.0; wheel empacota `src/tcf` canonical
  (corrigido de `old/tcf` v0.5 stale); `requires-python = ">=3.10"`
- `src/tcf/__init__.py`: `__version__ = "1.0.0"`
- CI: gate bloqueante `test_regression_v1_baseline.py` + PYTHONHASHSEED=0
  + matrix py 3.10-3.13

### Deprecated (removido em 2.0.0)

- `encode_table(table)` → use `encode(dict)`
- `decode_table(text)` → use `decode(text)`

---

## v0.6 (2026-05-10 → 2026-05-27): TCF (Tabular Compact Format), superseded por 1.0.0

**Reset em 2026-05-10**: foco do projeto migrou de "formato textual
columnar para LLMs" (v0.5) para **algoritmo de compressao de strings
tabulares** em duas camadas. Trabalho em `experiments/lab/dirty/`
(macros M0-M14) consolidado e welded para `src/tcf/`. Estabilizado
como 1.0.0 em 2026-05-27.

### Naming oficializado (2026-05-17, META-NAMING)

- **TCF** = **Tabular Compact Format** (projeto)
- **OBAT** = **Online Bidirectional Affix Tokenizer** (codnome `alg16`)
- **HCC** = **Hierarchical Compositional Coding** (codnome `M8.A`)

Ver `docs/algorithms/` para documentacao tecnica detalhada de cada
camada.

### Componentes canonicos

- **OBAT** (camada 1, tokenizacao): online incremental via LCP+LCS
  bidirecional. Tokens raiz: TokLit / TokRefPref / TokRefSuf.
  Intocado desde M0 (exp 16 do alg16).
- **HCC** (camada 2, compactacao): detector unificado (refs atomicos
  + virtuais no mesmo espaco) + emit composicional (`~` cria ref
  auto-nomeado, `,` concat efemero); restricao body-order para
  inline expansion correto; range `a..b` como caso particular.
- **Convencao output**: sem brackets `[`/`]`, LF only.

### Resultados validados

- D1-D9 (stress 9 datasets sinteticos): 1615 bytes em 2981 raw =
  **54.2% ratio medio**. Varia 26% (D8 cabeca-cauda) a 72% (D4 caos).
- RT 9/9 OK em todos os datasets.
- Cadeia byte-canonica: M9 → M10 → M11 → M12 → M13 → M14 (welding
  validado por contra-prova).

### Estado da API

```python
from tcf import encode, decode  # API publica v0.6

text = encode(["abc", "abcd", "abcde"])
values = decode(text)
```

### Phase 1 LLM (acessorio)

LLM benchmark (Q01-Q38 em `docs/findings/`) e' agora **acessorio**
ao foco. Codigo v0.5 (`old/tcf/`, antes `src/tcf/`) mantido para
referencia historica.

Ver:
- [`experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md`](experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md): narrativa M0-M14
- [`experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md`](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md): 12 direcoes futuras
- [`docs/algorithms/`](docs/algorithms/): OBAT, HCC, TCF-format

---

## v0.3-research (2026-04-27): research-grade (HISTORICA)

**Repository reorganization**: GitHub-style README, manual with 7 chapters
(EN + 3 PT-BR), findings catalogue split by theme into `docs/findings/`,
workbench (tickets + research notes + dev/science timelines) under
`docs/workbench/`, theory snapshot under `docs/theory/`. Removed obsolete
`data/` and `data-local/` from repo root. Tickets moved from
`tickets/` to `docs/workbench/tickets/`.

**M-schema-scope finished**: F-Q37 (schema scope doesn't degrade N0;
sub-finding: models infer `Supplier#NNN` from lexical patterns even
without `supplier` table visible; TPC-H memorization caveat) and F-Q38
(schema reduced **helps** in natural wordings: -33pp in N3 between
minimal and full schemas; empirically justifies schema pruning literature).

## v0.2.6-anthropic (2026-04-26): Anthropic family added

`commercial_client.py` extended for Anthropic Messages API:
- haiku 4.5 + sonnet 4.6 with `thinking={"type":"enabled","budget_tokens":2048}`
- opus 4.7 with `thinking={"type":"adaptive"}` + `output_config.effort`
  (different API!)
- 1968 records over 4 paradigms × 7 commercial models. Total spend
  $9.46 USD with prompt caching (~75% savings).

Findings:
- **F-Q36**: Anthropic ≈ OpenAI in Linha B (96-99% Adult, 80-88% TPC-H);
  OpenAI wins Linha A Adult (gpt-5.x 82-95% vs Anthropic 76-80%);
  paridade in Linha A TPC-H. claude-sonnet-4-6 wins TPC-H Linha B
  (88.1% > gpt-5.4 85.7%).

## v0.2.5-openai (2026-04-26): OpenAI commercials

Migrated `commercial_client.py` to **OpenAI Responses API** (recommended
2026 path), added structured outputs via Pydantic, prompt caching with
`prompt_cache_key`, tiktoken-based count_tokens.

Models: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-4o-mini (control).
1008 records (Linha A + B × Adult + TPC-H), $3.17 USD.

Findings:
- **F-Q31**: commercial reasoning models break the local Linha A ceiling
  (gpt-5.4 95% vs locals capped ~57%). The discriminating axis is
  REASONING, not size.
- **F-Q32**: gpt-5.4 + mini = **100% in all naturalness levels** for
  Adult Linha B.
- **F-Q33**: locals lose -30 to -45pp in TPC-H Linha B with N2
  wording; schema ambiguity systematic in multi-table.
- **F-Q34**: same applies to commercial top models; schema ambiguity
  is universal/paradigm-independent.
- **F-Q35**: Linha A commercial in TPC-H caps at 60-76%; even
  gpt-5.4 falls 21pp from Adult to TPC-H.

## v0.2.4-naturalness (2026-04-26): naturalness axis (locals only)

Introduced **N0..N3 naturalness taxonomy** for question wordings:
- N0: schema-aware (literal column names, technical hints)
- N1: system-aware (domain-aware prose)
- N2: business-intent (no schema mentions)
- N3: business + implicit context

Implementation: `experiments/eval/llm_eval/question_naturalness.py` with
28 wordings × 2 datasets, runners adapted with `--naturalness` flag.
N0 byte-identical to legacy questions for backwards compat.

Findings:
- **F-Q29**: naturalness does NOT degrade Linha A in 13 local models
  0.6B-20B (delta < 5-14pp, within Wilson CI). Mechanism: arithmetic
  ceiling dominates; wording is invisible below it.
- **F-Q30**: naturalness DEGRADES Linha B in locals selectively (qwen3:14b
  immune; qwen2.5-coder -15pp). Two mechanisms: domain-semantic ambiguity
  + hyphenated columns.

ScoringConfig dataclass added with `string_match=lenient` default
(strict still available for legacy comparability).

## v0.2.3-canonical (2026-04-25): canonical datasets baseline

`scripts/setup_adult.py` and `setup_tpch.py` for reproducible canonical
ingestion. `scripts/csv_to_sqlite.py` builds SQLite hubs in
`<data_root>/interim/`. Stratification metrics inline (TVD/JSD/Hellinger/
Wilson CI).

Findings:
- **F-Q24**: canonical TPC-H ≈ synthetic retail in accuracy under same
  protocol; synthetic was representative.
- **F-Q25**: H-TCF2 generalizes to single-table (Adult Census) with
  hyphenated columns. 100% Linha B local.
- **F-Q26**: random ≈ stratified in Adult; paradigm robust to sampling
  choice ("floor effect" of 100% accuracy).
- **F-Q27**: SQL quality structural metric correlates **inversely** with
  accuracy. Discarded.
- **F-Q28**: Linha A in canonical Adult = 52% bimodal (100% on full-table
  agg, 0-11% on filter+agg). Refines F-Q12.

## v0.2.2-shaper (2026-04-25): unified data pipeline

`scripts/shaper/` framework with 7 strategies (schema_filter, join,
compressibility, stratify, fk_preserving, volume, ordering).
`experiments/eval/data_sources.py` provides single entry point
`load_dataset(source, **kwargs)` for both synthetic and canonical.

All M-runners migrated to `load_dataset` (no more direct fixture imports).

## v0.2.1-mseries (2026-04-15..04-23): M1..M9 experiment runs

13 M-series runners exploring Linha B (LLM → SQL) systematically across
synthetic and canonical datasets. Findings F-Q13..F-Q23 (schema-only,
fewshot, cross-domain, format, intermediate forms, filter questions,
HAVING, complex queries, error types, style hints).

## v0.2.0-encoder (2026-04-10..04-13): encoder/decoder v0.2

Rewrote encoder/decoder with separated `compression.py` module.
Public API: `encode`, `encode_rows`, `decode`, `EncodeConfig`. CLI
modernized.

## v0.1-llm-comprehension (2026-04-04..04-10): Phase 1 LLM testing

Phase 1 ran 12 local models × 4 formats × 4 questions to test LLM
comprehension of TCF. **TCF 43% < JSONL 63%** in raw accuracy: pivot
to Linha B as the high-value path. F-Q1..F-Q12 catalogued.

## v0.0-prototype (2026-04 first week): initial sketch

First handcrafted draft of the columnar text format. Encoder/decoder
v0.1 written in two weeks (`src/tcf/encoder.py`, `decoder.py`).
Roundtrip CSV → TCF → CSV verified. Format had conceptual issues
(DICT with `=`, `[sorted]` confusing, redundant IDs); kept as
historical reference in `docs/archive/`.

---

## Roadmap (open)

- v0.3: schema_qualifier (auto-prune schema for N2/N3 wordings before LLM)
- v0.3: numeric precision (open issue 23)
- Future: TOON benchmark integration (head-to-head Adult/TPC-H)
- Future: Shaper as standalone pip package
