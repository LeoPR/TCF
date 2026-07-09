# 2026-07-08-1938 — GATE real-world do bN vs produção (D3, H-TYPE-02)

**Ticket/hipótese**: [H-TYPE-02](../notas/roadmap-hipoteses.md) · [H-TYPE-03](../notas/roadmap-hipoteses.md) ·
nota [tipos-como-specs](../notas/tipos-como-specs.md) · T-OPT-INFERENCE item 2. Frente **D3** da reconciliação
(o gate que tira H-TYPE-02 do "A-revalidar"). NÃO toca `src/tcf`.

> **Nome do dir diz "5fontes"** = o plano original (gate CLAUDE.md pede ≥5); a medição final rodou **8
> fontes**. Não renomear (history); o N verdadeiro é 8. Qualificação posterior do 8.8%: só 5.9% é
> bit-packing sub-byte w≤4 — ver [F3](../2026-07-08-2355-f3-bn-seletivo/result.md).

## Estado

- **era**: bN medido em 3 DBs (N<5) contra baseline errado (single-col); H-TYPE-02 `confirmada-empírica COM
  RESSALVA, A-revalidar`.
- **é**: bN vs **produção real** (`min(tcf,raw,v2b,split)`, fallback=True) em **8 fontes reais distintas**
  (inclui beijing-pm25, o ponto cego do ADR-0018), no **nível-tabela weighted**, pré e pós-brotli. RT-OK em
  toda coluna aplicável.
- **resultado**: weighted agregado **8.8% pré-brotli / 1.7% pós-brotli**. Terminal PASSA o gate (≥5%);
  re-comprimido NÃO.
- **será**: H-TYPE-02 atualizada; o weld continua gated por H-TYPE-03 (decisão de produto do owner: uso
  terminal é representativo?).

## Método

Pra cada fonte: encoda a tabela UMA vez (`fallback=True` = produção real); **extrai** o body por-coluna do
meta (não re-encoda); pra cada coluna low-card (k≤256) computa o body bN (domínio+índices) e substitui **se
vence** o body de produção. Weighted % = Σ economia / bytes-tabela-produção. Pós-brotli: brotli-q11 dos dois
lados. Tabelas grandes amostradas a LIMIT=20000 (declarado). `python3 run.py` (precisa brotli).

## Resultado (`artifacts/02-tabela-weighted.txt`)

| fonte | N | pré % | pós % |
|---|---|---|---|
| adult | 20000 | 26.1% | 3.1% |
| wine | 6497 | 29.3% | 7.1% |
| online-retail | 20000 | 15.2% | 5.9% |
| tpch.lineitem | 20000 | 8.8% | 1.4% |
| beijing-pm25 | 20000 | 7.1% | 0.7% |
| ibge.municipios | 5571 | 4.1% | 0.8% |
| receita.estab | 20000 | 2.2% | 0.1% |
| br.pessoas | 20000 | 0.0% | 0.0% |
| **WEIGHTED** | | **8.8%** | **1.7%** |

## Achados honestos

1. **Terminal passa, re-comprimido não**: 8.8% ≥ 5% (gate) só sem brotli a jusante; 1.7% com brotli.
   Confirma H-TYPE-03 no nível-corpus.
2. **Muito concentrado** (0-29%): alto em categorical-heavy (adult/wine/retail), ~0 em high-card (br.pessoas
   = nome/cpf/email, nenhuma coluna bN). O ganho depende da composição da tabela.
3. **O nicho do bN é mais estreito que "low-card"**: em beijing, `hour`/`month`/`day`/`year` a produção já
   resolve com **tcf-RLE** (year=34B vs bN 5020B!) porque são cadenciados/ordenados → bN **perde**. bN só
   vence em low-card **categórico sem estrutura explorável** (cbwd 4×). Compete com tcf-RLE E com v2b.
4. **O ponto cego do ADR-0018 (hour, 228.8% inflação) já não é cego** na produção atual (V2-B + cadence).

## Veredito → status de H-TYPE-02

- **Terminal (sem re-compressão)**: `confirmada-empírica` — 8.8% weighted, N=8 fontes reais, passa o gate
  ponto-5. `confiança: Média` (concentrado + condicionado a terminal).
- **Re-comprimido (brotli a jusante)**: `refutada-real-world` — 1.7%, colapsa.
- **Weld**: continua gated por **H-TYPE-03** (uso terminal é representativo? decisão do owner) + aprovação
  src/tcf + gate byte-canonical. O número não muda isso; só firma que terminal vale 8.8%, re-comprimido não.

## Limites

- Amostra LIMIT=20000 (tabelas grandes); pré-brotli usa bytes extraídos (header pequeno desprezado).
  Índices bN re-derivados de vals (Formato A usaria o ref-stream do HCC). Uma tabela principal por fonte.
