# Proveniência — polaridade × tipos (2026-07-26-2126)

**Escala pequena de propósito**: 50 linhas por coluna, 33 colunas. Não é benchmark nem teste
de resistência — é observação de comportamento e caça a bug, como pedido.

## 18 colunas sintéticas — LCG determinístico

`seed=7`, sem `random` global, sem relógio, sem rede.

**Os documentos são MÁSCARA, não documento.** `cpf-mascara-null` e `cartao-null` geram o
*formato* por aritmética sobre o LCG, **sem qualquer cálculo de dígito verificador**. Não há
CPF nem cartão válido aqui, e nenhum é publicado.

Escolhidas para exercer o cruzamento, não para medir ganho:

| grupo | colunas | o que exercem |
|---|---|---|
| bool | `bool-puro`, `bool-constante`, `bool-null`, `bool-null-maioria` | tag `b`, modo denso, `b` + null |
| binário | `binario-01`, `binario-01-null`, `binario-sn` | `"0"`/`"1"` como **string**, com e sem null |
| null | `null-puro`, `null-quase-tudo`, `null-esparso` | slot 0 em 3 densidades |
| tipado | `int-null`, `int-ordenado-null`, `int-negativo-null`, `float-null` | tag `n` + null |
| **colisão** | `str-zero-e-null`, `str-zero-misto` | o char `0` como **dado** e como **slot nulo** na mesma coluna |
| formatada | `cpf-mascara-null`, `cartao-null` | o regime onde a polaridade ganha, agora com null |

O par `str-zero-*` existe especificamente para produzir corrupção se o mecanismo estiver
errado — e **produziu**, na primeira rodada.

## 15 colunas reais — fixtures já committadas

**Nenhum download.** Todas de `datasets/samples/`, que já vive versionada no repo. 50 linhas
de cada (20 nas fixtures menores).

| coluna | arquivo | campo | transformação |
|---|---|---|---|
| `real-adult-sex-bool` | `adult-census/adult-sample.csv` | `sex` | `Male` → `True` |
| `real-adult-class-bool` | idem | `class` | `>50K` → `True` |
| `real-adult-age-int` · `real-adult-capgain-int` | idem | `age`, `capital-gain` | `int()` |
| `real-pm25-com-NA` | `beijing-pm25/beijing-pm25-sample.csv` | `pm2.5` | `"NA"` → `None` |
| `real-pm25-Iws-float` | idem | `Iws` | `float()` |
| `real-cnpj-matriz-bin` · `real-cnpj-fantasia-null` · `real-cnpj-doc` | `receita-cnpj/cnpj-2k.csv` | 3 campos | `""` → `None` |
| `real-pessoas-cpf` · `real-pessoas-email-null` | `br-identidades/pessoas-sample.csv` | 2 campos | `""` → `None` |
| `real-ibge-id` | `ibge-municipios/ibge-municipios-sample.csv` | `id` | `int()` |
| `real-retail-stockcode` | `online-retail/stockcode-2k.csv` | `StockCode` | — |
| `real-tpch-phone` · `real-tpch-acctbal` | `tpch-sf001/customer-sample.csv` | 2 campos | `float()` no saldo |

As transformações `""` → `None` e `"NA"` → `None` são **do lab**, não do dado: servem para
produzir colunas com null de origem real em vez de sintético.

`br-identidades` é dataset **sintético** de origem (nomes/CPF gerados), já assim no repo — não
há documento de pessoa real aqui.

## Validação — e por que ela pegou os bugs

Lição do lab `2026-07-26-0038` (retratado por circularidade): `de_X(para_X(c)) == c` prova
consistência interna, **não validade**.

```
dados -> encode            -> wire REAL (cabeçalho + corpo canônico)
      -> varredura_unica   -> tokens virtuais + alfabeto + trocas
      -> resolve           -> corpo com delimitador
      -> v3                -> wire da proposta
      -> de_v3             -> lê char e polaridade do SUFIXO, sem receber o eleito
      -> de_grafia         -> corpo reconstruído
      -> == corpo canônico byte a byte                      (`exato`)
      -> decode(cabeçalho + reconstruído) == dados          (`rt`)
```

O `rt` compara **valor E tipo, elemento a elemento**. Foi isso que pegou o primeiro bug: um
`"0"` virando `None` mantém o tamanho da lista e o tipo `list`, e passaria num RT frouxo.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado.
- 50 linhas por coluna: bom para achar bug, **inútil para medir ganho**. Os `Δ` da tabela são
  observação, não resultado.
- O modo denso (`b<N>` + base64) e o hierárquico (`H`) saem como **N/A** — o mecanismo recusa
  antes de olhar o corpo. Não foram testados por dentro.
- Multi-col não foi testado.
- Continua aberto desde o lab `1913`: se o delimitador virar grafia **canônica**, o seq-RLE
  ainda localiza o dígito incrementável pelo escape.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, fixtures lidas do repo, sem relógio,
sem rede.
