# 2026-07-08-2355 — F3: misto seletivo (bN-w≤4 como candidato do min)

**Hipótese**: [H-TYPE-07](../notas/roadmap-hipoteses.md) fluxo F3 · nota
[bn-dict-perspectivas](../notas/bn-dict-perspectivas-e-dict-interno.md). F3 = o terceiro fluxo do bN: NÃO
pula o núcleo (isso é F1), roda a produção inteira e ADICIONA bN como candidato do `min()` por-coluna,
**restrito a w≤4 (k≤16)** — o subconjunto byte-tileável honesto (só 1/2/4 bits empacotam >1 valor/byte).
Refina o D3 (que ia até w=8). NÃO toca `src/tcf`.

## Estado

- **era**: F3 proposto como "roda o núcleo, aplica bN só em k≤16 / ≤4 bits — gate mais estrito que o D3".
- **é**: medido o ganho MARGINAL de `min(prod, bN-w≤4)` vs produção `min(tcf,raw,v2b,split)`, em 8 fontes
  reais (weighted), pré e pós-brotli, com o domínio do bN **idêntico ao v2b** (troca só o radix do índice:
  base-94 → bits). **F3 (w≤4) = 5.9% terminal · 0.5% pós-brotli. wide (w≤8) = 8.8% terminal (= D3).**
- **será**: byte-safe TERMINAL por construção; o valor (como F1) é terminal/streaming, não byte re-comprimido.
  Weld gated (owner + src/tcf) — e o número não justifica welding por byte.

## Resultado

- **Terminal weighted 5.9%** (byte-SAFE só no terminal: `min()` garante F3 ≤ prod em bytes terminais).
- **Pós-brotli weighted 0.5%** e **NÃO é byte-safe**: `receita` vai **net-negativo −0.2%** (+469 B) — bits
  densos comprimem pior que o stream base-94 repetitivo do v2b. Não é "colapsa a zero", é "pode piorar".
- **Decomposição** (`03`): o ganho de bit-packing sub-byte real mora em **w≤4** (w=1: 1.32%, w=2: 1.21%,
  w=4: 3.32%). O extra até w=8 (2.9 p.p., k **95..256**) NÃO é bit-packing — 8 bits = 1 byte exato; só
  vence v2b porque v2b usa 2 chars/índice p/ k>94. F3 corretamente o descarta.
- **Por fonte**: adult 26.1%/2.9% · tpch 7.1%/0.5% · beijing 7.1%/0.7% · receita 2.2%/−0.2% · wine 2.0%/0.5%
  · br.pessoas / ibge / online-retail = 0% (suas vitórias de bN são todas w=8, fora do gate F3).

## Verificação adversarial (workflow 4 lentes, `f3-verify`)

Rodei 4 verificadores independentes (faithfulness / correção-RT / brotli-safety / decomposição) tentando
REFUTAR. Núcleo dos números **CONFIRMADO** (somas conferem: 217358 B = 5.85% → 5.9%; 325600 B = 8.76% →
8.8%; wide = D3). Correções aplicadas: (1) byte-safety re-escopada a TERMINAL (pós-brotli pode ir negativo);
(2) rótulo w=8 corrigido — "8 bits=1 byte, vence v2b p/ k 95..256", não "bN=v2b"; (3) "cross-check D3" →
"reprodução do método D3"; (4) notas: comparação corpo-only omite ~1 B/coluna do discriminador de modo
(~20 B, desprezível) e a referência v2b do bN usa min_len=None (isolamento do radix aproximado, conservador).

## Arquivos

- `bn_f3.py` — codec: reusa o domínio do v2b + índices bit-packed; `width_f3` (w≤4) / `width_wide` (w≤8).
- `run.py` — mede min(prod,bN) terminal + pós-brotli, decompõe por w. **`python3 run.py`** (lento, ~8 min:
  8× encode de produção em tabelas de 20k linhas). `run.log` = progresso.
- `artifacts/` — `00-resumo` · `01-por-coluna` · `02-tabela-weighted` · `03-decomposicao-w`.

## Escopo

Dirty. NÃO toca `src/tcf`. Tabelas grandes amostradas a LIMIT=20000 (declarado). Casa com D3 (colapso
pós-brotli) e F1 (o valor do bN é latência/terminal, não byte re-comprimido).
