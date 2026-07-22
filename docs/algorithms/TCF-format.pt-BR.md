<!-- l10n: doc_id=tcf-format · lang=pt-BR · source_lang=en · translation_of=TCF-format.en.md · synced=2026-07-01 -->
[English](TCF-format.en.md) · **Português**

> Tradução de [`TCF-format.en.md`](TCF-format.en.md). Se houver divergência, o original em inglês prevalece.
> A régua de atualização é o histórico do git.

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
> - **(A) Versão de FORMATO** — a **assinatura de formato / magic number** `#TCF.N` (termo canônico;
>   **não** "shebang", que é `#!` — análogo a `%PDF-1.7`; ver [vocabulary.md](../vocabulary.md)).
>   Contrato on-disk; só muda com mudança de formato. Hoje `#TCF.8` (default, ADR-0032); `#TCF.6/.7`
>   cortados de `src/tcf` (git-as-compat: recupere a era pra ler/comparar).
> - **(B) Geração do encoder** — marco interno (M8A→M9→M10); NÃO é versão pública (nota histórica).
> - **(C) Versão do pacote** (PyPI) — pré-1.0 = `0.<formato>.<release>`: minor = nº do formato
>   (`0.N` ↔ `#TCF.N`); release/patch = entrega DENTRO do formato.
>
> **Regra de bump**: mudança de FORMATO move o minor (`0.(N+1).0`); entrega sem mudar formato move o
> release (`0.N.x+1`). Ex.: `#TCF.8` default (ADR-0032) = `0.8.0` (o ciclo lazy+poda foi absorvido).
> `1.0` só quando o formato final congelar → aí semver estrito. As frases "frozen v1.0"/"v2.0"/
> "estável desde v1.0" abaixo são do modelo antigo (ADR-0017) — ler nessa chave.
> Termos: [`../vocabulary.md`](../vocabulary.md) §Versionamento.

TCF distingue **versão de FORMATO** (assinatura `#TCF.N`, eixo A) de **versão de PACOTE**
(semver `0.N.x`, eixo C) — não confundir os dois (ADR-0028).

### Format version (assinatura)

| Assinatura | Status | Introduzido | Compativel com |
|---|---|---|---|
| `#TCF.8` | **DEFAULT** (multi-col + single-col self-describing) | 2026-07 (default: [ADR-0032](../adr/0032-tcf8-default-format.md)) | encode default; decode le |
| `#TCF.7` / `#TCF.6` | **legado CORTADO** de `src/tcf` | 2026-05/06 | git-as-compat (ADR-0024): `git checkout` da era pra ler/comparar |
| `#TCF.5` | superseded | 2026-04 (v0.5) | tcf 0.5.x (legacy, nao manter) |

**`#TCF.8` e' o formato DEFAULT** ([ADR-0032](../adr/0032-tcf8-default-format.md), 2026-07-09): todo
multi-col emite `#TCF.8M`; single-col plano segue **orfao** (0 bytes de header, ADR-0029 camada 1 /
[ADR-0030](../adr/0030-freeze-single-col-body-at-1.0.md) freeze). O legado `#TCF.6`/`#TCF.7` foi
**cortado** de `src/tcf` (decode fail-loud com dica de git). Self-describing: natures (ADR-0027) + hex
+ escaping viajam no header.

**Discriminador de 1 char** ([ADR-0029](../adr/0029-version-format-identification-semi-implicit.md) +
[ADR-0031](../adr/0031-hierarchical-discriminator-H.md)): o caractere logo apos `#TCF.8` decide a
estrutura. 5 valores:

| apos `#TCF.8` | tipo | header |
|---|---|---|
| *(nada, body direto)* | single-col orfao (DEFAULT, 0 B) | — |
| `M` | multi-col plano | `#TCF.8M<meta>` (meta INLINE na linha da assinatura) |
| `H` | multi-col hierarquico (especializacao de `M`) — **reservado** (ADR-0031; codec no lab, fail-loud) | `#TCF.8H<meta-arvore>` |
| ` ` (espaco) | single + spec | `#TCF.8 [nome]:spec` (nome opcional, so' rotulo) |
| `\n` | single version-stamp | `#TCF.8` (carimbo opt-in; magic-number p/ `file`/libmagic) |

Discriminador desconhecido/reservado (incl. `H`) -> **fail-loud** no decode (nao degrada pra orfao).

**Meta do `#TCF.8M`** — INLINE apos a assinatura (`#TCF.8M<meta>\n<bodies>`), sem prefixo `# `. Cada
coluna = `[<pre>]<size>[=<nome>][:<id>]`:
- **byte-size em HEX** ([T-FMT-HEADER-BASE-HEX](../../tickets/T-FMT-HEADER-BASE-HEX.md), ADR-0032 §3):
  `format(n,'x')` (minusculo, sem `0x`, sem zero a esquerda). Colisao-livre com os separadores. Decimal
  so' via comando de inspecao (nao e' formato armazenado).
- **prefixo de modo** `!`=raw (V2-A) · `@`=dict (V2-B) · `%`=split (V2-C), antes do size.
- **sufixo `:id`** = nature (cpf/cnpj/ip, ADR-0027); resolve via dict fixo core-only, id desconhecido ->
  cru + warning, precedencia header-vence. O `:id` da nature = ULTIMO `:` NAO-escapado.
- **nome com separador** (`,`/`=`/`:`/`\`/prefixo `!@%` inicial): **escapado com backslash**
  ([T-FMT-NAME-ESCAPING](../../tickets/T-FMT-NAME-ESCAPING.md)); tokenizer splita em separador
  NAO-escapado. Unico proibido: `\n` (separador de linha do meta).
- **ultima coluna sem size** (`min_header`, corpo ate' EOF, O-FMT-15/ADR-0023): par sem `=`.
- **colunas anonimas** (`drop_names`): omite `=nome`; decode reconstroi pela ORDEM (`{'0':..,'1':..}`).

Exemplos (body na(s) linha(s) seguinte(s)):

    #TCF.8M7=doc:cnpj,x          <- multi: 2 cols, doc(size 0x7) com nature cnpj, x (ultima, sem size)
    #TCF.8M@a=uf,1e=nome         <- dict (@) na col uf; nome size 0x1e=30; ultima sem size
    #TCF.8 docs:cpf              <- single + spec cpf, nome 'docs'
    #TCF.8                       <- single version-stamp (body single-col puro)

- **byte-neutro do single-col**: single-col plano = body puro **orfao** (sem assinatura, D1-D9=1523B e
  real-world=89616B intactos — ADR-0032 nao mexe no single-col). So' o MULTI-COL virou `#TCF.8M`.

**Candidatos de coluna** (o fallback per-coluna, todos no `#TCF.8M`; `min(tcf,raw,dict,split)`):
- **V2-A fallback identity** ([ADR-0022](../adr/0022-v2a-fallback-identity-weld.md), `fallback=True`):
  min(TCF, raw); coluna raw marcada `!<size>=<name>`.
- **Header minimo** ([ADR-0023](../adr/0023-v2-minimal-header-weld.md), `min_header=True`): omite o size
  da ULTIMA coluna (corpo ate' EOF). Voltado a payload pequeno.
- **V2-B dicionario** ([ADR-0025](../adr/0025-v2b-dictionary-categorical-weld.md), `@`) e **split
  estrutural** ([ADR-0026](../adr/0026-structural-split-weld.md), `%`): mais candidatos per-coluna.
- **V2-RLE-STREAM** (follow-up de V2-B, **NAO weldado**): RLE no stream de indices `@dict`. Caracterizado
  2026-06-19: CLOSED-geral / nicho textual-puro aberto. `src/tcf` intocado.

> **Nota historica**: `#TCF.7`/`#TCF.6` foram os formatos default anteriores (opt-in `#TCF.8` era SSE
> nature). A partir de [ADR-0032](../adr/0032-tcf8-default-format.md) o `#TCF.8` e' o default e o legado
> saiu do codigo vivo (git-as-compat, pre-1.0 ADR-0024 — a versao antiga e' ponto de progresso/comparacao,
> nao producao). No 1.0 o passado morre no git.

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
captura bytes-canonical de D1-D9 (1523B total) e D17a (300B INVARIANT, #TCF.8M default — ADR-0032).
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
│   │  #TCF.8M   (DEFAULT — ADR-0032)                │ ADR-0004/0032 │ │
│   │  meta INLINE hex:  !<s1>=<n1>,...,<nN>          │ +0022/25/26/29│ │
│   │  <body1><body2><body3>...                      │               │ │
│   │  (concat byte-precise, sem delimitador)        │               │ │
│   └──────────────────────────────────────────────┘               │ │
│   legado #TCF.6/#TCF.7: CORTADO (git-as-compat, ADR-0032).         │ │
│                                                                  │ │
│   single-col: body puro, sem assinatura                             │ │
└─────────────────────────────────────────────────────────────────────┘
```

### Decode (espelho)

```
decode(text) → list[str] | dict[str, list[str]]
         │
         ├─ disc após "#TCF.8" == "M" ──► _decode_multi → dict
         │  (H/desconhecido → fail-loud; #TCF.6/.7 → erro de legado)
         └─ caso contrário            ──► _decode_column → list
```

Self-describing: a assinatura (`#TCF.8M` multi; órfão/espaço/`\n` single) identifica
o formato. O decoder dispatcha automaticamente; legado `#TCF.6/#TCF.7` → fail-loud
(ADR-0032, git-as-compat).

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
header `#TCF.8M` (DEFAULT, ADR-0032) + meta INLINE.

> **Default #TCF.8M (ADR-0032)**: `encode(dict)` emite **`#TCF.8M`** com
> `fallback` + dicionário V2-B + split + `min_header` **automáticos** — meta INLINE
> na linha da assinatura, byte-sizes em **HEX**, markers de modo por coluna (`!` raw,
> `@` dict, `%` split), nomes com separador **escapados** e a última coluna sem size.
> O legado `#TCF.6/#TCF.7` foi cortado (git-as-compat). Ex. real (sizes hex):
> `#TCF.8M!5=id,!f=nome,!plano\n...` (`f` = 15 em hex).

**V2-A fallback identity (ADR-0022, `fallback`)**: por coluna escolhe min(TCF, raw);
coluna raw vira `!<size>=<name>`. **Ligado por default**.

**Header mínimo (ADR-0023, `min_header`)**: o meta é INLINE (sem prefixo `# `); `min_header`
omite o size da última coluna (corpo até EOF): meta `<s1>=<n1>,...,<nN>`. **Ligado por default**.
Foco: payload pequeno (header fixo domina). `fallback`/`min_header` são knobs opt-out (não mudam
mais o formato — sempre `#TCF.8M`).

**V2-B dicionário (ADR-0025, `@`) + split estrutural (ADR-0026, `%`)**: candidatos
extras do fallback por coluna (dicionário categórico; quebra de campo estrutural).
Entram no default quando reduzem a coluna.

Restrições:
- Nomes de coluna com separador (`,`/`=`/`:`/`\`/prefixo `!@%`) são **escapados com backslash**
  (T-FMT-NAME-ESCAPING); só `\n` é proibido (separador de linha do meta)
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
│    #TCF.8...C name=timestamp chunk=1/3 of=table_X   (camada futura; família .8)                  │
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
- D17a sintético (13×4): **300 bytes** (#TCF.8M default, V2-B hex — ADR-0032; re-pinável ADR-0024/0025)
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
Detalhes: [experiments/lab/dirty/2026-05/2026-05-24/2026-05-24-benchmark-formats-compression/](../../experiments/lab/dirty/2026-05/2026-05-24/2026-05-24-benchmark-formats-compression/).

**Suite de testes** (snapshot 2026-05-27: 259 passed; contagem atual em
[STATUS.md](../../STATUS.md)). Guardião byte-canonical:
[`test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py)
(snapshot D1-D9=1523B single-col intacto + D17a=300B #TCF.8M default, ADR-0032).

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
- [`historia-dirty-lab.md`](../../experiments/lab/dirty/notas/2026-05/historia-dirty-lab.md) — M0-M14 desenvolvimento
- [`roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md) — hipóteses ativas/fechadas
- [`naturezas-numericas-2026-05-23.md`](../../experiments/lab/dirty/notas/2026-05/naturezas-numericas-2026-05-23.md) — catalogação 12 naturezas
- [`futuras-otimizacoes-formato.md`](../../experiments/lab/dirty/notas/2026-05/futuras-otimizacoes-formato.md) — O-FMT-* registry

### Plano de design v0.4 (referência arquitetural)
- [`2026-05-05-v04-design-recap.md`](../workbench/research-notes/_archive/2026-05-05-v04-design-recap.md) — D1-D18, EncodeManager (D13), Plan, 3 camadas
