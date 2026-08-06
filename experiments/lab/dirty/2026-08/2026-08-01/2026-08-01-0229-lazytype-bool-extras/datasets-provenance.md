# Proveniência — T-LAZYTYPE-BOOL, cabeça congelada + extras (2026-08-01-0229)

## Por que este lab existe

Coluna concentrada em null/true/false COM exceções string hoje é **fail-loud** (o `.8H`
recusa escalares mistos — descoberto na preparação deste lab; a hipótese original dizia
"expulsa pro `.8H`", o que se mostrou impreciso). O owner aprovou medir: slots congelados
da `TABELA_B2` + extras declarados do slot 3 em diante, na mecânica do `dominio_bn`.
**LAB APENAS — `src/tcf` intocado.**

## Sintéticas — determinísticas, sem RNG, viés declarado

**Construídas pra testar esta hipótese** (viés declarado, §4 do guia): base ternária
`None a cada 9º, bool alternado`, n=200, com extras injetados por índice:

| coluna | extras | construção |
|---|---|---|
| `extras-raro` | 1 | `"other"` em 2 posições (7, 113) |
| `extras-frequentes` | 1 | `"other"` a cada 5º (20%) |
| `k-extras-01/05/20` | 1/5/20 | `e{i}` ciclados, injeção a cada 7º/7º/4º |
| `armadilha-tipos` | 3 | `"true"`, `"0"`, `"1"` como STRINGS-extra a cada 11º — RT deve preservar str ≠ bool/int |
| `controle-0-extras` | 0 | ternário puro — o lazy deve RECUSAR (b2 cobre) |
| `controle-300-extras` | 300 | 300 distintos (n=400) — recusa por w>8 |

## Real — fixture já commitada, exceções INJETADAS

**Nenhum download.** `datasets/samples/adult-census/adult-sample.csv` (o mesmo dos labs
0829/2350/0037). Não há coluna bool+exceção direta nos fixtures; usa-se `sex` → bool
(conversão idêntica aos labs anteriores), com **null injetado a cada 11º** e a exceção
`" ?"` **injetada a cada 23º** — escolha DO LAB, não do dado (Adult usa `" ?"` como
sentinela em outros campos; aqui é emulado).

## Validação — e por que não é circular

```
dados -> lazy_bn.proto_encode: extras por 1ª aparição (slot 3+); pack_w (src/tcf);
         domínio de extras na grafia do core via _grafa/_encode_column (dominio_bn, src/tcf)
      -> lazy_bn.proto_decode: parse posicional + _decode_column + _le_grafia + unpack_w
         (src/tcf); fail-loud espelhado do decode_bn
      -> compara com os DADOS ORIGINAIS (valor, TIPO — NoneType/bool/str — e comprimento)
```

Rotas de comparação: (b) `bB` completo = `candidatos()` do `dominio_bn` com tag injetada
(mesmo truque do `tipado_bn.py` do lab 0829 — domínio INTEIRO declarado); (c) `encode()`
real — **fail-loud na união**, registrado como dado; (d) flat-string (perde tipo). A
cabeça do protótipo é assertada igual à `TABELA_B2` do `src/tcf/tipos_internos.py` no
`run.py`.

Roundtrip é ARQUIVO: `outputs/<nome>-dataset.roundtrip.json` byte-idêntico a
`intermediates/<nome>-dataset-consumido.json`, com assert no `run.py`.

## Limites declarados

- **Nada soldado**; os `-lazy.tcf`/`-completo.tcf` são proposta — o decode público não os lê.
- Sintéticos com viés declarado; real com null/exceção injetados pelo lab.
- A rota (b) completo **perde tipo** no caso armadilha (`"true"` str funde com `True`) —
  registrado como evidência, não como falha do lab.
- **gzip e CPU não medidos.** T-TIPOS-CONFORTO-MAP fora do escopo.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relógio, sem rede. Sai `0` só se RT
lazy tipo-estrito passar, os 3 fail-louds rejeitarem e o fio for determinístico.
