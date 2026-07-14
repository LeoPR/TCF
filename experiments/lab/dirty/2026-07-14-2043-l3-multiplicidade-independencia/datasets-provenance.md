# Proveniência das entradas

Sintéticas **geradas por parâmetro** (não há `inputs/` em arquivo — o gerador está em
`study.py::make(n_records, k_parents)`). Material de FORMA (crossover independência×bytes),
não medida de ganho.

- **Variável isolada**: `K` = nº de campos-pai (largura do registro), varrido em {1,2,4,8,16}.
- **Fixo**: 6 registros; array `telefones` com multiplicidade cíclica (2,1,3); valores de pai
  distintos por registro (`valor-J-do-registro-III`) para que a coluna-pai NÃO colapse por si
  (isola o efeito da multiplicidade, não da repetição de valor).
- **Viés declarado**: valores longos e distintos por registro favorecem medir o custo do `*N|`
  repetido na forma deduzida; largura pequena (K=1) é o pior caso para a explícita. Escolha
  proposital para expor o crossover. Tudo string (tipos = camada ortogonal).
