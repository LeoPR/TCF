# Stress-test rodada 1 (apos M1.E e M1.C)

Datasets descartaveis em `data_extra/` rodados via
`run_lote_extra.py`. RT 20/20 OK em todas as 5 sintaxes.

## Matriz

| dataset | M1.A | M1.A' | M1.B | M1.E | M1.C |
|---|---:|---:|---:|---:|---:|
| DE1-adversarial-E | 53 | 53 | 63 | 53 | 53 |
| DE2-favoravel-E | 132 | 132 | 132 | **82** | **82** |
| DE3-adversarial-C | 101 | 100 | 100 | 96 | 96 |
| DE4-favoravel-C | 84 | 77 | 77 | 77 | **69** |

## Hipoteses (confirmadas)

### M1.E em DE2 — refs K=7 sequencial → ganho 38%

```
M1.A': 1,2,3,4,5,6,7x      (13 chars)
M1.E : 1..7x               ( 5 chars, -8)
```

Strings com 1-char-diff em N posicoes geram refs sequenciais longas.
M1.E corta 50 bytes (132 → 82). Confirma que o ganho do range cresce
linearmente com K.

### M1.E em DE1 — refs raras/curtas → ganho 0

```
M1.A: abc*\1   (= M1.E)
```

Refs K≤1. M1.E nao tem o que agrupar. Empata M1.A'. **Confirma**
que o ganho do range e' condicional ao dataset ter sequencias.

### M1.C em DE4 — literais puro-digit no inicio → ganho 10%

```
M1.E: \4*\2*abc            (eid=1, 9 chars)
M1.C: 4*2*abc              (eid=1, 7 chars, -2)

M1.E: \42*xyz              (eid=7, 8 chars)
M1.C: 42*xyz               (eid=7, 7 chars, -1)
```

Literal puro-digit como PRIMEIRO frag do no fonte (max_visivel=0) ou
como inicio de novo no nao-RLE. Encoder M1.C nao precisa de `*`
separador antes (nao tem prev). Suprime escape → 1 byte por caso.

**Validacao concreta do que [M1-C-sumida/README.md] previa
teoricamente** (secao "Quando M1.C ganharia").

### M1.C em DE3 — literais puro-digit apos ref → empate com E

Confirma a [regra de ouro do agrupamento](regra-de-agrupamento.md):
quando contexto nao tem separador natural, agrupar troca `\` por
`*` (empate).

### M1.B em DE1 — perde 10 bytes vs A/A'/E/C

DE1 tem dígito ambiguo em CADA bloco. M1.B emite `'X'` por bloco,
custo 2 chars de aspas. Confirma que quote em grupo perde quando
ha' muitos blocos pequenos com 1-digit-cada.

## O que ESCAPOU dos datasets canonicos D1-D4

**Nenhum dataset canonico tem strings que comecam com puro-digit
literal.** Todos comecam com letra (`joao`, `maria`, `api`, `[a`).
Por isso M1.C empata com M1.E nos canonicos.

**Implicacao**: a vitoria de M1.E sobre todos nos canonicos pode ser
parcialmente um artefato do desenho dos datasets (nao acionar a
condicao de M1.C). Nao invalida M1.E como vencedor — apenas qualifica
o regime.

## Linhas que poderiam ser adicionadas aos canonicos

Sugestao (a confirmar com user):

1. **D2** adicionar `42@yahoo.com` ou `103@hotmail.com` (literal
   puro-digit no inicio) — acionaria M1.C ganho.
2. **D4** adicionar `42*'X'@'a'` ou similar — variedade adicional.

Nao adicionar D5/D6. Manter datasets compactos.

## Decisao apos analise

- Datasets `data_extra/` ficam arquivados (nao deletar — pode ser
  reaberto na fechamento de M2/M3).
- **Resultado canonico (D1-D4) mantido como esta**: M1.E vence
  676 bytes, M1.C empata.
- Quando rodar M1.D, fazer nova rodada de stress-test (rodada-2)
  com datasets adversariais para M1.D especificamente.

## Memorizado

Padrao salvo em
[`feedback_stress_test_antes_de_fechar_micro`](memory) para repetir
em micros futuros.
