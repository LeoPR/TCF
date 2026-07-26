# 2026-07-26-0038 — O delimitador do flip: variantes MATERIALIZADAS

**Correção da 1ª rodada.** O owner apontou: *"mas ganho do que exatamente? as pastas não têm
as variações, sem cabeçalho nem nada. elas ficaram em sua imaginação. preciso de evidências."*

Estava certo. A 1ª rodada **estimava** (`ganho − contagem × 1 B`) e gravava só o corpo
NORMAL. Agora as três formas são **construídas, gravadas com cabeçalho e round-trip-adas**.

```
NORMAL   \168116  = literal   ·  1     = referência          (o wire de hoje)
FLIP-A   168116   = literal   ·  \1    = referência, delimitador SÓ na adjacência
FLIP-B   168116   = literal   ·  \1;   = referência SEMPRE terminada
```

Delimitador `;` é **placeholder** (da lista de zero-ocorrência) — a escolha do char continua
sendo sua.

## O que está nas pastas agora

Para cada uma das 12 formas:

| arquivo | o que é |
|---|---|
| `outputs/<f>-wire-normal.tcf` | wire **REAL** de hoje (cabeçalho + corpo) |
| `outputs/<f>-wire-flipA.tcfp` | wire flipado, delimitador só na adjacência |
| `outputs/<f>-wire-flipB.tcfp` | wire flipado, toda referência terminada |
| `outputs/<f>-equivalente.json` | JSON compacto, régua de escala |
| `outputs/<f>-dataset.roundtrip.json` | prova de RT |
| `inputs/` · `intermediates/` | fonte e dataset consumido |

## Resultado — bytes do wire INTEIRO, n=500

**RT 36/36**: as três formas de cada coluna decodam para o dado original.

| forma | tag | JSON | normal | flipA | Δ A | flipB | Δ B |
|---|---|---:|---:|---:|---:|---:|---:|
| hex | `s` | 5501 | 5718 | 4509 | **−1209** | 4509 | **−1209** |
| moeda | `s` | 6443 | 6233 | 5439 | **−794** | 5454 | **−779** |
| int-ruído | `n` | 3423 | 3930 | 3431 | **−499** | 3431 | **−499** |
| telefone | `s` | 9001 | 8251 | 7899 | **−352** | 7903 | **−348** |
| int-seq | `n` | 1891 | 39 | 37 | **−2** | 37 | **−2** |
| versão | `s` | 4645 | 4936 | 5057 | +121 | 5182 | +246 |
| data-BR | `s` | 6501 | 4912 | 5157 | +245 | 5198 | +286 |
| URL | `s` | 15388 | 6570 | 7190 | +620 | 7207 | +637 |
| `com-delim` | `s` | 5443 | 3715 | 4650 | +935 | 4936 | +1221 |
| email | `s` | 8943 | 5750 | 6714 | +964 | 7202 | +1452 |
| path | `s` | 12403 | 6326 | 7445 | +1119 | 7848 | +1522 |
| JSON-ish | `s` | 13947 | 5355 | 6807 | +1452 | 7297 | +1942 |

**flipA** ganha em 5 de 12 (soma **−2856 B**); **flipB** também em 5 (soma **−2837 B**).

O `min(normal, flipA, flipB)` por coluna nunca emite o pior — as linhas positivas são
descartadas, como já acontece no FLOOR do seq-RLE.

## A estimativa da 1ª rodada estava certa — faltava a evidência

Comparando o que eu havia estimado com o medido agora:

| forma | estimado | medido |
|---|---:|---:|
| hex | +1211 | −1209 |
| moeda | +796 | −794 |
| int-ruído | +500 | −499 |
| telefone | +354 | −352 |

Bate em **1–2 B** — exatamente o custo do cabeçalho, que a 1ª rodada não contabilizava. Ou
seja: o número não estava errado, mas **não havia como você conferir**, e a conta do
cabeçalho faltava. A crítica continua válida.

## Custo de cabeçalho (o que a 1ª rodada ignorou)

O flag de polaridade mora no char de **modo** (índice 7), que só existe **depois de uma tag**:

| tipo | hoje | com flag | custo |
|---|---|---|---:|
| número | `#TCF.8n` | `#TCF.8nf` | **+1 B** |
| string | `#TCF.8` (implícita) | `#TCF.8sf` | **+2 B** |

Flipar uma coluna de string **força torná-la explícita** — a tag `s`, que hoje o encoder nunca
emite, passaria a aparecer no wire. Consequência de desenho, e já somada na tabela acima.

## A × B: a diferença quase não existe

Nos vencedores, `flipA` e `flipB` dão **o mesmo número** (hex, int-ruído, int-seq: idênticos;
moeda e telefone diferem por 4–15 B). O motivo é estrutural: as colunas onde o flip ganha são
as que têm **poucas ou nenhuma referência**, e o delimitador só incide sobre referência.

Onde diferem de verdade (email +964 vs +1452, JSON-ish +1452 vs +1942) o flip **já perde** nas
duas formas — o `min()` descarta antes de a escolha importar.

> **Leitura**: `flipB`, que é o parser mais simples (toda referência tem terminador, sem
> decidir por contexto), custa quase nada a mais nos casos que interessam.

## O caso `com-delim`

Existe para exercitar o delimitador **aparecendo no dado**. Em FLIP o `;` vira estrutural e o
literal precisa de escape (`\;`). O RT dessa coluna é a prova de que o esquema aguenta o
próprio delimitador — e o **+935 B** mostra o preço quando o char escolhido é comum no dado,
que é o argumento para escolher um char raro.

## Limites

- **Protótipo**: os `.tcfp` não são decodáveis pelo `src/tcf` — o RT é validado des-flipando e
  chamando o `decode` real. Nada foi soldado.
- **Uma coluna, single-col.** Multi-col e `.8H` fora.
- **12 formas sintéticas**, escolhidas para cobrir chars e regimes — não é amostra de
  frequência real de uso.
- **O char `;` é placeholder.** Trocá-lo muda a linha `com-delim` e nada mais.

## Rodar

```
python run.py     # 12 formas × 3 wires + RT
```
`polaridade.py` tem as transformações e suas inversas (o lab exige `de_X(para_X(c)) == c`).
**Não toca `src/tcf`.**
