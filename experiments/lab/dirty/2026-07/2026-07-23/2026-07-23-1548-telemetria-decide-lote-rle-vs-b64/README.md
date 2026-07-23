# 2026-07-23-1548 — Telemetria decide o modo POR LOTE (RLE vs base64)

Micro-lab EXPERIMENTAL (viabilidade). Reformulação do owner: os vetores (memória/cpu/latência) já
existem; o que muda é a **forma como o TCF compõe o arquivo**. O pipeline HOJE já escolhe o modo
vencedor **por coluna** (`emitted_mode` ∈ tcf/raw/dict/split) a partir de bytes *"contados no
processo, não no fim"* ([side_outputs.py:62-67](../../../../../src/tcf/side_outputs.py#L62-L67), zero
passada extra). Hipótese: a **mesma telemetria** pode decidir **por lote** — quais lotes viram RLE e
quais viram base64 — e lotes independentes são a base pra liberar/paralelizar por estágio.

Continua: [decisão passe-único `1533`](../2026-07-23-1533-decisao-rle-vs-denso-passe-unico/) ·
[modo denso/marcador `0345`](../../../notas/2026-07/2026-07-23-0345-modo-denso-marcador-binarizacao.md).

## Medição JUSTA (corpo-vs-corpo)

O framing genérico (`magic + S + n`) é igual pra toda composição e fica de fora; compara-se o **corpo**.
O manifesto `RDDR` (o registro da decisão por lote) É custo intrínseco do batch-dyn e entra. `Δ vs best`
< 0 = o dinâmico-por-lote bate o melhor modo único da coluna.

## Evidência (ver `result.md`, 6/6 RT + passe único ✅)

| regime | resultado |
|---|---|
| **heterogêneo grande** (`blocky-big` n=2048) | batch-dyn/128 = 264 vs melhor-único 344 → **Δ −80 (−23%)** |
| **heterogêneo médio** (`half-half` n=256) | batch-dyn/128 = 33 vs 44 → **Δ −11 (−25%)** |
| **heterogêneo pequeno** (`blocky` n=256) | +8 — manifesto não se paga em n pequeno |
| **homogêneo** (`runny`/`noisy`/`alt`) | modo único vence (+8) — por-lote não ajuda |

**Leitura**: o dinâmico-por-lote ganha **quando os regimes diferem E n amortiza o manifesto**. O `S`
vencedor foi sempre o maior (128) — menos overhead, e ainda separa os blocos de 128. Ou seja a
**granularidade (S, e lote-vs-coluna) é ela mesma uma escolha de telemetria**, não um valor fixo.

## O que isto valida (e o que NÃO)

- ✅ A decisão por lote sai **só da telemetria** (run-count do scan + tamanho por fórmula) — os
  "custos de qualquer forma"; materializa só o vencedor. **Passe único** preservado (`reads/n==1.0`).
- ✅ **Ganho real** em dados heterogêneos (−23% a −25% no corpo).
- ✅ Lotes são **unidades independentes** (encoda/decoda sozinhas) → base pra streaming/paralelismo.
- ⚠️ **Não é ganho universal**: homogêneo/pequeno → modo único vence. A granularidade tem que casar
  com a estrutura dos dados; escolher S mal perde.
- ⚠️ Só bool `w=1`, dados sintéticos pequenos. Generalização (bN, n real) = hipótese seguinte.
- ❌ Nada aqui é gate pra soldar — é sinal de VIABILIDADE e de ONDE (passo O(runs) por lote logo após
  o scan, reusando a telemetria, no ponto da seleção como o `emitted_mode` já faz).

## Como rodar

```
python run.py     # 6 casos × 3 lotes · esperado 0 falhas (RT + passe único)
```

## Layout

`inputs/<caso>.json` · `outputs/<caso>.bd<S>.tcfp` (corpo do batch-dyn por lote) · `result.md`.
Protótipos lab-local — NÃO tocam `src/tcf`.
