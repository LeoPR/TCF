# Proveniencia — custo x protecao do b64 (2026-08-06-2250)

## Deterministico, sem RNG

Uma unica coluna, `f"v{i%3}"`, em tres escalas (200, 20 000, 200 000). **Sem `random`, sem
relogio, sem rede.** Nao ha' documento sintetizado.

A coluna e' deliberadamente trivial: o que se mede e' **tempo de CPU das checagens** e **o que
cada uma seguraria** — nao compressao. Dado complexo so' adicionaria ruido ao cronometro.

### Por que `k=3`, e nao outro

`k=3 -> w=2`. Com `n=200`: `200*2/8 = 50` bytes -> **67 chars** base64 sem padding. **67 nao e'
multiplo de 4**, entao o ultimo char carrega **bits mortos** — que e' a condicao para a sonda
`caixa-trocada` produzir corrupcao de VALOR.

Com outra largura o payload poderia fechar exato e a mesma sonda viraria mudanca de conteudo
puro, fora do alcance de qualquer validacao sintatica. A distincao esta' medida no lab
`2026-08-06-2104`. **Nao e' acaso: e' a condicao que torna a tabela B significativa.**

## As 6 sondas

| sonda | classe de adulteracao |
|---|---|
| `char-invalido` · `quatro-invalidos` | fora do alfabeto base64 |
| `padding-extra` | grafia dupla dos mesmos bytes |
| `extensao-zero` (`+AAAA`) | bytes ZERO em base64 canonico |
| `truncado` | payload curto |
| **`caixa-trocada`** | o ultimo char — a UNICA que muda valores |

Os 6 wires adulterados sao materializados em `outputs/sonda-*.tcf`.

## Medicao de tempo — o que ela vale e o que nao vale

`timeit`, 200 repeticoes ate' `n=20 000` e 20 acima disso; o `decode` inteiro com 1/20 das
repeticoes.

**Numeros de UMA maquina, UMA rodada.** Servem para ORDEM DE GRANDEZA (o "sub-1%"), nao como
benchmark — o instrumento de benchmark do repo e' o `scripts/bench_perf`. A conclusao do lab
nao depende do valor exato: depende de o custo ser duas ordens de grandeza menor que o
`decode`, o que se sustenta nas tres escalas.

## Validacao

`le_parcial(wire, quais)` reimplementa o caminho de leitura aplicando **so'** o subconjunto de
checagens pedido — e' o que permite isolar o efeito de cada uma. O alvo de comparacao e' o
`decode` publico do wire VALIDO.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. Este lab **informa uma decisao**, nao propoe mudanca.
- A alternativa O(1) (checar so' os bits mortos do ultimo char) **NAO foi medida** — fica como
  `T-B64-BITS-MORTOS`.
- Corrupcao de CONTEUDO (char valido por char valido em payload SEM bits mortos) continua fora
  do alcance de qualquer validacao sintatica; seria checksum, outro ticket.
- So' a rota `bN modo B` foi cronometrada. As outras usam o mesmo `valida_payload_b64`, entao
  o custo relativo e' o mesmo, mas o `decode` delas tem custo-base diferente.

## Reprodutibilidade

`python run.py` regenera. Os tempos variam com a maquina; **a tabela B e' deterministica**.
