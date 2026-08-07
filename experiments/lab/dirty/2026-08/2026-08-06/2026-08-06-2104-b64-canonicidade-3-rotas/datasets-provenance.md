# Proveniencia — canonicidade b64, 3 rotas (2026-08-06-2104)

## Deterministico, sem RNG

Todas as 5 colunas sao aritmetica sobre o indice (`i % k`). **Sem `random`, sem relogio, sem
rede.** Nao ha' documento (CPF/CNPJ/cartao) sintetizado.

| rota | coluna | por que |
|---|---|---|
| `bn-B` | `f"v{i%3}"` | o modo default do bN (dominio primeiro) |
| `bn-C` | idem, via `candidatos()[1]` | o modo lote — NAO e' emitido por default |
| `denso-b1` | `bool(i%2)` | bool puro, w=1 — o PADRAO-OURO |
| `denso-b2` | bool + null | ternario, w=2 |
| `lazy-bB` | uniao bool+str+null | a rota do ADR-0039 |

As larguras foram escolhidas para o `lazy-bB` cair em **w=3, 75 bytes = multiplo de 3** — e'
o que faz o payload dele nao ter bits mortos, e e' o que separa corrupcao SINTATICA de
corrupcao de CONTEUDO na sonda `s9`. Nao e' acaso: esta' na tabela do `result.md`.

## As 9 sondas

| sonda | ataca |
|---|---|
| `s1-char-invalido` · `s2-espaco` | o alfabeto base64 (pega o `validate`) |
| `s3-quatro-invalidos` | 4 chars invalidos — mantem o comprimento multiplo de 4 |
| `s4-padding-extra` | grafia dupla dos mesmos bytes |
| `s5-truncado-2` · `s6-truncado-4` | payload curto |
| **`s7-extensao-zero-AA`** · **`s8-extensao-zero-AAAA`** | a sonda que o lab ANTERIOR nao tinha: bytes ZERO em base64 CANONICO, que atravessam ate' a checagem de bits-de-padding do `unpack_w` |
| **`s9-caixa-trocada`** | o ultimo char — separa sintaxe de conteudo |

s7/s8/s9 sao as tres que o lab anterior nao tinha e que mudaram as conclusoes.

## Validacao

Os 45 wires adulterados sao **materializados** em `outputs/sondas/` e **relidos do disco**
antes de cada decode — nao ha' string viva no meio. O `hoje` e' o `decode` publico REAL do
`src/tcf`; o `proposto` roda a validacao sobre o payload do wire relido.

Byte-neutralidade e' contraprova em arquivo: `cmp` entre
`intermediates/<rota>-dataset-consumido.json` e `outputs/<rota>-dataset.roundtrip.json`.

## Limites declarados

- **Char valido trocado por outro char valido, em payload sem bits mortos**, e' integridade
  de CONTEUDO. Nenhuma validacao sintatica pega; seria checksum, outro ticket.
- Uma coluna por rota, `n=200`. O objetivo e' cobrir as CLASSES de adulteracao, nao varrer
  tamanho.
- **gzip e CPU nao medidos.**
- Este lab **substitui as conclusoes** do `2026-08-06-2006`, nao a evidencia dele.

## Reprodutibilidade

`python run.py` regenera os 45 wires byte a byte. Sai `0` so' se todos os roundtrips forem
byte-identicos.
