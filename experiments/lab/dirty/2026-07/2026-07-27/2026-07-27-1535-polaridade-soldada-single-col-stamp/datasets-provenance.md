# Proveniência — polaridade soldada (2026-07-27-1535)

25 colunas sintéticas + 8 reais, `n = 200` (ou menos onde a fixture é menor).

## Sintéticas — LCG determinístico

`seed=7`, sem `random` global, sem relógio, sem rede.

**Os documentos são MÁSCARA, não documento.** `cpf-mascara`, `cnpj-mascara`, `cartao` e
`isbn` geram o *formato* por aritmética sobre o LCG, **sem qualquer cálculo de dígito
verificador**. Não há CPF, CNPJ, cartão ou ISBN válido aqui, e nenhum é publicado.

Três grupos, com papéis distintos:

| grupo | colunas | papel |
|---|---|---|
| formatadas | cpf, cnpj, cartão, cep, telefone, ip, mac, uuid, data-iso, data-br, timestamp, moeda, coord, isbn, placa, sku | o regime onde a polaridade ganha |
| deve recusar | texto, frase, nomes, email, binario-01, sem-digito | o FLOOR tem de dizer não |
| bordas | uma-linha, vazia, so-vazio | `n∈{0,1}` e valor vazio |

## Reais — fixtures já committadas

**Nenhum download.** Todas de `datasets/samples/`, versionada no repo.

| coluna | arquivo | campo |
|---|---|---|
| `retail-stockcode` | `online-retail/stockcode-2k.csv` | `StockCode` |
| `retail-description` | `online-retail/description-2k.csv` | `Description` |
| `lineitem-comment` | `tpch-sf001/lcomment-2k.csv` | `l_comment` |
| `cnpj-doc` · `cnpj-data-inicio` | `receita-cnpj/cnpj-2k.csv` | `cnpj`, `data_inicio` |
| `pessoas-cpf` | `br-identidades/pessoas-sample.csv` | `cpf` |
| `ibge-municipio` | `ibge-municipios/ibge-municipios-sample.csv` | `municipio` |
| `tpch-phone` | `tpch-sf001/customer-sample.csv` | `c_phone` |

Linhas com valor vazio são **puladas** (a rota flat exige `list[str]`); o `n` da tabela é o
número real de valores usados. `br-identidades` é dataset **sintético** de origem — não há
documento de pessoa real aqui.

## Por que a comparação antes/depois é exata

O weld é **camada de borda**: o corpo canônico não mudou um byte. Então a grafia anterior é
reconstruível sem checkout:

```
antes  = '#TCF.8\n' + _encode_column(dados)      # exatamente o que o encoder emitia
depois = encode(dados)                            # o que ele emite agora
```

Não é estimativa nem proxy. O `_encode_column` é a mesma função que o encoder chama, e o
`polariza` só entra depois dela.

## Validação

```
dados -> encode  -> wire REAL (o que o formato emite hoje)
      -> decode  -> parser REAL, publico
      -> compara valor E tipo, elemento a elemento, com guarda de comprimento
```

Sem transformação de lab no meio: os `.tcf` de `outputs/` são wires que o `decode` lê. O
`zip` sozinho truncaria, então o comprimento é conferido antes.

Os gates (D1-D9, D17a, real-world) são lidos das **constantes dos próprios testes**
(`tests/test_regression_v1_baseline.py`, `tests/test_real_world_snapshots.py`), não copiados
— se um pin mudar, o lab acusa sozinho.

## Limites declarados

- Escopo do weld: single-col **stamp** e **tipado**. `.8M`/`.8H`/spec/órfão fora — o `D17a`
  inalterado é evidência disso.
- `n = 200`: bom para comportamento e gate, **não é benchmark**.
- Os dois casos adversariais (dígito/letra eleitos) usam colunas construídas para saturar o
  início da FAIXA — são regressão, não dado plausível.

## Reprodutibilidade

`python run.py` regenera byte a byte. Sai `0` só se RT 33/33, pior caso ≤ 0, e os 3 gates
batendo.
