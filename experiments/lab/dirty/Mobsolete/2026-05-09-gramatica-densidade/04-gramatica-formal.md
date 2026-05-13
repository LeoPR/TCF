# Gramática formal consolidada

Toda decisão das mesas anteriores reunida em uma especificação única.

---

## Estrutura do arquivo TCF v0.5

```
file        ::= header? layout-block? column*

header      ::= '#' line-content '\n' (...)+
              ; declarações opcionais: TCF version, sort, ext, encoding flags

layout-block ::= '# layout: ' col-layout (',' col-layout)* '\n'
col-layout  ::= column-name '=' ('line' | 'inline')

column      ::= column-name ':' '\n' value-block

value-block ::= line-mode | inline-mode

line-mode   ::= (token '\n')+
inline-mode ::= token+ '\n'    ; tokens delimitados por prefixo
```

---

## Tokens

```
token       ::= literal | delta | ref | run

literal     ::= absolute-string | absolute-number | absolute-date | absolute-ts
              ; depende do tipo da coluna; auto-delimitado se em formato fixo

delta       ::= '+' digits | '-' digits | '0' | '+' | '-'
              ; '+' e '-' sozinhos = +1 e -1 respectivamente (apenas após '*')

ref         ::= digits | ':' digits
              ; bare em colunas não-numéricas; marcado em colunas numéricas
              ; (regra de auto-discrim do C11/Lxxx)

run         ::= digits '*' (literal | delta | ref)
              ; N*X = N ocorrências contíguas de X (N ≥ 2)
```

---

## Tipos de coluna e seus literais

```
absolute-date    ::= 'YYYY-MM-DD'                     ; 10 chars fixo
                   | 'YYMMDD'                          ; 6 chars (modo packed)
absolute-ts      ::= 'YYYY-MM-DDTHH:MM:SS'           ; 19 chars
                   | 'YYYYMMDDTHHMMSS'                ; 15 chars (packed)
absolute-string  ::= /[^\n*+:-]+/                    ; qualquer string sem chars reservados
absolute-number  ::= integer | decimal
integer          ::= /-?[0-9]+/
decimal          ::= /-?[0-9]+\.[0-9]+/
```

---

## Cabeçalho do arquivo

```
# TCF v0.5 <flags>                              ; obrigatório
# sort: <col1>, <col2>, ...                     ; opcional
# discrim: <col>=bare|marked, ...               ; opcional, default = auto
# ext: <col>=delta|prefix|packed, ...           ; opcional
# layout: <col>=line|inline, ...                ; opcional, default = line
```

### Flags

```
flags ::= S? R? D? M? A? δ? P? L'? K? I? Π?

S = sort applied
R = RLE enabled
D = dict implicit enabled
M = auto-discriminator (bare/marked)
A = adaptive alphabet for indices
δ = delta extension (per-column via # ext)
P = prefix elision (per-column)
L' = line-RLE layout
K = count-recycling
I = inline mode (per-column via # layout)
Π = packed-absolute (per-column via # ext)
```

Default produção: `SRDMA` (5 flags, todas baixo-risco e ganho ≥ 0).

---

## Regras do decoder

### Estado por coluna

- `dict[]`: idx → valor (construído inline conforme valores aparecem)
- `last_absolute`: para colunas com δ
- `discrim_mode`: bare ou marked (do header ou inferido pela 1ª varredura)
- `layout_mode`: line ou inline (do header)

### Pseudocódigo de parse de um token

```
parse_token(input, col_state):
  if col_state.layout == inline:
    skip whitespace not relevant
  
  c = peek_char()
  
  case c:
    digit followed by '*' → parse run = N*<inner_token>
    '+' → parse delta positivo (greedy digits, ou +1 se solitário e em RLE)
    '-' → parse delta negativo (idem)
    '0' (single char) → delta zero
    '0'-'9' (no *) → bare ref (em coluna não-numérica)
                      OU literal (em coluna numérica)
    ':' → marked ref, parse digits
    YYYY pattern → literal absolute-date
    other → literal string até newline ou separador inline
  
  if 1ª aparição de literal:
    col_state.dict.append(value)
```

### Resolução

```
para cada token:
  if token é run N*X:
    emit X N vezes
  if token é delta D:
    new_value = col_state.last_absolute + D
    col_state.last_absolute = new_value
    emit new_value
  if token é ref R:
    emit col_state.dict[R-1]   # idx 1-based
  if token é literal L:
    if 1ª vez: col_state.dict.append(L)
    if coluna em modo δ: col_state.last_absolute = L
    emit L
```

---

## Exemplo completo do dataset

Cabeçalho:
```
# TCF v0.5 SRDMAδ
# sort: data, produto, qty
# ext: data=delta
```

Coluna `data` (cenário 5 da mesa delta + shorthand `*+`):

```
data:
2026-01-05
6*+
+4
5*0
+7
1
3
+9
3
1
+13
3
1
+15
4
+2
+8
+5
4
2
+10
```

Decoder:
1. linha 1: `2026-01-05` → absolute, last_absolute = 01-05, dict de
   deltas vazio
2. linha 2: `6*+` → run de 6 deltas +1. Emite 01-06, 01-07, 01-08, 01-09,
   01-10, 01-11. Adiciona +1 ao dict (idx 1).
3. linha 3: `+4` → delta +4. Emite 01-15. Adiciona ao dict (idx 2).
4. linha 4: `5*0` → run de 5 deltas zero. Emite 01-15 5×. Adiciona 0 ao
   dict (idx 3).
5. linha 5: `+7` → delta +7. Emite 01-22. dict idx 4 = +7.
6. linha 6: `1` → ref idx 1 = +1. Emite 01-23.
7. linha 7: `3` → ref idx 3 = 0. Emite 01-23 (mesmo dia).
8. ... etc

Saída final: 30 datas idênticas ao dataset original.

---

## Consistência entre as mesas

Esta gramática consolida todas as decisões das mesas anteriores:

| Decisão | Origem | Onde aparece na gramática |
|---|---|---|
| Layout column-major | mesa de síntese | column-block |
| Regra unificada (RLE+dict por linha) | mesa unificada | tokens run/literal/ref + dict[] state |
| Auto-discrim bare/marcado | mesa de C11 | discrim_mode |
| Sort multi-chave | mesa de multisort | header `# sort:` |
| Alfabeto adaptativo | mesa de alfabeto | flag A + dict de letras |
| Delta como pré-transformação | mesa de delta | header `# ext: <col>=delta` |
| Empacotar absolutos | esta mesa | header `# ext: <col>=packed` |
| Inline mode | esta mesa | header `# layout: <col>=inline` |
| Shorthand `*+` | esta mesa | regra de delta solitário |

Tudo se encaixa. Nenhuma decisão conflita com outra. Modular.

---

## Dimensões de complexidade do decoder

Cada feature adiciona ~uma linha no parser:

| Feature | Linhas adicionadas (aprox) |
|---|---|
| Linha-mode + tokens absolutos | ~10 (base) |
| RLE | +3 |
| Dict implícito | +5 |
| Auto-discrim bare/marked | +4 |
| Multi-sort | 0 (parsing transparente) |
| Alfabeto A | +3 |
| Delta (δ) | +5 |
| Empacotar (Π) | +4 |
| Inline mode (I) | +5 |
| Shorthand `*+`/`*-` | +2 |

**Total decoder**: ~50 linhas de regras de parsing. Cabe em uma página.
Confirma **H-G4**.

---

## Próxima etapa

`05-conclusoes.md` consolida o que muda na hierarquia Lxxx e os
próximos passos.
