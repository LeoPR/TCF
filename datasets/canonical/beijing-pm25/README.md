# Beijing PM2.5 — UCI ML Repository

Dataset cientifico canonical (sensor air quality) pra testar
**natureza #5 (range narrow)** + decimais cientificos.

## Source

- **Name**: Beijing PM2.5 Data
- **Origin**: UCI ML 381 (US Embassy Beijing, 2010-2014)
- **License**: CC BY 4.0
- **Citation**: Liang, X., et al. (2015). Assessing Beijing's PM2.5 pollution:
  severity, weather impact, APEC and winter heating. Proceedings of the
  Royal Society A, 471(2182), 20150257.
- **URL**: https://archive.ics.uci.edu/dataset/381/beijing+pm2+5+data

## Schema

13 colunas × ~43,824 rows (hourly observations 2010-2014):

| Column | Type | Notes |
|---|---|---|
| No | INT | Row number |
| year | INT | 2010-2014 |
| month | INT | 1-12 |
| day | INT | 1-31 |
| hour | INT | 0-23 |
| pm2.5 | FLOAT | PM2.5 concentration ug/m^3 (~5% NA) |
| DEWP | FLOAT | **Dew Point (range -40..28)** — #5 range narrow |
| TEMP | FLOAT | **Temperature C (range -19..42)** — #5 range narrow |
| PRES | FLOAT | **Pressure hPa (range 991..1046)** — #5 range MUITO narrow |
| cbwd | TEXT | Wind direction (NW/NE/SE/cv) — 4 categorias |
| Iws | FLOAT | Cumulated wind speed (m/s) |
| Is | INT | Cumulated hours of snow |
| Ir | INT | Cumulated hours of rain |

## Naturezas alvo

**Hipoteses a re-testar** (T-EXP-NATUREZAS-RARAS-V2 futuro):
- **#5 Range narrow EXTREMO**: PRES (991..1046, range 55 em escala 1000).
  Encoder "base 1000 + local 2 digitos" deveria dar 50%+ ganho.
- **DEWP/TEMP**: ranges -40..42, encoder signed-delta poderia comprimir.
- **#1 Incremento temporal**: year/month/day/hour sao sequenciais
  (mas TCF M10 ja' captura via auto-cadence + seq-RLE).

## How to download

```bash
pip install -e ".[datasets]"  # requer requests
python scripts/setup_beijing_pm25.py
python scripts/csv_to_sqlite.py
```

Saida:
- Raw: `Z:/tcf-data/external/beijing-pm25/beijing_pm25.csv` (~2MB)
- SQLite: `Z:/tcf-data/interim/beijing-pm25.db`
- Sample git: `datasets/samples/beijing-pm25/beijing-pm25-sample.csv`

## Conexoes

- [T-DATA-1](../../../tickets/T-DATA-1-datasets-financeiros-cientificos.md)
- [Reflexao naturezas numericas](../../../experiments/lab/dirty/notas/naturezas-numericas-2026-05-23.md)
