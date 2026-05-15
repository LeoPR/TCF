# Contra-prova de formatos: porque comparar TCF vs CSV/JSON/JSONL

## Pergunta

Quando dizemos "TCF reduz **X%** vs raw", **qual** raw?

Resposta crua: depende do formato textual usado como baseline. CSV
inflado por delimitadores, JSONL inflado por chaves repetidas
(`{"val": "..."}` em cada linha), JSON array sem chaves repetidas
mas com aspas e virgulas. **Sem comparar com todos, nao sabemos se
TCF reduz redundancia ou apenas troca delimitador.**

## Formatos avaliados

| Formato | Serializacao | Overhead por linha |
|---|---|---|
| `csv` | `val\n<l1>\n<l2>\n...\n` | 1 byte (newline) + header `val\n` (4 bytes uma vez) |
| `jsonl` | `{"val":"<l>"}\n` por linha | ~11 bytes/linha (`{"val":"","\\}\n`) |
| `json` (array) | `["<l1>","<l2>",...]` | ~3 bytes/linha (`","`) + 2 totais (`[]`) |
| `tcf` | encoded | n/a (depende de redundancia detectada) |

## Resultado D1-D15

Totais agregados:

| Formato | Bytes total | vs CSV |
|---|---:|---:|
| csv | 4872 | 100% (baseline) |
| tcf | **3131** | **64%** |
| json | 5409 | 111% |
| jsonl | 7001 | 144% |

**Bold** = mais compacto. TCF reduz; JSON e JSONL aumentam (em
relacao a CSV) pelo overhead estrutural.

## Interpretacao

### Se compararmos TCF vs JSONL apenas:

3131 / 7001 = **45%**. Parece reducao impressionante.

### Se compararmos TCF vs CSV:

3131 / 4872 = **64%**. Reducao mais modesta.

### Se compararmos TCF vs JSON array:

3131 / 5409 = **58%**. Intermediario.

**A escolha do baseline muda a narrativa**. Reports oficiais devem
usar **CSV** como baseline padrao (formato textual mais compacto
ja' adotado universalmente em ETL). Qualquer outra escolha
exige justificativa explicita.

## Caso onde TCF nao vence: D10-datas-mundiais

| Formato | Bytes (D10) |
|---|---:|
| csv | **177** |
| tcf | 191 |
| json | 218 |
| jsonl | 338 |

15 datas, todas em formatos diferentes ("ISO", "US", "EU", "BR",
"written"). Zero substring repetida → OBAT nao encontra prefix/suffix
estaveis → marcadores estruturais do TCF adicionam custo sem reducao
correspondente. **Comprovacao**: ate' brotli/zstd no TCF nao
recuperam vs brotli/zstd no CSV (vide
[`../reports/05-campeao-por-dataset.md`](../reports/05-campeao-por-dataset.md)).

Esse caso e' importante: mostra que TCF **nao e' panaceia**; tem
custo estrutural pago quando nao ha' redundancia explicita pra
explorar.

## Caso onde TCF ganha sozinho: D8-cabeca-cauda

| Formato | Bytes (D8) |
|---|---:|
| csv | 388 |
| tcf | **100** |
| json | 420 |
| jsonl | 516 |

Padrao `prefix/X/suffix` com X variando — OBAT captura prefix +
suffix estaveis; HCC reduz cada linha a 2 atom refs. Reducao de
**74%** (vs csv). Aqui TCF se torna **estado da arte** ate' depois
de aplicar compressores externos: `tcf/brotli` (66 bytes) bate
`csv/brotli` (68 bytes).

## Por que importa adotar essa metodologia

Sem contra-prova de formatos:

- Reports podem dizer "TCF reduz 55%" sem mencionar que JSONL e'
  baseline irrealista (poucos sistemas mandam JSONL como
  encoding de coluna unica).
- Avaliacao se torna "TCF > JSONL" o que e' **trivialmente
  verdadeiro** dado overhead estrutural de JSONL.
- Difícil de identificar onde TCF perde valor (D10, D13, D14)
  porque o eixo de comparacao certo nao foi escolhido.

A contra-prova torna explicito **onde TCF tem valor** e **onde
nao tem**. Ambos sao informacao cientifica.
