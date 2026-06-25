# TCF — Tabular Compact Format

## Visão geral

TCF é um formato textual para representar **dados tabulares** de
forma **compacta**, mantendo:

- **Output em texto** (sem binário) — inspeção visual e
  processamento por LLMs/pipelines line-oriented
- **Roundtrip lossless** — `decode(encode(values)) == values` sempre
- **Compressão estrutural** — explora padrões em colunas (afixos
  compartilhados, sub-padrões recorrentes, cadências detectáveis,
  runs near-identical)

Formato projetado para:
- Colunas de dados tabulares onde valores compartilham estrutura
  (URLs, emails, IDs, datas, paths, identificadores estruturados)
- Volumes médios (não substitui gzip pra logs massivos; substitui
  CSV/JSON quando legibilidade importa)
- Tabelas multi-coluna onde cada coluna se beneficia de pipeline
  próprio (encoder per-column independente)

## Versionamento (ADR-0024 + ADR-0028 — pré-1.0; supersede ADR-0017)

> **MODELO DE 3 EIXOS (ADR-0028, 2026-06-24; refina ADR-0024)** — distinga:
> - **(A) Versão de FORMATO** — shebang `#TCF.N`. Contrato on-disk; só muda com mudança de formato.
>   Hoje `#TCF.7` (default), `#TCF.6` (legado, lido).
> - **(B) Geração do encoder** — marco interno (M8A→M9→M10); NÃO é versão pública (nota histórica).
> - **(C) Versão do pacote** (PyPI) — pré-1.0 = `0.<formato>.<release>`: minor = nº do formato
>   (`0.N` ↔ `#TCF.N`); release/patch = entrega DENTRO do formato.
>
> **Regra de bump**: mudança de FORMATO move o minor (`0.(N+1).0`); entrega sem mudar formato move o
> release (`0.N.x+1`). Ex.: lazy+poda (#TCF.7 inalterado) = `0.7.2`; cross-dict `#TCF.8` = `0.8.0`.
> `1.0` só quando o formato final congelar → aí semver estrito. As frases "frozen v1.0"/"v2.0"/
> "estável desde v1.0" abaixo são do modelo antigo (ADR-0017) — ler nessa chave.
> Termos: [`../vocabulary.md`](../vocabulary.md) §Versionamento.

TCF distingue **versão de FORMATO** (shebang `#TCF.N`, eixo A) de **versão de PACOTE**
(semver `0.N.x`, eixo C) — não confundir os dois (ADR-0028).

### Format version (shebang)

| Shebang | Status | Introduzido | Compativel com |
|---|---|---|---|
| `#TCF.8` | **opt-in** (self-describing natures) | 2026-06 | encode SSE ha nature; decode le |
| `#TCF.7` | **0.7 (default)** | 2026-06 | encode default (multi-col); decode le |
| `#TCF.6` | **legado** (0.6) | 2026-05 | decode le; produzivel internamente |
| `#TCF.5` | superseded | 2026-04 (v0.5) | tcf 0.5.x (legacy, nao manter) |

**`#TCF.8` (self-describing natures, [ADR-0027](../adr/0027-nature-mark-header-self-describing.md),
welded 2026-06-24)** — ADITIVO e opt-in ESTRITO: emitido SSE alguma coluna tem nature
(CPF/CNPJ/IP); senao `#TCF.7` byte-identico. A nature viaja no header como sufixo `:id`
no nome da coluna no meta-line (ex: `!11=cpf:cpf,13=doc:cnpj,!plain`) — o decode reverte
sozinho (resolve `:id` -> spec via dict fixo core-only, zero eval; id desconhecido -> valor
cru + warning, forward-compat). Validador proibe `:` em nome de coluna so' quando ha nature.
**byte-neutro**: `#TCF.8 M` condicionado SO' a `bool(nature_ids)` — caminho sem nature inalterado.

**Single-col** (welded 2026-06-24): mesmo `#TCF.8` mas **SEM o flag `M`** (a ausencia do
`M` => single-col, decode retorna `list`):

    #TCF.8
    [nome]:spec_id      <- nome OPCIONAL (so' rotulo; vazio = ':cpf')
    <body>

Emitido SSE `encode(list, nature=SPEC)` (opt-in). Sem nature -> body puro byte-identico
(D1-D9=1523B intacto). Custo ~12B de header so' no opt-in. `decode` despacha `#TCF.8\n`
(distinto de `#TCF.8 M`), resolve o spec e retorna `list`. Precedencia header-vence.

**Promessa v1**: `#TCF.6` e' imutavel ate' v2.0. Nenhum byte de arquivo
TCF v1 muda entre versoes tcf 1.x.y. Markers novos requerem `#TCF.7`.

**`#TCF.7` (v2, ADITIVO e opt-in)** — duas capacidades ortogonais, ambas multi-col,
ambas emitindo `#TCF.7 M` so' quando ativadas (senao `#TCF.6` byte-identico).
**Todo `#TCF.7` dispensa o prefixo `# ` do meta** (o flag `M` no shebang ja'
declara as colunas, ADR-0023) — `#TCF.6` mantem o `# ` (congelado). Decoder
self-describing. Default preserva 100% dos invariantes v1:
- **V2-A fallback identity** ([ADR-0022](../adr/0022-v2a-fallback-identity-weld.md),
  `fallback=True`): por coluna escolhe min(TCF, raw); coluna raw marcada
  `!<size>=<name>`. Meta: `!<s1>=<n1>,<s2>=<n2>,...`.
- **Header v2 minimo** ([ADR-0023](../adr/0023-v2-minimal-header-weld.md),
  `min_header=True`): alem do prefixo, OMITE o size da ULTIMA coluna (corpo ate'
  EOF) -> meta `<s1>=<n1>,...,<nN>`. Voltado a payload pequeno.
- **V2-B dicionario** ([ADR-0025](../adr/0025-v2b-dictionary-categorical-weld.md),
  marcador `@`) e **split estrutural** ([ADR-0026](../adr/0026-structural-split-weld.md),
  marcador `%`): mais candidatos do fallback per-coluna (welded; detalhe do corpo nos ADRs).
- **V2-RLE-STREAM** (follow-up experimental de V2-B, **NAO weldado**): RLE no stream de indices
  `@dict`. Caracterizado 2026-06-19 ->
  [lab](../../experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md): CLOSED-geral /
  nicho textual-puro aberto (decisao do owner). `src/tcf` intocado.

### Library version (semver)

- **1.0.x** — bug fixes (sem mudar bytes em D1-D9, D17a, real-world snapshots)
- **1.x.0** — features additive: novos `nature` specs, parametros
  keyword-only com default que preserva comportamento (ex: `encode(data, *, novo_param=def)`)
- **2.0.0** — breaking: format change, API removal, marker novo no body

### API publica congelada em v1.0

Imports estaveis ate' v2.0:

```python
from tcf import (
    encode, decode,                   # core
    SideOutputs,                       # debug/stats opt-in
    PipelineConfig,                    # toggle layers
    build_schema, TableSchema, ColumnSchema,  # schema introspection
    TemplatedCheckedSpec, TemplatedPaddedSpec,  # nature definitions
    SPEC_CPF, SPEC_CNPJ, SPEC_IP,    # nature specs canonicos
)
```

Assinaturas imutaveis. Novos parametros opcionais com default permitidos.

### Deprecated em v1.x (removidos em v2.0)

- `encode_table(table)` → use `encode(dict)`
- `decode_table(text)` → use `decode(text)`

Emitem `DeprecationWarning` em cada uso desde v1.0.

### Suite regressao formal

[`tests/test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py)
captura bytes-canonical de D1-D9 (1523B total) e D17a (322B INVARIANT).
Falha em CI = regressao. Snapshot so' pode ser atualizado via ADR
explicito + version bump.

Detalhes: ver [ADR-0017](../adr/0017-format-spec-v1-frozen.md).

## Pipeline completo

```
┌─────────────────────────────────────────────────────────────────────┐
│  ENCODE — dispatch por tipo (ADR-0014)                              │
│  ┌──────────────────────────┐    ┌──────────────────────────┐       │
│  │  encode(list[str])        │    │  encode(dict[str,list])   │       │
│  │  single-column semantic   │    │  multi-column semantic    │       │
│  └────────────┬─────────────┘    └────────────┬─────────────┘       │
│               │                                │                    │
│               │                          ┌─────┴───── 1 por col ──┐ │
│               ▼                          ▼                         │ │
│         ┌───────────────────────────────────────────────┐         │ │
│         │   PRE-PASS (1 passada O(N))                    │         │ │
│         │   ─────────────────────────                    │         │ │
│         │   analyze_column → ColumnFeatures              │ H-DA-11c│ │
│         │   ├─ n_rows, n_unicas, avg_len, cardinality   │         │ │
│         │   ├─ is_numeric, sample                       │         │ │
│         │   detect_cadence_from_features                 │ ADR-0008│ │
│         │   ├─ regra 1: wrapper+counter (LCP/LCS unif.) │         │ │
│         │   └─ regra 2: numeric AND cardinality > 0.5   │         │ │
│         │   detect_min_len_from_features                 │ ADR-0010│ │
│         │   └─ heur v3 (avg_len + card + is_numeric)    │         │ │
│         │      + gating n>=100 (preserva baseline)      │         │ │
│         └─────────────────────┬─────────────────────────┘         │ │
│                               │                                   │ │
│              cadence?         │                                   │ │
│              ┌──── sim ──────►│                                   │ │
│              │                ▼                                   │ │
│              │     ┌───────────────────────────────────┐         │ │
│              │     │   OBAT (camada 1)                  │         │ │
│              │     │   ─────────────                    │         │ │
│              │     │   alg16: LCP+LCS bidirectional     │         │ │
│              │     │   greedy cover, min_len threshold  │         │ │
│              │     │   tokens raiz:                     │         │ │
│              │     │   • TokLit(text)                   │         │ │
│              │     │   • TokRefPref(string_id, length)  │         │ │
│              │     │   • TokRefSuf(string_id, length)   │         │ │
│              │     │   ─────                            │         │ │
│              │     │   processar_with_hint              │ ADR-0011│ │
│              │     │   (shape-preserve per-length)      │         │ │
│              │     │   OU                                │         │ │
│              │     │   processar canonical              │         │ │
│              │     │   ─────                            │         │ │
│              │     │   Hash trigrama O(N^1.42)          │ ADR-0009│ │
│              │     └────────────────┬──────────────────┘         │ │
│              │                      │                            │ │
│              │       ┌──────────────┴──────────────────┐         │ │
│              │       │   HCC (camada 2)                 │        │ │
│              │       │   ─────────────                  │        │ │
│              │       │   M8.A: virtual refs unified    │        │ │
│              │       │   detector greedy (net > 0)     │        │ │
│              │       │   emit text:                    │        │ │
│              │       │   • `~` cria ref auto-nomeado   │        │ │
│              │       │   • `,` concat efêmero          │        │ │
│              │       │   • `1..5` range (açúcar)       │        │ │
│              │       │   • `*N|linha` RLE              │        │ │
│              │       │   • `\X` escape                 │        │ │
│              │       │   • `*` separator (ADR-0007)    │        │ │
│              │       │   ─────                          │        │ │
│              │       │   HCCSeqRLE (M10, ADR-0011):    │        │ │
│              │       │   `*N+delta|template` runs       │        │ │
│              │       │   near-identical                 │        │ │
│              │       └────────────────┬─────────────────┘        │ │
│              │                        │                           │ │
│              │                        │  body por coluna          │ │
│              │                        ▼                           │ │
│              └────────────────────────┘                           │ │
│                                       │                           │ │
│                multi-col              │                           │ │
│            ┌── concat ────────────────┘                           │ │
│            ▼                                                      │ │
│   ┌──────────────────────────────────────────────┐               │ │
│   │  #TCF.7 M   (default 0.7; #TCF.6 = legado)     │ ADR-0004/0013 │ │
│   │  meta V2:  !<s1>=<n1>,...,<nN>   (sem `# `)     │ +0022/23/24/25│ │
│   │  <body1><body2><body3>...                      │               │ │
│   │  (concat byte-precise, sem delimitador)        │               │ │
│   └──────────────────────────────────────────────┘               │ │
│   #TCF.6 legado: `# <s1>=<n1>,...` (com `# `, sem markers).        │ │
│                                                                  │ │
│   single-col: body puro, sem shebang                             │ │
└─────────────────────────────────────────────────────────────────────┘
```

### Decode (espelho)

```
decode(text) → list[str] | dict[str, list[str]]
         │
         ├─ startswith("#TCF.7 M") OU "#TCF.6 M" ──► _decode_multi → dict
         │
         └─ caso contrário                        ──► _decode_column → list
```

Self-describing: o shebang (`#TCF.7 M` default, `#TCF.6 M` legado) identifica
o formato. O decoder dispatcha automaticamente em ambos; o caller não precisa
saber se a saída é single ou multi.

## Camadas detalhadas

### Camada 0 — Pre-pass

Antes de entrar no OBAT, cada coluna passa por análise O(N) que
produz `ColumnFeatures` + hints heurísticos. Esses hints calibram
OBAT (shape-preserve ou canonical) e min_len ótimo.

Módulos:
- [`column_features.py`](../../src/tcf/column_features.py) — `analyze_column()` (H-DA-11c)
- [`auto_cadence.py`](../../src/tcf/auto_cadence.py) — `detect_cadence_from_features()` (ADR-0008)
- [`auto_min_len.py`](../../src/tcf/auto_min_len.py) — `detect_min_len_from_features()` (ADR-0010)

### Camada 1 — OBAT

Tokeniza cada string da coluna em refs (prefixo/sufixo de strings
anteriores) + literais. Produz **tokens discretos** que HCC consome.

Doc: [OBAT.md](OBAT.md). Implementação: [`src/tcf/core/online.py`](../../src/tcf/core/online.py)
+ [`src/tcf/obat_shape.py`](../../src/tcf/obat_shape.py).

### Camada 2 — HCC

Detecta composições recorrentes nos tokens (refs que se repetem
juntos viram refs nomeados pairwise) + compacta runs near-identical
em `*N+delta|template`. Produz **texto TCF** final do body.

Doc: [HCC.md](HCC.md). Implementação: [`src/tcf/composicional/syntax.py`](../../src/tcf/composicional/syntax.py)
+ [`src/tcf/composicional/hcc_seqrle.py`](../../src/tcf/composicional/hcc_seqrle.py).

### Camada 3 — Multi-column wrapper

Para input `dict[str, list[str]]`, cada coluna passa pelas camadas
0-2 independentemente. Os bodies são concatenados byte-precise com
header `#TCF.7 M` (default 0.7) + meta line.

> **Default 0.7 (ADR-0024)**: `encode(dict)` emite **`#TCF.7 M`** com
> `fallback` + dicionário V2-B + `min_header` **automáticos** — meta sem o
> prefixo `# `, markers de modo por coluna (`!` raw, `@` dict, `%` split) e a
> última coluna sem size. `#TCF.6 M` é **legado** (lido pelo decoder; produzível
> via `_encode_multi(fallback=False, min_header=False)`). Ex. real:
> `#TCF.7 M\n!5=id,!15=nome,!plano\n...`.

**V2-A fallback identity (ADR-0022, `fallback`)**: por coluna escolhe min(TCF, raw);
coluna raw vira `!<size>=<name>`. **Ligado por default** no 0.7.

**Header v2 mínimo (ADR-0023, `min_header`)**: todo `#TCF.7` dispensa o prefixo `# `
do meta (o `M` do shebang já declara colunas); `min_header` ainda omite o size da
última coluna (corpo até EOF): meta `<s1>=<n1>,...,<nN>`. **Ligado por default** no 0.7.
Foco: payload pequeno (header fixo domina). Para emitir `#TCF.6` byte-idêntico (legado),
opt-out explícito (`fallback=False, min_header=False`).

**V2-B dicionário (ADR-0025, `@`) + split estrutural (ADR-0026, `%`)**: candidatos
extras do fallback por coluna (dicionário categórico; quebra de campo estrutural).
Entram no default quando reduzem a coluna.

Restrições:
- Nomes de coluna não podem conter `,` ou `=` (reservados do header)
- Todas as colunas devem ter o mesmo número de valores
- `None` → `""` (TCF opera em strings)

Implementação: [`src/tcf/multi.py`](../../src/tcf/multi.py). ADR: [0004](../adr/0004-multi-column-header-compacto.md), [0013](../adr/0013-multi-column-canonical-api.md), [0014](../adr/0014-unified-api-side-outputs.md).

## API mínima

```python
from tcf import encode, decode, SideOutputs

# Single-column
text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
values = decode(text)  # list[str]

# Multi-column
table = {
    "timestamp": ["2026-01-01", "2026-01-02"],
    "email": ["a@x.com", "b@x.com"],
}
text = encode(table)
result = decode(text)  # dict[str, list[str]]

# Side outputs opcional (debug, stats, schema futuro)
side = SideOutputs()
text = encode(table, side_outputs=side)
print(side.hcc_trace)                       # detector iterations
print(side.per_col["email"].column_features) # pre-pass features
print(side.multi_info)                       # header_bytes, body_bytes
```

### SideOutputs (ADR-0014)

Recipiente opcional que captura informação produzida internamente
pelo pipeline mas que normalmente seria descartada. Útil para:

- Debug (inspecionar decisões do detector HCC, escolhas de cobertura
  do OBAT)
- Análise de compressão (qual coluna não se beneficiou, por quê)
- Schema builder futuro (consume features + heurísticas pra produzir
  schema rico)

Campos:
- Pre-pass: `column_features`, `cadence_detected`, `cadence_info`, `min_len`
- OBAT: `obat_log`, `obat_used_hint`
- HCC: `hcc_trace`, `hcc_rede`, `seq_rle_runs`
- Bytes: `body_bytes` (per coluna)
- Multi-col: `multi_info`, `per_col` (SideOutputs aninhado por coluna)

Sem `side_outputs=`: overhead zero (logs continuam sendo gerados e
descartados como antes). Doc: [SideOutputs](../../src/tcf/side_outputs.py).

## Camadas futuras (registradas, não implementadas)

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENT (welded canonical)                                      │
│  ────────                                                        │
│  encode(list|dict) → str                                         │
│  decode(str) → list|dict                                         │
│  SideOutputs (opcional)                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (próximas direções)
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer A — Encoder Manager (D13 v0.4, T-CODE-*)           │
│  ────────                                                        │
│  encode(data, parallel=True, output=Sink, plan=Plan(...))        │
│                                                                  │
│  • `_encode_column` em workers paralelos (ProcessPoolExecutor)   │
│  • Output sinks pluggable: FileSink, MultiFileSink, HTTPSink,    │
│    TCPSink, MemorySink                                           │
│  • Plan dataclass: group_by/order/batch_size/batch_unit          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer B — Distributed transport (O-FMT-08/13)            │
│  ────────                                                        │
│  Per-channel headers (re-assembly sem coordenação central):      │
│    #TCF.7 C name=timestamp chunk=1/3 of=table_X                  │
│  Streaming chunked: chunks autocontidos, decode chunk-a-chunk,   │
│    memória O(chunk_size), TTFB constante                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  FUTURE Layer C — Schema builder (T-CODE-SCHEMA-BUILDER)         │
│  ────────                                                        │
│  build_schema(data) → TableSchema (consume SideOutputs)          │
│                                                                  │
│  Detectores integrados (META-TYPE-ENCODERS T02-T07):             │
│  • detect_templated (date, email, uuid, CPF, IP, telefone)       │
│  • detect_enumerated (low-card categorical)                      │
│  • detect_checked (dígito verificador)                           │
│  • detect_composite (datetime split, money split)                │
│  • detect_hierarchical (paths, URLs)                             │
│                                                                  │
│  Outputs: TableSchema → JSON (compat metadata.json), Markdown,   │
│    diff (drift detection)                                        │
└──────────────────────────────────────────────────────────────────┘
```

Tickets de plano:
- [T-CODE-ENCODER-MANAGER](../../tickets/T-CODE-ENCODER-MANAGER.md) (P2) — Revive D13 v0.4
- [T-CODE-OUTPUT-SINKS](../../tickets/T-CODE-OUTPUT-SINKS.md) (P2) — Contract `Sink` pluggable
- [T-CODE-PLAN-CONTRACT](../../tickets/T-CODE-PLAN-CONTRACT.md) (P3) — Plan dataclass
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) (P3) — Consume SideOutputs

## Posicionamento na literatura de compressão

TCF se localiza no cruzamento de três famílias clássicas:

### 1. Compressão estrutural de string dictionaries

**Família**: front-coding e variantes (Witten et al., HTFC e RPDac de
Brisaboa et al. 2011, etc.)

**Comparação**:
- TCF, via OBAT, generaliza front-coding com **bidirecionalidade**
  (LCP + LCS), captura padrões "tipo email" onde sufixo
  (`@gmail.com`) é estável e prefixo varia.
- TCF, via HCC, adiciona **composições hierárquicas** — não há
  análogo direto em front-coding clássico.

### 2. Grammar-based compression

**Família**: Re-Pair (Larsson & Moffat 1999), Sequitur
(Nevill-Manning & Witten 1997).

**Comparação**:
- HCC é greedy iterative, espírito Re-Pair mas em tokens de OBAT
  (não bytes).
- HCC tem **operadores semânticos distintos** (`~` vs `,`) — não há
  análogo em Re-Pair (toda substituição cria regra).
- HCC é **offline** (analisa body completo) mas mais simples que
  Sequitur (que mantém invariantes online complexos).

### 3. Compactação para LLM consumption (acessório ao core)

**Família**: TabLLM (2023), TOON, JSON-tabular, formatos compactos
para LLMs lerem tabelas (Sui 2024 review).

**Comparação**:
- Phase 1 (ciclo v0.5) catalogou Q01-Q38 sobre LLM-readability do
  TCF antigo (columnar/RLE). Esse trabalho é **acessório** ao foco
  do core (algoritmo de compressão, 0.7).
- LLM-readability volta a ser relevante quando Phase 2 for revivida
  OU virar projeto a parte.

## Diferenciais agregados

| Característica | TCF | LZ77/gzip | Re-Pair | Front-coding |
|---|---|---|---|---|
| Output | textual | binário | binário | binário/textual |
| Inspecionável visualmente | sim | não | não | parcial |
| Online (streaming-friendly) | parcial | sim | não (offline) | sim |
| Bidirecional (prefixo + sufixo) | sim | n/a | n/a | só prefixo |
| Hierarquia de composições | sim | implícita | sim (grammar) | não |
| Auto-naming sem dict explícito | sim | n/a | não (precisa dict) | sim |
| Multi-coluna nativo | sim | não | não | não |
| Adequado a colunar | sim (desenhado pra) | genérico | genérico | sim |

## Quando usar TCF

**Bom uso**:
- Colunas de strings com padrões textuais (URLs, emails, IDs, datas,
  paths)
- Volume médio (centenas a milhares de linhas; valida até 60k em
  lineitem TPC-H)
- Output em texto é requisito (inspeção, pipelines line-oriented,
  consumo por LLMs)
- Tabelas multi-coluna onde cada coluna se beneficia de pipeline
  próprio

**Quando preferir alternativas**:
- **CSV/JSON** — formato muito simples, sem necessidade de
  compressão (mas TCF mantém legibilidade)
- **gzip/brotli/zstd** — datasets MUITO grandes, compressão crítica,
  binário OK
- **Re-Pair/Sequitur/HTFC** — dicionários gigantes, output binário OK,
  busca aleatória importante

## Estado 0.7 (snapshot 2026-05-27; estado vivo em [STATUS.md](../../STATUS.md))

> Números abaixo são um **snapshot datado** (§5: o teste mede, a prosa aponta).
> Para o estado corrente — versão do pacote, contagem de testes, ADRs welded —
> ver [STATUS.md](../../STATUS.md) e os guardiões em `tests/`.

### Implementação canônica

`src/tcf/` — API pública **pré-1.0** ([ADR-0024](../adr/0024-pre-1.0-versioning-git-as-compat.md)
supersede o "frozen" do ADR-0017): aditiva, sem compat rígida entre minors de dev
(git reproduz versões antigas). Ver secção "Versionamento" acima.

### Validação

**Single-column (M10 baseline, ADR-0011)**:
- D1-D9 sintéticos: **1523 bytes** em 2865 raw = 53.2% ratio (RT 9/9)
- Cadeia byte-canônica de checkpoints: M9 → M10 → M11 → M12 → M13 → M14
  → M14+Pacote1+Multi+API+Natures+MultiDelta+v1
- Adult Census + TPC-H 57 colunas: **-11.73% weighted** vs M9 puro

**Multi-column (ADR-0013/0014 + V2 ADR-0022/0023/0025/0026)**:
- D17a sintético (13×4): **303 bytes** (0.7 default, V2-B); 322B = `#TCF.6` legado
- 9 tabelas real-world (Adult Census + TPC-H tier 1+2, 136k linhas,
  15.8 MB raw):
  - **-33.02% weighted vs raw**, **-31.46%** vs single-col concat
  - RT 9/9 OK; Lineitem 60k×16: -17.11% vs raw

**Real-world extendido (UCI/OpenML, T-DATA-1)**:
- wine-quality 6.5k × 13: 90.9% ratio (decimais quimicos, baixa repeticao)
- beijing-pm25 43.8k × 13: 71.7% (sensores + timestamps)
- online-retail 541k × 8: **23.7%** (StockCode/Country/InvoiceDate repetidos)

**Benchmark vs csv/jsonl + gzip/brotli/zstd** (9 datasets totais):
**TCF venceu em 7/9** datasets. Perdeu em D17a tiny (header overhead
domina) e wine-quality (decimais quase unicos = sem estrutura).
Detalhes: [experiments/lab/dirty/2026-05-24-benchmark-formats-compression/](../../experiments/lab/dirty/2026-05-24-benchmark-formats-compression/).

**Suite de testes** (snapshot 2026-05-27: 259 passed; contagem atual em
[STATUS.md](../../STATUS.md)). Guardião byte-canonical:
[`test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py)
(snapshot D1-D9=1523B + D17a=303B default / 322B `#TCF.6` legado).

## Estado v0.5 (acessório)

Há código v0.5 em `old/tcf/` (formato columnar com RLE/dict/stats
para LLM benchmark). **Não é canônico no v1.0**. Mantido para
referência histórica e enquanto Phase 1 LLM findings (em
`docs/findings/`) tiverem relevância de pesquisa.

## Conexões

### Algoritmos
- [OBAT](OBAT.md) — camada 1 (tokenização)
- [HCC](HCC.md) — camada 2 (compactação composicional)

### ADRs welded
- [ADR-0004 — Multi-column header compacto](../adr/0004-multi-column-header-compacto.md)
- [ADR-0007 — Comma in literals bug fix](../adr/0007-comma-in-literals-bug.md)
- [ADR-0008 — detect_cadence regra 2 (numeric+high-card)](../adr/0008-detect-cadence-numeric-rule.md)
- [ADR-0009 — OBAT trigram index O(N^1.42)](../adr/0009-obat-trigram-index-optimization.md)
- [ADR-0010 — auto-detect min_len por coluna](../adr/0010-auto-detect-min-len.md)
- [ADR-0011 — Pacote 1 weld canonical (M9 → M10)](../adr/0011-pacote1-weld-canonical.md)
- [ADR-0013 — Multi-column canonical API (welded, superseded por 0014)](../adr/0013-multi-column-canonical-api.md)
- [ADR-0014 — API unificada + SideOutputs](../adr/0014-unified-api-side-outputs.md)
- [ADR-0015 — Naturezas templated/checked (CPF/CNPJ/IP)](../adr/0015-natures-templated-checked-weld.md)
- [ADR-0016 — HCC seq-RLE multi-delta](../adr/0016-hcc-multi-delta-seq-rle.md)
- [ADR-0017 — Format spec v1.0 frozen + versioning policy](../adr/0017-format-spec-v1-frozen.md)

### Tickets de plano futuro
- [T-CODE-ENCODER-MANAGER](../../tickets/T-CODE-ENCODER-MANAGER.md) — P2, paralelismo + sinks
- [T-CODE-OUTPUT-SINKS](../../tickets/T-CODE-OUTPUT-SINKS.md) — P2, Sink pluggable
- [T-CODE-PLAN-CONTRACT](../../tickets/T-CODE-PLAN-CONTRACT.md) — P3, Plan dataclass
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) — P3, build_schema
- [META-TYPE-ENCODERS](../../tickets/META-TYPE-ENCODERS.md) — naturezas (T02-T07)

### Narrativa
- [`historia-dirty-lab.md`](../../experiments/lab/dirty/notas/historia-dirty-lab.md) — M0-M14 desenvolvimento
- [`roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md) — hipóteses ativas/fechadas
- [`naturezas-numericas-2026-05-23.md`](../../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md) — catalogação 12 naturezas
- [`futuras-otimizacoes-formato.md`](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md) — O-FMT-* registry

### Plano de design v0.4 (referência arquitetural)
- [`2026-05-05-v04-design-recap.md`](../workbench/research-notes/_archive/2026-05-05-v04-design-recap.md) — D1-D18, EncodeManager (D13), Plan, 3 camadas
