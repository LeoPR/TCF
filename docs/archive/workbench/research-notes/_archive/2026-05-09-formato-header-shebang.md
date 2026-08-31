# Formato do header — sintaxe shebang `#TCF.5 SRDM`

Decisao consolidada 2026-05-09 apos EXP-004 / EXP-004b / EXP-004c.

## Forma final

```
#TCF.5 SRDM         <- linha 1: identificacao + flags
# s:1,2             <- sort por indice 1-based (opcional)
# d:3               <- discrim marked override (opcional, raro)
# e:1=δ,3=Π         <- ext (opcional, futuro)
# l:2=I             <- layout (opcional, futuro)
<col1>:
<token>
...
<col2>:
...
```

### Regras de emissao da versao

| Versao semantica | Header | Bytes |
|------------------|--------|------:|
| 0.5 | `#TCF.5` | 6 |
| 0.8 | `#TCF.8` | 6 |
| 1.0 | `#TCF1` | 5 |
| 1.3 | `#TCF1.3` | 7 |
| 2.0 | `#TCF2` | 5 |
| 2.10 | `#TCF2.10` | 8 |

**Algoritmo**:
- Major 0 → omite `0`, escreve `.<minor>`
- Minor 0 → omite `.0`, escreve so `<major>`
- Caso geral → `<major>.<minor>`

### Por que estilo shebang

1. **Identificacao formal**: linha 1 = "magic line", convencao de
   formatos plain-text (igual `#!/bin/bash`)
2. **Sem espaco apos `#`**: 1B economizado por arquivo, sem perda
   de legibilidade
3. **Versao colada**: `TCF.5` em vez de `TCF v0.5` — 4B a menos,
   sem perda informacional
4. **Escala futura**: versao 1, 1.3, 2.10 etc seguem mesma regra

## Comparativo medido (EXP-004c)

| Cenario | Verbose A | Mid B | Shebang C | C vs A | C vs B |
|---------|----------:|------:|----------:|-------:|-------:|
| S1 simple-strings (6 rows) | 112 | 93 | **89** | -20.5% | -4.3% |
| S2 with-int-col (6 rows) | 129 | 110 | **106** | -17.8% | -3.6% |
| S3 categorical-500 | 2452 | 2428 | **2424** | -1.1% | -0.2% |
| S4 tpch-supplier-100 | 2371 | 2357 | **2353** | -0.8% | -0.2% |
| **medias** | | | | **-10.07%** | **-2.07%** |

Apos gzip: C ainda vence A em -5.7% medio, B em -2.5% medio.

### Por que o ganho extra de C vs B nao zera apos gzip

A linha shebang nao tem nomes repetidos para gzip absorver — eh
literalmente menos bytes na origem. Gzip nao consegue comprimir
o que nao foi emitido.

## Outras decisoes registradas

### Sort

```
# s:<idx1>,<idx2>,...   <- 1-based, sem espacos, sem palavras
```

Indices sao a posicao da coluna no body (ordem de aparicao). Decoder
resolve em **late binding** (parseia indices, mapeia para nomes
quando body eh conhecido).

### Discriminacao

```
# d:<idx>,<idx>   <- so colunas com discrim "marked" sao listadas
                     (bare eh default; M auto-detecta)
```

Quando flag M esta ativa, normalmente nao precisa emitir `# d:` —
decoder infere por 1a passada. Header explicito so quando M off
ou para forcar override.

### Comentarios

Linhas que comecam com `#` mas nao casam com nenhuma regra =
**comentario livre**, decoder ignora. Util para metadata humana.

## Variantes consideradas e descartadas

### Variante D — modifiers per-coluna

Proposta:
```
comprador,s:        <- "esta coluna eh sort key"
qty,m:              <- "marked discrim"
data,δ:             <- "delta extension"
```

**Vantagem**: self-documenting na proxima linha de coluna.
**Desvantagem**: nomes de coluna com virgula viram tokens estruturais
— complica parser. Nao ha benefit direto de bytes.

**Status**: registrada mas **nao implementada**. Avaliar quando
chunks forem implementados — cada chunk pode ter modifiers locais
que diferem do header global.

### Variante E — single-line

Proposta agressiva:
```
#TCF.5 SRDM s:1,2 d:3
```

Tudo em 1 linha. Economiza 1 newline.
**Desvantagem**: limite de comprimento (alguns parsers de header
falham > 1024 bytes).

**Status**: rejeitada — newlines sao baratos e melhoram legibilidade.

## Migracao

Versoes anteriores ate v0.4 nao tem retrocompat. Decoder atual
**so le** sintaxe shebang. Encoder so emite shebang.

Para arquivos antigos: re-encodar com encoder atual.

## Como evolui no futuro

Quando v0.6/v1.0 mudar gramatica:
- Adicionar campo `version` no Header
- Decoder ramifica por versao
- Encoder default = ultima versao; flag para forcar antiga

Versao em si segue Semver:
- Patch (0.5.1) → bug fix em decoder, formato compativel
- Minor (0.6) → nova flag opt-in, ou refinamento
- Major (1.0) → mudanca de gramatica que quebra decoders antigos

Header reflete major.minor; patch nao aparece no formato.

## Status

- [x] EXP-004c rodado, ganho mensurado
- [x] Encoder default emite shebang
- [x] Decoder so aceita shebang
- [x] Validacao 6/6 testes
- [x] Documentado aqui (durable)
- [ ] Atualizar paper quando consolidar v0.5
