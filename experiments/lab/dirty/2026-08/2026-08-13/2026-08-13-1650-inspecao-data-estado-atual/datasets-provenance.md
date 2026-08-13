# Proveniência dos dados

## Sintéticos (`a*`, `b*`, `c*`, `d*`, `e*`)

Gerados por `casos.py`, determinísticos (seeds fixas: 20260813 e 7), **materializados em
`inputs/<c>.entrada.json`** — sintético em lab também vira arquivo, senão não dá pra
conferir o que gerou o wire. Âncora comum: `2026-01-01`.

Viés declarado: são **ilustrativos**, escolhidos para tornar um mecanismo visível (passo
constante, ciclo de dia útil, passo irregular do calendário). Não representam distribuição
de dado real e **não sustentam conclusão de ganho** — para isso, os `f*`.

## Reais (`f*`) — corpus já extraído, não re-extraído aqui

12 colunas de data extraídas de `Z:/tcf-data/` pelo **EXP-017** (`extrai.py`), lidas deste
lab em `experiments/lab/clean/EXP-017-data-alvos-mensais/inputs/fontes/`. Este lab **não
baixa nada e não toca `Z:`** — se as fontes não estiverem no disco, os `f*` são pulados e o
resto roda.

| rótulo | origem | n | grafia observada |
|---|---|---:|---|
| `tpch-orderdate` / `-ord` | `db:tpch-sf001.db` | 3000 | `YYYY-MM-DD` |
| `tpch-shipdate` | `db:tpch-sf001.db` | 3000 | `YYYY-MM-DD` |
| `tpch-commitdate` | `db:tpch-sf001.db` | 3000 | `YYYY-MM-DD` |
| `tpch-receiptdate` | `db:tpch-sf001.db` | 3000 | `YYYY-MM-DD` |
| `tpch-sf01-orderdate` | TPC-H sf01 (offset 90000 — o dbgen é determinístico e sem offset a amostra saía byte-a-byte igual à sf001) | 3000 | `YYYY-MM-DD` |
| `br-data-cadastro` | br-identidades | 3000 | `YYYY-MM-DD` |
| `br-data-abertura` | br-identidades | 3000 | `YYYY-MM-DD` |
| `receita-data-inicio` / `-ord` | Receita Federal (CNPJ) | 3000 | **`YYYYMMDD`** (8 chars) |
| `retail-invoicedate` | online retail | 3000 | **`YYYY-MM-DD HH:MM:SS`** (19 chars) |
| `football-date` | resultados de partidas | 3000 | `YYYY-MM-DD` |

Anonimização: as colunas são **datas**, não identificadores pessoais — não há CPF/CNPJ nos
inputs deste lab. (A coluna da Receita é a *data de início de atividade*, não o CNPJ.)

Viés: 5 das 12 são TPC-H (mesma família sintética de benchmark, mesmo gerador); duas são a
mesma coluna em versão natural e ordenada. Colunas **distintas** de origem independente:
**10** — TPC-H (5), br-identidades (2), Receita (1), retail (1), football (1). Ao ler
proporções, contar isso.
