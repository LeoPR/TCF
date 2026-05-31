# M1.A — Escape pontual

## Tecnica

Para cada char no literal que mudaria o modo do parser, prefixar
com `\`.

Chars escapados em modo literal:
- digitos (0-9) — mudariam para modo refs
- `*` — seria separador entre literais
- `\` — proprio escape (para diferenciar)

Outros chars no literal **nao** sao escapados — so' tem
significado em positions especificas (inicio de linha, etc.)
que nao ocorrem no meio de um literal emitido pelo algoritmo
do exp 16.

## Custo

+1 byte por char ambiguo no literal.

## Roundtrip nos 4 datasets

| Dataset | Bytes | Roundtrip |
|---|---:|---|
| D1-emails-simples | 162 | OK |
| D2-emails-quote-id | 200 | OK |
| D3-stress-substring | 242 | OK |
| D4-caos-mix | 152 | OK |

## Propriedades para F2

| Eixo | Comportamento |
|---|---|
| Stateful encoder? | nao — processa tokens em ordem |
| Stateful decoder? | nao — parse linear, sem lookback |
| Latencia incremental | linha por linha |
| Complexidade encoder | 1 regra (escape de digito/*/\\) |
| Complexidade decoder | 1 modo de literal + escape |
| Lookahead | nao precisa |

## Exemplo (D2 linha 2: ref+lit+ref)

`1,2,3\4\25,6,7`

- `1,2,3` refs (digitos+virgulas)
- `\4\2` literal `"42"` com cada digito escapado
- `5,6,7` refs

## Limitacoes

- Cada char ambiguo custa 1 byte de escape — em literais com
  muitos digitos consecutivos, escape acumula
- Nao distingue escape de outras semanticas (ex: `\n`)
- Nao permite chars de controle no literal — escapados
  literalmente, nao tratados

## Implementacao

Arquivo `syntax.py`. Classe `M1AEscapeSyntax(Syntax)`. Importa
`online.py` (raiz exp 16) e `syntax_base.py` (interface).

Compartilha com outros micros do M1:
- `_coletar_quebras` (propagacao de quebras entre nos)
- `_rle_adjacente` (RLE de linhas)

Especifico de M1.A: apenas `_escape` e logica de literal raw +
escape no `_parse_decl`.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade/M1-A-escape
python teste.py
```

Imprime TCFs gerados em D1-D4 com bytes e roundtrip.
