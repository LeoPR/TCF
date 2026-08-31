# Pesquisa 2026-04-10: Datasets Canonicos para Tabular Reasoning

Documento de referencia completo. Registra TODOS os datasets pesquisados,
mesmo os que nao vamos usar inicialmente. A escolha inicial e TPC-H + Adult,
mas os outros ficam como **backlog documentado** para:

1. Validar robustez em dominios diferentes (expansao futura)
2. Comparar com literatura que usa outros datasets
3. Ter alternativas caso TPC-H ou Adult tenham limitacoes

---

## 1. Datasets academicos para Table QA

Tabelas pequenas (tipicamente 10-50 rows), frequentemente de Wikipedia,
com perguntas curadas por humanos. Padrao em papers de LLM+Table.

### 1.1 WikiTableQuestions (WTQ)

- **Autores:** Pasupat & Liang, 2015 (Stanford)
- **Origem:** Wikipedia HTML tables
- **Tamanho:** 2.108 tabelas, 22.033 perguntas
- **Tipo:** Perguntas em linguagem natural, respostas textuais
- **Perguntas:** comparacao, agregacao, aritmetica, ordenacao
- **Usado por:** TabLLM, Sui 2024, TableBench, TReB, quase todo paper de Table QA
- **Licenca:** CC BY-SA (Wikipedia)
- **Link:** https://ppasupat.github.io/WikiTableQuestions/
- **Forca:** padrao de comparacao com literatura
- **Fraqueza:** tabelas pequenas, estrutura HTML pode ter quirks (merged cells, units in cells)

### 1.2 TabFact

- **Autores:** Chen et al., 2020
- **Origem:** Wikipedia tables
- **Tamanho:** ~16K tabelas, ~118K declaracoes
- **Tipo:** Verificacao de fato (true/false)
- **Usado por:** Table Meets LLM (Sui 2024), varios papers de factuality
- **Link:** https://tabfact.github.io/
- **Forca:** tarefa binaria mais simples de scoring
- **Fraqueza:** nao testa agregacao numerica (nosso foco)

### 1.3 SQA (Sequential Question Answering)

- **Autores:** Iyyer et al., 2017 (Microsoft Research)
- **Origem:** Wikipedia tables + sequencias de perguntas
- **Tamanho:** 6K sequencias, 17K perguntas
- **Tipo:** Multi-turn QA (perguntas dependentes do contexto anterior)
- **Forca:** testa raciocinio multi-step
- **Fraqueza:** complexidade de avaliacao multi-turn

### 1.4 TableBench

- **Autores:** Wu et al., 2024 (arxiv 2408.09174)
- **Tamanho:** 886 perguntas complexas
- **Tipo:** 18 sub-categorias (fact verification, numerical reasoning,
  data analysis, visualization, etc)
- **Forca:** benchmark moderno, bem categorizado
- **Link:** https://tablebench.github.io/
- **Fraqueza:** pequeno, pode saturar rapido

### 1.5 TReB (2025)

- **Autores:** 2025 (arxiv 2506.18421)
- **Foco:** Avaliacao abrangente de table reasoning em LLMs
- **Relevancia:** benchmark muito recente, pode ser referencia futura

### 1.6 HiTab

- **Origem:** Microsoft Research, 2022
- **Foco:** Tabelas hierarquicas, relatorios financeiros
- **Forca:** testa estruturas aninhadas
- **Fraqueza:** nicho (hierarquico)

### 1.7 RealTableBench

- **Origem:** 2024-2025
- **Foco:** Tabelas reais de analytics empresarial
- **Status:** recente, explorar para v2

### 1.8 FeTaQA

- **Origem:** 2022, tabelas free-form
- **Tipo:** Respostas longas em linguagem natural
- **Relevancia:** para futuro trabalho em geracao de texto

---

## 2. Benchmarks de banco de dados (OLAP / analytics)

Padrao da industria ha decadas. Schemas relacionais reais com FK/PK/tipos.
**Parametrizaveis** por scale factor.

### 2.1 TPC-H *** PRIORIDADE MAXIMA ***

- **Autor:** TPC (Transaction Processing Performance Council), 1999
- **Dominio:** Wholesale retail, decision support
- **Schema:** 8 tabelas em 3NF
  - `region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`
- **Relacionamentos:** FK entre todas as tabelas, PK definidas
- **Tipos:** INT, DECIMAL, DATE, CHAR, VARCHAR
- **Escalas:** 1GB → 100TB (parametrizavel com `-s SF`)
- **Para nosso uso:**
  - SF=0.001 → ~6 rows region, 25 nations, 100 suppliers, 1500 customers, 6000 orders
  - SF=0.01 → 10x maior
  - SF=0.1 → 100x maior
  - SF=1 → 150K customers, 1.5M orders, 6M lineitems
- **Como gerar:**
  - Gerador oficial `dbgen` (C, precisa compilar)
  - DuckDB tem nativo: `INSTALL tpch; LOAD tpch; CALL dbgen(sf=0.01)`
  - Snowflake, Databricks, ClickHouse tambem tem
- **Link:** https://www.tpc.org/tpch/
- **Licenca:** TPC Fair Use Agreement (uso academico permitido)
- **Forca:** padrao da industria, tipos reais, relacoes reais, escalavel
- **Fraqueza:** schema fixo (retail), nao e Wikipedia

### 2.2 TPC-DS

- **Autor:** TPC, 2005+
- **Dominio:** Retail multi-canal (store, web, catalog)
- **Schema:** 24 tabelas (7 fact + 17 dimension)
- **Escalas:** 1GB → 100TB
- **Para nosso uso:** mais complexo que TPC-H, possivelmente excessivo para v1
- **Link:** https://www.tpc.org/tpcds/
- **Relevancia:** versao maior e mais moderna do TPC-H

### 2.3 SSB (Star Schema Benchmark)

- **Autor:** O'Neil et al., 2009
- **Schema:** 4 tabelas em star schema simples
- **Origem:** simplificacao do TPC-H para OLAP
- **Relevancia:** mais simples que TPC-H, podemos considerar como alternativa leve

### 2.4 Join Order Benchmark (JOB)

- **Autor:** Leis et al., 2015
- **Dados:** IMDB real (filmes, atores)
- **Foco:** complexidade de joins
- **Forca:** dados reais (nao sinteticos)
- **Fraqueza:** bases grandes, requer download do IMDB

---

## 3. Datasets reais de machine learning (classificacao/regressao)

Tabelas flat (sem FK), mas **dados reais** com outliers, missing values,
comportamento estatistico de producao.

### 3.1 Adult (Census Income) *** PRIORIDADE MAXIMA ***

- **Origem:** US Census Bureau, 1994 (UCI ML Repository)
- **Tamanho:** 48.842 rows, 14 colunas
- **Colunas:**
  - age (int), workclass (categorical), fnlwgt (int), education (categorical),
  - education-num (int), marital-status (cat), occupation (cat), relationship (cat),
  - race (cat), sex (binary), capital-gain (int), capital-loss (int),
  - hours-per-week (int), native-country (cat), **income** (target: >50K/<=50K)
- **Tipos:** mix de int, categorical, binary
- **Missing values:** sim (` ?` em algumas celulas — precisa tratar)
- **Usado por:** centenas de papers de classificacao e fairness
- **Como obter:**
  - `sklearn.datasets.fetch_openml("adult", version=2)`
  - `https://archive.ics.uci.edu/ml/datasets/adult`
  - `https://www.openml.org/d/1590`
- **Licenca:** CC BY 4.0
- **Forca:** dados demograficos reais, mixed types, missing values naturais
- **Fraqueza:** tabela flat (sem FK), binary target (classificacao, nao QA)

### 3.2 California Housing

- **Origem:** Pace & Barry, 1997 (Sci. Res. Letters)
- **Tamanho:** 20.640 rows, 9 colunas
- **Colunas:** MedInc, HouseAge, AveRooms, AveBedrms, Population,
  AveOccup, Latitude, Longitude, MedHouseVal (target)
- **Tipos:** todas float
- **Como obter:** `sklearn.datasets.fetch_california_housing()`
- **Forca:** dados geograficos reais, so numericos (agregacoes limpas)
- **Fraqueza:** sem FK, sem strings, muito homogeneo

### 3.3 Titanic

- **Origem:** Kaggle (challenge publico)
- **Tamanho:** 891 rows (train) + 418 rows (test), 12 colunas
- **Colunas:** PassengerId, Survived, Pclass, Name, Sex, Age, SibSp,
  Parch, Ticket, Fare, Cabin, Embarked
- **Tipos:** int, float, string, bool
- **Missing values:** sim (Age, Cabin, Embarked)
- **Forca:** dados semi-reais, mixed types, NaN comum, pequeno o suficiente
- **Fraqueza:** muito pequeno, overfit de benchmark (todo mundo ja viu)

### 3.4 Diamonds

- **Origem:** ggplot2 R package
- **Tamanho:** 53.940 rows, 10 colunas
- **Colunas:** carat (float), cut (ord cat), color (cat), clarity (cat),
  depth (float), table (float), price (int), x/y/z (float)
- **Tipos:** mix float + categorical ordinal
- **Forca:** categorias ordinais (D > E > F), outliers, agregaveis
- **Fraqueza:** dominio especifico (joias)

### 3.5 NYC Taxi Trips

- **Origem:** NYC OpenData
- **Tamanho:** MILHOES de rows (1 mes = ~10M)
- **Colunas:** pickup_datetime, dropoff_datetime, lat/lon, passenger_count,
  trip_distance, fare_amount, tip_amount, payment_type
- **Tipos:** timestamps, geo coords, numericos grandes
- **Forca:** escala enorme, tipos ricos, real-time feel
- **Fraqueza:** requer download grande, rows demais para LLM direto

### 3.6 OpenML Datasets (agregador)

- **Origem:** openml.org
- **Acesso:** `sklearn.datasets.fetch_openml(name="...", version=...)`
- **Cobertura:** milhares de datasets reais
- **Usados frequentes:**
  - `credit-g` (1000 rows, credit scoring)
  - `diabetes` (768 rows, Pima Indian diabetes)
  - `wine` (178 rows, wine classification)
  - `heart` (303 rows, heart disease)
- **Relevancia:** nos permite diversificar rapidamente via API

---

## 4. Datasets publicos adicionais

### 4.1 Kaggle Datasets

- **Origem:** kaggle.com/datasets
- **Volume:** milhares, qualidade variavel
- **Exemplos classicos:** House Prices, Titanic, Iris
- **Forca:** comunidade ativa, baselines publicos
- **Fraqueza:** qualidade variavel, curagem necessaria

### 4.2 Data.gov (US Government)

- **Origem:** datasets do governo americano
- **Exemplos:** Census, BLS, BTS, NOAA
- **Forca:** dados oficiais, grande volume
- **Fraqueza:** formato heterogeneo, muita limpeza necessaria

### 4.3 GitHub Awesome Lists

- `awesome-public-datasets` — 500+ datasets por categoria
- `awesome-llm-tabular` — datasets especificos para LLM+tabular
- Relevancia: index para descoberta

---

## 5. Sinteticos gerados por codigo

### 5.1 dbgen (TPC-H oficial)

- **Linguagem:** C
- **Saida:** arquivos .tbl (pipe-delimited)
- **Tamanho:** parametrizado por scale factor
- **Forca:** oficial, reproduzivel
- **Fraqueza:** precisa compilar, producao de arquivos .tbl (nao CSV)

### 5.2 Faker (Python)

- **Pacote:** `pip install Faker`
- **Saida:** gera dados sinteticos realistas (nomes, enderecos, datas)
- **Uso:** gerar dados customizados com tipos realistas
- **Forca:** flexivel, multi-idioma
- **Fraqueza:** nao e benchmark padrao, qualidade depende do uso

### 5.3 Nosso retail_sales (poor-reference)

- **Localizacao:** `tests/fixtures/synthetic_v2.py`
- **Problema:** dados minimalistas (Ana, Bruno, Caneta)
- **Decisao:** **mover para `datasets/poor-reference/`** e deixar claro
  que e apenas para comparacao com papers que usam exemplos pobres
- **Uso futuro:** baseline "qual o minimo de dados para ver o efeito X?"

---

## 6. Criterios de selecao para fase 1

Criterios para entrar em `datasets/canonical/`:

1. **Origem consagrada:** TPC, UCI, OpenML, Kaggle top-100
2. **Referencia em literatura:** usado por pelo menos 10+ papers
3. **Tipos ricos:** ao menos 3 tipos {int, float, string, date, bool}
4. **Tamanho controlavel:** consegue gerar versoes pequenas
5. **Licenca:** uso academico explicitamente permitido
6. **Ground truth:** respostas verificaveis programaticamente

### Escolha para fase 1 (ordem de prioridade)

1. **TPC-H SF=0.01** (`datasets/canonical/tpch-sf001/`)
   - Cobre: relacional, FK/PK, tipos declarados, escalavel, padrao industria
   - Tamanho em SF=0.01: ~60K lineitems, 15K orders, 1.5K customers (controlado)

2. **Adult (Census Income)** (`datasets/canonical/adult-census/`)
   - Cobre: dados reais, mixed types, missing values, flat table
   - Tamanho: 48K rows (pode amostrar)

Decidido em 2026-04-10. Outros datasets ficam como **backlog** neste
documento para expansao futura.

---

## 7. Como obter cada dataset (comandos concretos)

### TPC-H via DuckDB (recomendado)

```bash
pip install duckdb
python -c "
import duckdb
con = duckdb.connect(':memory:')
con.execute('INSTALL tpch; LOAD tpch;')
con.execute('CALL dbgen(sf=0.01)')  # 0.01 = ~10MB total
for table in ['region','nation','supplier','customer','part','partsupp','orders','lineitem']:
    con.execute(f'COPY {table} TO \"datasets/canonical/tpch-sf001/{table}.csv\" (HEADER, DELIMITER \",\")')
con.close()
"
```

DuckDB e a forma mais limpa. Alternativa e compilar `dbgen` oficial em C.

### Adult via sklearn

```bash
pip install scikit-learn pandas
python -c "
from sklearn.datasets import fetch_openml
import pandas as pd

data = fetch_openml('adult', version=2, as_frame=True)
df = data.frame
df.to_csv('datasets/canonical/adult-census/adult.csv', index=False)
print(f'Downloaded {len(df)} rows, {len(df.columns)} columns')
"
```

### Alternativas (futuro)

```python
# California Housing
from sklearn.datasets import fetch_california_housing
ca = fetch_california_housing(as_frame=True)

# Titanic (via openml)
titanic = fetch_openml('titanic', version=1, as_frame=True)

# Diamonds (via seaborn)
import seaborn as sns
diamonds = sns.load_dataset('diamonds')

# Credit-g
credit = fetch_openml('credit-g', version=1, as_frame=True)
```

---

## 8. Dependencias sugeridas

Para processar os datasets, adicionar como **opcionais** no pyproject.toml:

```toml
[project.optional-dependencies]
datasets = [
    "duckdb>=1.0",       # para TPC-H generation
    "scikit-learn>=1.3", # para fetch_openml
    "pandas>=2.0",       # para manipulacao
]
```

Instalacao: `pip install -e .[datasets]`

Core do TCF continua zero-deps.

---

## 9. Referencias

### Benchmarks de banco de dados
- [TPC Benchmarks Home](https://www.tpc.org/)
- [TPC-H Specification](https://www.tpc.org/tpch/)
- [TPC-DS Specification](https://www.tpc.org/tpcds/)
- [DuckDB TPC-H extension](https://duckdb.org/docs/stable/core_extensions/tpch)
- [ClickHouse TPC-H example](https://clickhouse.com/docs/getting-started/example-datasets/tpch)

### Table QA benchmarks
- [WikiTableQuestions](https://ppasupat.github.io/WikiTableQuestions/)
- [TabFact](https://tabfact.github.io/)
- [TableBench](https://tablebench.github.io/)
- [Awesome-LLM-Tabular](https://github.com/johnnyhwu/Awesome-LLM-Tabular)
- [TReB paper (arxiv 2506.18421)](https://arxiv.org/abs/2506.18421)
- [TableBench paper (arxiv 2408.09174)](https://arxiv.org/abs/2408.09174)
- [Sui et al. 2024 Table Meets LLM](https://arxiv.org/abs/2305.13062)

### ML datasets
- [UCI ML Repository](https://archive.ics.uci.edu/)
- [OpenML](https://www.openml.org/)
- [sklearn fetch_openml docs](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_openml.html)

### Publicos
- [Kaggle Datasets](https://www.kaggle.com/datasets)
- [Data.gov](https://www.data.gov/)
- [awesome-public-datasets](https://github.com/awesomedata/awesome-public-datasets)

---

## 10. Nota de escopo

Este documento lista **~20 datasets**. Para fase 1, so vamos usar **2**
(TPC-H + Adult). Os outros ficam registrados aqui para:

- Referencia futura (expansao do paper)
- Comparacao com literatura (citar "outros benchmarks foram considerados")
- Documentacao de decisoes (por que escolhemos estes dois)
- Validacao externa eventual (se reviewer pedir)

**Nao apagar este arquivo.** Ele e o registro da pesquisa completa.
