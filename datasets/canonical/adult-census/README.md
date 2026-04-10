# Adult (Census Income) — UCI ML Repository

Placeholder para o dataset Adult. O download e metadata completo
serao criados no ticket [05-T-datasets-adult](../../../tickets/open/05-T-datasets-adult.md).

## Origem

- **Nome:** Adult (tambem conhecido como "Census Income")
- **Origem:** US Census Bureau, 1994
- **Curadores:** Ronny Kohavi e Barry Becker (Silicon Graphics)
- **Disponibilizado por:** UCI Machine Learning Repository
- **Via:** OpenML (id=1590)

## Licenca

CC BY 4.0 — Creative Commons Attribution 4.0 International
Uso academico e comercial permitido com atribuicao.

## Como baixar

```bash
pip install -e ".[datasets]"  # instala scikit-learn
python scripts/setup_adult.py  # baixa para Z:\tcf-data\external\adult-census\
```

## Tamanho

- **Rows:** 48.842 (train + test combinados)
- **Colunas:** 14 features + 1 target
- **Tamanho CSV:** ~5MB
- **Missing values:** sim (representados como `?` em 3 colunas)

## Colunas

| # | Nome | Tipo | Descricao |
|---|------|------|-----------|
| 1 | age | int | Idade |
| 2 | workclass | category | Tipo de emprego (nullable) |
| 3 | fnlwgt | int | Peso amostral do Census |
| 4 | education | category | Nivel educacional |
| 5 | education-num | int | Anos de educacao |
| 6 | marital-status | category | Estado civil |
| 7 | occupation | category | Ocupacao (nullable) |
| 8 | relationship | category | Relacao familiar |
| 9 | race | category | Raca declarada |
| 10 | sex | binary | Male/Female |
| 11 | capital-gain | int | Ganho de capital anual |
| 12 | capital-loss | int | Perda de capital anual |
| 13 | hours-per-week | int | Horas trabalhadas por semana |
| 14 | native-country | category | Pais de origem (nullable) |
| 15 | **class** | binary | Target: `>50K` ou `<=50K` |

## Por que este dataset

- **Real:** dados demograficos reais dos EUA (nao sintetico)
- **Padrao academico:** usado em centenas de papers de classificacao e fairness
- **Mixed types:** int, category, binary — testa multiplos tipos
- **Missing values naturais:** `?` em workclass, occupation, native-country
- **Tamanho:** 48K rows e realista para benchmarks sem ser excessivo

## Citacao

Becker, Barry and Kohavi, Ronny (1996). Adult. UCI Machine Learning
Repository. https://doi.org/10.24432/C5XW20

## Referencias

- [UCI ML Repository](https://archive.ics.uci.edu/dataset/2/adult)
- [OpenML dataset 1590](https://www.openml.org/d/1590)
- [scikit-learn fetch_openml docs](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_openml.html)
