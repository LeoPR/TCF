# 2026-07-06-2246 — TCF.8H fronteira do link posicional + fix nullable/presença (Ciclo 1c)

**Ticket**: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) (peças 10/11) ·
[estudo-mapa](../notas/estudo-tcf-hierarquico-mapa.md) · teoria
[cardinalidade](../notas/teoria-cardinalidade.md) (H-CARD-06). Fecha o **Ciclo 1c** (last do
Ciclo 1 — funcionalidade), teed-up pelas fronteiras SH3/SH4 do
[1b](../2026-07-06-2238-tcf8h-escala-formas-e-tipos/result.md).

## Estado

- **era**: o 1b bateu em SH3 (chave-ausente) e SH4 (null-misto) — o codec tabular supõe retângulo homogêneo.
- **foi**: caracterizadas as 4 formas que quebram o retângulo (B1–B4) no codec do 1b; prototipada a máscara.
- **é**: **B1 (presença) + B2 (nullable) = MESMO mecanismo** (máscara 3-estados = definition level do
  Dremel) — **fix provado, RT-OK**. **B3 (array-em-array)** precisa de **repetition level** (deferido).
  **B4 (N:N)** é **flat-RT-OK** — a fronteira é de normalização (tabela-ponte), não de RT (deferido). → **fecha
  o Ciclo 1 (funcionalidade)**.
- **será**: Ciclo 2 (fluxo). No welding: def-level (máscara) + rep-level (Dremel) + ponte N:N.

## As 4 fronteiras (por que quebram e o que cada uma pede)

| # | forma | no codec tabular | canal que falta |
|---|---|---|---|
| B1 | chave-ausente `[{a,b},{a}]` | CRASH (KeyError) | **presença** (bitmap/def-level) |
| B2 | null-em-coluna `[{x:1},{x:null}]` | CRASH (ValueError) | **null-mask** (nullable/def-level) |
| B3 | array-em-array `{grupos:[{itens:[…]}]}` | CORROMPE (coluna de listas) | **repetition level** (Dremel) |
| B4 | N:N `[{aluno,curso}×]` | **RT-OK (flat)** | normalização/ponte (não é gap de RT) |

## Arquivos

- `mask_codec.py` — máscara 3-estados (`.` valor / `0` null / `-` ausente) + array↔masked (o fix de B1/B2).
- `run.py` — `python run.py`: thread 1 (4 fronteiras no tabular) + thread 2 (fix RT-OK) + caracterização.
- `artifacts/` — `00-resumo` · `01-fronteiras-no-tabular` · `02-fix-mascara-presenca`.

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2246-tcf8h-fronteira-link-posicional/run.py
```

## Escopo

Dirty. NÃO toca `src/tcf`. B1/B2 provados tratáveis (máscara); B3/B4 caracterizados e **deferidos ao
welding** (rep-level + ponte). Mapeamento direto a Dremel (rep/def levels, Melnik 2010) e H-CARD-06.
