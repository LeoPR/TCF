# Dados de teste

```
nome, produto, quantidade, valor_unitario
João, Caneta, 10, 1.50
João, Caderno, 5, 3.00
Maria, Caneta, 10, 1.50
Maria, Caderno, 5, 3.00
Ana, Caderno, 5, 3.0
Maria, Lápis, 20, 0.50
Carlos, Caneta, 10, 1.50
Carlos, Caderno, 5, 3.0
Ana, Régua, 8, 2.00
Ana, Borracha, 15, 0.75
Carlos, Régua, 8, 2.00
João, Régua, 8, 2.00
```

## Cenário (para guiar as quebras)

UI quer mostrar **"o que cada pessoa comprou"** — uma linha por pessoa,
detalhes (produtos, quantidades, valores) abaixo.

## Observações neutras (sem decidir formato ainda)

- 12 linhas, 4 colunas
- 4 nomes distintos: João, Maria, Ana, Carlos
- 5 produtos distintos: Caneta, Caderno, Lápis, Régua, Borracha
- Cardinalidade: nome=4, produto=5, quantidade=5, valor_unitario=5
- Repetições por valor de coluna estão altas (boa candidata para RLE/dict)
- Inconsistência leve nos valores: `3.00` vs `3.0`, `2.00` aparece sempre — decidir
  se normaliza antes de comprimir, ou se isso é problema da camada acima
