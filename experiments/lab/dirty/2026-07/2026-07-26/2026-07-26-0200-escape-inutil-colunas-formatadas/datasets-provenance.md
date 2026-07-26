# Proveniência — escape inútil em colunas formatadas (2026-07-26-0200)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa). Nenhum download, nenhum dado real.

**Os documentos são MÁSCARA, não documento.** `cpf-mascara` e `cnpj-mascara` geram o *formato*
(`NNN.NNN.NNN-NN`) a partir do LCG, sem qualquer cálculo de dígito verificador. **Não há CPF
nem CNPJ válido aqui**, e nenhum é publicado. O mesmo vale para `cartao` e `isbn` — são
máscaras, não números válidos.

## As 12 formas

Escolhidas por serem **formatadas**: máscara fixa, alta unicidade, dígitos em toda parte — o
regime que motivou a pergunta do owner.

| forma | máscara |
|---|---|
| `cpf-mascara` · `cnpj-mascara` | documento brasileiro |
| `cep` | `NNNNN-NNN` |
| `telefone` | `(NN) 9NNNN-NNNN` |
| `cartao` | `NNNN-NNNN-NNNN-NNNN` |
| `placa` | `AAANANN` (mistura letra e dígito) |
| `data-iso` · `hora` | temporal |
| `ip` | `N.N.N.N` |
| `moeda` | `R$ N,NN` |
| `coord` | `-NN.NNNNNN` |
| `isbn` | `978-N-NNNN-NNNN-N` |

`n = 500` na tabela principal; a seção de variação varre `n ∈ {20, 100, 500, 2000}` em 4
formas, para expor que a aplicabilidade **depende do conteúdo, não do formato**.

## Validação — e por que não é circular

O corpo sem-escape é lido por `le_sem_escape`, que **reimplementa a semântica** (dígito =
literal, `*` = separador, `^N` = linha) e é comparado com o `decode` **REAL** do corpo normal.

Isso corrige o método do lab `2026-07-26-0038`, onde a validação era `de_X(para_X(c)) == c` —
**circular**: dava 36/36 enquanto 2 wires estavam corrompidos.

O leitor **devolve `None`** quando encontra marcador seq-RLE, em vez de fingir que leu. Foi
esse `None` que expôs o caso `coord`.

## Limites declarados

- **Métrica única: bytes do corpo.** O cabeçalho do modo (1 char) não entra na coluna `Δ` —
  seria +1 B, dentro do ruído das economias medidas.
- **Resultado negativo**: 1 de 12. A regra binária não cobre o caso que a motivou.
- A variante `min()` ("abrir mão de poucas referências para destravar o modo") **não foi
  medida** — está anotada como próximo passo.
- **Nada soldado**; `src/tcf` intocado.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede.
