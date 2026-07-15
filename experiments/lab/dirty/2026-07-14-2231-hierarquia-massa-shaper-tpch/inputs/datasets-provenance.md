# Proveniência das entradas

Dado **REAL**, não sintético. Fonte: hub `Z:/tcf-data/interim/tpch-sf001.db` (TPC-H scale
factor 0.01, canônico do projeto — ver `datasets/canonical/tpch-sf001/`). Não committado no repo
(dado real vive em Z:, como os demais canônicos); `build.py` lê direto do hub.

## Como o dataset hierárquico é montado (o "shaper montando pra gente")

O shaper (`scripts/shaper/strategies/join.py`) ACHATA tabelas normalizadas via JOIN pela FK. Aqui
fazemos o **INVERSO**: pegamos as tabelas normalizadas e **aninhamos** pela mesma FK declarada em
`metadata.json`:

- `customer` (pk `c_custkey`) ← `orders` (fk `o_custkey`) ← `lineitem` (fk `l_orderkey`).
- Forma 1: `customer → [pedidos] → [itens]` (1:N em 2 níveis). 1500 docs.
- Forma 2: `orders → [itens]` (1:N, 1 nível, pai diferente). 15000 docs.

Volumes reais: customer 1500 · orders 15000 · lineitem 60175. Até 32 pedidos/cliente, 7 itens/pedido.

## Coerção declarada (viés)

- **Classe coberta = all-string**: `str()` em TODA folha ANTES do encode (input == decode output →
  RT byte-exato). Tipos (float/date) e `null` são **camada ortogonal**, deixados pro FIM (decisão do
  owner). Não há ragged (schema uniforme por tabela). Chaves sem null (verificado).
- É teste de **CAPACIDADE + robustez de topologia** em massa (a hierarquia representa o dado real
  aninhado e faz RT), não de ganho de compressão.
