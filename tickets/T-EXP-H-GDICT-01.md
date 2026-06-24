---
title: T-EXP-H-GDICT-01 — Caracterizar cross-dict / dicionário global (B1 do plano 0.8)
status: in-progress
priority: P2
created: 2026-06-21
updated: 2026-06-21
related:
  - experiments/lab/dirty/2026-06-21-gdict-caracterizacao/
  - experiments/lab/dirty/notas/v08-plano-etapas.md
  - experiments/lab/dirty/notas/dict-referencia-hipoteses.md
  - experiments/lab/dirty/notas/rle-familia-estudo.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# T-EXP-H-GDICT-01 (B1 do plano 0.8)

## Contexto / motivação

Hipótese do owner: **dicionário global no header** — 1 tabela de únicos cross-column
no header + stream de índices globais por coluna. Distinto de V2-B (`@dict`
per-column), de V2-RLE-STREAM (CLOSED) e de H-CODEBOOK-01 (dict externo). O argumento:
colunas que **compartilham valores** (enums, UF, SIM/NÃO, códigos) pagariam uma tabela
de únicos só uma vez. Caracterização **conceitual** pronta (3 docs cross-linkados);
**execução read-only pendente**.

## Pergunta

O cross-dict global paga **vs o `@dict` per-column atual (V2-B)** — em bytes E/OU em
estrutura (leitura única do header pelo lazy)?

## Plano (lab read-only, NÃO toca src/tcf)

Lab `experiments/lab/dirty/2026-06-21-gdict-caracterizacao/`:
1. Fixar straw-man de índice global (H-REF-02 mínimo; reusar largura base-94).
2. Medir, por blob multi-col em **≥5 reais** (adult, tpch, receita, br-identidades,
   ibge), o NET: tabela única cross-column + índice global mais largo − soma das
   tabelas `@dict` per-column. Computar Jaccard/overlap **intra-blob**.
3. **3 braços do gate**: (a) textual-puro, (b) **sob brotli**, (c) latência/leitura-única
   no lazy (`tcf.view`).
4. Preencher checklist anti-incidente 2026-05-21 (real-world, N≥5, sintético vs real,
   bytes absolutos ≥5% RW).

## Critério de aceite (gate de weld — para B2+)

- **≥15% weighted em 2+ reais** OU justificativa **estrutural** (latência/leitura-única
  no lazy, já que o payoff pode não ser só bytes).
- Se falhar o gate → cross-dict **sai do 0.8**, vira 0.9/estudo (como V2-RLE-STREAM).

## Riscos / notas

- Risco honesto (auditoria 2026-06-21): o sharing forte (UF, município) é em boa parte
  **cross-TABELA** (br-identidades pessoas vs empresas), não intra-tabela; `encode()`
  opera sobre **1 blob**, então o caso feliz pode exigir cenário multi-tabela que não é
  o uso padrão. Intra-tabela observado só parcial (lineitem `{O,F}`).
- Precedente: V2-RLE-STREAM (mesma família) deu +1,19% textual mas −1,39% sob brotli →
  CLOSED-INSUFFICIENT-GAIN. Medir sob brotli é obrigatório.
- Read-only, roda em **paralelo** ao A; NÃO bloqueia o release do lazy (ADR-0024
  desacopla pacote 0.8.0 de formato #TCF.8). B2/B3/B4 dependem deste veredito.
- **Decisão do owner (2026-06-21)**: B1 SEGURADO até A4 fechar (foco no workstream A
  primeiro). A4 fechou — pode iniciar quando o owner liberar.

## Updates

- **2026-06-21**: aberto. Segurado por decisão do owner até A4 (feito).
- **2026-06-21 (B1.0 design)**: owner liberou + levantou 3 tensões (paralelismo↔sincronismo,
  custo do dict no header, namespace de índice cross-coluna). Lab
  [`2026-06-21-gdict-caracterizacao/`](../experiments/lab/dirty/2026-06-21-gdict-caracterizacao/),
  medição sintética. **Achado**: net = dedup_tabela − índice_global_mais_largo; dobradiça = limite
  base-94. Proposta modo híbrido (V2, dicts por grupo). 3 tensões resolvidas (header-only / custo é
  largura / namespace por grupo).
- **2026-06-21 (B1 reais — Etapa 1/2)**: overlap intra-blob ~0 nos 5 canônicos (colunas categóricas
  = domínios disjuntos). Sharing forte é CROSS-TABELA (uf/municipio). Quase fechei como
  CLOSED-INSUFFICIENT-GAIN.
- **2026-06-21 (CORREÇÃO metodológica do owner)**: brotli NÃO é critério de exclusão — nem sempre é
  aplicado E é incompatível com lazy (não dá query seletiva sobre blob comprimido); medir TCF-nativo.
  Ver [[gzip-e-compressao-externa-sao-intuicao-nao-parte-do-tcf]].
- **2026-06-21 (B1 Etapa 4 — TCF-nativo, SEM brotli)**: **VEREDITO INVERTIDO**. Cross-dict GANHA no
  regime **same-domain-refs** (−19.2% textual sintético + lazy 1× decode). Perde em disjunto/partial →
  híbrido V2 evita. **NÃO FECHAR.**
- **2026-06-21 (B1 Etapa 5 — GATE em DADO REAL, owner aprovou add datasets)**: 2 reais same-domain-ref
  (raw em Z:, [provenance](../experiments/lab/dirty/2026-06-21-gdict-caracterizacao/datasets-provenance.md)):
  **SNAP ca-GrQc** (grafo from/to, Jaccard 1.0) **−19.3% textual** (cruza 15% com só 2 colunas);
  **OpenFlights** (airport src/dest IATA −4.6%; ids −6.6%, Jaccard ~0.99). Lazy cross-col ("tudo que
  toca o nó/aeroporto X") ganha o mesmo % + lê o dict **1× em vez de 2×**. Ganho escala com K/N e nº de
  colunas same-domain. **B1 PASSA** (gate de bytes em 1; estrutural/lazy em todos; brotli fora do gate).
  → **recomendação: ir pro B2** (design #TCF.8 opt-in + híbrido V2 + ADR + GATE). Escopo 0.8 vs 0.9: owner.
