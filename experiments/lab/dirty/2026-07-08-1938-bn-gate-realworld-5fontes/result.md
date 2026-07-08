# Resultado — gate real-world do bN (D3) [probatório]

Números: `artifacts/` (`python3 run.py`). Baseline = **produção real** (`min(tcf,raw,v2b,split)`,
fallback=True). 8 fontes reais distintas (inclui beijing-pm25, o ponto cego do ADR-0018). Nível-tabela
weighted, pré e pós-brotli q11. RT-OK em toda coluna bN. Tabelas grandes a LIMIT=20000 (declarado).

## Weighted por fonte + agregado (`02-tabela-weighted.txt`)

| fonte | pré-brotli % | pós-brotli % |
|---|---|---|
| wine | 29.3 | 7.1 |
| adult | 26.1 | 3.1 |
| online-retail | 15.2 | 5.9 |
| tpch.lineitem | 8.8 | 1.4 |
| beijing-pm25 | 7.1 | 0.7 |
| ibge.municipios | 4.1 | 0.8 |
| receita.estab | 2.2 | 0.1 |
| br.pessoas | 0.0 | 0.0 |
| **WEIGHTED (8 fontes)** | **8.8** | **1.7** |

## Veredito (do número, gate CLAUDE.md ponto-5 = ≥5% weighted)

- **Terminal (pré-brotli)**: **8.8% ≥ 5% → PASSA** (N=8). bN vale como TCF terminal.
- **Re-comprimido (pós-brotli)**: **1.7% < 5% → NÃO passa** (colapsa; confirma H-TYPE-03).

## Achados que qualificam o número

1. **Concentrado** (0–29%): alto em categorical-heavy (wine/adult/retail), zero em high-card (br.pessoas).
2. **Nicho estreito**: bN compete com **tcf-RLE** também. Em beijing, `year`/`month`/`day`/`hour` (cadenciados)
   a produção resolve com tcf-RLE (`year`=34B vs bN 5020B) → bN **perde**. bN só vence low-card **categórico
   sem estrutura** (cbwd 4×). O ponto cego do ADR-0018 já não é cego na produção atual.

## Status de H-TYPE-02 (atualizar)

- **terminal**: `confirmada-empírica` (8.8% weighted, N=8), `confiança: Média` — condicionado a uso terminal
  + concentrado por composição da tabela.
- **re-comprimido**: `refutada-real-world` (1.7%).
- **weld**: gated por **H-TYPE-03** (owner: terminal é representativo?) + aprovação src/tcf + byte-canonical.
