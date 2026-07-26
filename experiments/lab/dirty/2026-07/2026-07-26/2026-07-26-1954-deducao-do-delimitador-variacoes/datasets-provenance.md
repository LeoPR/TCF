# Proveniência — dedução do delimitador (2026-07-26-1954)

**Fonte**: 100% sintético/determinístico (LCG, `seed=7`). Nenhum download, nenhuma rede,
nenhum dado real, nenhum relógio. 35 colunas × 300 linhas.

## Os documentos são MÁSCARA, não documento

`cpf`, `cnpj`, `cartao` e `isbn` geram o *formato* por aritmética sobre o LCG, **sem qualquer
cálculo de dígito verificador**. Não há CPF, CNPJ, cartão ou ISBN válido aqui, e nenhum é
publicado.

## Por que 35 e não 8

O lab anterior (`1913`) media 10 formas + 3 colunas reais. A pergunta aqui é sobre a
**robustez de uma regra de dedução**, e regra de dedução só se testa contra o que tenta
quebrá-la. Daí os 4 grupos:

| grupo | n | por que |
|---|---:|---|
| **Formatadas** | 19 | o regime onde o ganho existe; várias máscaras diferentes |
| **Numéricas** | 5 | ordenado, aleatório, negativo, decimal, com `null` |
| **Texto** | 5 | o regime onde a regra deve **recusar** |
| **Adversariais** | 6 | construídas para quebrar |

### As adversariais, e o que cada uma ataca

| forma | ataca |
|---|---|
| `adv-usa-bang` | contém `!` = `FAIXA[0]` — quebra a dedução por menor-char de propósito |
| `adv-alfabeto-total` | usa **todos** os 88 chars da FAIXA — não sobra char livre |
| `adv-so-digitos` | nenhum separador; toda a linha é uma corrida só |
| `adv-sem-digitos` | nenhum literal de dígito para economizar |
| `adv-um-valor` | 300 linhas idênticas — o corpo vira referência |
| `adv-unicode` | chars fora de ASCII (`café`, `ção`) fora da FAIXA |

Elas existem para produzir **resultado negativo**, e produziram: `adv-alfabeto-total` é a
única coluna sem char livre, e `adv-usa-bang` é a única falha de dedução pelo motivo que eu
previa.

## Validação — e por que não é circular

Lição do lab `2026-07-26-0038` (retratado): `de_X(para_X(c)) == c` prova consistência interna,
**não validade**. A cadeia aqui é:

```
dados -> _encode_column   -> corpo CANÔNICO
      -> varredura_unica  -> (tokens VIRTUAIS, alfabeto, trocas_R, trocas_L)
      -> resolve          -> grafia com delimitador
      -> de_grafia        -> corpo reconstruído
      -> compara byte a byte com o corpo CANÔNICO       (`exato`)
      -> decode(cabeçalho + reconstruído) == dados      (`rt`, parser REAL do src/tcf)
```

Para as duas deduções, o teste é mais estrito e é o que importa:

- **menor-char**: reconstrói com o char **deduzido do corpo**, nunca com o eleito guardado.
- **V3**: `de_v3` lê o char **e** a polaridade do prefixo, e só então reconstrói. A função não
  recebe o eleito.

É por isso que as duas puderam falhar — e uma falhou.

## Limites declarados

- **Métrica**: bytes de corpo + o custo de cabeçalho de cada materialização.
- O prefixo V3 é contado como **1-2 B na linha de cabeçalho que já existe**; o `\n` extra nos
  artefatos `.tcfp` é só para o teste de leitura ser exato, e não entra na conta.
- Faixa do delimitador: ASCII imprimível menos a gramática (`* ~ ^ , | \`) = 88 chars.
- **Nada soldado**; `src/tcf` intocado.
- **Falta**: escala maior com variedade e dado real — pedido explícito do owner para a etapa
  seguinte.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede.
