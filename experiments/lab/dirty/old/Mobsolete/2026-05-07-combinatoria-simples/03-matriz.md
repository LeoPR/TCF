# Matriz combinatória — qual compressão × qual quebra testar

Linhas: hipóteses de compressão (C1–C9 de `01-compressao.md`)
Colunas: hipóteses de quebra (B1–B6 de `02-quebra.md`)

Marcar com `X` as combinações que valem teste de mesa.
Marcar com `—` as que claramente não fazem sentido.
Deixar em branco as duvidosas (decidir depois).

|        | B1 mono | B2 N-linhas | B3 coluna | B4 grupo | B5 tier | B6 híbrido |
|--------|---------|-------------|-----------|----------|---------|------------|
| **C1** row literal     |   |   |   |   |   |   |
| **C2** col literal     |   |   |   |   |   |   |
| **C3** col + RLE local |   |   |   |   |   |   |
| **C4** col + sort nome + RLE |   |   |   |   |   |   |
| **C5** col + sort produto + RLE |   |   |   |   |   |   |
| **C6** col + group produto + RLE |   |   |   |   |   |   |
| **C7** col + sort valor + RLE |   |   |   |   |   |   |
| **C8** col + dict |   |   |   |   |   |   |
| **C9** sort+RLE+dict |   |   |   |   |   |   |

---

## Combinações que provavelmente são interessantes (palpite inicial)

- C3 × B4 (RLE local + chunk por nome): testa se a ordem original já agrupa o
  suficiente para RLE ser útil dentro de cada grupo
- C4 × B6 (sort nome + RLE, depois quebra híbrida): RLE eficaz no nome (vira
  `3*João` etc.), depois quebra por pessoa para entrega prioritária
- C5 × B4 (sort produto + RLE, chunks por nome): conflito interessante —
  sortear por produto, mas quebrar por nome. RLE perde força dentro do chunk.
- C2 × B3 (col literal + por coluna): cada coluna vira um chunk independente,
  sem nenhuma compressão — útil para medir overhead puro de quebra
- C1 × B1 (row literal + monolítico): baseline absoluto, é o CSV cru

## Combinações que provavelmente não fazem sentido

- C1 × B3 (row-major + por coluna): contradição — row-major não tem coluna
  isolada
- Qualquer C × B2 com N=1 (chunks de 1 linha): degenera em row-major sem
  compressão útil

---

## Métricas para anotar em cada combinação preenchida

| Métrica | O que mede |
|---|---|
| `bytes_total` | soma dos chunks |
| `bytes_overhead` | bytes_total - bytes_da_compressão_sem_quebra |
| `bytes_first_useful` | bytes do primeiro chunk útil para renderizar algo |
| `chunks_indep` | quantos chunks decodificam sozinhos |
| `rle_preservado` | RLE sobreviveu à quebra? (sim/parcial/não) |
| `comentário` | observação livre |

---

## Roteiro do teste de mesa (sugestão)

1. Começar pela coluna B1 (monolítico) preenchendo C1, C2, C3, C4 — só para
   sentir as compressões sozinhas.
2. Depois fixar a melhor compressão e variar a quebra (B1 → B6).
3. Por último, escolher 2-3 combinações cruzadas que parecem interessantes e
   preencher.

Não é para preencher os 54 casos. É para preencher uns 8-12 e sentir o terreno.
