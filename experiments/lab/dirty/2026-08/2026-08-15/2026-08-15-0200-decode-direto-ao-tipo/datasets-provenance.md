# Procedência dos dados — e o viés declarado

## Inteiramente sintético

Três colunas de datas diárias em progressão (`2024-01-01` + i dias), geradas em `run.py`,
determinísticas, sem `random`. O caso `diaria-com-literal` planta **uma** não-canônica
(`2024-9-7`) na posição 250 — para exibir a união `date|str` na saída, não para estimar
frequência.

## Viés, declarado

- **Progressão diária é o melhor caso do spec** (o seq-RLE esmaga o ordinal) — escolhida de
  propósito para o wire ser pequeno e a medição isolar a CONVERSÃO, não a descompressão do
  corpo. Numa coluna irregular o decode gasta mais no corpo e a economia percentual da
  conversão **dilui**.
- **A medição de tempo é dev-run** (melhor-de-5, máquina não quiescente). O −5,9% do caso
  n=200 está dentro do ruído e é tratado como tal no `result.md`.
- O protótipo usa `wire_id` próprio (`dtobj`) porque o registry tem precedência na resolução
  do header — é **veículo de lab**. O desenho real (kwarg de saída) manteria o wire `:dt`
  byte-idêntico; essa equivalência **não foi medida aqui** porque exigiria tocar `src/tcf`.
