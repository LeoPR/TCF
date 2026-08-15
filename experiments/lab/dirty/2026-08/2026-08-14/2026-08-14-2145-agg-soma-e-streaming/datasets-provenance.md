# Procedência dos dados — e o viés declarado

## Sintético (`rateio`)

`[100/3]×3 + [1000/7]×7`, arredondados a 6 casas antes de entrar. Gravado em
`inputs/rateio.entrada.json` com `.fonte.json` ao lado.

**Viés, deliberado**: são dízimas cujo total é redondo (1100,00 exatos). É o **melhor caso
possível** para qualquer método que preserve soma — foi construído para exibir o mecanismo, não
para estimar ganho. Um rateio real tem menos regularidade.

## Real (`retail-d1`, `retail-d0`)

`Z:/tcf-data/interim/online-retail.db`, `online_retail.UnitPrice`, filtro `> 0`. Amostra por
passo espalhado (`v[::passo]`), alvo 2000. Nunca `LIMIT` puro. **Não versionado**; o lab roda
sem `Z:`, ficando só com o sintético.

Duas precisões: `d=1` (o primeiro corte real, já que a coluna tem ≤2 casas) e `d=0` (limite
absurdo para preço, presente como **extremo**, não como opção).

**Viés, declarado:**

- **Uma fonte só**, varejo britânico. A distribuição de preços (concentrada em valores baixos,
  cauda até ~800) afeta diretamente o erro relativo e a quantidade de resíduo a redistribuir.
- **A ordem das linhas importa para a difusão de erro** e não importa para o maior resto. Aqui
  a ordem é a do `rowid` amostrado — se o dado chegasse ordenado por valor, a difusão se
  comportaria diferente. **Não medi essa sensibilidade**; é uma lacuna declarada, e seria o
  próximo caso adversarial a rodar.
- Nada aqui é gate real-world: 1 coluna de 1 fonte. Qualquer weld lossy exige N≥5 mais decisão
  explícita do owner.
