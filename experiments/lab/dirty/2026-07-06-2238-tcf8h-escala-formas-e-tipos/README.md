# 2026-07-06-2238 — TCF.8H escala de formas + decisão de tipo (Ciclo 1b)

**Ticket**: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) ·
[T-FMT-TCF8H-HEADER](../../../../tickets/T-FMT-TCF8H-HEADER.md) · hipótese
[H-TYPE-01](../notas/roadmap-hipoteses.md) · checklist
[C1/C2](../notas/tcf8h-header-checklist.md). Build-on-prior: reusa o `typed_codec` do
[Ciclo 1a](../2026-07-06-2221-tcf8h-fidelidade-tipos/). **Ciclo 1b** do caminho-feliz "fechar TCF.8".

## Estado

- **era**: o 1a fechou RT tipado com **tag explícita em toda não-string** (A). Faltava: (i) decidir tag
  explícita **vs dedução** com número (owner: "medir os dois"); (ii) escalar as formas de borda.
- **foi**: 3 estratégias de tipo implementadas (A/B/C) e medidas; 4 formas de borda escaladas.
- **é**: decisão **do número** — **C-híbrida = default** (lossless + mais barato quando números dominam);
  **A = fallback** (auditável, e menor quando strings-ambíguas dominam); **B pura descartada** (lossy
  silencioso). Formas: aninhamento fundo + array vazio **fecham RT** (funcionalidade de graça);
  chave-ausente + null-em-array-misto = **FRONTEIRA** (tabela não-retangular / coluna de tipo misto).
- **será** (1c): tratar as fronteiras (chave-ausente/null-misto/array-em-array/N:N) — **família do link
  posicional** (peça 10/11): presença (bitmap/sentinela) + nullable + repetition level.

## Threads

1. **TIPO (decisão com número)** — `01-tipos-A-B-C.txt`:
   - **A** explícita: tag i/f/b/n em toda não-string. Lossless. custo = #não-string.
   - **B** dedução pura: sem tag, deduz no decode. custo 0, mas **LOSSY** (`"01310"`→1310, `"true"`→bool, null→`""`).
   - **C** híbrida: tag só onde a dedução erraria (string-ambígua→`s`, null→`n`; número/bool que deduz certo→sem tag).
2. **FORMA (escala de borda)** — `02-formas-fronteiras.txt`: aninhamento fundo, array vazio, chave-ausente, null-em-array.

## Arquivos

- `tipos_codec.py` — as 3 estratégias (encode/decode A/B/C) sobre o `typed_codec` do 1a.
- `run.py` — `python run.py` regenera `artifacts/`.
- `artifacts/` — `00-resumo` · `01-tipos-A-B-C` (tabela+regra) · `02-formas-fronteiras` (RT vs fronteira) ·
  `03-obat-hcc-trace` (SideOutputs).

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2238-tcf8h-escala-formas-e-tipos/run.py
```

## Escopo

Dirty (engenhoca). NÃO toca `src/tcf` nem EXP-015 clean. Ponteiro de escala: `datasets/synthetic/` (CSV).
