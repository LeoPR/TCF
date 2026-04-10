# TPC-H Scale Factor 0.01

Placeholder para o dataset TPC-H SF=0.01. O download e metadata completo
serao criados no ticket [04-T-datasets-tpch](../../../tickets/open/04-T-datasets-tpch.md).

## Origem

- **Nome:** TPC-H (Transaction Processing Performance Council — Decision Support)
- **Versao:** especificacao 3.0.1
- **Dominio:** wholesale retail / supply chain
- **Padrao:** usado como benchmark de OLAP desde 1999

## Licenca

TPC Fair Use Agreement — uso academico permitido sem restricao.
Ver [www.tpc.org](https://www.tpc.org/information/about/documentation.asp)
para o texto completo.

## Como baixar

```bash
pip install -e ".[datasets]"  # instala duckdb
python scripts/setup_tpch.py  # baixa para Z:\tcf-data\external\tpch-sf001\
```

## Tamanho (SF=0.01)

Estimativas (baseadas em DuckDB tpch extension):

| Tabela | Rows aproximadas | Tamanho CSV |
|--------|------------------|-------------|
| region | 5 | <1KB |
| nation | 25 | ~2KB |
| supplier | 100 | ~15KB |
| customer | 1.500 | ~220KB |
| part | 2.000 | ~250KB |
| partsupp | 8.000 | ~1.2MB |
| orders | 15.000 | ~1.8MB |
| lineitem | 60.000 | ~7MB |
| **Total** | ~87.000 | **~10MB** |

## Schema

Ver `metadata.json` nesta pasta para o schema completo com PK, FK
e tipos declarados.

**Resumo das relacoes:**

```
region (r_regionkey) <- nation (n_regionkey)
nation (n_nationkey) <- supplier, customer
part (p_partkey) <- partsupp, lineitem
supplier (s_suppkey) <- partsupp, lineitem
customer (c_custkey) <- orders
orders (o_orderkey) <- lineitem
```

## Referencias

- [TPC-H specification](https://www.tpc.org/tpch/)
- [DuckDB TPC-H extension](https://duckdb.org/docs/stable/core_extensions/tpch)
- [ClickHouse TPC-H example](https://clickhouse.com/docs/getting-started/example-datasets/tpch)
