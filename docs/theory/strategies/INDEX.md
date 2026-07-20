---
title: Strategies map (segmented index)
type: reference
---

# Strategies map — indice

> Mapa de estrategias TCF v1.0 segmentado por subsistema pra facilitar
> analise/codificacao/compilacao independente. Origem unificada (1
> arquivo): [../strategies-map.md](../strategies-map.md) (preservado).

## Camadas do pipeline

| Arquivo | Subsistema | Estrategias |
|---|---|---|
| [00-prepass-filtros.md](00-prepass-filtros.md) | CAMADA 0 — Pre-pass (filtros, heuristicas) | 14 |
| [01-obat.md](01-obat.md) | CAMADA 1 — OBAT (tokenizacao bidir LCP+LCS) | 20 |
| [02-hcc-core.md](02-hcc-core.md) | CAMADA 2 — HCC core (M8.A composicional) | 24 |
| [03-hcc-seqrle.md](03-hcc-seqrle.md) | CAMADA 2b — HCC seq-RLE + multi-delta | 14 |
| [04-naturezas.md](04-naturezas.md) | CAMADA 0-pre — Naturezas (CPF/CNPJ/IP) | 19 |
| [05-dispatch-formato.md](05-dispatch-formato.md) | Dispatch + multi-col + formato + PipelineConfig | 27 |
| [99-cross-cutting.md](99-cross-cutting.md) | Tabelas cruzadas (knobs + extension points) | — |

**Total**: 118 estrategias mapeadas (auditoria workflow 2026-05-27).

## Para que esta segmentacao serve

- **Analise independente** por subsistema (cada camada pode ser estudada/
  refatorada/compilada em separado)
- **Codificacao guiada** por arquivo: quando atacar uma camada, leia apenas
  o arquivo correspondente (10-30KB cada vs 153KB monolitico)
- **Preparacao pra compilacao**: cada subsistema tem extension points
  proprios — compilacao Cython/Rust pode ser por camada
- **Preparacao pra HCC binarizacao futura** (post-disk/streaming work):
  CAMADA 2 (HCC core + seq-RLE) e' candidata natural pra binarizacao
  como otimizacao de IO/transport, **sem alterar a semantica textual
  observavel** do formato

## Filosofia de design (registrada em AGENTS.md)

- **Texto + explicabilidade** enquanto comprimido (RLE `*N|linha` mostra
  N items sem expansao — agrupamento natural)
- **Speed-first** dentro do espaco textual, NAO competir com compressores
  binarios (zstd/brotli) — eles ocupam areas cinzas, TCF ocupa areas
  explicaveis
- HCC binarizacao planejada (futuro) e' **transport optimization** pra
  IO/disco/web, NAO um competidor de compressao binaria
