---
title: T-DATA-1 — Datasets financeiros/cientificos canonicos (Online Retail, Beijing PM2.5, Wine Quality)
status: open
priority: P3
created: 2026-05-23
updated: 2026-05-23
blocked-by: []
related:
  - tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md
  - tickets/T-EXP-PACOTE5-T03-ENUMERATED.md
  - experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md
  - scripts/setup_adult.py
  - scripts/setup_tpch.py
---

# T-DATA-1 — Datasets financeiros/cientificos canonicos

## Contexto / motivacao

Refutacoes T-EXP-NATUREZAS-RARAS (#5 range, #8 arredondamento) e
T-EXP-PACOTE5-T03-ENUMERATED concluiram que padroes nao aparecem em
volume significativo em Adult + TPC-H (datasets "general purpose").

Padroes financeiros REAIS (precos R$X.99, taxas %.5) precisariam
dataset financeiro real-world. Padroes cientificos (sensor decimais,
features quimicas) idem.

Owner escolheu 3 datasets publicos UCI/OpenML pra adicionar como
canonicos:
- **Online Retail** (UCI 352): ~500k transacoes com preços GBP
  (.99/.95/.50 patterns)
- **Beijing PM2.5** (UCI 381): ~50k registros sensor (decimais cientificos)
- **Wine Quality** (UCI 186): ~6k amostras (features quimicas decimais)

## Plano

Padrao similar a `setup_adult.py` / `setup_tpch.py`:

1. **Scripts setup**: `scripts/setup_{name}.py` — baixa dataset, escreve
   CSV em `Z:/tcf-data/external/{name}/`, gera SQLite hub em
   `Z:/tcf-data/interim/{name}.db` via `csv_to_sqlite.py`
2. **Metadata + READMEs**: `datasets/canonical/{name}/`:
   - `metadata.json` (schema, source, license, row counts)
   - `README.md` (descricao, columns, casos de uso)
3. **Test integration**: futuro — `test_shaper.py` ja' generico,
   funciona com qualquer SQLite hub
4. **Re-test naturezas raras**: T-EXP-NATUREZAS-RARAS-V2 com novos
   datasets — esperar achar padroes #5/#8 que Adult+TPC-H nao tinha

## Implementacao desta sessao

- Scripts setup criados (NAO rodados — owner roda quando quiser)
- READMEs criados em datasets/canonical/{name}/
- Documentacao em STATUS.md

**Download dos datasets adiado pra owner** (1-50MB cada, requer
internet + Z:/tcf-data/ writable).

## Datasets

### Online Retail (UCI 352)

- **URL**: archive.ics.uci.edu/dataset/352/online+retail
- **Size**: ~45MB CSV
- **Rows**: 541,909
- **Columns**: InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
  UnitPrice (DECIMAL), CustomerID, Country
- **Naturezas alvo**: UnitPrice tem padrao .99/.95/.50 (#8 arredondamento)
- **License**: CC BY 4.0 (UCI)
- **Citation**: Chen, D. (2015). Online Retail Data Set. UCI ML.

### Beijing PM2.5 (UCI 381)

- **URL**: archive.ics.uci.edu/dataset/381/beijing+pm2+5+data
- **Size**: ~2MB CSV
- **Rows**: ~43,824
- **Columns**: No, year, month, day, hour, pm2.5 (DECIMAL), DEWP (DECIMAL),
  TEMP (DECIMAL), PRES (DECIMAL), cbwd, Iws, Is, Ir
- **Naturezas alvo**: DEWP/TEMP/PRES range narrow + decimais cientificos
- **License**: CC BY 4.0 (UCI)
- **Citation**: Liang, X. et al. (2015). Assessing Beijing's PM2.5 pollution.

### Wine Quality (UCI 186)

- **URL**: archive.ics.uci.edu/dataset/186/wine+quality
- **Size**: ~100KB CSV (red + white separados)
- **Rows**: 1,599 (red) + 4,898 (white) = 6,497 total
- **Columns**: 11 features quimicas decimais + quality (int 0-10)
  (fixed_acidity, volatile_acidity, citric_acid, residual_sugar,
   chlorides, free_sulfur_dioxide, total_sulfur_dioxide, density,
   pH, sulphates, alcohol)
- **Naturezas alvo**: decimais com precisao fixa, range narrow
- **License**: CC BY 4.0 (UCI)
- **Citation**: Cortez, P. et al. (2009). Modeling wine preferences.
- **Disponivel via**: sklearn.datasets.fetch_openml (id=40691 red,
  id=40692 white) OR UCI direct

## Criterio de aceite

- [ ] `scripts/setup_online_retail.py` criado
- [ ] `scripts/setup_beijing_pm25.py` criado
- [ ] `scripts/setup_wine_quality.py` criado
- [ ] `datasets/canonical/{name}/README.md` + `metadata.json` (3)
- [ ] Owner roda scripts localmente (post-sessao) e valida SQLite hubs
- [ ] Futuro: T-EXP-NATUREZAS-RARAS-V2 re-testa #5/#8 com novos datasets

## Riscos

1. **URLs UCI mudam**: scripts usam URLs hard-coded. Mitigacao: tentar
   sklearn fetch_openml primeiro (mais estavel), fallback requests UCI.
2. **Datasets requerem auth (Kaggle)**: NAO usar Kaggle nesta lista
   (todos UCI/OpenML, sem auth).
3. **Tamanho Online Retail (~45MB)**: cabe em Z:/tcf-data/external/
   facilmente.
4. **Encoding**: Online Retail UCI tem char encoding inconsistente
   (Latin-1 em alguns), scripts precisam tratar.

## Conexoes

- T-EXP-NATUREZAS-RARAS (refutada em datasets gerais — esperar achar
  padroes nos financeiros/cientificos)
- T-EXP-PACOTE5-T03-ENUMERATED (idem)
- Reflexao naturezas numericas
- scripts/setup_adult.py / setup_tpch.py — padroes existentes

## Updates datados

### 2026-05-23 — abertura + scripts criados

Ticket criado. Scripts setup criados nesta sessao (sem rodar download).
Owner pode rodar localmente:
```bash
pip install -e ".[datasets]"
python scripts/setup_wine_quality.py     # 100KB, rapido
python scripts/setup_beijing_pm25.py     # 2MB
python scripts/setup_online_retail.py    # 45MB
python scripts/csv_to_sqlite.py          # gera SQLite hubs
```

Apos SQLite hubs criados, T-EXP-NATUREZAS-RARAS-V2 pode re-testar
hipoteses #5/#8 com dados reais financeiros/cientificos.
