---
title: Join strategy — normalized vs flat
type: task
status: OPEN
priority: 20
parent: 12-M-dataset-shaper
---

# Join Level

`scripts/shaper/strategies/join.py`

## Modos

- `normalized` (default): tabelas separadas com FKs. Consumidor decide como juntar.
- `flat`: JOIN completo em uma supertabela desnormalizada.

## Flat mode

Para TPC-H schema=chain: JOIN customer + orders + lineitem via FKs:

```sql
SELECT c.c_name, o.o_orderdate, o.o_totalprice,
       l.l_quantity, l.l_extendedprice, l.l_shipdate
FROM lineitem l
JOIN orders o ON l.l_orderkey = o.o_orderkey
JOIN customer c ON o.o_custkey = c.c_custkey
```

Resultado: 1 tabela flat com colunas de todas as tabelas. IDs removidos, nomes resolvidos.

Para Adult: flat == normalized (1 tabela, sem join a fazer).

## Como o join e feito

O shaper le os FKs do `metadata.json` e gera o SQL adequado.
Executa via `DatasetReader.query()` — o JOIN e feito pelo SQLite.

## Tarefas

- [ ] Implementar JoinStrategy
- [ ] Ler FKs do metadata para construir JOIN SQL
- [ ] Registrar no pipeline (apos schema, antes de compressibility)
- [ ] Testes: normalized retorna tabelas separadas
- [ ] Testes: flat retorna 1 tabela com colunas de todas
- [ ] Testes: flat em Adult nao muda nada (1 tabela)
- [ ] Testes: flat em TPC-H chain gera supertabela
- [ ] Verificar contagem: flat rows == lineitem rows (mais externo)
