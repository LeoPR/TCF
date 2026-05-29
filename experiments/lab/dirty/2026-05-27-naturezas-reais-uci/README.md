---
title: 2026-05-27 — Naturezas reais em datasets UCI + fechamento do limbo
type: dirty-lab
status: concluido
foco: reavaliar naturezas raras/Pacote 7 + B-tier nos UCI (T-DATA-1)
created: 2026-05-27
---

# Naturezas reais UCI + fechamento do limbo

## Contexto

Auditoria profunda (2026-05-27) revelou um "limbo": hipoteses propostas e
nunca concluidas. Owner escolheu fechar empiricamente o subconjunto
tratavel: naturezas raras / Pacote 7 (refutadas em Adult/TPC-H gerais) +
decisao B-tier (H-DA-01/06/10 marcadas "A-revalidar"). Bloqueador era
T-DATA-1 (datasets financeiro/cientifico) — resolvido no Sprint 1.

## Conteudo

- [`characterize.py`](characterize.py) — mede estrutura por coluna numerica
  (arredondamento, range, precisao, cardinalidade, ratio M10)
- [`proto_fallback.py`](proto_fallback.py) — prototipo fallback identity
  por coluna (fork, NAO toca src/tcf)
- [`result.md`](result.md) — conclusoes 4.1 + 4.2 + 4.3

## Conclusao resumida

1. **Naturezas raras NAO eram beco sem saida** — a estrutura (arredondamento
   `.0`/`.95`, range estreito, precisao fixa) EXISTE no financeiro/cientifico,
   ao contrario de Adult/TPC-H. A refutacao anterior foi em datasets errados.
2. **TCF tem ponto cego de baixa-cardinalidade** — colunas numericas curtas
   e repetitivas (hour 24 unicos) infla ate' 2.3x vs raw-sem-delimitador.
3. **Fallback identity** funciona (RT OK), ganho 0.8-10.2%, mas exige
   marcador novo no formato → v2.0 (nao v1.x, por ADR-0017).
4. **B-tier H-DA-01 (seq-RLE) CONFIRMADO** — nao e' marginal: economiza
   29.5% em beijing (sensores cadenced). Sai de "A-revalidar" pra A.

Decisao: limbo (fallback/dict/lossy) → roadmap v2.0 com evidencia empirica
([ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md)).
