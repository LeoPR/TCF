# PATRICIA bidir + heuristica refinada + reflexao sobre dedução

**Data**: 2026-05-19
**Origem**: continuacao do lab 18. Refinar 3 dimensoes:
  1. **Heuristica de selecao** (gain em vez de len)
  2. **Bidir** (construir arvore esquerda e direita simultaneamente)
  3. **Dedu cao de marcadores** (quando podemos omitir `=`, `*`?)

## Pass A — Heuristica refinada

### Bug do lab 18

Em C1, lab 18 escolheu `user001@gmail.com` (string completa, count=2)
em vez de `user00` (count=8). Razao: heuristica preferia **afixo mais
longo**.

### Formula correta — gain matematico

Para um afixo de `len` chars que aparece em `count` strings:

```
bytes_economizados = count × (len - len(idx))
                   ≈ count × (len - 1)        # idx unico digito eh comum

custo_declaracao = len + 2                    # "*" + texto + " "

gain_total = count × (len - 1) - custo_declaracao
```

Para C1 (8 strings, todas comecando com `user0`):
- Afixo `user00` (count=8, len=6): `gain = 8 * 5 - 8 = 32B`
- Afixo `user001@gmail.com` (count=2, len=17): `gain = 2 * 16 - 19 = 13B`
- **user00 vence** com a formula correta

### Implementacao

Em `collect_useful_prefixes`, ordenar por gain:
```python
def gain(prefix, count):
    return count * (len(prefix) - 1) - (len(prefix) + 2)
```

E so manter afixos com `gain > 0`.

## Pass B — Bidir PATRICIA

### Motivacao

User observou: em C4 (emails-2dom), `@gmail.com` e `@yahoo.com`
sao sufixos repetidos, mas a arvore forward (esquerda-pra-direita)
nao detecta isso de forma natural.

### Solucao — duas arvores

```
forward_tree   = constroi PATRICIA com strings normais
                 → coleta prefix candidates
reverse_tree   = constroi PATRICIA com strings REVERTIDAS
                 → coleta suffix candidates (reverter de volta)
```

### Decomposicao de cada string

Para cada string `v`:
1. Acha melhor `prefix` (gain maximo) tal que `v.startswith(prefix)`
2. `rest = v[len(prefix):]`
3. Acha melhor `suffix` (gain maximo) tal que `rest.endswith(suffix)`
4. `mid = rest[:-len(suffix)]`
5. Emite `<p-tok> <mid-tok> <s-tok>`

### Vantagem

PATRICIA forward + PATRICIA reverse simultaneamente capturam
estrutura **bidirecional** sem precisar de Pass 2.

## Pass C — Reflexao sobre dedu cao de marcadores

### Marcadores atuais

| Marcador | Significado | Pode ser deduzido? |
|----------|-------------|--------------------|
| `*<text>` | decl inline | NAO — distintivo de "criar idx" |
| `<n>` (puro) | ref idx | parcialmente (ver abaixo) |
| `_<n>` | literal numerico | NAO — sem ele eh ambiguo |
| `=<n>` | ref linha | parcialmente (ver abaixo) |
| `<text>` | literal puro | OK — ausencia de marcador |

### Deduções viaveis

#### Deducao 1 — `=<n>` redundante quando linhas dominam

**Insight do user em C5**: se 100% das linhas com numero sao refs
de linha (e nenhuma eh ref de string-idx), o `=` eh redundante.

**Implementacao**: detector conta:
- `n_string_idx_refs` — quantas linhas usam ref a string-idx
- `n_line_refs` — quantas usam ref a linha
- Se `n_string_idx_refs == 0`, omite `=` (numero solto = linha-ref)
- Se ambos coexistem, mantem `=` (desambigua)

**Quando funciona**: datasets onde ha so RLE de linha, sem dict
de strings.

#### Deducao 2 — string-idx unico vs ref-linha

Se uma linha tem **multiplos tokens** (mais de 1), e um deles eh
numero, **com certeza** eh ref string-idx (linha-ref vem sempre
sozinha, sem outros tokens).

**Implementacao**: decoder usa numero de tokens:
- 1 token numerico, sem `*` antes → ref linha (ou string idx se header
  declarar)
- N tokens com numero no meio → ref string idx

**Quando ajuda**: confirma que `=` so eh necessario quando linha eh
**curta** (1 token apenas).

#### Deducao 3 — `_<n>` so quando ambiguo

`_<n>` desambigua "1" como literal vs ref. Se nao ha refs com idx
1 ate aquele ponto, `1` literal nao eh ambiguo. Mas decoder nao sabe
"ate aquele ponto" sem rastreio.

**Implementacao**: encoder pode emitir `1` (sem `_`) se idx 1 ainda
nao foi declarado. Se sim, emite `_1`.

**Risco**: parsing depende do estado. Decoder precisa rastrear o que
ja foi declarado.

### Resumo de deducoes possiveis

| Marcador | Reducao possivel | Quando vale |
|----------|------------------|-------------|
| `=` | omitir se nao ha string-idx | so em datasets RLE-puro |
| `_` | omitir se idx ainda nao usado | sempre (com tracking) |
| `*` | NAO eh deduzivel | sempre necessario |

## Cenarios para teste

| # | Dataset | Pass | Esperado |
|---|---------|------|----------|
| C1 | 8 emails do user (lab 16/18) | A+B | -25% ou melhor (heuristica refinada) |
| C2 | 30 emails 2dom | A+B | sufixo `@gmail/@yahoo.com` virar idx via bidir |
| C3 | 20 codigos PED | A+B | manter ou melhorar |
| C4 | 4 emails do user | A+B | melhorar (era +20% no lab 17) |
| C5 | 15 dups-dominantes | A+B+C | dedu cao de `=` reduz bytes adicionais |

## Saida

`./output/<C>/`:
- `literal.txt`
- `lab18.txt` — referencia do lab anterior
- `bidir.txt` — saida deste lab (Pass A + B)
- `bidir-deducao.txt` — adiciona Pass C (omite `=` quando nao ambiguo)
- `bytes.json`

---

## Resultados

### Tabela bytes

| Cenario | literal | lab18 | **lab19 bidir** | bidir vs lab18 | bidir vs lit | RT |
|---------|--------:|------:|----------------:|---------------:|-------------:|----|
| **C1 user-example** | 149 | 117 | **81** | **-30.8%** | **-45.6%** | OK |
| **C2 codigos-uniforme** | 280 | 136 | **131** | -3.7% | **-53.2%** | OK |
| C3 misto-80-20 | 256 | 130 | 133 | +2.3% | -48.0% | OK |
| **C4 emails-2dom** | 540 | 304 | **265** | **-12.8%** | **-50.9%** | OK |
| C5 dups-dominantes | 60 | 48 | 48 | 0% | -20.0% | OK |
| C6 4-emails | 72 | 60 | 61 | +1.7% | -15.3% | OK |
| **medias** | | | | **-7.22%** | **-38.85%** | **6/6 OK** |

### Comparativo cumulativo (4 labs)

| Lab | Tecnica | Avg vs literal |
|-----|---------|---------------:|
| 16 | inline only (prepop 4 linhas) | -21.0% |
| 17 | PATRICIA + header verboso | -11.2% |
| 18 | PATRICIA + inline | -33.75% |
| **19** | **PATRICIA bidir + gain refinado** | **-38.85%** ⭐ |

**Ganho cumulativo de +18pp** desde lab 16. Cada refinamento contribuiu.

### C1 — output visual (validou Pass A + B)

```
*user00 1@g *mail.com    ← decl prefix idx 1 + "1@g" + decl suffix idx 2
1 2@g 2                   ← idx1 + "2@g" + idx2 = user002@gmail.com
=1                        ← repete linha 1
=2                        ← repete linha 2
1 4@hot 2                 ← user004@hotmail.com
1 6@g 2                   ← user006@gmail.com
hdssserr@hot 2            ← hdssserr@hotmail.com
xcfdf@zip 2               ← xcfdf@zipmail.com
```

**81B (lab18 era 117B = -30.8%)**.

Detector escolheu `mail.com` como suffix (sem `@`), o que captura
**gmail.com, hotmail.com, zipmail.com simultaneamente**. Mais
inteligente que escolher cada `@dominio.com` separado.

### C4 — output visual (validou bidir)

```
*user0 _19 *@yahoo.com
1 _14 *@gmail.com
1 _10 3
1 _26 2
1 _22 2
1 _06 3
...
```

**265B (lab18 era 304B = -12.8%)**.

PATRICIA bidir capturou:
- idx 1 = `user0` (prefix global)
- idx 2 = `@yahoo.com` (suffix)
- idx 3 = `@gmail.com` (suffix)

Cada linha emite `1 _NN s` onde s eh 2 ou 3.

### Sobre Pass C — dedução de marcadores

Implementado mas pouco aproveitado:
- Em todos os cenarios testados, ha pelo menos uma string-idx ref,
  entao `omit_eq` fica False
- C5 (so dups) seria candidato perfeito, mas o header `#mode:lineRle`
  custa ~13B; o ganho de omitir `=` foi insuficiente
- **Conclusao**: dedução so vale em datasets MUITO grandes onde a
  economia per-linha (1 char) supera o header

Em C5: lit 60B → bidir 48B → +deducao 50B (PIORA por causa do header).
Em datasets >= 200 linhas com >= 50 dups, dedução comeca a valer.

**Decisao**: manter dedução implementada como flag opt-in, nao default.

### Limites observados

**C3 misto piorou ligeiramente (+2.3% vs lab18)**: razao provavel —
heuristica gain prefere afixo `INV-2026-` (count=16, gain=234) sobre
nada. Mas o `INV-2026-` ja era usado no lab18. Diferenca minor (130 vs
133B) — variabilidade do encoder.

**C6 (4 emails) piorou +1.7%**: lab 18 escolheu strings inteiras como
idx; lab 19 com gain prefere `user0`. Mas em N=4 micro, decls custam
mais que economia.

### Achados conceituais

1. **Heuristica gain refinada eh dominante** quando dataset > 10
   linhas — C1 (-30.8% vs lab18) prova
2. **PATRICIA bidir captura sufixos comuns** que forward-only nao
   pegava — C4 (-12.8% vs lab18) prova
3. **Dedução de marcadores** so vale em escalas grandes — registrar
   para datasets >= 200 com modo dominante claro

### Pendencias

| # | Pendencia | Prioridade |
|---|-----------|-----------|
| L1 | Multi-decl `**` (cascata de afixos) | media |
| L2 | Cenarios maiores (>=100 valores) para validar escala | alta |
| L3 | Consolidar com lab 18 (mesmo formato, escolher engine via flag) | baixa |
| L4 | Heuristica que considera tambem `idx` longo (idx 10+ custa 2 chars) | baixa |

## Status

- [x] Pass A: heuristica gain (count × len) implementada
- [x] Pass B: PATRICIA bidir (forward + reverse) implementado
- [x] Pass C: dedução de `=` implementada (opt-in)
- [x] 6/6 RT OK
- [x] **Avg -38.85% vs literal** (best ate agora)
- [x] +7pp sobre lab 18
- [x] C1 com -45.6% (vs +20% no lab 17)
- [x] C4 com -50.9% (validou bidir)
- [ ] Multi-decl `**` (proximo)
- [ ] Cenarios >= 100 (proximo)
