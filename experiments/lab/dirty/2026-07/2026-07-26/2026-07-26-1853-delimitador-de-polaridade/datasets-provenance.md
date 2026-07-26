# Proveniência — delimitador de polaridade (2026-07-26-1853)

**Fonte**: 100% sintético/determinístico (LCG, `seed=7`). Nenhum download, nenhuma rede,
nenhum dado real, nenhum relógio.

## Os documentos são MÁSCARA, não documento

`cpf` e `cnpj-mascara` geram o *formato* (`NNN.NNN.NNN-NN`, `NN.NNN.NNN/0001-NN`) por
aritmética — **sem qualquer cálculo de dígito verificador**. Não há CPF nem CNPJ válido aqui,
e nenhum é publicado. Idem `cartao`: é a máscara, não um número válido.

## As 10 formas

As 8 primeiras são **idênticas às do lab `0330`** (mesma função `gera`, mesma seed), para as
duas medições serem comparáveis lado a lado sem reinterpretação.

| forma | por que está aqui |
|---|---|
| `cpf` | o caso pedido pelo owner; coluna toda literal → 0 transições |
| `ip` | outro fluxo constante, corpo menor |
| `cartao` | o caso que a máscara não conseguia (6 adjacências) |
| `cep` | poucas transições |
| `telefone` · `data-iso` | fluxo alternado — o regime desfavorável |
| `email` | dígito misturado com texto; é onde a proposta **perde** |
| `texto` | controle: 0 literais, a regra tem de recusar |
| `data-br` · `cnpj-mascara` | **contêm `/`** — existem só para provar que o `min` troca de candidato |

`n = 500`, exceto `cpf` com `n = 200` (o mesmo do caso original, `A-cpf-like-n200`).

As duas últimas foram acrescentadas **depois da primeira rodada**, em que a tabela de
candidatos deu zero em todas as colunas e portanto não demonstrava nada sobre a escolha do
char. Sem elas o `min` sobre candidatos seria código não exercido.

## Validação — e por que não é circular

A lição do lab `2026-07-26-0038` (retratado): `de_X(para_X(c)) == c` prova consistência
interna, **não validade**. A cadeia aqui é:

```
dados -> _encode_column -> corpo CANÔNICO
      -> para_delim     -> corpo com delimitador
      -> de_delim       -> corpo reconstruído
      -> compara byte a byte com o corpo CANÔNICO         (`exato`)
      -> decode(cabeçalho + reconstruído) == dados        (`rt`, parser REAL do src/tcf)
```

Os alvos de comparação são o **corpo canônico** e o **dado original**; quem lê é o `decode`
de `src/tcf`. `rt` só é avaliado se `exato` passou, para não mascarar diferença de corpo com
acerto de dado.

A checagem do seq-RLE usa `find_escape_digit_runs` do **próprio core**
(`tcf.composicional.hcc_seqrle`) — não uma reimplementação minha, que já produziu falso
positivo em lab anterior.

## Limites declarados

- **Métrica**: bytes de corpo. Os 2 chars de modo no cabeçalho (`d<char><polaridade>`) **não**
  entram — seriam +2 B, dentro do ruído das economias medidas.
- Candidatos varridos: `/ ! ? & % #`. Escolha por `min(transições + ocorrências)` sobre
  candidato × polaridade inicial.
- Estado reseta por linha. Estado global entre linhas **não medido**.
- **Nada soldado**; `src/tcf` intocado.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede.
