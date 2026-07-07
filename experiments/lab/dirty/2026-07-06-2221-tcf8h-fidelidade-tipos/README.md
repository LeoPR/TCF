# 2026-07-06-2221 — TCF.8H fidelidade de tipos (Ciclo 1a)

**Ticket**: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) ·
[T-FMT-TCF8H-HEADER](../../../../tickets/T-FMT-TCF8H-HEADER.md) ·
hipótese [H-TYPE-01](../notas/roadmap-hipoteses.md) ·
checklist [C1 `:tipo`](../notas/tcf8h-header-checklist.md).
Parte do [estudo hierárquico](../notas/estudo-tcf-hierarquico-mapa.md) — **Ciclo 1a** do caminho-feliz
"fechar TCF.8" (funcionalidade primeiro).

## Estado

- **era**: o codec clean [EXP-015](../../clean/EXP-015-tcf-hierarquico-csv-json/) faz `str(v)` → JSON
  **tipado NÃO faz RT** (`30`→`"30"`, `true`→`"True"`, `null`→`"None"`). Só lossless em all-string.
- **foi**: provada a lacuna (RT=False em escalar/array tipados); forkado um `typed_codec` naive.
- **é**: **string = default (sem tag); tipo divergente leva 1 letra `i/f/b/n` colada no size** (`idade:4i`).
  Body em forma JSON-canônica (`true`/`false`, não `True`; `null` = body vazio + tag `n`). **RT-exato nos 3
  casos** (T1/T2/T3); all-string medido como menor-porém-lossy. Custo medido: +2B/+5B/+8B.
- **será** (1b): escalar formas (array vazio, `null` em array, chave ausente, aninhamento fundo) + decidir
  **tag explícita vs dedução** (`analyze_column`/`is_numeric`, zero-cost via SideOutputs); levar o achado
  "última-tipada perde a última-sem-size" pro reorder (C5).

## Achado que sai daqui

O custo líquido (+5B/+8B) é **maior que só as tags** porque, quando a **folha DFS-última é tipada**, ela
**perde a `última-folha-sem-size`** (paga `:size` + tag de volta). Isso amarra tipos ao **reorder (C5)** e
ao `SAVING(L)`: preferir deixar uma folha **string** por último minimiza o custo dos tipos.
Ver [result.md](result.md).

## Fluxo (rastreável)

```
inputs/T*.json ─obj_to_tcf(typed)→ #TCF.8H <meta c/ tags i/f/b/n>\n<bodies> ─tcf_to_obj→ obj (cast) [RT]
              └obj_to_tcf_allstr → baseline lossy (str(v)) ─────────────────────────────→ obj (str) [FALHA]
```

## Arquivos

- `typed_codec.py` — fork naive (string-default + tag de tipo na divergência). Não copia EXP-015 clean.
- `run.py` — reproduzível: `python run.py` regenera `artifacts/`.
- `inputs/` — T1 (escalares tipados), T2 (array tipado), T3 (aninhado misto).
- `artifacts/` — `00-resumo` · `01-inputs` · `02-typed.tcf.txt` (typed vs all-str) · `03-obat-hcc-trace`
  (SideOutputs.body_bytes) · `04-roundtrip` (OK/MISMATCH por caso) · `05-bytes-custo`.

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2221-tcf8h-fidelidade-tipos/run.py
```

## Escopo

Dirty (engenhoca descartável — prova a IDEIA). NÃO toca `src/tcf` nem o EXP-015 clean. Amostras minúsculas
(consistência) → a escala é o 1b.
