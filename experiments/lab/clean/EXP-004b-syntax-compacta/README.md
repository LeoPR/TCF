# EXP-004b — Sintaxe compacta no header (variante B)

## Hipotese

Header verbose (`# sort: col1, col2`) repete nomes ja presentes no body.
Trocar por sintaxe compacta (`# s:1,2`) com indices 1-based deveria
reduzir bytes sem perder informacao.

## Mudanca proposta

| Aspecto | A (verbose) | B (compact) |
|---------|-------------|-------------|
| Sort | `# sort: comprador, produto` | `# s:1,2` |
| Discrim | `# discrim: a=bare, b=marked` | `# d:2` (so indices marked) |
| Ext (futuro) | `# ext: data=delta` | `# e:1=δ` |
| Layout (futuro) | `# layout: nome=inline` | `# l:1=I` |

Indices sao 1-based pela ordem de aparicao da coluna no body.

## Decoder

Aceita ambas sintaxes (auto-detecta). Resolve indices em **late binding**
— guarda como `int[]` no header, resolve para nomes quando body eh
parseado e ordem das colunas eh conhecida.

## Roundtrip

OK em todos os 4 cenarios (decoder le tanto A quanto B).

## Resultados

### Tabela de bytes

| Cenario | rows × cols | csv | tcf A | tcf B | **B vs A** | csv+gz | A+gz | B+gz | **B+gz vs A+gz** |
|---------|------------:|----:|------:|------:|-----------:|-------:|-----:|-----:|-----------------:|
| S1 simple-strings | 6×2 | 93 | 112 | **93** | **-17.0%** | 79 | 116 | 109 | **-6.0%** |
| S2 with-int-col | 6×3 | 109 | 129 | 110 | **-14.7%** | 97 | 129 | 123 | -4.7% |
| S3 categorical-500 | 500×4 | 7927 | 2452 | 2428 | -1.0% | 1926 | 1226 | 1212 | -1.1% |
| S4 tpch-supplier-100 | 100×3 | 2484 | 2371 | 2357 | -0.6% | 521 | 564 | 555 | -1.6% |
| **medias** | | | | | **-8.32%** | | | | **-3.36%** |

### Achados

**1. Em datasets pequenos, ganho substancial.** S1 economiza 17% no texto
puro e 6% apos gzip — caiu para o mesmo tamanho do CSV (93B). Antes (A),
TCF v0.5 perdia em 20% para CSV em micro datasets; com B, empata.

**2. Em datasets medios/grandes, ganho marginal (~1%).** O header eh
fracao pequena do payload. Mas eh ganho **livre** — sem custo de
implementacao alem da nomeacao.

**3. gzip nao anula o ganho.** Apesar de gzip comprimir nomes repetidos
(o que diminuiria o ganho de B), o ganho nao zera porque os nomes
**nem sao emitidos** em B.

**4. Roundtrip OK em todos os casos.** Decoder aceita ambas sintaxes
(auto-detecta `# sort:` ou `# s:`).

## Headers reais (lado a lado)

### S1 (6 rows × 2 cols)
```
A:  # TCF v0.5 SRDM\n# sort: comprador, produto\n  → 47B
B:  # TCF v0.5 SRDM\n# s:1,2\n                       → 28B  (-40% no header)
```

### S3 (500 rows × 4 cols, 3 sort keys)
```
A:  # TCF v0.5 SRDM\n# sort: cidade, status, categoria\n  → 50B
B:  # TCF v0.5 SRDM\n# s:4,2,3\n                            → 27B  (-46% no header)
```

### S4 (100 rows × 3 cols, 1 sort key)
```
A:  # TCF v0.5 SRDM\n# sort: s_nationkey\n  → 35B
B:  # TCF v0.5 SRDM\n# s:3\n                  → 21B  (-40% no header)
```

Em **headers**, ganho consistente de **40-46%** — vai escalar quando
chunks adicionarem mais metadata por bloco.

## Decisao consolidada

**Adotar variante B como default**.

Razoes:
- Ganho **mensuravel e gratuito** (sem custo de complexidade)
- Crucial em **micro datasets** onde header dominava
- Crucial em **chunks** (proximas fases) — cada chunk pode ter header
  curto, reduzindo overhead
- Roundtrip preservado

A variante A continua suportada pelo decoder mas o encoder usa B por
default. Apenas ablacao cientifica explicita (`header_style="verbose"`)
emite A.

## Reflexao adicional — por-coluna modifiers (variante C, futura)

Proposta do user durante a sessao:
```
comprador,s:        ← override per-column: "esta coluna eh chave de sort"
qty,m:              ← marked discrim per-column
data,δ:             ← delta extension per-column
```

**Vantagem**: self-documenting na coluna, sem precisar de header
auxiliar.
**Desvantagem**: parser fica mais complexo (vírgulas em nome de coluna
viram tokens estruturais).

**Decisao**: registrar como variante C futura. Avaliar quando chunks
forem implementados (cada chunk pode ter colunas com modifiers locais
que diferem do header global).

## Arquivos produzidos

```
outputs/
  S1-simple-strings/
    source.csv          ← fonte CSV
    tcf-A-verbose.tcf   ← variante A
    tcf-B-compact.tcf   ← variante B
  S2-with-int-col/
    ...
  S3-categorical-500/
    ...
  S4-tpch-supplier-100/
    ...
  results.json          ← dados estruturados
```

## Codigo

`run.py` reusa encoder/decoder de `src/tcf/v05/`. Mesmas Flags(SRDM),
diferenca apenas em `header_style="compact"` vs `"verbose"`.

## Status

- [x] Encoder com `header_style` parametro
- [x] Decoder auto-detecta `# sort:` vs `# s:`
- [x] 4 cenarios rodados, roundtrip OK
- [x] Ganho mensurado: -8.3% texto / -3.4% pos gzip (medias)
- [x] Variante B = default a partir desta data
- [ ] Variante C (per-column modifiers) — futuro com chunks
