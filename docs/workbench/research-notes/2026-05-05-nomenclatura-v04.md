# Nomenclatura TCF v0.4 — proposta de revisao

Os nomes `L0/L1/L2/L3` herdados do v0.2 ficaram confusos com a
expansao de tecnicas (cross-DICT, affix, key-elim, type-preserving,
strat-stats). Esta nota propoe sistema novo.

## Problema dos `Lxxx`

| Antigo | Significado | Problema |
|--------|-------------|----------|
| L0 | Expanded (sem compressao) | OK, mas eh apenas "raw" |
| L1 | RLE | OK, mas raramente usado isolado |
| L2 | Sorted + RLE | mistura 2 conceitos no mesmo nivel |
| L3 | DICT + sorted + RLE | mistura 3 conceitos |
| Novos? | E (cross), H (affix), I (key-elim) | nao cabem em escala numerica |

Escala numerica da impressao errada de "mais alto = mais comprimido",
mas nao eh assim — algumas tecnicas se aplicam ou nao conforme dados.

## Proposta — 3 camadas de nomenclatura

### Camada 1 — Modos macro (curtos, humanos)

Apelidos de alto nivel para usuario escolher comportamento geral:

| Modo | Significado | Quando usar |
|------|-------------|-------------|
| **`raw`** | Sem compressao, valores diretos | debug, datasets minusculos |
| **`compact`** | RLE + sort automatico | dados com repeticao moderada |
| **`smart`** | Caminho feliz: auto-tudo (E + H + I + bypass) | DEFAULT recomendado |
| **`extreme`** | Forca todas tecnicas (mesmo se piora) | ablacao cientifica |

Usuario tipico nunca sai de `smart`. Pesquisa cientifica usa `extreme`
ou granular.

### Camada 2 — Tecnicas individuais (siglas curtas)

Para configuracao granular ou logging:

| Sigla | Tecnica | Proposta original |
|-------|---------|-------------------|
| `RLE` | Run-length encoding (`N*val`) | base v0.2 |
| `DICT` | Dicionario inline per-column | base v0.2 (D16 inline) |
| `XDICT` | Cross-column DICT | Proposta E |
| `AFFIX` | Prefix/sufix comum | Proposta H |
| `KEY-ELIM` | Eliminacao PK/FK grau 2/3 | Proposta I |
| `SORT` | Ordenacao (lex/num/freq) | base + Proposta F |
| `STRAT-STATS` | STATS condicionados por categorical | Proposta A |
| `TYPE` | Type-preserving decode | Proposta B |
| `CHUNK` | Chunking autocontido | M-chunks-v04 |

### Camada 3 — Modificadores por tecnica

Cada tecnica aceita 3 estados:

| Modificador | Comportamento |
|-------------|---------------|
| `auto` | heuristica decide ativar (DEFAULT) |
| `force` | sempre ativa (mesmo se piora) |
| `off` | nunca ativa |

## API resultante

```python
# Caminho feliz (recomendado)
EncodeConfig(mode="smart")

# Granular (para experimento)
EncodeConfig(
    rle="auto",
    dict="auto",
    xdict="auto",
    affix="auto",
    key_elim="auto",
    sort="auto",
    strat_stats="off",  # so com schema
    type="auto",
)

# Ablacao
EncodeConfig(mode="extreme", legacy={"dict_in_header": True})
```

## Conversao do que ja temos

| Antigo `Lxxx` | Novo |
|--------------|------|
| L0 | `mode="raw"` |
| L1 | `mode="compact"` com `dict="off"` |
| L2 | `mode="compact"` (default — RLE + sort) |
| L3 | `mode="compact"` com `dict="auto"` |
| Caminho feliz | `mode="smart"` |
| Tudo forcado | `mode="extreme"` |

`Lxxx` saem da API publica. Internamente, encoder traduz `mode` em
plano de execucao.

## Exemplo de log

Encoder pode logar decisoes em formato legivel:

```
[encoder] mode=smart
  table pessoas (n=100):
    SORT: auto → escolheu coluna 'categoria' (cardinality=4)
    DICT: auto → cardinality=4/100 < 0.5 → ativa em 'categoria'
    XDICT: auto → 'categoria' compartilha vocab com produtos.categoria → GLOBAL_1
    KEY-ELIM: auto → 'id' eh PK grau 2 → eliminada
    AFFIX: auto → nao detectado
  table produtos (n=50):
    ...
```

## Apelidos para combinacoes uteis (nomeacao livre)

Algumas combinacoes podem ganhar apelido para discussao:

| Combo | Apelido sugerido | Quando vale |
|-------|------------------|-------------|
| RLE + SORT | `RLE-sorted` ou `RS` | dados com repeticao agrupada |
| DICT + KEY-ELIM | `dict-relational` ou `DR` | schemas com FKs grau 2 |
| XDICT + AFFIX | `cross-affix` ou `XA` | identificadores estruturados compartilhados |
| RLE + DICT + SORT + XDICT + KEY-ELIM | `smart` (eh o caminho feliz) | default |

Apelidos sao **opcionais** — formal eh sempre via `mode=` ou
configuracao granular.

## Decisoes tomadas (2026-05-05)

- **Q1 — modos macro `raw/compact/smart/extreme`**: ACEITO
- **Q2 — siglas tecnicas (RLE/DICT/XDICT/AFFIX/KEY-ELIM/SORT/STRAT-STATS/TYPE/CHUNK)**: ACEITO
- **Q3 — modificadores `auto/force/off`**: ACEITO (default implicito)

Sigla geral confirmada: **TCF = Tabular Compact Format** (ver
[2026-05-05-sigla-tcf.md](2026-05-05-sigla-tcf.md)).

A nomenclatura entra em vigor na proxima fase (lab clean EXP-003+).
Implementacao no core ocorre apos validacao de hipoteses operacionais
(HP-T1, HP-T2, HP-T3).
