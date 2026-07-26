# Proveniência — o escape como máscara (2026-07-26-0330)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa, `seed=7`). Nenhum download,
nenhuma rede, nenhum dado real, nenhum relógio.

## Os documentos são MÁSCARA, não documento

`cpf` gera o *formato* `NNN.NNN.NNN-NN` a partir de aritmética sobre o índice — **sem
qualquer cálculo de dígito verificador**. Não há CPF válido aqui, e nenhum é publicado. O
mesmo vale para `cartao`: é a máscara `NNNN-NNNN-NNNN-NNNN`, não um número válido.

## As 8 formas

Escolhidas para cobrir o espectro do fluxo L/R, dos extremos ao meio:

| forma | máscara | por que está aqui |
|---|---|---|
| `cpf` | `NNN.NNN.NNN-NN` | o caso pedido; fluxo constante (1 run) |
| `ip` | `N.N.N.N` | outro fluxo constante, corpo menor |
| `cartao` | `NNNN-NNNN-NNNN-NNNN` | maior ganho aparente — e o que expõe a adjacência |
| `cep` | `NNNNN-NNN` | poucos runs, poucas adjacências |
| `telefone` | `(NN) 9NNNN-NNNN` | fluxo alternado: a máscara **perde** |
| `data-iso` | `20NN-NN-NN` | idem, com muita referência |
| `email` | `userN@dN.com` | dígito misturado com texto |
| `texto` | `palavraX` | controle: 0 literais, a regra tem de recusar |

`n = 500`, exceto `cpf` com `n = 200` (o mesmo `n` do caso original que motivou a discussão,
`A-cpf-like-n200`).

## Validação — e por que não é circular

A lição do lab `2026-07-26-0038` (retratado): `de_X(para_X(c)) == c` prova consistência
interna, **não validade**. Aqui a cadeia é:

```
dados -> _encode_column -> corpo NORMAL
      -> para_mascara    -> (corpo sem escape, máscara)
      -> de_mascara      -> corpo reconstruído
      -> compara byte a byte com o corpo NORMAL          (`exato`)
      -> decode(cabeçalho + reconstruído) == dados       (`rt`, parser REAL do src/tcf)
```

O alvo da comparação é o **dado original** e o **corpo canônico**, e quem lê é o `decode` de
`src/tcf` — não a inversa da transformação. `rt` só é avaliado se `exato` passou, para não
mascarar diferença de corpo com acerto de dado.

A checagem do seq-RLE usa `find_escape_digit_runs` do **próprio core**
(`tcf.composicional.hcc_seqrle`), comparando as corridas antes e depois — não uma
reimplementação minha, que já produziu falso positivo em lab anterior.

## Limites declarados

- **Métrica**: bytes de corpo, e corpo-sem-escape + máscara + 1 LF. O char de modo no
  cabeçalho (`m`) **não** entra — seria +1 B, dentro do ruído.
- Só materializa `.tcfp` onde a regra é **aplicável**; onde não é, grava
  `*-NAO-APLICAVEL.txt` com a contagem de adjacências, em vez de um wire que não se lê.
- **Nada soldado**; `src/tcf` intocado.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede.
