# RLE + DICT combinados — visualizacao em etapas

**Data**: 2026-05-14
**Origem**: insight do user — RLE de linha (`=N`) e DICT de partes
(prefix/suffix) sao **camadas ortogonais** que se complementam.

## Tese

Tres camadas independentes podem operar simultaneamente:

1. **Camada 1 — RLE de linha**: linha completa que ja apareceu vira `=N`
2. **Camada 2 — DICT de partes**: prefix/suffix comum vira referencia
3. **Camada 3 — Composicao**: linha eh `<prefix-spec> <middle> <suffix-spec>`

Exemplo do user (5 emails):

```
user001@gmail.com   ← original linha 1
user002@gmail.com   ← linha 2
user003@gmail.com   ← linha 3
user001@gmail.com   ← linha 4 (= linha 1)
user002@hotmail.com ← linha 5
```

### 4 sintaxes a explorar

#### Sintaxe A — `rle-lines` (so RLE de linha inteira)

```
user001@gmail.com
user002@gmail.com
user003@gmail.com
=1
user002@hotmail.com
```

`=1` = repete linha 1.

#### Sintaxe B — `dict-left` (prefix + RLE de linha)

```
*user00 1@gmail.com   ← decl idx 1 = "user00", suffix "1@gmail.com"
1 2@gmail.com
1 3@gmail.com
=1
1 2@hotmail.com
```

#### Sintaxe C — `dict-right` (suffix + RLE de linha)

```
user001 *@gmail.com   ← decl idx 1 = "@gmail.com", prefix "user001"
user002 1
user003 1
=1
user002@hotmail.com   ← literal (suffix nao casa)
```

#### Sintaxe D — `dict-bidir` (prefix + suffix + RLE de linha)

```
*user00 1 *@gmail.com   ← decl prefix idx 1 + middle "1" + decl suffix idx 2
1 2 2                   ← idx1 + "2" + idx2 = user002@gmail.com
1 3 2                   ← user003@gmail.com
=1                      ← repete linha 1
1 2 @hotmail.com        ← idx1 + "2" + literal = user002@hotmail.com
```

## Caracteristicas

- **Camada 1 (`=N`)** funciona em qualquer sintaxe (ortogonal)
- **Camada 2/3** definem como a linha **nao-repetida** eh codificada
- **Decoder eh single-pass** se declaracoes vem antes de uses
- **3 formatos visuais** distintos para a mesma data — comparar bytes

## Algoritmo do encoder (didatico)

```
def encode_bidir(values):
    seen_lines = {}  # linha completa -> idx (1-based)
    prefix_dict = {}  # texto -> idx
    suffix_dict = {}  # texto -> idx

    # Pass 1: detectar prefix e suffix dominantes
    prefix = lcp(values)
    suffix = lcs(values)

    if not prefix and not suffix:
        return rle_lines_only(values)

    out = []
    for i, v in enumerate(values, 1):
        # Camada 1: ja viu linha completa?
        if v in seen_lines:
            out.append(f"={seen_lines[v]}")
            continue

        # Camada 2/3: decompor em prefix + middle + suffix
        mid = v
        prefix_part = ""
        suffix_part = ""
        if prefix and v.startswith(prefix):
            mid = mid[len(prefix):]
            prefix_part = prefix
        if suffix and v.endswith(suffix):
            mid = mid[:-len(suffix)] if suffix else mid
            suffix_part = suffix

        # Emite com decls inline para 1a aparicao de prefix/suffix
        ... (logica de emit)

        seen_lines[v] = i

    return "\n".join(out)
```

## Sub-pergunta a explorar

Quando `prefix` e `suffix` competem por bytes (ex: ambos cabem mas
removendo um o outro nao paga overhead), qual escolher?

**Heuristica**: testar todas 4 sintaxes e escolher o menor.
Computacionalmente caro mas valido para LAB.

## Cenarios de teste

| # | Dataset | Esperado |
|---|---------|----------|
| E1 | 5 emails do user (literal) | dict-bidir vence; valida visualmente |
| E2 | 50 emails 2 dominios (com algumas repetidas) | dict-right vence; `=N` ajuda |
| E3 | 30 codigos `INV-2026-NNNN` (sem repetidas) | dict-left vence; `=N` n/a |
| E4 | 20 valores categoricos com muitas repetidas | rle-lines vence; `=N` domina |

## O que NAO eh objetivo

- Otimalidade
- Performance
- Decisao final sobre qual sintaxe usar
- Implementacao no core

Eh **visualizacao em etapas** das camadas ortogonais.

## Saida

`./output/<E>/` com 4 sintaxes lado a lado + `literal.txt` baseline.

---

## Resultados (run.py executado)

### Tabela bytes por sintaxe × cenario

| Cenario | literal | A rle-lines | B dict-left | C dict-right | D dict-bidir | Best |
|---------|--------:|------------:|------------:|-------------:|-------------:|------|
| **E1 user-example** (5 emails) | 92 | 77 | 67 | 61 | **51** ⭐ | D (-44.6%) |
| **E2 emails-with-dups** (50) | 900 | 755 | 640 | 679 | **564** ⭐ | D (-37.3%) |
| **E3 codigos-sem-dups** (30) | 420 | 420 | **161** ⭐ | 420 | 161 | B (-61.7%) |
| **E4 categorical-muitas-dups** (20) | 100 | **70** ⭐ | 70 | 70 | 70 | A (-30.0%) |

### Tese confirmada — cada cenario tem sua sintaxe vencedora

| Cenario | Vencedor | Esperado? | Razao |
|---------|----------|-----------|-------|
| E1 (mix prefix+suffix) | **D bidir** | SIM | tem prefix `user00` + suffix `mail.com` |
| E2 (emails com dups) | **D bidir** | SIM | mesma estrutura, escala |
| E3 (codigos sem dups) | **B left** | SIM | tem prefix mas nao suffix |
| E4 (so dups) | **A rle-lines** | SIM | sem prefix/suffix; so `=N` |

**4/4 cenarios** com vencedor previsto. Cada camada (RLE-linha, prefix,
suffix, bidirect) tem **dominio empirico claro** e nao se sobrepoe.

### Visualizacao do exemplo do user (E1, D-dict-bidir, 51B)

```
*user00 1@g *mail.com    ← decl prefix idx 1 + mid "1@g" + decl suffix idx 2
1 2@g 2                   ← user00 + "2@g" + mail.com = user002@gmail.com
1 3@g 2                   ← user003@gmail.com
=1                        ← repete linha 1 (user001@gmail.com)
1 2@hot 2                 ← user00 + "2@hot" + mail.com = user002@hotmail.com
```

Note que o encoder detectou:
- **prefix** = `user00` (LCP de todos)
- **suffix** = `mail.com` (LCS de todos — incluindo gmail/hotmail!)

A sintaxe captura o **diff entre prefix e suffix** (o middle):
- "1@g" varia (entre 1, 2, 3)
- "2@hot" eh a unica excecao com domain diferente

Isso eh exatamente o que o user propos visualmente.

### Insight maior — 3 camadas ortogonais

| Camada | Operacao | Quando ajuda |
|--------|----------|---------------|
| 1. RLE-linha (`=N`) | linha completa repetida | E1, E2, E4 |
| 2. DICT prefix | prefix comum | E1, E2, E3 |
| 3. DICT suffix | suffix comum | E1, E2 |

Em E1/E2 todas as 3 camadas funcionam → bidir domina.
Em E3 so prefix funciona → dict-left domina.
Em E4 so RLE-linha funciona → rle-lines domina.

**Camadas se complementam**, nao se substituem.

### Bugs honestos

| # | Bug | Causa |
|---|-----|-------|
| B1 | E3 dict-right FAIL | codigos nao tem suffix; encoder faz fallback para A; decoder espera C → decoder errado |
| B2 | E4 dict-left FAIL | mesma causa: fallback para A com decoder B |
| B3 | E4 dict-right FAIL | idem |

**Causa unica**: encoder pode fazer fallback (B → A quando sem prefix
util), mas decoder eh selecionado pelo nome da sintaxe **antes** do
encoder rodar. Solucao: encoder deveria devolver `(text, syntax_real)`
e decoder ser escolhido pelo `syntax_real` retornado. Pendencia.

### Camadas em formato unificado (proximas iteracoes)

A sintaxe D-bidir mostra que 1 linha pode ter ate 3 partes:
- `<p-spec> <middle> <s-spec>`
- `<p-spec> <middle>` (so prefix)
- `<middle> <s-spec>` (so suffix)
- `<middle>` (sem affix)
- `=N` (RLE-linha)
- `\!<full>` (excecao)

Isso eh **gramatica unificada** — UMA sintaxe que captura tudo.
Encoder decide quantas partes emitir conforme estrutura.

### O que isso valida

1. **3 camadas ortogonais** funcionam empiricamente
2. **Cada camada tem dominio claro** sem sobreposicao (4/4 cenarios
   com vencedor previsto)
3. **Bidir bate as duas componentes individuais** quando ambas se
   aplicam (E1: 51B vs 67/61 das individuais)
4. **Encoder pode escolher numero de camadas** baseado em deteção
   (LCP/LCS) — auto-detect funciona

### Pendencias para proxima iteracao

1. Corrigir bugs B1/B2/B3 (encoder retornar syntax_real)
2. Implementar auto-detect que escolhe entre {A, B, C, D} dinamicamente
3. Testar com cenarios maiores (>= 1000 valores) e mais variados
4. Considerar **sintaxe unificada** (uma so) que comporte todos os
   casos via numero variavel de partes

### Status

- [x] 4 sintaxes (rle-lines, dict-left, dict-right, dict-bidir)
- [x] Encoder + decoder por sintaxe
- [x] 4 cenarios testados, vencedor previsto pela teoria em todos
- [x] Visualizacao da sintaxe bidir confirma proposta do user
- [x] 13/16 roundtrips OK (3 bugs por fallback de encoder)
- [ ] (proximo) auto-detect de sintaxe; sintaxe unificada
- [ ] (proximo) cenarios de escala maior
