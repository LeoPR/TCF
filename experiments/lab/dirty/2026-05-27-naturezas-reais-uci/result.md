# Result — naturezas reais UCI + fechamento do limbo (2026-05-27)

## 4.1 Caracterizacao (characterize.py)

Colunas numericas dos 3 datasets UCI, medidas: rounding, range, precisao,
cardinalidade, ratio M10 (vs raw SEM delimitador).

### Estrutura encontrada (≠ Adult/TPC-H)

| Coluna | dataset | padrao | M10 |
|---|---|---|---|
| free_sulfur_dioxide | wine | precisao fixa 1 casa, decimal sempre `.0` (99%) | 97.1% |
| total_sulfur_dioxide | wine | idem `.0` | 96.8% |
| UnitPrice | retail | terminacoes `.95`(18%)/`.25`(10%)/`.65`(8%) | 83.3% |
| CustomerID | retail | 100% `.0`, precisao fixa | 9.0% |
| DEWP/TEMP/PRES | beijing | range estreito ([-40,28],[991,1046]) | 56-175% |

A estrutura-alvo das naturezas raras (#5 range, #8 arredondamento) e do
Pacote 7 (H-LR-* lossy float) EXISTE aqui — confirmando que a refutacao
anterior (Adult/TPC-H) foi por dataset inadequado, nao por hipotese errada.

### Ponto cego de baixa-cardinalidade

Colunas com M10 > 100% (TCF infla vs raw-sem-delimitador):

| Coluna | unicos | M10 ratio |
|---|---|---|
| beijing hour | 24 | 228.8% |
| retail Quantity | 156 | 213.1% |
| beijing TEMP | 64 | 174.5% |
| beijing DEWP | 69 | 127.7% |
| wine residual_sugar | 316 | 124.5% |
| wine fixed_acidity | 106 | 121.3% |

Causa (ablacao PipelineConfig): toggles (seq_rle/pre_pass/shape) NAO mudam
(228.8% vs 228.9%). E' o nucleo OBAT+HCC: pra valores curtos, o marcador
de referencia custa mais que repetir. TCF nao tem encoder dicionario.

## 4.2 Prototipo fallback identity (proto_fallback.py)

"Se TCF de uma coluna > raw, guarda raw." Marcador `!name` na meta line.

| Dataset | M10 | Fallback | Ganho | Cols→raw |
|---|---|---|---|---|
| wine-quality | 300.483B | 298.006B | 0.8% | 1/13 |
| beijing-pm25 | 1.001.749B | 899.753B | **10.2%** | 3/13 |
| online-retail-50k | 975.675B | 955.856B | 2.0% | 1/8 |

RT OK em todos.

### Reframe do baseline

O ">100%" da caracterizacao era vs raw SEM delimitador. Baseline justo =
raw+newlines. Com isso, TCF so' perde nas colunas patologicas (hour,
Quantity, TEMP, pm2.5). Ex: DEWP tcf=117466 < raw+nl=135826 → fallback
mantem TCF (correto).

### Conflito com freeze v1 (CRITICO)

Verificado: body raw NAO decodifica com decoder atual (`_decode_column`
lanca KeyError — "1" vira ref a string id 1). Logo fallback EXIGE marcador
novo → por ADR-0017, e' #TCF.7 + v2.0 (breaking), nao cabe em v1.x.

Mesma conclusao vale pra dicionario e lossy: todos exigem mudanca de
formato → todos sao v2.0.

## 4.3 Decisao B-tier (ablacao seq-RLE full multi-col)

| Dataset | seqRLE on | off | diff se removido |
|---|---|---|---|
| wine | 300.483B | 300.469B | -0.00% (neutro) |
| beijing | 1.001.749B | 1.297.647B | **+29.54%** (seq-RLE economiza muito) |
| retail50k | 975.675B | 978.407B | +0.28% |

**H-DA-01 (seq-RLE) CONFIRMADO** — nao e' marginal. Em sensores cadenced
(beijing) economiza 29.5%. A "1.36% real-world" da audit era so' Adult/TPC-H.
Revalidado em dado independente → confianca A-revalidar → **A**.

- H-DA-06: subsumida em H-DA-09b-v2 (ja confirmada). Sem acao.
- H-DA-10 (min_len): confirmada 9.92% real-world. Mantida.

Todos os B-tier "A-revalidar" → resolvidos (confirmados, manter welded).

## Conclusao geral

O limbo "naturezas/Pacote 7" deixa de ser limbo:
- Estrutura-alvo confirmada nos UCI (nao era beco sem saida)
- Ponto cego baixa-card identificado (novo achado)
- Fallback prototipado: 0.8-10.2%, RT OK, mas v2.0 (format change)
- Dicionario + lossy: idem v2.0

→ Roadmap v2.0 fundamentado em [ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md).
B-tier resolvido (seq-RLE confirmado forte em sensores).
