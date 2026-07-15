# Proveniência das entradas

Dado **REAL**, seleção **HONESTA** (não fatia arbitrária). Duas fontes reais:
- `Z:/tcf-data/interim/tpch-sf001.db` — TPC-H (o único hub do repo com grafo rico de ligações:
  8 tabelas, 9 FKs). Cadeia de contenção `customer→orders→lineitem` + ligações diversas (partsupp
  N:N, lineitem multi-pai).
- `Z:/tcf-data/interim/br-identidades.db` — BR real; FK `empresas.socio_cpf→pessoas.cpf` (N:N
  sócio↔empresa). 2ª fonte, domínio diferente.

## Seleção honesta (o ponto do owner)

Uma representação selecionada ≠ amostra do todo. Para não pegar "a fatia que funciona por sorte",
a amostragem usa o **Shaper** (`scripts/shaper/strategies/fk_preserving.py`):
- **Estratificação proporcional (Neyman)** na fact table (`customer`), por `c_mktsegment` e por
  `c_nationkey` — preserva a distribuição da população (métrica de representatividade TVD/JSD/χ² no trace).
- **Integridade referencial** preservada (dims filtradas em cascata).
- Varredura em **múltiplos estratos × volumes (0.1/0.3/0.6) × seeds (7/42/101)** — se o RT dependesse
  de uma fatia de sorte, falharia em ALGUM; passar em todos = evidência de que é **estrutural**.

## Coerção declarada (viés)

- Classe coberta = all-string (`str()` em folha). Tipos/`null`/ragged = camada ortogonal (pro fim).
- É estudo de **cobertura de população + fronteira** (contenção vs ligações diversas), não de ganho.
- **Pobreza de dados**: só TPC-H tem grafo rico; br-identidades tem 1 FK. Declarado como limite —
  ampliar a população (mais fontes ligadas reais OU Shaper gerando estruturas) fica registrado.
