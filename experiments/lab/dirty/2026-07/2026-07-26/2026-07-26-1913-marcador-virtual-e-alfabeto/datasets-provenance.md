# Proveniência — marcador virtual + alfabeto (2026-07-26-1913)

Dois conjuntos: **10 formas sintéticas** e **3 colunas reais**.

## Sintéticas — LCG determinístico

`seed=7`, sem `random` global, sem relógio, sem rede. São **idênticas às do lab `1853`**
(mesma função `gera`), para as duas medições serem comparáveis número com número.

**Os documentos são MÁSCARA, não documento.** `cpf` e `cnpj-mascara` geram o *formato* por
aritmética, **sem qualquer cálculo de dígito verificador**. Não há CPF nem CNPJ válido aqui, e
nenhum é publicado. Idem `cartao`.

## Reais — fixtures já committadas no repo

**Nenhum download.** São as mesmas fixtures do gate `tests/test_real_world_snapshots.py`, que
já vivem versionadas em `datasets/samples/`:

| coluna | arquivo | n |
|---|---|---:|
| `retail-description` | `online-retail/description-2k.csv` | 2000 |
| `retail-stockcode` | `online-retail/stockcode-2k.csv` | 2000 |
| `lineitem-comment` | `tpch-sf001/lcomment-2k.csv` | 2000 |

Elas existem no lab por um motivo específico: a pergunta *"sempre existe char livre?"* não
pode ser respondida com forma sintética, que tem alfabeto artificialmente pequeno por
construção. As três são **texto livre real**, e são o pior caso da tabela (35, 45 e 60 chars
livres de 88).

## Validação — e por que não é circular

Lição do lab `2026-07-26-0038` (retratado): `de_X(para_X(c)) == c` prova consistência interna,
**não validade**. A cadeia aqui é:

```
dados -> _encode_column  -> corpo CANÔNICO
      -> varredura_unica -> (tokens VIRTUAIS, alfabeto, trocas_R, trocas_L)
      -> resolve         -> grafia com delimitador
      -> de_grafia       -> corpo reconstruído
      -> compara byte a byte com o corpo CANÔNICO        (`exato`)
      -> decode(cabeçalho + reconstruído) == dados       (`rt`, parser REAL do src/tcf)
```

Os alvos de comparação são o **corpo canônico** e o **dado original**; quem lê é o `decode` de
`src/tcf`. `rt` só é avaliado se `exato` passou, para não mascarar diferença de corpo com
acerto de dado.

## Limites declarados

- **Métrica**: bytes de corpo. Os 2 chars de modo no cabeçalho não entram (ruído).
- `virtual.py` **simula** o que moraria em `_escape_lit`; percorre o corpo canônico uma vez.
  A contagem "1 varredura contra 8" é sobre **a decisão**, não sobre o encode inteiro.
- Faixa do delimitador: ASCII imprimível menos a gramática (`* ~ ^ , | \`) = 88 chars.
  Chars fora de ASCII não foram considerados (custariam >1 B em UTF-8).
- **Nada soldado**; `src/tcf` intocado.

## Reprodutibilidade

`python run.py` regenera byte a byte. As fixtures reais são lidas do repo; se ausentes, a
linha correspondente sai como `fixture ausente` em vez de falhar silenciosamente.
