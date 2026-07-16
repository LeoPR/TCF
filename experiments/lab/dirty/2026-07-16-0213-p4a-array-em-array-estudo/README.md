# Lab 2026-07-16-0213 — ESTUDO P4a: array-em-array via COUNT RECURSIVO

**Status**: estudo PARA INSPEÇÃO DO OWNER — nada weldado. **Fontes**:
[p4-levantamento + parecer](../notas/p4-replevel-nroots-levantamento.md) ·
[checkpoint 2026-07-16](../notas/checkpoints/2026-07-16-revisao-p2-p4.md) (o gate daqui é o de lá) ·
[T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P4a).

**Tese** (levantamento + parecer do owner): o repetition-level colapsa em **counts por nível** —
elemento-de-array reusa o mecanismo count→elementos recursivamente. A estrutura (contagens por
nível) fica **legível sem materializar as folhas** (princípio O(1)/stream/view do Ciclo 4).

## A gramática que o estudo demonstra (o item a inspecionar)

Cada `#` abre um nível de array; `?` após o `#` do nível = element-mask DAQUELE nível:

| construto | meta demonstrado |
|---|---|
| `[[1,2],[3]]` | `m#[#[]n]` |
| profundidade 3 | `cubo#[#[#[]n]]` |
| array de arrays de objetos | `turmas#[#[nome]]` |
| **null ENTRE arrays** `[[1],null,[2]]` | `m#?[#[]n]` — P3b no nível EXTERNO |
| **null no inner** `[[1,null,2],[3]]` | `m#[#?[]n]` — P3b no nível INTERNO |
| **compose total** `[[1,null,2],null,[3]]` + typed | `m#?[#?[]n],rotulo,okb` |

→ Confirma o refinamento da análise crítica: **null-entre-arrays = P3b∘P4a** (element-mask por
nível), NÃO precisa de gramática nova nem é P5. No weld, os sizes entram como hoje
(`m#:c0?:e0[#:c1?:e1[]:asize n`).

## Resultado (rodar `python study.py`) — [outputs/00-resultado.txt](outputs/00-resultado.txt)

| etapa | resultado |
|---|---|
| **Didático** (12 formas = o gate do checkpoint: matriz, prof>2, inner-vazios, arr-de-arr-de-objetos, null externo/interno, compose, tipos, campo no meio) | **RT 12/12** |
| **Fuzz de profundidade** (seedado, níveis 1–4, ~20% null/nível, n/b/s) | **4000/4000** |
| **Adversarial de frame** (count interno truncado/excedente, folha faltando/sobrando) | fail-loud 4/4, nunca silencioso |

## Colunas (modelo, no proto)

`(p,'count',0) [, (p,'emask',0)], (p,'count',1) [, (p,'emask',1)], …, folhas` — counts do nível k+1
têm 1 entrada por elemento NÃO-null do nível k (denso, consistente com P3b).

## O que fica pro WELD (após inspeção/aprovação)

Port pro core (`hierarchical.py`): spec de ELEMENTO recursiva no nó de array (hoje `arr_scalars`/
`arr_objects` são casos fixos; viram `elemento ∈ {scalar, object, array}`); parser do meta por nível;
gate padrão (didático→realista→massa + suíte + flat byte-canônico + auditoria adversarial). É a
mudança estrutural MAIOR até agora no módulo (recursão de spec) — por isso estudo-primeiro.
Ver [result.md](result.md). Zero mudança em `src/tcf` neste lab.
